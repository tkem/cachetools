import collections
import operator

from .base import Cache


class LFUCache(Cache):
    """Least Frequently Used (LFU) cache implementation."""

    def __init__(self, maxsize, missing=None, getsizeof=None, callback=None):
        Cache.__init__(self, maxsize, missing, getsizeof, callback)
        self.__counter = collections.Counter()

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value = cache_getitem(self, key)
        self.__counter[key] += 1
        return value

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        self.__counter[key] += 1

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        del self.__counter[key]

    def popitem(self):
        """Remove and return the `(key, value)` pair least frequently used."""
        try:
            key = min(self.__counter.items(), key=operator.itemgetter(1))[0]
        except ValueError:
            raise KeyError('cache is empty')
        return key, self.pop(key)
