from .cache import Cache
from .decorators import cachedfunc
from .lock import RLock

import time


class Link(object):

    __slots__ = (
        'key', 'value', 'expire',
        'ttl_prev', 'ttl_next',
        'lru_prev', 'lru_next'
    )

    def unlink(self):
        ttl_next = self.ttl_next
        ttl_prev = self.ttl_prev
        ttl_prev.ttl_next = ttl_next
        ttl_next.ttl_prev = ttl_prev

        lru_next = self.lru_next
        lru_prev = self.lru_prev
        lru_prev.lru_next = lru_next
        lru_next.lru_prev = lru_prev


class TTLCache(Cache):
    """LRU Cache implementation with per-item time-to-live (TTL) value.

    This class associates a time-to-live value with each item.  Items
    that expire because they have exceeded their time-to-live will be
    removed.  If no expired items are there to remove, the least
    recently used items will be discarded first to make space when
    necessary.  Trying to access an expired item will raise a
    :exc:`KeyError`.

    By default, the time-to-live is specified in seconds, and the
    standard :func:`time.time` function is used to retrieve the
    current time.  A custom `timer` function can be supplied if
    needed.

    """

    ExpiredError = KeyError  # deprecated

    def __init__(self, maxsize, ttl, timer=time.time, getsizeof=None):
        if getsizeof is None:
            Cache.__init__(self, maxsize)
        else:
            Cache.__init__(self, maxsize, lambda e: getsizeof(e.value))
            self.getsizeof = getsizeof
        self.__root = root = Link()
        root.ttl_prev = root.ttl_next = root
        root.lru_prev = root.lru_next = root
        self.__timer = timer
        self.__ttl = ttl

    def __repr__(self, cache_getitem=Cache.__getitem__):
        # prevent item reordering/expiration
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            [(key, cache_getitem(self, key).value) for key in self],
            self.maxsize,
            self.currsize,
        )

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        link = cache_getitem(self, key)
        if link.expire < self.__timer():
            raise KeyError(key)
        next = link.lru_next
        prev = link.lru_prev
        prev.lru_next = next
        next.lru_prev = prev
        link.lru_next = root = self.__root
        link.lru_prev = tail = root.lru_prev
        tail.lru_next = root.lru_prev = link
        return link.value

    def __setitem__(self, key, value,
                    cache_getitem=Cache.__getitem__,
                    cache_setitem=Cache.__setitem__):
        time = self.__timer()
        self.expire(time)
        try:
            oldlink = cache_getitem(self, key)
        except KeyError:
            oldlink = None
        link = Link()
        link.key = key
        link.value = value
        link.expire = time + self.__ttl
        cache_setitem(self, key, link)
        if oldlink:
            oldlink.unlink()
        root = self.__root
        link.ttl_next = root
        link.ttl_prev = tail = root.ttl_prev
        tail.ttl_next = root.ttl_prev = link
        link.lru_next = root
        link.lru_prev = tail = root.lru_prev
        tail.lru_next = root.lru_prev = link

    def __delitem__(self, key,
                    cache_getitem=Cache.__getitem__,
                    cache_delitem=Cache.__delitem__):
        link = cache_getitem(self, key)
        cache_delitem(self, key)
        link.unlink()
        self.expire()

    def __iter__(self):
        timer = self.__timer
        root = self.__root
        curr = root.ttl_next
        while curr is not root:
            if not (curr.expire < timer()):
                yield curr.key
            curr = curr.ttl_next

    def __len__(self, cache_len=Cache.__len__):
        expired = 0
        time = self.__timer()
        root = self.__root
        head = root.ttl_next
        while head is not root and head.expire < time:
            expired += 1
            head = head.ttl_next
        return cache_len(self) - expired

    def expire(self, time=None):
        """Remove expired items from the cache.

        If `time` is not :const:`None`, remove all items whose
        time-to-live would have expired by `time`.

        """
        if time is None:
            time = self.__timer()
        root = self.__root
        head = root.ttl_next
        cache_delitem = Cache.__delitem__
        while head is not root and head.expire < time:
            cache_delitem(self, head.key)
            next = head.ttl_next
            head.unlink()
            head = next

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used."""
        root = self.__root
        link = root.lru_next
        if link is root:
            raise KeyError('cache is empty')
        key = link.key
        Cache.__delitem__(self, key)
        link.unlink()
        return (key, link.value)

    @property
    def currsize(self):
        getsize = Cache._getitemsize  # TODO: decide on final interface
        expired = 0
        time = self.__timer()
        root = self.__root
        head = root.ttl_next
        while head is not root and head.expire < time:
            expired += getsize(self, head.key)
            head = head.ttl_next
        return super(TTLCache, self).currsize - expired

    @property
    def timer(self):
        """Return the timer used by the cache."""
        return self.__timer

    @property
    def ttl(self):
        """Return the time-to-live of the cache."""
        return self.__ttl


def ttl_cache(maxsize=128, ttl=600, timer=time.time, typed=False,
              getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm with a per-item time-to-live (TTL) value.
    """
    return cachedfunc(TTLCache(maxsize, ttl, timer, getsizeof), typed, lock)
