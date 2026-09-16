"""Descriptor helpers."""

__all__ = ()


class _MethodDescriptor:
    """Descriptor class implementing the basic descriptor protocol."""

    def __init__(self, wrapper):
        self.__attrname = None
        self.__wrapper = wrapper  # called as wrapper(obj, attrname)

    def __set_name__(self, owner, name):
        if self.__attrname is None:
            self.__attrname = name
        elif name != self.__attrname:
            raise TypeError(
                "Cannot assign the same descriptor to two different names "
                f"({self.__attrname!r} and {name!r})."
            )

    def __get__(self, obj, objtype=None):
        if obj is None:
            # Return the wrapper itself without modification when accessed
            # through the class to support class-level introspection, such
            # as for mocking with autospec=True in unittest.mock.
            return self.__wrapper(obj, self.__attrname)
        if self.__attrname is None:
            msg = "Cannot use descriptor instance without calling __set_name__ on it"
            raise TypeError(msg) from None
        # replace descriptor instance with wrapper in instance dict
        wrapper = self.__wrapper(obj, self.__attrname)
        try:
            # In case of a race condition where another thread already replaced
            # the descriptor, prefer the initial wrapper.
            return obj.__dict__.setdefault(self.__attrname, wrapper)
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

    # called for @classmethod since Python 3.13
    def __call__(self, *args, **kwargs):
        msg = "Decorating class methods is not supported"
        raise TypeError(msg)
