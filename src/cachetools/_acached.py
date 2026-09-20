"""Asynchronous function decorator helpers."""

__all__ = ()

import functools

# TODO: How to handle cache stampede issues?
#
# Option 1: Store futures early in the cache, so repeatedly accessing
# the same key while the async function is still executing returns the
# same future.  This seems to be how it's implemented in
# cachetools-async async-lru.
#
# Option 2: Use asyncio.Condition to guard access to a "pending" set
# of keys, similar to how this is implemendted in @cachedmethod.


def _acache_info(func, cache, key, info):
    hits = misses = 0

    async def wrapper(*args, **kwargs):
        nonlocal hits, misses
        k = key(*args, **kwargs)
        try:
            result = cache[k]
            hits += 1
            return result
        except KeyError:
            misses += 1
        v = await func(*args, **kwargs)
        try:
            cache[k] = v
        except ValueError:
            pass  # value too large
        return v

    def cache_clear():
        nonlocal hits, misses
        cache.clear()
        hits = misses = 0

    def cache_info():
        return info(hits, misses)

    wrapper.cache_clear = cache_clear
    wrapper.cache_info = cache_info
    return wrapper


def _acache(func, cache, key):
    async def wrapper(*args, **kwargs):
        k = key(*args, **kwargs)
        try:
            return cache[k]
        except KeyError:
            pass  # key not found
        v = await func(*args, **kwargs)
        try:
            cache[k] = v
        except ValueError:
            pass  # value too large
        return v

    wrapper.cache_clear = lambda: cache.clear()
    return wrapper


def _wrapper(func, cache, key, info=None):
    if info is not None:
        wrapper = _acache_info(func, cache, key, info)
    else:
        wrapper = _acache(func, cache, key)
    wrapper.cache = cache
    wrapper.cache_key = key
    return functools.update_wrapper(wrapper, func)
