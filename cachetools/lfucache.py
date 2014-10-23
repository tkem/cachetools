from .cache import Cache
from .decorators import cachedfunc
from .lock import RLock

import operator


class LFUCache(Cache):
    """Least Frequently Used (LFU) cache implementation.

    This class counts how often an item is retrieved, and discards the
    items used least often to make space when necessary.

    """

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is None:
            Cache.__init__(self, maxsize)
        else:
            Cache.__init__(self, maxsize, lambda e: getsizeof(e[0]))
            self.getsizeof = getsizeof

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        entry = cache_getitem(self, key)
        entry[1] += 1
        return entry[0]

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, [value, 0])

    def popitem(self):
        """Remove and return the `(key, value)` pair least frequently used."""
        items = ((key, Cache.__getitem__(self, key)[1]) for key in self)
        try:
            key, _ = min(items, key=operator.itemgetter(1))
        except ValueError:
            raise KeyError('cache is empty')
        return (key, self.pop(key))


def lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Frequently Used (LFU)
    algorithm.

    """
    return cachedfunc(LFUCache(maxsize, getsizeof), typed, lock)
