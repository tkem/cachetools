"""Asynchronous memoizing decorators."""

__all__ = ("acached", "acachedmethod")

from . import CacheInfo, keys


# require to pass "info" as kwargs for now for future extensions
def acached(cache, key=keys.hashkey, *, info=False):
    """Decorator to wrap a coroutine with a memoizing callable that
    saves results in a cache.

    """
    from ._acached import _wrapper

    if cache is None:
        raise TypeError("cache must not be None")

    def decorator(func):
        # FIXME: assert func is awaitable?
        make_info = CacheInfo.maker(cache) if info else None  # type: ignore
        return _wrapper(func, cache, key, make_info)

    return decorator


# require to pass "info" as kwargs for now for future extensions
def acachedmethod(cache, key=keys.methodkey, *, info=False):
    """Decorator to wrap an async method with a memoizing callable
    that saves results in a cache.

    """
    from ._acachedmethod import _wrapper

    def decorator(method):
        # FIXME: assert method is awaitable?
        make_info = CacheInfo.make if info else None  # type: ignore
        return _wrapper(method, cache, key, make_info)

    return decorator
