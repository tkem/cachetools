"""`functools.lru_cache` compatible memoizing function decorators."""

__all__ = ("fifo_cache", "lfu_cache", "lru_cache", "mru_cache", "rr_cache", "ttl_cache")

import functools
import math
import random
import time

try:
    from threading import Condition
except ImportError:  # pragma: no cover
    from dummy_threading import Condition

from . import FIFOCache, LFUCache, LRUCache, MRUCache, RRCache, TTLCache
from . import _CacheInfo
from . import keys


class _UnboundTTLCache(TTLCache):
    def __init__(self, ttl, timer):
        TTLCache.__init__(self, math.inf, ttl, timer)

    @property
    def maxsize(self):
        return None


def _cache(cache, maxsize, typed):
    key = keys.typedkey if typed else keys.hashkey

    def decorator(func):
        cond = Condition()
        pending = set()
        hits = misses = 0

        def wrapper(*args, **kwargs):
            nonlocal hits, misses
            k = key(*args, **kwargs)
            with cond:
                cond.wait_for(lambda: k not in pending)
                try:
                    result = cache[k]
                    hits += 1
                    return result
                except KeyError:
                    pass
                misses += 1
                pending.add(k)
            try:
                v = func(*args, **kwargs)
                try:
                    with cond:
                        cache[k] = v
                except ValueError:
                    pass  # value too large
                return v
            finally:
                with cond:
                    pending.remove(k)
                    cond.notify_all()

        def cache_clear():
            nonlocal hits, misses
            with cond:
                cache.clear()
                hits = misses = 0

        if isinstance(cache, dict):

            def cache_info():
                with cond:
                    return _CacheInfo(hits, misses, None, len(cache))

        else:

            def cache_info():
                with cond:
                    return _CacheInfo(hits, misses, cache.maxsize, cache.currsize)

        wrapper.cache = cache
        wrapper.cache_key = key
        wrapper.cache_lock = cond
        wrapper.cache_clear = cache_clear
        wrapper.cache_info = cache_info
        wrapper.cache_parameters = lambda: {"maxsize": maxsize, "typed": typed}

        return functools.update_wrapper(wrapper, func)

    return decorator


def fifo_cache(maxsize=128, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a First In First Out (FIFO)
    algorithm.

    """
    if maxsize is None:
        return _cache({}, None, typed)
    elif callable(maxsize):
        return _cache(FIFOCache(128), 128, typed)(maxsize)
    else:
        return _cache(FIFOCache(maxsize), maxsize, typed)


def lfu_cache(maxsize=128, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Frequently Used (LFU)
    algorithm.

    """
    if maxsize is None:
        return _cache({}, None, typed)
    elif callable(maxsize):
        return _cache(LFUCache(128), 128, typed)(maxsize)
    else:
        return _cache(LFUCache(maxsize), maxsize, typed)


def lru_cache(maxsize=128, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm.

    """
    if maxsize is None:
        return _cache({}, None, typed)
    elif callable(maxsize):
        return _cache(LRUCache(128), 128, typed)(maxsize)
    else:
        return _cache(LRUCache(maxsize), maxsize, typed)


def mru_cache(maxsize=128, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Most Recently Used (MRU)
    algorithm.
    """
    from warnings import warn

    warn("@mru_cache is deprecated", DeprecationWarning, stacklevel=2)

    if maxsize is None:
        return _cache({}, None, typed)
    elif callable(maxsize):
        return _cache(MRUCache(128), 128, typed)(maxsize)
    else:
        return _cache(MRUCache(maxsize), maxsize, typed)


def rr_cache(maxsize=128, choice=random.choice, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    if maxsize is None:
        return _cache({}, None, typed)
    elif callable(maxsize):
        return _cache(RRCache(128, choice), 128, typed)(maxsize)
    else:
        return _cache(RRCache(maxsize, choice), maxsize, typed)


def ttl_cache(maxsize=128, ttl=600, timer=time.monotonic, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm with a per-item time-to-live (TTL) value.
    """
    if maxsize is None:
        return _cache(_UnboundTTLCache(ttl, timer), None, typed)
    elif callable(maxsize):
        return _cache(TTLCache(128, ttl, timer), 128, typed)(maxsize)
    else:
        return _cache(TTLCache(maxsize, ttl, timer), maxsize, typed)
