from .lrucache import LRUCache
from .decorators import cachedfunc
from .link import Link
from .lock import RLock

import time

_marker = object()


class TTLCache(LRUCache):
    """Cache implementation with per-item time-to-live (TTL) value.

    This class associates a time-to-live value with each item.  Items
    that expire because they have exceeded their time-to-live will be
    removed.  If no expired items are there to remove, the least
    recently used items will be discarded first to make space when
    necessary.

    By default, the time-to-live is specified in seconds, and the
    standard :func:`time.time` function is used to retrieve the
    current time.  A custom `timer` function can be supplied if
    needed.

    """

    class ExpiredError(KeyError):
        """Raised when a cached item's time-to-live has expired.

        This is a subclass of :exc:`KeyError`.

        """
        pass

    def __init__(self, maxsize, ttl, timer=time.time, getsizeof=None):
        if getsizeof is None:
            LRUCache.__init__(self, maxsize)
        else:
            LRUCache.__init__(self, maxsize, lambda e: getsizeof(e[0]))
            self.getsizeof = getsizeof
        root = Link()
        root.prev = root.next = root
        self.__root = root
        self.__timer = timer
        self.__ttl = ttl

    def __repr__(self, cache_getitem=LRUCache.__getitem__):
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            [(key, cache_getitem(self, key)[0]) for key in self],
            self.maxsize,
            self.currsize,
        )

    def __getitem__(self, key, cache_getitem=LRUCache.__getitem__):
        value, link = cache_getitem(self, key)
        if link.data[1] < self.__timer():
            raise TTLCache.ExpiredError(key)
        return value

    def __setitem__(self, key, value,
                    cache_getitem=LRUCache.__getitem__,
                    cache_setitem=LRUCache.__setitem__,
                    cache_delitem=LRUCache.__delitem__):
        time = self.__timer()
        self.expire(time)
        try:
            _, link = cache_getitem(self, key)
        except KeyError:
            link = Link()
        cache_setitem(self, key, (value, link))
        try:
            link.prev.next = link.next
            link.next.prev = link.prev
        except AttributeError:
            pass
        root = self.__root
        link.data = (key, time + self.__ttl)
        link.prev = tail = root.prev
        link.next = root
        tail.next = root.prev = link

    def __delitem__(self, key,
                    cache_getitem=LRUCache.__getitem__,
                    cache_delitem=LRUCache.__delitem__):
        _, link = cache_getitem(self, key)
        cache_delitem(self, key)
        link.unlink()
        self.expire()

    def expire(self, time=None, cache_delitem=LRUCache.__delitem__):
        """Remove expired items from the cache."""
        if time is None:
            time = self.__timer()
        root = self.__root
        head = root.next
        while head is not root and head.data[1] < time:
            cache_delitem(self, head.data[0])
            head.next.prev = root
            head = root.next = head.next

    def pop(self, key, default=_marker):
        try:
            value, link = LRUCache.__getitem__(self, key)
        except KeyError:
            if default is _marker:
                raise
            return default
        LRUCache.__delitem__(self, key)
        link.unlink()
        self.expire()
        return value

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
