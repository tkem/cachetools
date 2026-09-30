"""Function decorator helpers.

At least for now, the implementation prefers clarity and performance
over ease of maintenance, thus providing separate wrappers for all
valid combinations of parameters lock, condition and info.

"""

# pyright: reportOptionalContextManager=false, reportOptionalMemberAccess=false

__all__ = ()

import functools


class _WrapperBase:
    """Wrapper base class providing default implementations for properties."""

    def __init__(self, func, cache, key, lock=None, cond=None):
        self.__wrapped__ = func  # FIXME: silence pyright reportAttributeAccessIssue
        # functools.update_wrapper(self, func)
        # TODO: make this methods, so they can be overloaded?
        self.cache = cache
        self.cache_key = key
        self.cache_lock = lock
        self.cache_condition = cond

    def __call__(self, *args, **kwargs):
        raise NotImplementedError()  # pragma: no cover

    # def __reduce__(self):
    #    # rebuild via the descriptor instead of pickling unpicklable
    #    # internals, e.g. __wrapped__, lock/cond closures; note that
    #    # this will also reset hits and misses counts for *Info*
    #    # wrappers
    #    if self._obj is None:
    #        raise TypeError(f"Cannot pickle {self.__name!r}")
    #    return (getattr, (self._obj, self.__name))

    def cache_clear(self):
        raise NotImplementedError()  # pragma: no cover


class _UnlockedWrapper(_WrapperBase):
    def __call__(self, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)
        try:
            return cache[key]
        except KeyError:
            pass  # key not found
        val = self.__wrapped__(*args, **kwargs)
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
        val = self.__wrapped__(*args, **kwargs)
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


class _ConditionWrapper(_LockedWrapper):
    def __init__(self, func, cache, key, lock, cond):
        super().__init__(func, cache, key, lock, cond)
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
            val = self.__wrapped__(*args, **kwargs)
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


class _UnlockedInfoWrapper(_WrapperBase):
    def __init__(self, func, cache, key, info):
        super().__init__(func, cache, key)
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
        val = self.__wrapped__(*args, **kwargs)
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
        # return self.__info(self.__hits, self.__misses)


class _LockedInfoWrapper(_WrapperBase):
    def __init__(self, func, cache, key, lock, info):
        super().__init__(func, cache, key, lock)
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
        val = self.__wrapped__(*args, **kwargs)
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
            # return self.__info(self.__hits, self.__misses)


class _ConditionInfoWrapper(_WrapperBase):
    def __init__(self, func, cache, key, lock, cond, info):
        super().__init__(func, cache, key, lock, cond)
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
            val = self.__wrapped__(*args, **kwargs)
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
            # return self.__info(self.__hits, self.__misses)


def _wrapper(func, cache, key, lock=None, cond=None, info=None):
    if info is not None:
        if cond is not None and lock is not None:
            wrapper = _ConditionInfoWrapper(func, cache, key, lock, cond, info)
        elif cond is not None:
            wrapper = _ConditionInfoWrapper(func, cache, key, cond, cond, info)
        elif lock is not None:
            wrapper = _LockedInfoWrapper(func, cache, key, lock, info)
        else:
            wrapper = _UnlockedInfoWrapper(func, cache, key, info)
    else:
        if cond is not None and lock is not None:
            wrapper = _ConditionWrapper(func, cache, key, lock, cond)
        elif cond is not None:
            wrapper = _ConditionWrapper(func, cache, key, cond, cond)
        elif lock is not None:
            wrapper = _LockedWrapper(func, cache, key, lock)
        else:
            wrapper = _UnlockedWrapper(func, cache, key)
    return functools.update_wrapper(wrapper, func)
