"""Descriptor helpers."""

# pyright: reportAttributeAccessIssue=false

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
        attrname = self.__attrname

        if attrname is None:
            if isinstance(obj, type):
                # before Python 3.13, @classmethod calls __get__(cls, type(cls))
                # without forwarding __set_name__
                self.__call__()  # raise TypeError as in Python >= 3.13
            msg = "Cannot use descriptor instance without calling __set_name__ on it"
            raise TypeError(msg) from None

        if obj is None:
            # objtype is not used for instance lookups, so it need not be bound
            return self.__get_unbound()

        for cls in type(obj).__mro__:
            if attrname in cls.__dict__:
                descriptor = cls.__dict__[attrname]
                break
        else:
            descriptor = None  # removed from the class after __set_name__
        if descriptor is self:
            # replace descriptor instance with wrapper in instance dict; in case
            # of a race condition where another thread already replaced the
            # descriptor, prefer the initial wrapper.
            wrapper = self.__wrapper(obj, self)
            try:
                wrapper = obj.__dict__.setdefault(attrname, wrapper)
            except (AttributeError, TypeError) as e:
                self.__instance_dict_error(obj, e)
        else:
            # A super() lookup must neither reuse the override's wrapper
            # nor replace it, so preserve state separately for each descriptor.
            try:
                wrappers = obj.__dict__.setdefault("__cachetools_cachedmethods", {})
            except (AttributeError, TypeError) as e:
                self.__instance_dict_error(obj, e)
            wrapper = wrappers.get(self)
            if wrapper is None:
                wrapper = self.__wrapper(obj, self)
                wrapper = wrappers.setdefault(self, wrapper)
        return wrapper

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

    def __instance_dict_error(self, obj, error):
        if isinstance(error, AttributeError):
            # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(obj).__name__!r} "
                f"instance to cache {self.__attrname!r}"
            )
        else:
            # some objects may have an immutable __dict__
            msg = (
                f"The '__dict__' attribute on {type(obj).__name__!r} "
                f"instance does not support item assignment for "
                f"caching {self.__attrname!r}"
            )
        raise TypeError(msg) from None


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

    def __repr__(self):
        wrapped = self.__wrapped__
        return f"<cachedmethod {wrapped!r}>"

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
