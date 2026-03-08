"""Property decorator helpers."""

import functools

__all__ = ()


class _DescriptorBase:
    """Descriptor base class implementing the basic descriptor protocol."""

    def __init__(self):
        self.__attrname = None

    def __set_name__(self, owner, name):
        if self.__attrname is None:
            self.__attrname = name
        elif name != self.__attrname:
            raise TypeError(
                "Cannot assign the same @cachedproperty to two different names "
                f"({self.__attrname!r} and {name!r})."
            )

    def __get__(self, obj, objtype=None):
        wrapper = self.Wrapper(obj)  # FIXME: wrapper may also be a value?!?
        if obj is None:
            # e.g. mocking with autospec=True in unittest.mock
            pass
        elif self.__attrname is not None:
            # replace descriptor instance with wrapper in instance dict
            try:
                # In case of a race condition where another thread already replaced
                # the descriptor, prefer the initial wrapper.
                # FIXME: wrapper may also be a value?!?
                wrapper = obj.__dict__.setdefault(self.__attrname, wrapper)
            except AttributeError:
                # not all objects have __dict__ (e.g. class defines slots)
                msg = (
                    f"No '__dict__' attribute on {type(obj).__name__!r} "
                    f"instance to cache {self.__attrname!r} property."
                )
                raise TypeError(msg) from None
            except TypeError:
                msg = (
                    f"The '__dict__' attribute on {type(obj).__name__!r} "
                    f"instance does not support item assignment for "
                    f"caching {self.__attrname!r} property."
                )
                raise TypeError(msg) from None
        else:
            msg = (
                "Cannot use @cachedproperty instance without calling __set_name__ on it"
            )
            raise TypeError(msg) from None
        return wrapper


class _DefaultLock:
    def __enter__(_self):
        pass

    def __exit__(_self, _exc_type, _exc_value, _traceback):
        return False


_default_lock = _DefaultLock()


def _ttl_property(ttl, timer, lock):
    pass


def _property(lock):
    pass


def _wrapper(method, ttl, timer, lock=_default_lock):
    if ttl is not None:
        wrapper = _ttl_property(method, ttl, timer, lock)
    else:
        wrapper = _property(method, lock)
    return functools.update_wrapper(wrapper, method)
