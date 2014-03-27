"""Extensible memoizing collections and decorators"""
import collections
import functools
import random

try:
    from threading import RLock
except ImportError:
    from dummy_threading import RLock

__version__ = '0.2.0'


def cache(cls):
    """Class decorator that wraps any mutable mapping to work as a
    cache."""

    class Cache(collections.MutableMapping):

        __wrapped__ = cls

        def __init__(self, maxsize, *args, **kwargs):
            self.__wrapped__ = cls(*args, **kwargs)
            self.maxsize = maxsize

        def __getitem__(self, key):
            return self.__wrapped__[key]

        def __setitem__(self, key, value):
            while len(self) >= self.maxsize:
                self.popitem()
            self.__wrapped__[key] = value

        def __delitem__(self, key):
            del self.__wrapped__[key]

        def __iter__(self):
            return iter(self.__wrapped__)

        def __len__(self):
            return len(self.__wrapped__)

        def __repr__(self):
            return '%s(%r, maxsize=%d)' % (
                self.__class__.__name__,
                self.__wrapped__,
                self.__maxsize,
            )

        @property
        def maxsize(self):
            return self.__maxsize

        @maxsize.setter
        def maxsize(self, value):
            if not value > 0:
                raise ValueError('maxsize must be > 0')
            while (len(self) > value):
                self.popitem()
            self.__maxsize = value

    # TODO: functools.update_wrapper() for class decorators?

    return Cache


class LRUCache(cache(collections.OrderedDict)):
    """Least Recently Used (LRU) cache implementation.

    Discards the least recently used items first to make space when
    necessary.

    This implementation uses :class:`collections.OrderedDict` to keep
    track of item usage.
    """

    # OrderedDict.move_to_end is only available in Python 3
    if hasattr(collections.OrderedDict, 'move_to_end'):
        def __getitem__(self, key):
            value = self.__wrapped__[key]
            self.__wrapped__.move_to_end(key)
            return value
    else:
        def __getitem__(self, key):
            value = self.__wrapped__.pop(key)
            self.__wrapped__[key] = value
            return value

    def popitem(self):
        return self.__wrapped__.popitem(False)


class LFUCache(cache(dict)):
    """Least Frequently Used (LFU) cache implementation.

    Counts how often an item is needed, and discards the items used
    least often to make space when necessary.

    This implementation uses :class:`collections.Counter` to keep
    track of usage counts.
    """

    def __init__(self, maxsize, *args, **kwargs):
        super(LFUCache, self).__init__(maxsize, *args, **kwargs)
        self.__counter = collections.Counter()

    def __getitem__(self, key):
        value = super(LFUCache, self).__getitem__(key)
        self.__counter[key] += 1
        return value

    def __setitem__(self, key, value):
        super(LFUCache, self).__setitem__(key, value)
        self.__counter[key] += 0

    def __delitem__(self, key):
        super(LFUCache, self).__delitem__(key)
        del self.__counter[key]

    def popitem(self):
        try:
            item = self.__counter.most_common()[-1]
        except IndexError:
            raise KeyError
        super(LFUCache, self).pop(item[0])
        return item


class RRCache(cache(dict)):
    """Random Replacement (RR) cache implementation.

    Randomly selects a candidate item and discards it to make space
    when necessary.

    This implementations uses :func:`random.choice` to select the item
    to be discarded.
    """

    def popitem(self):
        try:
            item = random.choice(list(self.items()))
        except IndexError:
            raise KeyError
        self.pop(item[0])
        return item


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
        count = [0, 0]

        def wrapper(*args, **kwargs):
            key = makekey(args, kwargs)
            with lock:
                try:
                    result = cache[key]
                    count[0] += 1
                    return result
                except KeyError:
                    count[1] += 1
            result = func(*args, **kwargs)
            with lock:
                cache[key] = result
            return result

        def cache_info():
            return CacheInfo(count[0], count[1], cache.maxsize, len(cache))

        def cache_clear():
            cache.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return functools.update_wrapper(wrapper, func)

    return decorator


def lru_cache(maxsize=128, typed=False, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that
    saves up to the `maxsize` most recent calls based on a Least
    Recently Used (LRU) algorithm.
    """
    if typed:
        return _cachedfunc(LRUCache(maxsize), _makekey_typed, lock())
    else:
        return _cachedfunc(LRUCache(maxsize), _makekey, lock())


def lfu_cache(maxsize=128, typed=False, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that
    saves up to the `maxsize` most recent calls based on a Least
    Frequently Used (LFU) algorithm.
    """
    if typed:
        return _cachedfunc(LFUCache(maxsize), _makekey_typed, lock())
    else:
        return _cachedfunc(LFUCache(maxsize), _makekey, lock())


def rr_cache(maxsize=128, typed=False, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that
    saves up to the `maxsize` most recent calls based on a Random
    Replacement (RR) algorithm.
    """
    if typed:
        return _cachedfunc(RRCache(maxsize), _makekey_typed, lock())
    else:
        return _cachedfunc(RRCache(maxsize), _makekey, lock())
