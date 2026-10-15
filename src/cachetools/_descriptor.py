"""Descriptor helpers."""

__all__ = ()

import functools
import warnings


def _warn_classmethod(stacklevel):
    warnings.warn(
        "decorating class methods with @cachedmethod is deprecated",
        DeprecationWarning,
        stacklevel=stacklevel,
    )


def _warn_instance_dict(msg, stacklevel):
    warnings.warn(
        msg,
        DeprecationWarning,
        stacklevel=stacklevel,
    )


class _MethodDescriptor:
    """Descriptor class implementing the basic descriptor protocol."""

    def __init__(self, deprecated=False):
        self.__attrname = None
        self.__deprecated = deprecated
        self.__unbound = None

    def __set_name__(self, owner, name):
        if self.__attrname is None:
            self.__attrname = name
        elif name != self.__attrname:
            raise TypeError(
                "Cannot assign the same @cachedmethod to two different names "
                f"({self.__attrname!r} and {name!r})."
            )

    def __get__(self, obj, objtype=None):
        if obj is None:
            # objtype is not used for instance lookups, so it need not be bound here
            return self.__get_unbound()
        elif self.__attrname is not None:
            # replace descriptor instance with wrapper in instance dict
            wrapper = self.Wrapper(obj)  # type: ignore
            try:
                descriptor = next(
                    (
                        cls.__dict__[self.__attrname]
                        for cls in type(obj).__mro__
                        if self.__attrname in cls.__dict__
                    ),
                    None,
                )
                if descriptor is self:
                    # In case of a race condition where another thread already replaced
                    # the descriptor, prefer the initial wrapper.
                    wrapper = obj.__dict__.setdefault(self.__attrname, wrapper)
                else:
                    # A super() lookup must neither reuse the override's wrapper
                    # nor replace it, so preserve state separately for each descriptor.
                    wrappers = obj.__dict__.setdefault("__cachetools_cachedmethods", {})
                    wrapper = wrappers.setdefault(self, wrapper)
            except AttributeError:
                # not all objects have __dict__ (e.g. class defines slots)
                msg = (
                    f"No '__dict__' attribute on {type(obj).__name__!r} "
                    f"instance to cache {self.__attrname!r} property."
                )
                if self.__deprecated:
                    _warn_instance_dict(msg, 3)
                else:
                    raise TypeError(msg) from None
            except TypeError:
                msg = (
                    f"The '__dict__' attribute on {type(obj).__name__!r} "
                    f"instance does not support item assignment for "
                    f"caching {self.__attrname!r} property."
                )
                if self.__deprecated:
                    _warn_instance_dict(msg, 3)
                else:
                    raise TypeError(msg) from None
        elif self.__deprecated:
            # deprecated @classmethod, warning already raised elsewhere
            wrapper = self.Wrapper(obj)  # type: ignore
        else:
            msg = "Cannot use @cachedmethod instance without calling __set_name__ on it"
            raise TypeError(msg) from None
        return wrapper

    def __get_unbound(self):
        # Created once and shared by all class accesses; objtype is not
        # used for instance lookups, so it need not be bound here.
        if self.__unbound is None:
            descriptor = self

            # As in the previous function wrapper, the receiver is named self.
            @functools.wraps(self.__wrapped__)  # type: ignore
            def unbound(self, *args, **kwargs):
                return descriptor.__get__(self)(*args, **kwargs)

            self.__unbound = unbound  # type: ignore
        return self.__unbound


class _ClassMethodDescriptor(_MethodDescriptor):
    """Descriptor base class supporting deprecated @classmethod use."""

    def __init__(self, wrapper, cache_clear):
        super().__init__(deprecated=True)
        self.__wrapper = wrapper
        self.__cache_clear = cache_clear

    # called for @classmethod with Python >= 3.13
    def __call__(self, *args, **kwargs):
        _warn_classmethod(stacklevel=3)
        return self.__wrapper(*args, **kwargs)

    # backward-compatible @classmethod handling with Python >= 3.13
    def cache_clear(self, objtype):
        _warn_classmethod(stacklevel=3)
        return self.__cache_clear(objtype)
