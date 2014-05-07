"""Extensible memoizing collections and decorators"""

import collections
import functools
import operator
import random

try:
    from threading import RLock
except ImportError:
    from dummy_threading import RLock

__version__ = '0.3.1'


class _Cache(collections.MutableMapping):
    """Class that wraps a mutable mapping to work as a cache."""

    def __init__(self, mapping, maxsize):
        self.__data = mapping
        self.__size = sum(map(self.getsizeof, mapping.values()), 0)
        self.maxsize = maxsize

    def __getitem__(self, key):
        return self.__data[key]

    def __setitem__(self, key, value):
        size = self.getsizeof(value)
        if size > self.maxsize:
            raise ValueError
        while self.size > self.maxsize - size:
            self.pop(next(iter(self)))
        self.__data[key] = value
        self.__size += size

    def __delitem__(self, key):
        self.__size -= self.getsizeof(self.__data.pop(key))

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __repr__(self):
        return '%s(%r, size=%d, maxsize=%d)' % (
            self.__class__.__name__,
            self.__data,
            self.__size,
            self.__maxsize,
        )

    @property
    def size(self):
        return self.__size

    @property
    def maxsize(self):
        return self.__maxsize

    @maxsize.setter
    def maxsize(self, value):
        while self.size > value:
            self.pop(next(iter(self)))
        self.__maxsize = value

    @staticmethod
    def getsizeof(_):
        return 1


class LRUCache(_Cache):
    """Least Recently Used (LRU) cache implementation.

    Discards the least recently used items first to make space when
    necessary.

    This implementation uses :class:`collections.OrderedDict` to keep
    track of item usage.
    """

    class OrderedDict(collections.OrderedDict):
        # OrderedDict.move_to_end is only available in Python 3
        if hasattr(collections.OrderedDict, 'move_to_end'):
            def __getitem__(self, key,
                            getitem=collections.OrderedDict.__getitem__):
                self.move_to_end(key)
                return getitem(self, key)
        else:
            def __getitem__(self, key,
                            getitem=collections.OrderedDict.__getitem__,
                            delitem=collections.OrderedDict.__delitem__,
                            setitem=collections.OrderedDict.__setitem__):
                value = getitem(self, key)
                delitem(self, key)
                setitem(self, key, value)
                return value

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is not None:
            self.getsizeof = getsizeof
        _Cache.__init__(self, self.OrderedDict(), maxsize)


class LFUCache(_Cache):
    """Least Frequently Used (LFU) cache implementation.

    Counts how often an item is needed, and discards the items used
    least often to make space when necessary.

    This implementation uses :class:`collections.Counter` to keep
    track of usage counts.
    """

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is not None:
            self.getsizeof = getsizeof
        _Cache.__init__(self, {}, maxsize)
        self.__counter = collections.Counter()

    def __getitem__(self, key):
        value = _Cache.__getitem__(self, key)
        self.__counter[key] += 1
        return value

    def __setitem__(self, key, value):
        _Cache.__setitem__(self, key, value)
        self.__counter[key] += 0

    def __delitem__(self, key):
        _Cache.__delitem__(self, key)
        del self.__counter[key]

    def __iter__(self):
        items = reversed(self.__counter.most_common())
        return iter(map(operator.itemgetter(0), items))


class RRCache(_Cache):
    """Random Replacement (RR) cache implementation.

    Randomly selects candidate items and discards then to make space
    when necessary.

    This implementations uses :func:`random.shuffle` to select the
    items to be discarded.
    """

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is not None:
            self.getsizeof = getsizeof
        _Cache.__init__(self, {}, maxsize)

    def __iter__(self):
        keys = list(_Cache.__iter__(self))
        random.shuffle(keys)
        return iter(keys)


CacheInfo = collections.namedtuple('CacheInfo', 'hits misses maxsize currsize')


def _makekey(args, kwargs):
    return (args, tuple(sorted(kwargs.items())))


def _makekey_typed(args, kwargs):
    key = _makekey(args, kwargs)
    key += tuple(type(v) for v in args)
    key += tuple(type(v) for k, v in sorted(kwargs.items()))
    return key


def _cachedfunc(cache, makekey, lock):
    def decorator(func):
        stats = [0, 0]

        def wrapper(*args, **kwargs):
            key = makekey(args, kwargs)
            with lock:
                try:
                    result = cache[key]
                    stats[0] += 1
                    return result
                except KeyError:
                    stats[1] += 1
            result = func(*args, **kwargs)
            with lock:
                cache[key] = result
            return result

        def cache_info():
            with lock:
                return CacheInfo(stats[0], stats[1], cache.maxsize, cache.size)

        def cache_clear():
            with lock:
                cache.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return functools.update_wrapper(wrapper, func)

    return decorator


def _cachedmeth(getcache, makekey, lock):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            key = makekey((func,) + args, kwargs)
            cache = getcache(self)
            with lock:
                try:
                    return cache[key]
                except KeyError:
                    pass
            result = func(self, *args, **kwargs)
            with lock:
                cache[key] = result
            return result

        return functools.update_wrapper(wrapper, func)

    return decorator


def lru_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(LRUCache(maxsize, getsizeof), makekey, lock())


def lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Frequently Used (LFU)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(LFUCache(maxsize, getsizeof), makekey, lock())


def rr_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(RRCache(maxsize, getsizeof), makekey, lock())


def cachedmethod(getcache, typed=False, lock=RLock):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a (possibly shared) cache.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedmeth(getcache, makekey, lock())
