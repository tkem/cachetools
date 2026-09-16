"""Method decorator helpers."""

# pyright: reportOptionalContextManager=false, reportOptionalMemberAccess=false

__all__ = ()

import functools

from ._descriptor import _MethodDescriptor


def _none(_):
    return None


class _WrapperBase:
    """Wrapper base class providing default implementations for properties."""

    def __init__(self, obj, method, cache, key, lock=None, cond=None):
        functools.update_wrapper(self, method)
        self._obj = obj  # protected
        self.__cache = cache
        self.__key = functools.partial(key, obj)
        self.__lock = lock if lock is not None else _none
        self.__cond = cond if cond is not None else _none

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()  # pragma: no cover

    def cache_clear(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def cache(self):
        return self.__cache(self._obj)

    @property
    def cache_key(self):
        return self.__key  # self._obj passed via functools.partial

    @property
    def cache_lock(self):
        return self.__lock(self._obj)

    @property
    def cache_condition(self):
        return self.__cond(self._obj)


# At least for now, the implementation prefers clarity and performance
# over ease of maintenance, thus providing separate descriptors for
# all valid combinations of decorator parameters lock, condition and
# info.


def _condition_info(method, cache, key, lock, cond, info):
    class Descriptor(_MethodDescriptor):
        class Wrapper(_WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key, lock, cond)
                self.__hits = self.__misses = 0
                self.__pending = set()

            def __call__(self, *args, **kwargs):
                cache = self.cache
                lock = self.cache_lock
                cond = self.cache_condition
                key = self.cache_key(*args, **kwargs)

                with lock:
                    cond.wait_for(lambda: key not in self.__pending)
                    try:
                        result = cache[key]
                        self.__hits += 1
                        return result
                    except KeyError:
                        self.__pending.add(key)
                        self.__misses += 1
                try:
                    val = method(self._obj, *args, **kwargs)
                    with lock:
                        try:
                            cache[key] = val
                        except ValueError:
                            pass  # value too large
                        return val
                finally:
                    with lock:
                        self.__pending.remove(key)
                        cond.notify_all()

            def cache_clear(self):
                with self.cache_lock:
                    self.cache.clear()
                    self.__hits = self.__misses = 0

            def cache_info(self):
                with self.cache_lock:
                    return info(self.cache, self.__hits, self.__misses)

    return Descriptor()


def _locked_info(method, cache, key, lock, info):
    class Descriptor(_MethodDescriptor):
        class Wrapper(_WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key, lock)
                self.__hits = self.__misses = 0

            def __call__(self, *args, **kwargs):
                cache = self.cache
                lock = self.cache_lock
                key = self.cache_key(*args, **kwargs)
                with lock:
                    try:
                        result = cache[key]
                        self.__hits += 1
                        return result
                    except KeyError:
                        self.__misses += 1
                val = method(self._obj, *args, **kwargs)
                with lock:
                    try:
                        # In case of a race condition, i.e. if another thread
                        # stored a value for this key while we were calling
                        # method(), prefer the cached value.
                        return cache.setdefault(key, val)
                    except ValueError:
                        return val  # value too large

            def cache_clear(self):
                with self.cache_lock:
                    self.cache.clear()
                    self.__hits = self.__misses = 0

            def cache_info(self):
                with self.cache_lock:
                    return info(self.cache, self.__hits, self.__misses)

    return Descriptor()


def _unlocked_info(method, cache, key, info):
    class Descriptor(_MethodDescriptor):
        class Wrapper(_WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key)
                self.__hits = self.__misses = 0

            def __call__(self, *args, **kwargs):
                cache = self.cache
                key = self.cache_key(*args, **kwargs)
                try:
                    result = cache[key]
                    self.__hits += 1
                    return result
                except KeyError:
                    self.__misses += 1
                val = method(self._obj, *args, **kwargs)
                try:
                    cache[key] = val
                except ValueError:
                    pass  # value too large
                return val

            def cache_clear(self):
                self.cache.clear()
                self.__hits = self.__misses = 0

            def cache_info(self):
                return info(self.cache, self.__hits, self.__misses)

    return Descriptor()


def _condition(method, cache, key, lock, cond):
    class Descriptor(_MethodDescriptor):
        class Wrapper(_WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key, lock, cond)
                self.__pending = set()

            def __call__(self, *args, **kwargs):
                cache = self.cache
                lock = self.cache_lock
                cond = self.cache_condition
                key = self.cache_key(*args, **kwargs)

                with lock:
                    cond.wait_for(lambda: key not in self.__pending)
                    try:
                        return cache[key]
                    except KeyError:
                        self.__pending.add(key)
                try:
                    val = method(self._obj, *args, **kwargs)
                    with lock:
                        try:
                            cache[key] = val
                        except ValueError:
                            pass  # value too large
                        return val
                finally:
                    with lock:
                        self.__pending.remove(key)
                        cond.notify_all()

            def cache_clear(self):
                with self.cache_lock:
                    self.cache.clear()

    return Descriptor()


def _locked(method, cache, key, lock):
    class Descriptor(_MethodDescriptor):
        class Wrapper(_WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key, lock)

            def __call__(self, *args, **kwargs):
                cache = self.cache
                lock = self.cache_lock
                key = self.cache_key(*args, **kwargs)
                with lock:
                    try:
                        return cache[key]
                    except KeyError:
                        pass  # key not found
                val = method(self._obj, *args, **kwargs)
                with lock:
                    try:
                        # In case of a race condition, i.e. if another thread
                        # stored a value for this key while we were calling
                        # method(), prefer the cached value.
                        return cache.setdefault(key, val)
                    except ValueError:
                        return val  # value too large

            def cache_clear(self):
                with self.cache_lock:
                    self.cache.clear()

    return Descriptor()


def _unlocked(method, cache, key):
    class Descriptor(_MethodDescriptor):
        class Wrapper(_WrapperBase):
            def __init__(self, obj):
                super().__init__(obj, method, cache, key)

            def __call__(self, *args, **kwargs):
                cache = self.cache
                key = self.cache_key(*args, **kwargs)
                try:
                    return cache[key]
                except KeyError:
                    pass  # key not found
                val = method(self._obj, *args, **kwargs)
                try:
                    cache[key] = val
                except ValueError:
                    pass  # value too large
                return val

            def cache_clear(self):
                self.cache.clear()

    return Descriptor()


def _wrapper(method, cache, key, lock=None, cond=None, info=None):
    if info is not None:
        if cond is not None and lock is not None:
            wrapper = _condition_info(method, cache, key, lock, cond, info)
        elif cond is not None:
            wrapper = _condition_info(method, cache, key, cond, cond, info)
        elif lock is not None:
            wrapper = _locked_info(method, cache, key, lock, info)
        else:
            wrapper = _unlocked_info(method, cache, key, info)
    else:
        if cond is not None and lock is not None:
            wrapper = _condition(method, cache, key, lock, cond)
        elif cond is not None:
            wrapper = _condition(method, cache, key, cond, cond)
        elif lock is not None:
            wrapper = _locked(method, cache, key, lock)
        else:
            wrapper = _unlocked(method, cache, key)

    # functools.update_wrapper() will not accept descriptor (decorator) as wrapper
    # https://github.com/python/typeshed/issues/9846
    return functools.update_wrapper(wrapper, method)
