"""Method decorator helpers."""

import functools
import weakref


def warn_classmethod():
    from warnings import warn

    warn(
        "decorating class methods with @cachedmethod is deprecated",
        DeprecationWarning,
        stacklevel=3,
    )


class WrapperBase:
    def __init__(self, obj, method, cache, key):
        functools.update_wrapper(self, method)
        self.__obj = obj
        self.__cache = cache
        self.__key = key

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()  # pragma: no cover

    def cache_clear(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def cache(self):
        return self.__cache(self.__obj)

    @property
    def cache_key(self):
        return self.__key  # TODO: how to handle self?

    @property
    def cache_lock(self):
        return None

    @property
    def cache_condition(self):
        return None


def _condition(method, cache, key, lock, cond):
    pending = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        if type(self) is type:
            warn_classmethod()
        c = cache(self)
        k = key(self, *args, **kwargs)
        with lock(self):
            p = pending.setdefault(self, set())
            cond(self).wait_for(lambda: k not in p)
            try:
                return c[k]
            except KeyError:
                p.add(k)
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
                pending[self].remove(k)
                cond(self).notify_all()

    def cache_clear(self):
        c = cache(self)
        with lock(self):
            c.clear()

    class Descriptor:
        def __get__(self, obj, objtype=None):
            class Wrapper(WrapperBase):
                def __call__(self, *args, **kwargs):
                    return wrapper(obj, *args, **kwargs)

                def cache_clear(self):
                    return cache_clear(obj)

                @property
                def cache_lock(self):
                    return lock(obj)

                @property
                def cache_condition(self):
                    return cond(obj)

            return Wrapper(obj, method, cache, key)

        # called for @classmethod with Python >= 3.13
        def __call__(self, *args, **kwargs):
            return wrapper(*args, **kwargs)

    return Descriptor()


def _locked(method, cache, key, lock):
    def wrapper(self, *args, **kwargs):
        if type(self) is type:
            warn_classmethod()
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

    class Descriptor:
        def __get__(self, obj, objtype=None):
            class Wrapper(WrapperBase):
                def __call__(self, *args, **kwargs):
                    return wrapper(obj, *args, **kwargs)

                def cache_clear(self):
                    return cache_clear(obj)

                @property
                def cache_lock(self):
                    return lock(obj)

            return Wrapper(obj, method, cache, key)

        # called for @classmethod with Python >= 3.13
        def __call__(self, *args, **kwargs):
            return wrapper(*args, **kwargs)

    return Descriptor()


# FIXME: _unlocked as Descriptor class?
def _unlocked(method, cache, key):
    def wrapper(self, *args, **kwargs):
        if type(self) is type:
            warn_classmethod()
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

    class Descriptor:
        def __init__(self):
            self.attrname = None

        # TODO: BaseDescriptor
        def __set_name__(self, owner, name):
            if self.attrname is None:
                self.attrname = name
            elif name != self.attrname:
                raise TypeError(
                    "Cannot assign the same @cachedmethos to two different names "
                    f"({self.attrname!r} and {name!r})."
                )

        def __get__(self, obj, objtype=None):
            class Wrapper(WrapperBase):
                def __call__(self, *args, **kwargs):
                    return wrapper(obj, *args, **kwargs)

                def cache_clear(self):
                    return cache_clear(obj)

            w = Wrapper(obj, method, cache, key)
            if self.attrname is not None:
                try:
                    obj.__dict__[self.attrname] = w
                except (
                    AttributeError
                ):  # not all objects have __dict__ (e.g. class defines slots)
                    msg = (
                        f"No '__dict__' attribute on {type(obj).__name__!r} "
                        f"instance to cache {self.attrname!r} property."
                    )
                    raise TypeError(msg) from None
                except TypeError:
                    msg = (
                        f"The '__dict__' attribute on {type(obj).__name__!r} "
                        f"instance does not support item assignment for "
                        f"caching {self.attrname!r} property."
                    )
                    raise TypeError(msg) from None
            return w

        # called for @classmethod with Python >= 3.13
        def __call__(self, *args, **kwargs):
            return wrapper(*args, **kwargs)

    return Descriptor()


def _wrapper(method, cache, key, lock=None, cond=None):
    if cond is not None and lock is not None:
        wrapper = _condition(method, cache, key, lock, cond)
    elif cond is not None:
        wrapper = _condition(method, cache, key, cond, cond)
    elif lock is not None:
        wrapper = _locked(method, cache, key, lock)
    else:
        wrapper = _unlocked(method, cache, key)

    wrapper.cache = cache
    wrapper.cache_key = key
    wrapper.cache_lock = lock if lock is not None else cond
    wrapper.cache_condition = cond

    return functools.update_wrapper(wrapper, method)
