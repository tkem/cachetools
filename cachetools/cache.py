from __future__ import absolute_import

from .abc import DefaultMapping

from collections import MutableMapping

class _DefaultSize(object):
    def __getitem__(self, _):
        return 1

    def __setitem__(self, _, value):
        assert value == 1

    def pop(self, _):
        return 1

class CacheDict(MutableMapping):

    def __init__(self):
        self.store = dict()
        self.size = 0

    def __setitem__(self, key, item):
        self.store[key] = item

    def __getitem__(self, key):
        return self.store[key]

    def __len__(self):
        return len(self.store)

    def __delitem__(self, key):
        del self.store[key]

    def items(self):
        return self.store.items()

    def __iter__(self):
        return iter(self.store)


class Cache(DefaultMapping):
    """Mutable mapping to serve as a simple cache or cache base class."""

    __size = _DefaultSize()

    def __init__(self, maxsize, missing=None, getsizeof=None, data=None):
        if missing:
            self.__missing = missing
        if getsizeof:
            self.__getsizeof = getsizeof
            self.__size = dict()
        if data is None or not isinstance(data, CacheDict):
            self.__data = CacheDict()
        else:
            self.__data = data
        self.__maxsize = maxsize

    def __repr__(self):
        return '%s(%r, maxsize=%r, currsize=%r)' % (
            self.__class__.__name__,
            list(self.__data.items()),
            self.__maxsize,
            self.__data.size,
        )

    def __getitem__(self, key):
        try:
            return self.__data[key]
        except KeyError:
            return self.__missing__(key)

    def __setitem__(self, key, value):
        maxsize = self.__maxsize
        size = self.getsizeof(value)
        if size > maxsize:
            raise ValueError('value too large')
        if key not in self.__data or self.__size[key] < size:
            while self.__data.size + size > maxsize:
                self.popitem()
        if key in self.__data:
            diffsize = size - self.__size[key]
        else:
            diffsize = size
        self.__data[key] = value
        self.__size[key] = size
        self.__data.size += diffsize

    def __delitem__(self, key):
        size = self.__size.pop(key)
        del self.__data[key]
        self.__data.size -= size

    def __contains__(self, key):
        return key in self.__data

    def __missing__(self, key):
        value = self.__missing(key)
        try:
            self.__setitem__(key, value)
        except ValueError:
            pass  # value too large
        return value

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    @staticmethod
    def __getsizeof(value):
        return 1

    @staticmethod
    def __missing(key):
        raise KeyError(key)

    @property
    def maxsize(self):
        """The maximum size of the cache."""
        return self.__maxsize

    @property
    def currsize(self):
        """The current size of the cache."""
        return self.__data.size

    @property
    def data(self):
        """The data of the cache (CacheDict)."""
        return self.__data

    def getsizeof(self, value):
        """Return the size of a cache element's value."""
        return self.__getsizeof(value)
