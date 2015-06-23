import functools


def cachekey(*args, **kwargs):
    return (args, tuple(sorted(kwargs.items())))


def _typedkey(method, *args, **kwargs):
    key = cachekey(method, *args, **kwargs)
    key += tuple(type(v) for v in args)
    key += tuple(type(v) for _, v in sorted(kwargs.items()))
    return key


def cache(cache, key=cachekey, lock=None):
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
                    cache[k] = v
                except ValueError:
                    pass  # value too large
                return v
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
                        cache[k] = v
                except ValueError:
                    pass  # value too large
                return v
        functools.update_wrapper(wrapper, func)
        if not hasattr(wrapper, '__wrapped__'):
            wrapper.__wrapped__ = func  # Python < 3.2
        return wrapper
    return decorator


def cachedmethod(cache, typed=False):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a (possibly shared) cache.

    """
    key = _typedkey if typed else cachekey

    def decorator(method):
        def wrapper(self, *args, **kwargs):
            c = cache(self)
            if c is None:
                return method(self, *args, **kwargs)
            k = key(method, *args, **kwargs)
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

        wrapper.cache = cache
        return functools.update_wrapper(wrapper, method)

    return decorator
