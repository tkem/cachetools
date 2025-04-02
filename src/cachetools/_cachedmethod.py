"""Method decorator helpers."""

import weakref


def _cachedmethod_condition(method, cache, key, lock, cond):
    pending = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)
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
        if c is not None:
            with lock(self):
                c.clear()

    wrapper.cache_clear = cache_clear
    return wrapper


def _cachedmethod_locked(method, cache, key, lock):
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


def _cachedmethod_unlocked(method, cache, key):
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


def _cachedmethod_wrapper(func, cache, key, lock=None, cond=None):
    if cond is not None and lock is not None:
        wrapper = _cachedmethod_condition(func, cache, key, lock, cond)
    elif cond is not None:
        wrapper = _cachedmethod_condition(func, cache, key, cond, cond)
    elif lock is not None:
        wrapper = _cachedmethod_locked(func, cache, key, lock)
    else:
        wrapper = _cachedmethod_unlocked(func, cache, key)
    return wrapper
