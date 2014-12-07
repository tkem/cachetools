from .cache import Cache
from .decorators import cachedfunc
from .lock import RLock

import time


class Link(object):

    __slots__ = (
        'key', 'value', 'expire', 'size',
        'ttl_prev', 'ttl_next',
        'lru_prev', 'lru_next'
    )

    def getsize(self):
        return self.size

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

    def __init__(self, maxsize, ttl, timer=time.time, missing=None,
                 getsizeof=None):
        if getsizeof is not None:
            Cache.__init__(self, maxsize, missing, Link.getsize)
            self.getsizeof = getsizeof
        else:
            Cache.__init__(self, maxsize, missing)
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

    def __getitem__(self, key,
                    cache_getitem=Cache.__getitem__,
                    cache_missing=Cache.__missing__):
        link = cache_getitem(self, key)
        if link.expire < self.__timer():
            return cache_missing(self, key).value
        next = link.lru_next
        prev = link.lru_prev
        prev.lru_next = next
        next.lru_prev = prev
        link.lru_next = root = self.__root
        link.lru_prev = tail = root.lru_prev
        tail.lru_next = root.lru_prev = link
        return link.value

    def __setitem__(self, key, value,
                    cache_contains=Cache.__contains__,
                    cache_getitem=Cache.__getitem__,
                    cache_setitem=Cache.__setitem__):
        time = self.__timer()
        self.expire(time)
        if cache_contains(self, key):
            oldlink = cache_getitem(self, key)
        else:
            oldlink = None
        link = Link()
        link.key = key
        link.value = value
        link.expire = time + self.__ttl
        link.size = self.getsizeof(value)
        cache_setitem(self, key, link)
        if oldlink:
            oldlink.unlink()
        link.ttl_next = root = self.__root
        link.ttl_prev = tail = root.ttl_prev
        tail.ttl_next = root.ttl_prev = link
        link.lru_next = root
        link.lru_prev = tail = root.lru_prev
        tail.lru_next = root.lru_prev = link

    def __delitem__(self, key,
                    cache_contains=Cache.__contains__,
                    cache_getitem=Cache.__getitem__,
                    cache_delitem=Cache.__delitem__):
        if not cache_contains(self, key):
            raise KeyError(key)
        link = cache_getitem(self, key)
        cache_delitem(self, key)
        link.unlink()
        self.expire()

    def __contains__(self, key,
                     cache_contains=Cache.__contains__,
                     cache_getitem=Cache.__getitem__):
        if not cache_contains(self, key):
            return False
        elif cache_getitem(self, key).expire < self.__timer():
            return False
        else:
            return True

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
        expired = 0
        time = self.__timer()
        root = self.__root
        head = root.ttl_next
        while head is not root and head.expire < time:
            expired += head.size
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
