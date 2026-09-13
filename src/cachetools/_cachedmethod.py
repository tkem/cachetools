"""Method decorator helpers.

At least for now, the implementation prefers clarity and performance
over ease of maintenance, thus providing separate wrappers for all
valid combinations of parameters lock, condition and info.

"""

__all__ = ()

import functools

from ._descriptor import _MethodDescriptor


class _WrapperBase:
    """Wrapper base class providing default implementations for properties."""

    def __init__(self, obj, name, method, cache, key, lock=None, cond=None):
        self.__wrapped__ = method  # FIXME: silence pyright reportAttributeAccessIssue
        functools.update_wrapper(self, method)
        self._obj = obj  # protected
        self.__name = name  # attribute name, may differ from method.__name__
        self.__cache = cache
        self.__key = functools.partial(key, obj)
        self.__lock = lock if lock is not None else lambda _: None
        self.__cond = cond if cond is not None else lambda _: None

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()  # pragma: no cover

    def __reduce__(self):
        # rebuild via the descriptor instead of pickling unpicklable
        # internals, e.g. __wrapped__, lock/cond closures; note that
        # this will also reset hits and misses counts for *Info*
        # wrappers
        if self._obj is None:
            raise TypeError(f"Cannot pickle {self.__wrapped__.__qualname__!r}")
        return (getattr, (self._obj, self.__name))

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


class _UnlockedWrapper(_WrapperBase):
    def __call__(self, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)
        try:
            return cache[key]
        except KeyError:
            pass  # key not found
        val = self.__wrapped__(self._obj, *args, **kwargs)
        try:
            cache[key] = val
        except ValueError:
            pass  # value too large
        return val

    def cache_clear(self):
        self.cache.clear()


class _LockedWrapper(_WrapperBase):
    def __call__(self, *args, **kwargs):
        cache = self.cache
        lock = self.cache_lock
        key = self.cache_key(*args, **kwargs)
        with lock:
            try:
                return cache[key]
            except KeyError:
                pass  # key not found
        val = self.__wrapped__(self._obj, *args, **kwargs)
        with lock:
            try:
                # In case of a race condition, i.e. if another thread
                # stored a value for this key while we were calling
                # self.__wrapped__(), prefer the cached value.
                return cache.setdefault(key, val)
            except ValueError:
                return val  # value too large

    def cache_clear(self):
        with self.cache_lock:
            self.cache.clear()


class _ConditionWrapper(_WrapperBase):
    def __init__(self, obj, name, method, cache, key, lock, cond):
        super().__init__(obj, name, method, cache, key, lock, cond)
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
            val = self.__wrapped__(self._obj, *args, **kwargs)
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


class _UnlockedInfoWrapper(_WrapperBase):
    def __init__(self, obj, name, method, cache, key, info):
        super().__init__(obj, name, method, cache, key)
        self.__info = info
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
        val = self.__wrapped__(self._obj, *args, **kwargs)
        try:
            cache[key] = val
        except ValueError:
            pass  # value too large
        return val

    def cache_clear(self):
        self.cache.clear()
        self.__hits = self.__misses = 0

    def cache_info(self):
        return self.__info(self.cache, self.__hits, self.__misses)


class _LockedInfoWrapper(_WrapperBase):
    def __init__(self, obj, name, method, cache, key, lock, info):
        super().__init__(obj, name, method, cache, key, lock)
        self.__info = info
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
        val = self.__wrapped__(self._obj, *args, **kwargs)
        with lock:
            try:
                # In case of a race condition, i.e. if another thread
                # stored a value for this key while we were calling
                # self.__wrapped__(), prefer the cached value.
                return cache.setdefault(key, val)
            except ValueError:
                return val  # value too large

    def cache_clear(self):
        with self.cache_lock:
            self.cache.clear()
            self.__hits = self.__misses = 0

    def cache_info(self):
        with self.cache_lock:
            return self.__info(self.cache, self.__hits, self.__misses)


class _ConditionInfoWrapper(_WrapperBase):
    def __init__(self, obj, name, method, cache, key, lock, cond, info):
        super().__init__(obj, name, method, cache, key, lock, cond)
        self.__info = info
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
            val = self.__wrapped__(self._obj, *args, **kwargs)
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
            return self.__info(self.cache, self.__hits, self.__misses)


def _wrapper(method, cache, key, lock=None, cond=None, info=None):
    if info is not None:
        if cond is not None and lock is not None:
            wrapper = lambda obj, name: _ConditionInfoWrapper(
                obj, name, method, cache, key, lock, cond, info
            )
        elif cond is not None:
            wrapper = lambda obj, name: _ConditionInfoWrapper(
                obj, name, method, cache, key, cond, cond, info
            )
        elif lock is not None:
            wrapper = lambda obj, name: _LockedInfoWrapper(
                obj, name, method, cache, key, lock, info
            )
        else:
            wrapper = lambda obj, name: _UnlockedInfoWrapper(
                obj, name, method, cache, key, info
            )
    else:
        if cond is not None and lock is not None:
            wrapper = lambda obj, name: _ConditionWrapper(
                obj, name, method, cache, key, lock, cond
            )
        elif cond is not None:
            wrapper = lambda obj, name: _ConditionWrapper(
                obj, name, method, cache, key, cond, cond
            )
        elif lock is not None:
            wrapper = lambda obj, name: _LockedWrapper(
                obj, name, method, cache, key, lock
            )
        else:
            wrapper = lambda obj, name: _UnlockedWrapper(obj, name, method, cache, key)
    descriptor = _MethodDescriptor(wrapper)
    # functools.update_wrapper() will not accept descriptor (decorator) as wrapper
    # https://github.com/python/typeshed/issues/9846
    return functools.update_wrapper(descriptor, method)  # type: ignore
