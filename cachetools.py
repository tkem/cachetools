"""Python 2.7 memoizing collections and decorators"""
import collections
import functools
import threading

__version__ = '0.0.0'


CacheInfo = collections.namedtuple('CacheInfo', 'hits misses maxsize currsize')


class LRUCache(collections.MutableMapping):

    def __init__(self, maxsize, lock=threading.RLock):
        self.__maxsize = maxsize
        self.__lock = lock()
        self.__cache = collections.OrderedDict()
        self.__hits = 0
        self.__misses = 0

    def __getitem__(self, key):
        with self.__lock:
            try:
                value = self.__cache[key]
            except KeyError:
                self.__misses += 1
                raise
            self.__hits += 1
            self._update(key, value)
            return value

    def __setitem__(self, key, value):
        with self.__lock:
            if len(self.__cache) >= self.__maxsize:
                # FIXME: popitem
                del self.__cache[next(iter(self.__cache))]
            self.__cache[key] = value
            self._update(key, value)

    def __delitem__(self, key):
        with self._lock:
            del self.__cache[key]

    def __iter__(self):
        return iter(self.__cache)

    def __len__(self):
        return len(self.__cache)

    def _update(self, key, value):
        del self.__cache[key]
        self.__cache[key] = value

    def info(self):
        return CacheInfo(self.__hits, self.__misses, self.__maxsize, len(self))


class LFUCache(collections.MutableMapping):

    def __init__(self, maxsize, lock=threading.RLock):
        self.__maxsize = maxsize
        self.__lock = lock()
        self.__cache = {}
        self.__count = collections.Counter()
        self.__hits = 0
        self.__misses = 0

    def __getitem__(self, key):
        with self.__lock:
            value = self.__cache[key]
            self.__count[key] += 1
            return value

    def __setitem__(self, key, value):
        with self.__lock:
            if len(self.__cache) >= self.__maxsize:
                key, _ = self.__count.most_common()[-1]
                del self.__cache[key]
                del self.__count[key]
            self.__cache[key] = value
            self.__count[key] = 0

    def __delitem__(self, key):
        del self.__cache[key]
        del self.__count[key]

    def __iter__(self):
        return iter(self.__cache)

    def __len__(self):
        return len(self.__cache)

    def info(self):
        return CacheInfo(self.__hits, self.__misses, self.__maxsize, len(self))


def makekey(args, kwargs, typed=False):
    # TODO: support typed argument keys
    return (tuple(sorted(kwargs.items()))) + args


def lru_cache(maxsize=128, typed=False, key=makekey):
    def decorator(func):
        cache = LRUCache(maxsize)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = makekey(args, kwargs, typed)
            try:
                return cache[key]
            except KeyError:
                result = func(*args, **kwargs)
                cache[key] = result
                return result

        def cache_info():
            return cache.info()

        def cache_clear():
            cache.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper

    return decorator


def lfu_cache(maxsize=128, typed=False, key=makekey):
    def decorator(func):
        cache = LRUCache(maxsize)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = makekey(args, kwargs, typed)
            try:
                return cache[key]
            except KeyError:
                result = func(*args, **kwargs)
                cache[key] = result
                return result

        def cache_info():
            return cache.info()

        def cache_clear():
            cache.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper

    return decorator
