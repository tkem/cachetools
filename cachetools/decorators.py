from .rrcache import RRCache
from .lfucache import LFUCache
from .lrucache import LRUCache

import collections
import functools

try:
    from threading import RLock
except ImportError:
    from dummy_threading import RLock

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
                hits, misses = stats
                maxsize = cache.maxsize
                currsize = cache.currsize
            return CacheInfo(hits, misses, maxsize, currsize)

        def cache_clear():
            with lock:
                cache.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return functools.update_wrapper(wrapper, func)

    return decorator


def rr_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(RRCache(maxsize, getsizeof), makekey, lock())


def lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Frequently Used (LFU)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(LFUCache(maxsize, getsizeof), makekey, lock())


def lru_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(LRUCache(maxsize, getsizeof), makekey, lock())


def cachedmethod(cache, typed=False):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a (possibly shared) cache.

    """
    makekey = _makekey_typed if typed else _makekey

    def decorator(method):
        def wrapper(self, *args, **kwargs):
            # TODO: `shared`, locking...
            key = makekey((method,) + args, kwargs)
            mapping = cache(self)
            try:
                return mapping[key]
            except KeyError:
                pass
            result = method(self, *args, **kwargs)
            mapping[key] = result
            return result

        return functools.update_wrapper(wrapper, method)

    return decorator
