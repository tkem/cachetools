import collections


class Cache(collections.MutableMapping):
    """Mutable mapping to serve as a simple cache or cache base class."""

    def __init__(self, maxsize, missing=None, getsizeof=None):
        self.__data = dict()
        self.__currsize = 0
        self.__maxsize = maxsize
        self.__missing = missing
        self.__getsizeof = getsizeof

    def __repr__(self):
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            list(self.items()),
            self.__maxsize,
            self.__currsize,
        )

    def __getitem__(self, key):
        try:
            return self.__data[key][0]
        except KeyError:
            return self.__missing__(key)

    def __setitem__(self, key, value):
        data = self.__data
        maxsize = self.__maxsize
        size = 1 if self.__getsizeof is None else self.__getsizeof(value)
        if size > maxsize:
            raise ValueError('value too large')
        if key not in data or data[key][1] < size:
            while self.__currsize + size > maxsize:
                self.popitem()
        if key in data:
            diffsize = size - data[key][1]
        else:
            diffsize = size
        data[key] = (value, size)
        self.__currsize += diffsize

    def __delitem__(self, key):
        _, size = self.__data.pop(key)
        self.__currsize -= size

    def __contains__(self, key):
        return key in self.__data

    def __missing__(self, key):
        missing = self.__missing
        if missing:
            # return value as stored in data!
            self.__setitem__(key, missing(key))
            return self.__data[key][0]
        else:
            raise KeyError(key)

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    @property
    def maxsize(self):
        """The maximum size of the cache."""
        return self.__maxsize

    @property
    def currsize(self):
        """The current size of the cache."""
        return self.__currsize

    def getsizeof(self, value):
        """Return the size of a cache element's value."""
        if self.__getsizeof:
            return self.__getsizeof(value)
        return 1

    # collections.MutableMapping mixin methods do not handle __missing__

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default

    __marker = object()

    def pop(self, key, default=__marker):
        if key in self:
            value = self[key]
            del self[key]
            return value
        elif default is self.__marker:
            raise KeyError(key)
        else:
            return default

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]
