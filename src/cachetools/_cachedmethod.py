"""Method decorator helpers.

At least for now, the implementation prefers clarity and performance
over ease of maintenance, thus providing separate wrappers for all
valid combinations of parameters lock, condition and info.

"""

# pyright: reportArgumentType=false

__all__ = ()

import functools

from ._decorator import (
    _BasicMixin,
    _ConditionInfoMixin,
    _ConditionMixin,
    _InfoMixin,
    _LockedInfoMixin,
    _LockedMixin,
)
from ._descriptor import _MethodDescriptor


class _WrapperBase:
    """Wrapper base class providing default implementations for properties."""

    def __init__(self, obj, name, method, cache, key, lock=None, cond=None):
        functools.update_wrapper(self, method)  # FIXME: cannot be moved to _wrapper()?
        self.__obj = obj
        self.__name = name  # attribute name, may differ from method.__name__
        self.__cache = cache
        self.__key = functools.partial(key, obj)
        self.__lock = lock if lock is not None else lambda _: None
        self.__cond = cond if cond is not None else lambda _: None

    def __reduce__(self):
        # rebuild via the descriptor instead of pickling unpicklable
        # internals, e.g. __wrapped__, lock/cond closures; note that
        # this will also reset hits and misses counts for *Info*
        # wrappers
        if self.__obj is None:
            raise TypeError(f"Cannot pickle {self.__name!r}")
        return (getattr, (self.__obj, self.__name))

    @property
    def cache(self):
        return self.__cache(self.__obj)

    @property
    def cache_key(self):
        return self.__key  # self.__obj passed via functools.partial

    @property
    def cache_lock(self):
        return self.__lock(self.__obj)

    @property
    def cache_condition(self):
        return self.__cond(self.__obj)


class _BasicWrapper(_WrapperBase, _BasicMixin):
    def __init__(self, obj, name, method, cache, key):
        _WrapperBase.__init__(self, obj, name, method, cache, key)
        _BasicMixin.__init__(self, functools.partial(method, obj))


class _LockedWrapper(_WrapperBase, _LockedMixin):
    def __init__(self, obj, name, method, cache, key, lock):
        _WrapperBase.__init__(self, obj, name, method, cache, key, lock)
        _LockedMixin.__init__(self, functools.partial(method, obj))


class _ConditionWrapper(_WrapperBase, _ConditionMixin):
    def __init__(self, obj, name, method, cache, key, lock, cond):
        _WrapperBase.__init__(self, obj, name, method, cache, key, lock, cond)
        _ConditionMixin.__init__(self, functools.partial(method, obj))


class _InfoWrapper(_WrapperBase, _InfoMixin):
    def __init__(self, obj, name, method, cache, key, info):
        _WrapperBase.__init__(self, obj, name, method, cache, key)
        _InfoMixin.__init__(self, functools.partial(method, obj), info)


class _LockedInfoWrapper(_WrapperBase, _LockedInfoMixin):
    def __init__(self, obj, name, method, cache, key, lock, info):
        _WrapperBase.__init__(self, obj, name, method, cache, key, lock)
        _LockedInfoMixin.__init__(self, functools.partial(method, obj), info)


class _ConditionInfoWrapper(_WrapperBase, _ConditionInfoMixin):
    def __init__(self, obj, name, method, cache, key, lock, cond, info):
        _WrapperBase.__init__(self, obj, name, method, cache, key, lock, cond)
        _ConditionInfoMixin.__init__(self, functools.partial(method, obj), info)


def _wrapper(method, cache, key, lock=None, cond=None, info=None):
    if info is not None:
        if cond is not None and lock is not None:
            wrapper = lambda obj, name: _ConditionInfoWrapper(
                obj, name, method, cache, key, lock, cond, info
            )
        elif cond is not None:
            wrapper = lambda obj, name: _ConditionInfoWrapper(
                obj, name, method, cache, key, cond, cond, info
            )
        elif lock is not None:
            wrapper = lambda obj, name: _LockedInfoWrapper(
                obj, name, method, cache, key, lock, info
            )
        else:
            wrapper = lambda obj, name: _InfoWrapper(
                obj, name, method, cache, key, info
            )
    else:
        if cond is not None and lock is not None:
            wrapper = lambda obj, name: _ConditionWrapper(
                obj, name, method, cache, key, lock, cond
            )
        elif cond is not None:
            wrapper = lambda obj, name: _ConditionWrapper(
                obj, name, method, cache, key, cond, cond
            )
        elif lock is not None:
            wrapper = lambda obj, name: _LockedWrapper(
                obj, name, method, cache, key, lock
            )
        else:
            wrapper = lambda obj, name: _BasicWrapper(obj, name, method, cache, key)
    descriptor = _MethodDescriptor(wrapper)
    # functools.update_wrapper() will not accept descriptor (decorator) as wrapper
    # https://github.com/python/typeshed/issues/9846
    return functools.update_wrapper(descriptor, method)  # type: ignore
