"""Method decorator helpers."""

import functools
import weakref


class BaseDescriptor:

    def __init__(self, method, cache, key, lock=None, cond=None):
        # print("init", self, method, cache, key)
        self.method = method
        self.cache = cache
        self.cache_key = key
        # TODO: always present? check @cached!
        self.cache_lock = lock
        self.cache_condition = cond
        functools.update_wrapper(self, method)

    def __get__(self, obj, objtype=None):
        # print("get", self, obj, objtype)
        wrapper = functools.partial(self.__call__, obj)
        wrapper.cache = self.cache
        wrapper.cache_key = self.cache_key
        wrapper.cache_lock = self.cache_lock
        wrapper.cache_condition = self.cache_condition
        wrapper.cache_clear = self.cache_clear
        functools.update_wrapper(wrapper, self.method)
        return wrapper

    def __call__(self, obj, *args, **kwargs):
        # print("call", self, obj, args, kwargs)
        c = self.cache(obj)
        k = self.cache_key(obj, *args, **kwargs)
        try:
            return c[k]
        except KeyError:
            pass  # key not found
        v = self.method(obj, *args, **kwargs)
        try:
            c[k] = v
        except ValueError:
            pass  # value too large
        return v

    def cache_clear(self, obj=None):
        # print("clear", self, obj)
        c = self.cache(obj)
        if c is not None:
            c.clear()


class LockedDescriptor(BaseDescriptor):

    def __call__(self, obj, *args, **kwargs):
        # print("call", self, obj, args, kwargs)
        c = self.cache(obj)
        k = self.cache_key(obj, *args, **kwargs)
        with self.cache_lock(obj):
            try:
                return c[k]
            except KeyError:
                pass  # key not found
        v = self.method(obj, *args, **kwargs)
        # in case of a race, prefer the item already in the cache
        with self.cache_lock(obj):
            try:
                return c.setdefault(k, v)
            except ValueError:
                return v  # value too large

    def cache_clear(self, obj=None):
        # print("clear", self, obj)
        c = self.cache(obj)
        if c is not None:
            with self.cache_lock(obj):
                c.clear()


class ConditionDescriptor(LockedDescriptor):

    def __init__(self, method, cache, key, lock, cond):
        LockedDescriptor.__init__(self, method, cache, key, lock, cond)
        # FIXME: private?
        self.pending = weakref.WeakKeyDictionary()

    def __call__(self, obj, *args, **kwargs):
        # print("call", self, obj, args, kwargs)
        c = self.cache(obj)
        k = self.cache_key(obj, *args, **kwargs)
        with self.cache_lock(obj):
            p = self.pending.setdefault(obj, set())
            self.cache_condition(obj).wait_for(lambda: k not in p)
            try:
                return c[k]
            except KeyError:
                p.add(k)
        try:
            v = self.method(obj, *args, **kwargs)
            with self.cache_lock(obj):
                try:
                    c[k] = v
                except ValueError:
                    pass  # value too large
                return v
        finally:
            with self.cache_lock(obj):
                self.pending[obj].remove(k)
                self.cache_condition(obj).notify_all()


class InfoDescriptor(BaseDescriptor):

    HITS = 0
    MISSES = 1

    def __init__(self, method, cache, key, info, lock=None, cond=None):
        BaseDescriptor.__init__(self, method, cache, key, lock, cond)
        self.info = info
        self.stats = weakref.WeakKeyDictionary()

    def __get__(self, obj, objtype=None):
        wrapper = BaseDescriptor.__get__(self, obj, objtype)
        wrapper.cache_info = functools.partial(self.cache_info, obj)
        return wrapper

    def __call__(self, obj, *args, **kwargs):
        c = self.cache(obj)
        k = self.cache_key(obj, *args, **kwargs)
        s = self.stats.setdefault(obj, [0, 0])
        try:
            result = c[k]
            s[self.HITS] += 1
            return result
        except KeyError:
            s[self.MISSES] += 1
        v = self.method(obj, *args, **kwargs)
        try:
            c[k] = v
        except ValueError:
            pass  # value too large
        return v

    def cache_clear(self, obj=None):
        print("clear", self, obj)
        c = self.cache(obj)
        if c is not None:
            self.stats[obj] = [0, 0]
            c.clear()

    def cache_info(self, obj=None):
        print("cache_info", self, obj, self.stats)
        hits, misses = self.stats.setdefault(obj, [0, 0])
        return self.info(self.cache(obj), hits, misses)


class LockedInfoDescriptor(InfoDescriptor):

    def __call__(self, obj, *args, **kwargs):
        # print("call", self, obj, args, kwargs)
        c = self.cache(obj)
        k = self.cache_key(obj, *args, **kwargs)
        with self.cache_lock(obj):
            try:
                result = c[k]
                self.stats.setdefault(obj, [0, 0])[self.HITS] += 1
                return result
            except KeyError:
                self.stats.setdefault(obj, [0, 0])[self.MISSES] += 1
        v = self.method(obj, *args, **kwargs)
        # in case of a race, prefer the item already in the cache
        with self.cache_lock(obj):
            try:
                return c.setdefault(k, v)
            except ValueError:
                return v  # value too large

    def cache_clear(self, obj=None):
        # print("clear", self, obj)
        c = self.cache(obj)
        with self.cache_lock(obj):
            c.clear()
            self.stats[obj] = [0, 0]

    def cache_info(self, obj=None):
        # print("info", self, obj)
        with self.cache_lock(obj):
            hits, misses = self.stats.setdefault(obj, [0, 0])
        return self.info(self.cache(obj), hits, misses)


class ConditionInfoDescriptor(LockedDescriptor):

    def __init__(self, method, cache, key, info, lock, cond):
        LockedInfoDescriptor.__init__(self, method, cache, key, info, lock, cond)
        # FIXME: private?
        self.pending = weakref.WeakKeyDictionary()

    def __call__(self, obj, *args, **kwargs):
        # print("call", self, obj, args, kwargs)
        c = self.cache(obj)
        k = self.cache_key(obj, *args, **kwargs)
        with self.cache_lock(obj):
            p = self.pending.setdefault(self, set())
            self.cache_condition(obj).wait_for(lambda: k not in p)
            try:
                result = c[k]
                self.stats.setdefault(self, [0, 0])[self.HITS] += 1
                return result
            except KeyError:
                self.stats.setdefault(self, [0, 0])[self.MISSES] += 1
                p.add(k)
        try:
            v = self.method(obj, *args, **kwargs)
            with self.cache_lock(obj):
                try:
                    c[k] = v
                except ValueError:
                    pass  # value too large
                return v
        finally:
            with self.cache_lock(obj):
                self.pending[obj].remove(k)
                self.cache_condition(obj).notify_all()


def _wrapper(method, cache, key, lock=None, cond=None, info=None):

    if info:
        # FIXME: Full info support
        # if cond is not None and lock is not None:
        #     return ConditionInfoDescriptor(method, cache, key, info, lock, cond)
        # elif cond is not None:
        #     return ConditionInfoDescriptor(method, cache, key, info, cond, cond)
        # elif lock is not None:
        #     return LockedInfoDescriptor(method, cache, key, info, lock)
        # else:
        return InfoDescriptor(method, cache, key, info)
    else:
        if cond is not None and lock is not None:
            return ConditionDescriptor(method, cache, key, lock, cond)
        elif cond is not None:
            return ConditionDescriptor(method, cache, key, cond, cond)
        elif lock is not None:
            return LockedDescriptor(method, cache, key, lock)
        else:
            return BaseDescriptor(method, cache, key)
