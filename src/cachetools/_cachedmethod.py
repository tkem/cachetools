"""Method decorator helpers."""

import functools
import weakref


def warn_classmethod(stacklevel):
    from warnings import warn

    warn(
        "decorating class methods with @cachedmethod is deprecated",
        DeprecationWarning,
        stacklevel=stacklevel,
    )


class WrapperBase:
    def __init__(self, obj, method, cache, key, lock=None, cond=None):
        if type(obj) is type:
            warn_classmethod(stacklevel=5)
        functools.update_wrapper(self, method)
        self._obj = obj  # protected
        self.__cache = cache
        self.__key = key
        self.__lock = lock
        self.__cond = cond

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()  # pragma: no cover

    def cache_clear(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def cache(self):
        return self.__cache(self._obj)

    @property
    def cache_key(self):
        return self.__key  # TODO: how to handle self?

    @property
    def cache_lock(self):
        return None if self.__lock is None else self.__lock(self._obj)

    @property
    def cache_condition(self):
        return None if self.__cond is None else self.__cond(self._obj)


class DescriptorBase:
    def __init__(self, wrapper, cache_clear):
        self.__attrname = None
        self.__wrapper = wrapper
        self.__cache_clear = cache_clear

    def __set_name__(self, owner, name):
        if self.__attrname is None:
            self.__attrname = name
        elif name != self.__attrname:  # pragma: no cover
            raise TypeError(
                "Cannot assign the same @cachedmethod to two different names "
                f"({self.__attrname!r} and {name!r})."
            )

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self  # deprecated @classmethod
        wrapper = self.Wrapper(obj)
        if self.__attrname is not None:
            try:
                wrapper = obj.__dict__.setdefault(self.__attrname, wrapper)
            except AttributeError:  # pragma: no cover
                # not all objects have __dict__ (e.g. class defines slots)
                msg = (
                    f"No '__dict__' attribute on {type(obj).__name__!r} "
                    f"instance to cache {self.__attrname!r} property."
                )
                raise TypeError(msg) from None
            except TypeError:  # pragma: no cover
                msg = (
                    f"The '__dict__' attribute on {type(obj).__name__!r} "
                    f"instance does not support item assignment for "
                    f"caching {self.__attrname!r} property."
                )
                raise TypeError(msg) from None
        return wrapper

    # called for @classmethod with Python >= 3.13
    def __call__(self, *args, **kwargs):
        warn_classmethod(stacklevel=3)
        return self.__wrapper(*args, **kwargs)

    # backward-compatible @classmethod handling with Python >= 3.13
    def cache_clear(self, objtype):
        warn_classmethod(stacklevel=3)
        return self.__cache_clear(objtype)


def _condition(method, cache, key, lock, cond):
    # backward-compatible weakref dictionary for Python >= 3.13
    pending = weakref.WeakKeyDictionary()

    def wrapper(self, pending, *args, **kwargs):
        c = cache(self)
        k = key(self, *args, **kwargs)
        with lock(self):
            cond(self).wait_for(lambda: k not in pending)
            try:
                return c[k]
            except KeyError:
                pending.add(k)
        try:
            v = method(self, *args, **kwargs)
            with lock(self):
                try:
                    c[k] = v
                except ValueError:
                    pass  # value too large
                return v
        finally:
            with lock(self):
                pending.remove(k)
                cond(self).notify_all()

    def cache_clear(self):
        c = cache(self)
        with lock(self):
            c.clear()

    def classmethod_wrapper(self, *args, **kwargs):
        p = pending.setdefault(self, set())
        return wrapper(self, p, *args, **kwargs)

    class Descriptor(DescriptorBase):
        class Wrapper(WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key, lock, cond)
                self.__pending = set()

            def __call__(self, *args, **kwargs):
                return wrapper(self._obj, self.__pending, *args, **kwargs)

            # objtype: backward-compatible @classmethod handling with Python < 3.13
            def cache_clear(self, _objtype=None):
                return cache_clear(self._obj)

    return Descriptor(classmethod_wrapper, cache_clear)


def _locked(method, cache, key, lock):
    def wrapper(self, *args, **kwargs):
        c = cache(self)
        k = key(self, *args, **kwargs)
        with lock(self):
            try:
                return c[k]
            except KeyError:
                pass  # key not found
        v = method(self, *args, **kwargs)
        # in case of a race, prefer the item already in the cache
        with lock(self):
            try:
                return c.setdefault(k, v)
            except ValueError:
                return v  # value too large

    def cache_clear(self):
        c = cache(self)
        with lock(self):
            c.clear()

    class Descriptor(DescriptorBase):
        class Wrapper(WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key, lock)

            def __call__(self, *args, **kwargs):
                return wrapper(self._obj, *args, **kwargs)

            # objtype: backward-compatible @classmethod handling with Python < 3.13
            def cache_clear(self, _objtype=None):
                return cache_clear(self._obj)

    return Descriptor(wrapper, cache_clear)


def _unlocked(method, cache, key):
    def wrapper(self, *args, **kwargs):
        c = cache(self)
        k = key(self, *args, **kwargs)
        try:
            return c[k]
        except KeyError:
            pass  # key not found
        v = method(self, *args, **kwargs)
        try:
            c[k] = v
        except ValueError:
            pass  # value too large
        return v

    def cache_clear(self):
        c = cache(self)
        c.clear()

    class Descriptor(DescriptorBase):
        class Wrapper(WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key)

            def __call__(self, *args, **kwargs):
                return wrapper(self._obj, *args, **kwargs)

            # objtype: backward-compatible @classmethod handling with Python < 3.13
            def cache_clear(self, _objtype=None):
                return cache_clear(self._obj)

    return Descriptor(wrapper, cache_clear)


def _wrapper(method, cache, key, lock=None, cond=None):
    if cond is not None and lock is not None:
        wrapper = _condition(method, cache, key, lock, cond)
    elif cond is not None:
        wrapper = _condition(method, cache, key, cond, cond)
    elif lock is not None:
        wrapper = _locked(method, cache, key, lock)
    else:
        wrapper = _unlocked(method, cache, key)

    # backward-compatible properties for @classmethod
    wrapper.cache = cache
    wrapper.cache_key = key
    wrapper.cache_lock = lock if lock is not None else cond
    wrapper.cache_condition = cond

    return functools.update_wrapper(wrapper, method)
