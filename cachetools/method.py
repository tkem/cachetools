import functools


def _makekey_untyped(method, args, kwargs):
    return (method, args, tuple(sorted(kwargs.items())))


def _makekey_typed(method, args, kwargs):
    key = _makekey_untyped(method, args, kwargs)
    key += tuple(type(v) for v in args)
    key += tuple(type(v) for _, v in sorted(kwargs.items()))
    return key


def cachedmethod(cache, typed=False):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a (possibly shared) cache.

    """
    makekey = _makekey_typed if typed else _makekey_untyped

    def decorator(method):
        def wrapper(self, *args, **kwargs):
            mapping = cache(self)
            if mapping is None:
                return method(self, *args, **kwargs)
            key = makekey(method, args, kwargs)
            try:
                return mapping[key]
            except KeyError:
                pass
            result = method(self, *args, **kwargs)
            try:
                mapping[key] = result
            except ValueError:
                pass  # value too large
            return result

        wrapper.cache = cache
        return functools.update_wrapper(wrapper, method)

    return decorator
