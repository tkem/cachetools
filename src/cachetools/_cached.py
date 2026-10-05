"""Function decorator helpers.

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


class _WrapperBase:
    """Wrapper base class providing default implementations for properties."""

    def __init__(self, cache, key, lock=None, cond=None):
        self.cache = cache
        self.cache_key = key
        self.cache_lock = lock
        self.cache_condition = cond


class _BasicWrapper(_WrapperBase, _BasicMixin):
    def __init__(self, func, cache, key):
        _WrapperBase.__init__(self, cache, key)
        _BasicMixin.__init__(self, func)


class _LockedWrapper(_WrapperBase, _LockedMixin):
    def __init__(self, func, cache, key, lock):
        _WrapperBase.__init__(self, cache, key, lock)
        _LockedMixin.__init__(self, func)


class _ConditionWrapper(_WrapperBase, _ConditionMixin):
    def __init__(self, func, cache, key, lock, cond):
        _WrapperBase.__init__(self, cache, key, lock, cond)
        _ConditionMixin.__init__(self, func)


class _InfoWrapper(_WrapperBase, _InfoMixin):
    def __init__(self, func, cache, key, info):
        _WrapperBase.__init__(self, cache, key)
        _InfoMixin.__init__(self, func, info)


class _LockedInfoWrapper(_WrapperBase, _LockedInfoMixin):
    def __init__(self, func, cache, key, lock, info):
        _WrapperBase.__init__(self, cache, key, lock)
        _LockedInfoMixin.__init__(self, func, info)


class _ConditionInfoWrapper(_WrapperBase, _ConditionInfoMixin):
    def __init__(self, func, cache, key, lock, cond, info):
        _WrapperBase.__init__(self, cache, key, lock, cond)
        _ConditionInfoMixin.__init__(self, func, info)


def _wrapper(func, cache, key, lock=None, cond=None, info=None):
    if info is not None:
        if cond is not None and lock is not None:
            wrapper = _ConditionInfoWrapper(func, cache, key, lock, cond, info)
        elif cond is not None:
            wrapper = _ConditionInfoWrapper(func, cache, key, cond, cond, info)
        elif lock is not None:
            wrapper = _LockedInfoWrapper(func, cache, key, lock, info)
        else:
            wrapper = _InfoWrapper(func, cache, key, info)
    else:
        if cond is not None and lock is not None:
            wrapper = _ConditionWrapper(func, cache, key, lock, cond)
        elif cond is not None:
            wrapper = _ConditionWrapper(func, cache, key, cond, cond)
        elif lock is not None:
            wrapper = _LockedWrapper(func, cache, key, lock)
        else:
            wrapper = _BasicWrapper(func, cache, key)
    return functools.update_wrapper(wrapper, func)
