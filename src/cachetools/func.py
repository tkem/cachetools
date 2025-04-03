"""`functools.lru_cache` compatible memoizing function decorators."""

__all__ = ("fifo_cache", "lfu_cache", "lru_cache", "rr_cache", "ttl_cache")

import functools
import math
import random
import time
from threading import Condition, Lock

from . import FIFOCache, LFUCache, LRUCache, RRCache, TTLCache
from . import cached
from . import keys


class _UnboundTTLCache(TTLCache):
    def __init__(self, *, ttl, timer):
        TTLCache.__init__(self, maxsize=math.inf, ttl=ttl, timer=timer)

    @property
    def maxsize(self):
        return None


def _cache(*, cache, maxsize=128, typed=False, lock=None, condition=None, info=False):
    if condition is None:
        condition = Condition()

    def decorator(func):
        key = keys.typedkey if typed else keys.hashkey
        wrapper = cached(
            cache=cache, key=key, condition=condition, info=info, lock=lock
        )(func)
        wrapper.cache_parameters = lambda: {"maxsize": maxsize, "typed": typed}
        return wrapper

    return decorator


def fifo_cache(maxsize=128, *, typed=False, lock=None, condition=None, info=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a First In First Out (FIFO)
    algorithm.

    """
    if maxsize is None:
        return _cache(
            cache={},
            maxsize=None,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )
    elif callable(maxsize):
        return _cache(
            cache=FIFOCache(maxsize=128),
            maxsize=128,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )(maxsize)
    else:
        return _cache(
            cache=FIFOCache(maxsize=maxsize),
            maxsize=maxsize,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )


def lfu_cache(maxsize=128, *, typed=False, lock=None, condition=None, info=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Frequently Used (LFU)
    algorithm.

    """
    if maxsize is None:
        return _cache(
            cache={},
            maxsize=None,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )
    elif callable(maxsize):
        return _cache(
            cache=LFUCache(maxsize=128),
            maxsize=128,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )(maxsize)
    else:
        return _cache(
            cache=LFUCache(maxsize=maxsize),
            maxsize=maxsize,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )


def lru_cache(maxsize=128, *, typed=False, lock=None, condition=None, info=False):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm.

    """
    if maxsize is None:
        return _cache(
            cache={},
            maxsize=None,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )
    elif callable(maxsize):
        return _cache(
            cache=LRUCache(maxsize=128),
            maxsize=128,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )(maxsize)
    else:
        return _cache(
            cache=LRUCache(maxsize=maxsize),
            maxsize=maxsize,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )


def rr_cache(
    maxsize=128,
    *,
    choice=random.choice,
    typed=False,
    lock=None,
    condition=None,
    info=False
):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    if maxsize is None:
        return _cache(
            cache={},
            maxsize=None,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )
    elif callable(maxsize):
        return _cache(
            cache=RRCache(maxsize=128, choice=choice),
            maxsize=128,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )(maxsize)
    else:
        return _cache(
            cache=RRCache(maxsize=maxsize, choice=choice),
            maxsize=maxsize,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )


def ttl_cache(
    maxsize=128,
    *,
    ttl=600,
    timer=time.monotonic,
    typed=False,
    lock=None,
    condition=None,
    info=False
):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm with a per-item time-to-live (TTL) value.
    """
    if maxsize is None:
        return _cache(
            cache=_UnboundTTLCache(ttl=ttl, timer=timer),
            maxsize=None,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )
    elif callable(maxsize):
        return _cache(
            cache=TTLCache(maxsize=128, ttl=ttl, timer=timer),
            maxsize=128,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )(maxsize)
    else:
        return _cache(
            cache=TTLCache(maxsize=maxsize, ttl=ttl, timer=timer),
            maxsize=maxsize,
            typed=typed,
            lock=lock,
            condition=condition,
            info=info,
        )
