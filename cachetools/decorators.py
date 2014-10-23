import collections
import contextlib  # noqa
import functools

try:
    from contextlib import ExitStack as NullContext  # Python 3.3
except ImportError:
    class NullContext:
        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

CacheInfo = collections.namedtuple('CacheInfo', 'hits misses maxsize currsize')

nullcontext = NullContext()


def makekey_untyped(args, kwargs):
    return (args, tuple(sorted(kwargs.items())))


def makekey_typed(args, kwargs):
    key = makekey_untyped(args, kwargs)
    key += tuple(type(v) for v in args)
    key += tuple(type(v) for _, v in sorted(kwargs.items()))
    return key


def cachedfunc(cache, typed=False, lock=None):
    makekey = makekey_typed if typed else makekey_untyped
    context = lock() if lock else nullcontext

    def decorator(func):
        stats = [0, 0]

        def wrapper(*args, **kwargs):
            key = makekey(args, kwargs)
            with context:
                try:
                    result = cache[key]
                    stats[0] += 1
                    return result
                except KeyError:
                    stats[1] += 1
            result = func(*args, **kwargs)
            with context:
                cache[key] = result
            return result

        def cache_info():
            with context:
                hits, misses = stats
                maxsize = cache.maxsize
                currsize = cache.currsize
            return CacheInfo(hits, misses, maxsize, currsize)

        def cache_clear():
            with context:
                cache.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return functools.update_wrapper(wrapper, func)

    return decorator


def cachedmethod(cache, typed=False):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a (possibly shared) cache.

    """
    makekey = makekey_typed if typed else makekey_untyped

    def decorator(method):
        def wrapper(self, *args, **kwargs):
            mapping = cache(self)
            if mapping is None:
                return method(self, *args, **kwargs)
            key = makekey((method,) + args, kwargs)
            try:
                return mapping[key]
            except KeyError:
                pass
            result = method(self, *args, **kwargs)
            mapping[key] = result
            return result

        wrapper.cache = cache
        return functools.update_wrapper(wrapper, method)

    return decorator
