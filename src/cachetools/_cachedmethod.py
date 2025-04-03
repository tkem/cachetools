"""Method decorator helpers."""

import weakref


def _cachedmethod_condition(*, method, cache, key, lock, condition):
    pending = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)
        k = key(self, *args, **kwargs)
        with lock(self):
            p = pending.setdefault(self, set())
            condition(self).wait_for(lambda: k not in p)
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
                condition(self).notify_all()

    def cache_clear(self):
        c = cache(self)
        if c is not None:
            with lock(self):
                c.clear()

    wrapper.cache_clear = cache_clear
    return wrapper


def _cachedmethod_locked(*, method, cache, key, lock):
    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)
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
        if c is not None:
            with lock(self):
                c.clear()

    wrapper.cache_clear = cache_clear
    return wrapper


def _cachedmethod_unlocked(*, method, cache, key):
    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)
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
        if c is not None:
            c.clear()

    wrapper.cache_clear = cache_clear
    return wrapper


def _cachedmethod_wrapper(*, method, cache, key, lock=None, condition=None):
    if condition is not None and lock is not None:
        wrapper = _cachedmethod_condition(
            method=method, cache=cache, key=key, lock=lock, condition=condition
        )
    elif condition is not None:
        # passing lock=condition because _cachedmethod_condition does 'with lock(self)'
        wrapper = _cachedmethod_condition(
            method=method, cache=cache, key=key, lock=condition, condition=condition
        )
    elif lock is not None:
        wrapper = _cachedmethod_locked(method=method, cache=cache, key=key, lock=lock)
    else:
        wrapper = _cachedmethod_unlocked(method=method, cache=cache, key=key)
    return wrapper
