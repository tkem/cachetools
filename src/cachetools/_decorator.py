"""Mixin helpers.

At least for now, the implementation prefers clarity and performance
over ease of maintenance, thus providing separate wrappers for all
valid combinations of parameters lock, condition and info.

"""

# pyright: reportAttributeAccessIssue=false

__all__ = ()


class _BasicMixin:
    def __init__(self, func):
        self.__func = func

    def __call__(self, /, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)

        try:
            return cache[key]
        except KeyError:
            pass  # key not found
        val = self.__func(*args, **kwargs)
        try:
            cache[key] = val
        except ValueError:
            pass  # value too large
        return val

    def cache_clear(self):
        self.cache.clear()


class _LockedMixin:
    def __init__(self, func):
        self.__func = func

    def __call__(self, /, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)
        lock = self.cache_lock

        with lock:
            try:
                return cache[key]
            except KeyError:
                pass  # key not found
        val = self.__func(*args, **kwargs)
        with lock:
            try:
                # In case of a race condition, i.e. if another thread
                # stored a value for this key while we were calling
                # self.__func(), prefer the cached value.
                return cache.setdefault(key, val)
            except ValueError:
                return val  # value too large

    def cache_clear(self):
        with self.cache_lock:
            self.cache.clear()


class _ConditionMixin:
    def __init__(self, func):
        from threading import get_ident

        self.__func = func
        self.__get_ident = get_ident
        self.__pending = {}  # maps keys to the calling thread

    def __call__(self, /, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)
        lock = self.cache_lock
        cond = self.cache_condition

        with lock:
            while key in self.__pending:
                if self.__pending[key] == self.__get_ident():
                    # A recursive call would wait for its own pending
                    # call forever, so it calls the function again.
                    recursive = True
                    break
                cond.wait()
            else:
                try:
                    return cache[key]
                except KeyError:
                    self.__pending[key] = self.__get_ident()
                    recursive = False
        if recursive:
            return self.__func(*args, **kwargs)
        try:
            val = self.__func(*args, **kwargs)
            with lock:
                try:
                    cache[key] = val
                except ValueError:
                    pass  # value too large
                return val
        finally:
            with lock:
                del self.__pending[key]
                cond.notify_all()

    def cache_clear(self):
        with self.cache_lock:
            self.cache.clear()


class _InfoMixin:
    def __init__(self, func, info):
        self.__func = func
        self.__info = info
        self.__hits = self.__misses = 0

    def __call__(self, /, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)

        try:
            result = cache[key]
            self.__hits += 1
            return result
        except KeyError:
            self.__misses += 1
        val = self.__func(*args, **kwargs)
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


class _LockedInfoMixin:
    def __init__(self, func, info):
        self.__func = func
        self.__info = info
        self.__hits = self.__misses = 0

    def __call__(self, /, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)
        lock = self.cache_lock

        with lock:
            try:
                result = cache[key]
                self.__hits += 1
                return result
            except KeyError:
                self.__misses += 1
        val = self.__func(*args, **kwargs)
        with lock:
            try:
                # In case of a race condition, i.e. if another thread
                # stored a value for this key while we were calling
                # self.__func(), prefer the cached value.
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


class _ConditionInfoMixin:
    def __init__(self, func, info):
        from threading import get_ident

        self.__func = func
        self.__info = info
        self.__hits = self.__misses = 0
        self.__get_ident = get_ident
        self.__pending = {}  # maps keys to the calling thread

    def __call__(self, /, *args, **kwargs):
        cache = self.cache
        key = self.cache_key(*args, **kwargs)
        lock = self.cache_lock
        cond = self.cache_condition

        with lock:
            while key in self.__pending:
                if self.__pending[key] == self.__get_ident():
                    # A recursive call would wait for its own pending
                    # call forever, so it calls the function again.
                    self.__misses += 1
                    recursive = True
                    break
                cond.wait()
            else:
                try:
                    result = cache[key]
                    self.__hits += 1
                    return result
                except KeyError:
                    self.__pending[key] = self.__get_ident()
                    self.__misses += 1
                    recursive = False
        if recursive:
            return self.__func(*args, **kwargs)
        try:
            val = self.__func(*args, **kwargs)
            with lock:
                try:
                    cache[key] = val
                except ValueError:
                    pass  # value too large
                return val
        finally:
            with lock:
                del self.__pending[key]
                cond.notify_all()

    def cache_clear(self):
        with self.cache_lock:
            self.cache.clear()
            self.__hits = self.__misses = 0

    def cache_info(self):
        with self.cache_lock:
            return self.__info(self.cache, self.__hits, self.__misses)
