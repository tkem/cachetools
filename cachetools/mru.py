import collections

from cachetools.cache import Cache


class MRUCache(Cache):
    """Most Recently Used (MRU) cache implementation."""

    def __init__(self, maxsize, getsizeof=None):
        super().__init__(maxsize, getsizeof)
        self.__order = collections.OrderedDict()

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.__update(key)
        return value

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.__update(key)

    def __delitem__(self, key):
        super().__delitem__(key)
        del self.__order[key]

    def popitem(self):
        """Remove and return the `(key, value)` pair most recently used."""
        if not self.__order:
            raise KeyError(type(self).__name__ + ' cache is empty') from None

        key = next(iter(self.__order))
        return (key, self.pop(key))

    def __update(self, key):
        try:
            self.__order.move_to_end(key, last=False)
        except KeyError:
            self.__order[key] = None
