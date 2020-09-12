import functools

from .keys import hashkey


def cached(cache, key=hashkey, lock=None):
    """Decorator to wrap a function with a memoizing callable that saves
    results in a cache.

    """
    def decorator(func):
        if cache is None:
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
        elif lock is None:
            def wrapper(*args, **kwargs):
                k = key(*args, **kwargs)
                try:
                    return cache[k]
                except KeyError:
                    pass  # key not found
                v = func(*args, **kwargs)
                try:
                    return cache.setdefault(k, v)
                except ValueError:
                    return v  # value too large; just return it without caching
        else:
            def wrapper(*args, **kwargs):
                k = key(*args, **kwargs)
                try:
                    with lock:
                        return cache[k]
                except KeyError:
                    pass  # key not found
                v = func(*args, **kwargs)
                try:
                    with lock:
                        return cache.setdefault(k, v)
                except ValueError:
                    return v  # value too large; just return it without caching
        return functools.update_wrapper(wrapper, func)
    return decorator


def cachedmethod(cache, key=hashkey, lock=None):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a cache.

    """
    def decorator(method):
        if lock is None:
            def wrapper(self, *args, **kwargs):
                c = cache(self)
                if c is None:
                    return method(self, *args, **kwargs)
                k = key(*args, **kwargs)
                try:
                    return c[k]
                except KeyError:
                    pass  # key not found
                v = method(self, *args, **kwargs)
                try:
                    return c.setdefault(k, v)
                except ValueError:
                    return v  # value too large; just return it without caching
        else:
            def wrapper(self, *args, **kwargs):
                c = cache(self)
                if c is None:
                    return method(self, *args, **kwargs)
                k = key(*args, **kwargs)
                try:
                    with lock(self):
                        return c[k]
                except KeyError:
                    pass  # key not found
                v = method(self, *args, **kwargs)
                try:
                    with lock(self):
                        return c.setdefault(k, v)
                except ValueError:
                    return v  # value too large; just return it without caching
        return functools.update_wrapper(wrapper, method)
    return decorator
