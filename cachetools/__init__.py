"""Extensible memoizing collections and decorators"""

import functools

from .base import Cache
from .func import lfu_cache, lru_cache, rr_cache, ttl_cache
from .keys import hashkey, typedkey
from .lfu import LFUCache
from .lru import LRUCache
from .rr import RRCache
from .ttl import TTLCache

__all__ = (
    'Cache', 'LFUCache', 'LRUCache', 'RRCache', 'TTLCache',
    'cache', 'cachedmethod', 'hashkey', 'typedkey',
    # make cachetools.func.* available for backwards compatibility
    'lfu_cache', 'lru_cache', 'rr_cache', 'ttl_cache',
)

__version__ = '1.0.3'


def cache(cache, key=hashkey, lock=None):
    """Decorator to wrap a function with a memoizing callable that saves
    results in a cache.

    """
    def decorator(func):
        if cache is None:
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
        elif lock is None:
            def wrapper(*args, **kwargs):
                k = key(*args, **kwargs)
                try:
                    return cache[k]
                except KeyError:
                    pass  # key not found
                v = func(*args, **kwargs)
                try:
                    cache[k] = v
                except ValueError:
                    pass  # value too large
                return v
        else:
            def wrapper(*args, **kwargs):
                k = key(*args, **kwargs)
                try:
                    with lock:
                        return cache[k]
                except KeyError:
                    pass  # key not found
                v = func(*args, **kwargs)
                try:
                    with lock:
                        cache[k] = v
                except ValueError:
                    pass  # value too large
                return v
        functools.update_wrapper(wrapper, func)
        if not hasattr(wrapper, '__wrapped__'):
            wrapper.__wrapped__ = func  # Python < 3.2
        return wrapper
    return decorator


def cachedmethod(cache, typed=False):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a (possibly shared) cache.

    """
    key = typedkey if typed else hashkey

    def decorator(method):
        def wrapper(self, *args, **kwargs):
            c = cache(self)
            if c is None:
                return method(self, *args, **kwargs)
            k = key(method, *args, **kwargs)
            try:
                return c[k]
            except KeyError:
                pass  # key not found
            v = method(self, *args, **kwargs)
            try:
                c[k] = v
            except ValueError:
                pass  # value too large
            return v

        wrapper.cache = cache
        return functools.update_wrapper(wrapper, method)

    return decorator
