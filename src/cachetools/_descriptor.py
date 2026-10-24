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
        self.__owner = None
        self.__attrname = None
        self.__deprecated = deprecated
        self.__unbound = None

    def __set_name__(self, owner, name):
        if self.__attrname is None:
            self.__owner = owner
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
            wrapper = self.Wrapper(obj, self)  # type: ignore
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
            wrapper = self.Wrapper(obj, self)  # type: ignore
        else:
            msg = "Cannot use @cachedmethod instance without calling __set_name__ on it"
            raise TypeError(msg) from None
        return wrapper

    def __reduce__(self):
        # pickle and copy by reference, so wrappers and their keys in
        # "__cachetools_cachedmethods" can be pickled and deep-copied
        return (self._lookup, (self.__owner, self.__attrname))

    @staticmethod
    def _lookup(owner, name):
        return owner.__dict__[name]

    def __get_unbound(self):
        # Created once and shared by all class accesses; objtype is not
        # used for instance lookups, so it need not be bound here.
        if self.__unbound is None:
            self.__unbound = _Unbound(self)
        return self.__unbound


class _Unbound:
    """Callable returned on class access.

    Deliberately not a function: unittest.mock.create_autospec() only strips
    the receiver from plain functions found in the class dict, so a function
    here would leave the receiver in an autospec'd instance's signature.
    """

    def __init__(self, descriptor):
        functools.update_wrapper(self, descriptor.__wrapped__)
        self.__descriptor = descriptor
        self.__receiver = None  # name of the wrapped method's first parameter

    def __reduce__(self):
        # pickle and copy by reference, as functions are
        return (self.__descriptor.__get__, (None,))

    # bind like a method when aliased in another class body
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.__descriptor.__get__(obj)

    # Receiver is taken from *args so autospec'd instances accept any call,
    # as they did before class access returned a callable.
    def __call__(self, /, *args, **kwargs):
        if args:
            obj, *args = args
        else:
            obj = self.__pop_receiver(kwargs)
        return self.__descriptor.__get__(obj)(*args, **kwargs)

    def __pop_receiver(self, kwargs):
        # the receiver may also be passed by keyword, as for a plain function
        if self.__receiver is None:
            import inspect

            self.__receiver = ""
            try:
                param = next(iter(inspect.signature(self).parameters.values()))
            except (ValueError, StopIteration):
                pass  # no signature, or no parameters at all
            else:
                if param.kind is param.POSITIONAL_OR_KEYWORD:
                    self.__receiver = param.name
        try:
            return kwargs.pop(self.__receiver)
        except KeyError:
            msg = "Cannot call @cachedmethod through the class without an instance"
            raise TypeError(msg) from None


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
