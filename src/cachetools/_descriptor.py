"""Descriptor helpers."""

__all__ = ()

import functools

_CLASSMETHOD_MSG = "Decorating class methods is not supported"


class _MethodDescriptor:
    """Descriptor class implementing the basic descriptor protocol."""

    class Unbound:
        """Callable returned on class access.

        Deliberately not a function: unittest.mock.create_autospec() only
        strips the receiver from plain functions found in the class dict,
        so a function here would leave the receiver in an autospec'd
        instance's signature.
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

        # Receiver is taken from *args so autospec'd instances accept any
        # call, as they did before class access returned a callable.
        def __call__(self, /, *args, **kwargs):
            if not args:
                msg = "Cannot call @cachedmethod through the class without an instance"
                raise TypeError(msg)
            obj, *args = args
            return self.__descriptor.__get__(obj)(*args, **kwargs)

    def __init__(self, wrapper):
        self.__owner = None
        self.__attrname = None
        self.__unbound = None
        self.__wrapper = wrapper  # called as wrapper(obj, descriptor)

    def __set_name__(self, owner, name):
        if self.__attrname is None:
            self.__owner = owner
            self.__attrname = name
            # created once and shared by all class accesses
            self.__unbound = _MethodDescriptor.Unbound(self)
        elif name != self.__attrname:
            msg = (
                "Cannot assign the same descriptor to two different names "
                f"({self.__attrname!r} and {name!r})."
            )
            raise TypeError(msg)

    def __get__(self, obj, objtype=None):
        name = self.__attrname
        if name is None:
            if isinstance(obj, type):
                # before Python 3.13, @classmethod calls __get__(cls, type(cls))
                # without forwarding __set_name__
                raise TypeError(_CLASSMETHOD_MSG)
            msg = "Cannot use descriptor instance without calling __set_name__ on it"
            raise TypeError(msg)

        if obj is None:
            # objtype is not used for instance lookups, so it need not be bound
            return self.__unbound

        try:
            instdict = obj.__dict__
        except AttributeError:
            # not all objects have __dict__ (e.g. class defines slots)
            msg = f"No '__dict__' attribute on {type(obj).__name__!r} instance to cache {name!r}"
            raise TypeError(msg) from None

        # a super() lookup, or an alias, finds this descriptor behind another
        primary = False
        for cls in type(obj).__mro__:
            if name in cls.__dict__:
                primary = cls.__dict__[name] is self
                break

        if primary:
            # replace descriptor instance with wrapper in instance dict
            wrappers, key = instdict, name
        else:
            # A super() lookup must neither reuse the override's wrapper
            # nor replace it, so preserve state separately for each descriptor.
            wrappers = self.__setdefault(
                obj, instdict, "__cachetools_cachedmethods", {}
            )
            key = self

        # super() and class access bypass the instance dict, so an existing
        # wrapper must be found here before a new one is built
        wrapper = wrappers.get(key)
        if wrapper is None:
            # In case of a race condition where another thread already
            # stored a wrapper, prefer that one.
            wrapper = self.__setdefault(obj, wrappers, key, self.__wrapper(obj, self))
        return wrapper

    def __setdefault(self, obj, mapping, key, default):
        try:
            return mapping.setdefault(key, default)
        except TypeError:
            msg = (
                f"The '__dict__' attribute on {type(obj).__name__!r} instance "
                f"does not support item assignment for caching {self.__attrname!r}"
            )
            raise TypeError(msg) from None

    # called for @classmethod since Python 3.13
    def __call__(self, *args, **kwargs):
        raise TypeError(_CLASSMETHOD_MSG)

    def __reduce__(self):
        # pickle and copy by reference, so wrappers and their keys in
        # "__cachetools_cachedmethods" can be pickled and deep-copied
        return (self._lookup, (self.__owner, self.__attrname))

    @staticmethod
    def _lookup(owner, name):
        return owner.__dict__[name]
