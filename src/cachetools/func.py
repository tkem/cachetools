"""`functools.lru_cache` compatible memoizing function decorators."""

__all__ = ("fifo_cache", "lfu_cache", "lru_cache", "rr_cache", "ttl_cache")

import math
import random
import time
from threading import Condition

from . import FIFOCache, LFUCache, LRUCache, RRCache, TTLCache, cached, keys


class _UnboundTTLCache(TTLCache):
    def __init__(self, ttl, timer):
        TTLCache.__init__(self, math.inf, ttl, timer)

    @property
    def maxsize(self):  # type: ignore
        return None


def _cache(cache_factory, maxsize, typed):
    if maxsize is not None and maxsize < 0:
        raise ValueError("maxsize must be non-negative")

    def decorator(func):
        # like functools.lru_cache, this has to be thread-safe;
        # additionally, this also prevents cache stampede scenarios
        # using a condition variable
        key = keys.typedkey if typed else keys.hashkey
        wrapper = cached(
            cache=cache_factory(), key=key, condition=Condition(), info=True
        )(func)
        wrapper.cache_parameters = lambda: {"maxsize": maxsize, "typed": typed}  # type: ignore
        return wrapper

    return decorator


def fifo_cache(maxsize=128, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a First In First Out (FIFO)
    algorithm.

    """
    if maxsize is None:
        return _cache(dict, None, typed)
    elif callable(maxsize):
        return _cache(lambda: FIFOCache(128), 128, typed)(maxsize)
    else:
        return _cache(lambda: FIFOCache(maxsize), maxsize, typed)


def lfu_cache(maxsize=128, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Frequently Used (LFU)
    algorithm.

    """
    if maxsize is None:
        return _cache(dict, None, typed)
    elif callable(maxsize):
        return _cache(lambda: LFUCache(128), 128, typed)(maxsize)
    else:
        return _cache(lambda: LFUCache(maxsize), maxsize, typed)


def lru_cache(maxsize=128, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm.

    """
    if maxsize is None:
        return _cache(dict, None, typed)
    elif callable(maxsize):
        return _cache(lambda: LRUCache(128), 128, typed)(maxsize)
    else:
        return _cache(lambda: LRUCache(maxsize), maxsize, typed)


def rr_cache(maxsize=128, choice=random.choice, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    if maxsize is None:
        return _cache(dict, None, typed)
    elif callable(maxsize):
        return _cache(lambda: RRCache(128, choice), 128, typed)(maxsize)
    else:
        return _cache(lambda: RRCache(maxsize, choice), maxsize, typed)


def ttl_cache(maxsize=128, ttl=600, timer=time.monotonic, typed=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm with a per-item time-to-live (TTL) value.

    """
    if maxsize is None:
        return _cache(lambda: _UnboundTTLCache(ttl, timer), None, typed)
    elif callable(maxsize):
        return _cache(lambda: TTLCache(128, ttl, timer), 128, typed)(maxsize)
    else:
        return _cache(lambda: TTLCache(maxsize, ttl, timer), maxsize, typed)
