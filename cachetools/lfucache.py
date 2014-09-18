from .cache import Cache

import operator


class LFUCache(Cache):
    """Least Frequently Used (LFU) cache implementation.

    This class counts how often an item is retrieved, and discards the
    items used least often to make space when necessary.

    """

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is not None:
            Cache.__init__(self, maxsize, lambda e: getsizeof(e[0]))
        else:
            Cache.__init__(self, maxsize)

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
