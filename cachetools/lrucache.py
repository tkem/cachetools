from .cache import Cache
from .decorators import cachedfunc
from .link import Link
from .lock import RLock


class LRUCache(Cache):
    """Least Recently Used (LRU) cache implementation.

    This class discards the least recently used items first to make
    space when necessary.

    """

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is None:
            Cache.__init__(self, maxsize)
        else:
            Cache.__init__(self, maxsize, lambda e: getsizeof(e[0]))
            self.getsizeof = getsizeof
        root = Link()
        root.prev = root.next = root
        self.__root = root

    def __repr__(self, cache_getitem=Cache.__getitem__):
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            [(key, cache_getitem(self, key)[0]) for key in self],
            self.maxsize,
            self.currsize,
        )

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value, link = cache_getitem(self, key)
        root = self.__root
        link.prev.next = link.next
        link.next.prev = link.prev
        link.prev = tail = root.prev
        link.next = root
        tail.next = root.prev = link
        return value

    def __setitem__(self, key, value,
                    cache_getitem=Cache.__getitem__,
                    cache_setitem=Cache.__setitem__):
        try:
            _, link = cache_getitem(self, key)
        except KeyError:
            link = Link()
        cache_setitem(self, key, (value, link))
        try:
            link.prev.next = link.next
            link.next.prev = link.prev
        except AttributeError:
            link.data = key
        root = self.__root
        link.prev = tail = root.prev
        link.next = root
        tail.next = root.prev = link

    def __delitem__(self, key,
                    cache_getitem=Cache.__getitem__,
                    cache_delitem=Cache.__delitem__):
        _, link = cache_getitem(self, key)
        cache_delitem(self, key)
        link.unlink()

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used."""
        root = self.__root
        link = root.next
        if link is root:
            raise KeyError('cache is empty')
        key = link.data
        return (key, self.pop(key))


def lru_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm.

    """
    return cachedfunc(LRUCache(maxsize, getsizeof), typed, lock)
