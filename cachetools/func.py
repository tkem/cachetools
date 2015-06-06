import collections
import functools
import random
import time

from .lfu import LFUCache
from .lru import LRUCache
from .rr import RRCache
from .ttl import TTLCache

try:
    from threading import RLock
except ImportError:
    from dummy_threading import RLock


_CacheInfo = collections.namedtuple('CacheInfo', [
    'hits', 'misses', 'maxsize', 'currsize'
])


class _NullContext:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


_nullcontext = _NullContext()


def _makekey_untyped(args, kwargs):
    return (args, tuple(sorted(kwargs.items())))


def _makekey_typed(args, kwargs):
    key = _makekey_untyped(args, kwargs)
    key += tuple(type(v) for v in args)
    key += tuple(type(v) for _, v in sorted(kwargs.items()))
    return key


def _cachedfunc(cache, typed=False, lock=None):
    makekey = _makekey_typed if typed else _makekey_untyped
    context = lock() if lock else _nullcontext

    def decorator(func):
        stats = [0, 0]

        def wrapper(*args, **kwargs):
            key = makekey(args, kwargs)
            with context:
                try:
                    result = cache[key]
                    stats[0] += 1
                    return result
                except KeyError:
                    stats[1] += 1
            result = func(*args, **kwargs)
            with context:
                try:
                    cache[key] = result
                except ValueError:
                    pass  # value too large
            return result

        def cache_info():
            with context:
                hits, misses = stats
                maxsize = cache.maxsize
                currsize = cache.currsize
            return _CacheInfo(hits, misses, maxsize, currsize)

        def cache_clear():
            with context:
                cache.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return functools.update_wrapper(wrapper, func)

    return decorator


def lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Frequently Used (LFU)
    algorithm.

    """
    return _cachedfunc(LFUCache(maxsize, getsizeof), typed, lock)


def lru_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm.

    """
    return _cachedfunc(LRUCache(maxsize, getsizeof), typed, lock)


def rr_cache(maxsize=128, choice=random.choice, typed=False, getsizeof=None,
             lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    return _cachedfunc(RRCache(maxsize, choice, getsizeof), typed, lock)


def ttl_cache(maxsize=128, ttl=600, timer=time.time, typed=False,
              getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm with a per-item time-to-live (TTL) value.
    """
    return _cachedfunc(TTLCache(maxsize, ttl, timer, getsizeof), typed, lock)
