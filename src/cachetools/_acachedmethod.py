"""Asynchronous method decorator helpers."""

__all__ = ()

import functools

from ._descriptor import _MethodDescriptor

# TODO: How to handle cache stampede issues?
#
# See _acached.py for details.


class _AsyncWrapperBase:
    """Asynchronous wrapper base class providing default
    implementations for properties."""

    def __init__(self, obj, name, method, cache, key):
        self.__wrapped__ = method  # FIXME: silence pyright reportAttributeAccessIssue
        functools.update_wrapper(self, method)
        self._obj = obj  # protected
        self.__name = name  # attribute name, may differ from method.__name__
        self.__cache = cache
        self.__key = functools.partial(key, obj)

    async def __call__(self, *args, **kwargs):
        raise NotImplementedError()  # pragma: no cover

    def __reduce__(self):
        # rebuild via the descriptor instead of pickling unpicklable
        # internals, e.g. __wrapped__, lock/cond closures; note that
        # this will also reset hits and misses counts for *Info*
        # wrappers
        if self._obj is None:
            raise TypeError(f"Cannot pickle {self.__name!r}")
        return (getattr, (self._obj, self.__name))

    def cache_clear(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def cache(self):
        return self.__cache(self._obj)

    @property
    def cache_key(self):
        return self.__key  # self._obj passed via functools.partial


class _AsyncWrapper(_AsyncWrapperBase):
    async def __call__(self, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)
        try:
            return cache[key]
        except KeyError:
            pass  # key not found
        val = await self.__wrapped__(self._obj, *args, **kwargs)
        try:
            cache[key] = val
        except ValueError:
            pass  # value too large
        return val

    def cache_clear(self):
        self.cache.clear()


class _AsyncInfoWrapper(_AsyncWrapperBase):
    def __init__(self, obj, name, method, cache, key, info):
        super().__init__(obj, name, method, cache, key)
        self.__info = info
        self.__hits = self.__misses = 0

    async def __call__(self, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)
        try:
            result = cache[key]
            self.__hits += 1
            return result
        except KeyError:
            self.__misses += 1
        val = await self.__wrapped__(self._obj, *args, **kwargs)
        try:
            cache[key] = val
        except ValueError:
            pass  # value too large
        return val

    def cache_clear(self):
        self.cache.clear()
        self.__hits = self.__misses = 0

    def cache_info(self):
        return self.__info(self.cache, self.__hits, self.__misses)


def _wrapper(method, cache, key, info=None):
    if info is not None:
        wrapper = lambda obj, name: _AsyncInfoWrapper(
            obj, name, method, cache, key, info
        )
    else:
        wrapper = lambda obj, name: _AsyncWrapper(obj, name, method, cache, key)
    descriptor = _MethodDescriptor(wrapper)
    # functools.update_wrapper() will not accept descriptor (decorator) as wrapper
    # https://github.com/python/typeshed/issues/9846
    return functools.update_wrapper(descriptor, method)  # type: ignore
