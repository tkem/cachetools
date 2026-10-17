"""Descriptor helpers."""

__all__ = ()

import functools


class _MethodDescriptor:
    """Descriptor class implementing the basic descriptor protocol."""

    def __init__(self, wrapper):
        self.__owner = None
        self.__attrname = None
        self.__unbound = None
        self.__wrapper = wrapper  # called as wrapper(obj, descriptor)

    def __set_name__(self, owner, name):
        if self.__attrname is None:
            self.__owner = owner
            self.__attrname = name
        elif name != self.__attrname:
            raise TypeError(
                "Cannot assign the same descriptor to two different names "
                f"({self.__attrname!r} and {name!r})."
            )

    def __get__(self, obj, objtype=None):
        if self.__attrname is None:
            if isinstance(obj, type):
                # before Python 3.13, @classmethod calls __get__(cls, type(cls))
                # without forwarding __set_name__
                self.__call__()  # raise TypeError as in Python >= 3.13
            msg = "Cannot use descriptor instance without calling __set_name__ on it"
            raise TypeError(msg) from None

        if obj is None:
            # objtype is not used for instance lookups, so it need not be bound
            return self.__get_unbound()

        # replace descriptor instance with wrapper in instance dict
        wrapper = self.__wrapper(obj, self)
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
            return wrapper
        except AttributeError:
            # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(obj).__name__!r} "
                f"instance to cache {self.__attrname!r}"
            )
            raise TypeError(msg) from None
        except TypeError:
            msg = (
                f"The '__dict__' attribute on {type(obj).__name__!r} "
                f"instance does not support item assignment for "
                f"caching {self.__attrname!r}"
            )
            raise TypeError(msg) from None

    def __reduce__(self):
        # pickle and copy by reference, so wrappers and their keys in
        # "__cachetools_cachedmethods" can be pickled and deep-copied
        return (self._lookup, (self.__owner, self.__attrname))

    @staticmethod
    def _lookup(owner, name):
        return owner.__dict__[name]

    # called for @classmethod since Python 3.13
    def __call__(self, *args, **kwargs):
        raise TypeError("Decorating class methods is not supported")

    def __get_unbound(self):
        # created once and shared by all class accesses
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
        if not args:
            msg = "Cannot call @cachedmethod through the class without an instance"
            raise TypeError(msg)
        obj, *args = args
        return self.__descriptor.__get__(obj)(*args, **kwargs)
