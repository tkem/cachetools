"""Method decorator helpers."""

import weakref

HITS = 0
MISSES = 1


def _cachedmethod_condition_info(method, cache, key, lock, cond, info):
    pending = weakref.WeakKeyDictionary()
    stats = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            with lock(self):
                stats.setdefault(self, [0, 0])[MISSES] += 1
            return method(self, *args, **kwargs)
        k = key(self, *args, **kwargs)
        with lock(self):
            p = pending.setdefault(self, set())
            cond(self).wait_for(lambda: k not in p)
            try:
                result = c[k]
                stats.setdefault(self, [0, 0])[HITS] += 1
                return result
            except KeyError:
                stats.setdefault(self, [0, 0])[MISSES] += 1
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
            if c is not None:
                c.clear()
            stats[self] = [0, 0]

    def cache_info(self):
        with lock(self):
            hits, misses = stats.setdefault(self, [0, 0])
        return info(cache(self), hits, misses)

    wrapper.cache_clear = cache_clear
    wrapper.cache_info = cache_info
    return wrapper


def _cachedmethod_locked_info(method, cache, key, lock, info):
    stats = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            with lock(self):
                stats.setdefault(self, [0, 0])[MISSES] += 1
            return method(self, *args, **kwargs)
        k = key(self, *args, **kwargs)
        with lock(self):
            try:
                result = c[k]
                stats.setdefault(self, [0, 0])[HITS] += 1
                return result
            except KeyError:
                stats.setdefault(self, [0, 0])[MISSES] += 1
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
            if c is not None:
                c.clear()
            stats[self] = [0, 0]

    def cache_info(self):
        with lock(self):
            hits, misses = stats.setdefault(self, [0, 0])
        return info(cache(self), hits, misses)

    wrapper.cache_clear = cache_clear
    wrapper.cache_info = cache_info
    return wrapper


def _cachedmethod_unlocked_info(method, cache, key, info):
    stats = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        s = stats.setdefault(self, [0, 0])
        c = cache(self)
        if c is None:
            s[MISSES] += 1
            return method(self, *args, **kwargs)
        k = key(self, *args, **kwargs)
        try:
            result = c[k]
            s[HITS] += 1
            return result
        except KeyError:
            s[MISSES] += 1
        v = method(self, *args, **kwargs)
        try:
            c[k] = v
        except ValueError:
            pass  # value too large
        return v

    def cache_clear(self):
        c = cache(self)
        if c is not None:
            stats[self] = [0, 0]
            c.clear()

    def cache_info(self):
        hits, misses = stats.setdefault(self, [0, 0])
        return info(cache(self), hits, misses)

    wrapper.cache_clear = cache_clear
    wrapper.cache_info = cache_info
    return wrapper


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


def _cachedmethod_wrapper(func, cache, key, lock=None, cond=None, info=None):
    if info:
        if cond is not None and lock is not None:
            wrapper = _cachedmethod_condition_info(func, cache, key, lock, cond, info)
        elif cond is not None:
            wrapper = _cachedmethod_condition_info(func, cache, key, cond, cond, info)
        elif lock is not None:
            wrapper = _cachedmethod_locked_info(func, cache, key, lock, info)
        else:
            wrapper = _cachedmethod_unlocked_info(func, cache, key, info)
    else:
        if cond is not None and lock is not None:
            wrapper = _cachedmethod_condition(func, cache, key, lock, cond)
        elif cond is not None:
            wrapper = _cachedmethod_condition(func, cache, key, cond, cond)
        elif lock is not None:
            wrapper = _cachedmethod_locked(func, cache, key, lock)
        else:
            wrapper = _cachedmethod_unlocked(func, cache, key)
    return wrapper
