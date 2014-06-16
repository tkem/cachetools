"""Extensible memoizing collections and decorators"""

import collections
import functools
import operator
import random
import time

try:
    from threading import RLock
except ImportError:
    from dummy_threading import RLock

__version__ = '0.4.0'

_marker = object()


class _Link(object):
    __slots__ = 'prev', 'next', 'data'


class Cache(collections.MutableMapping):
    """Mutable mapping to serve as a simple cache or cache base class.

    This class discards arbitrary items using :meth:`popitem` to make
    space when necessary.  Derived classes may override
    :meth:`popitem` to implement specific caching strategies.  If a
    subclass has to keep track of item access, insertion or deletion,
    it may need override :meth:`__getitem__`, :meth:`__setitem__` and
    :meth:`__delitem__`, too.

    """

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is not None:
            self.getsizeof = getsizeof
        self.__mapping = dict()
        self.__maxsize = maxsize
        self.__currsize = 0

    def __getitem__(self, key):
        return self.__mapping[key][0]

    def __setitem__(self, key, value):
        mapping = self.__mapping
        maxsize = self.__maxsize
        size = self.getsizeof(value)
        if size > maxsize:
            raise ValueError('value too large')
        if key not in mapping or mapping[key][1] < size:
            while self.__currsize + size > maxsize:
                self.popitem()
        if key in mapping:
            self.__currsize -= mapping[key][1]
        mapping[key] = (value, size)
        self.__currsize += size

    def __delitem__(self, key):
        _, size = self.__mapping.pop(key)
        self.__currsize -= size

    def __iter__(self):
        return iter(self.__mapping)

    def __len__(self):
        return len(self.__mapping)

    def __repr__(self):
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            list(self.items()),
            self.__maxsize,
            self.__currsize,
        )

    @property
    def maxsize(self):
        """Return the maximum size of the cache."""
        return self.__maxsize

    @property
    def currsize(self):
        """Return the current size of the cache."""
        return self.__currsize

    @staticmethod
    def getsizeof(value):
        """Return the size of a cache element."""
        return 1


class RRCache(Cache):
    """Random Replacement (RR) cache implementation.

    This class randomly selects candidate items and discards them to
    make space when necessary.

    """

    def popitem(self):
        """Remove and return a random `(key, value)` pair."""
        try:
            key = random.choice(list(self))
        except IndexError:
            raise KeyError('cache is empty')
        return (key, self.pop(key))


class LFUCache(Cache):
    """Least Frequently Used (LFU) cache implementation.

    This class counts how often an item is retrieved, and discards the
    items used least often to make space when necessary.

    """

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is not None:
            Cache.__init__(self, maxsize, lambda e: getsizeof(e[0]))
        else:
            Cache.__init__(self, maxsize)

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        entry = cache_getitem(self, key)
        entry[1] += 1
        return entry[0]

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, [value, 0])

    def popitem(self):
        """Remove and return the `(key, value)` pair least frequently used."""
        items = ((key, Cache.__getitem__(self, key)[1]) for key in self)
        try:
            key, _ = min(items, key=operator.itemgetter(1))
        except ValueError:
            raise KeyError('cache is empty')
        return (key, self.pop(key))


class LRUCache(Cache):
    """Least Recently Used (LRU) cache implementation.

    This class discards the least recently used items first to make
    space when necessary.

    """

    def __init__(self, maxsize, getsizeof=None):
        if getsizeof is not None:
            Cache.__init__(self, maxsize, lambda e: getsizeof(e[0]))
        else:
            Cache.__init__(self, maxsize)
        root = _Link()
        root.prev = root.next = root
        self.__root = root

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value, link = cache_getitem(self, key)
        root = self.__root
        link.prev.next = link.next
        link.next.prev = link.prev
        link.prev = tail = root.prev
        link.next = root
        tail.next = root.prev = link
        return value

    def __setitem__(self, key, value,
                    cache_getitem=Cache.__getitem__,
                    cache_setitem=Cache.__setitem__):
        try:
            _, link = cache_getitem(self, key)
        except KeyError:
            link = _Link()
        cache_setitem(self, key, (value, link))
        try:
            link.prev.next = link.next
            link.next.prev = link.prev
        except AttributeError:
            link.data = key
        root = self.__root
        link.prev = tail = root.prev
        link.next = root
        tail.next = root.prev = link

    def __delitem__(self, key,
                    cache_getitem=Cache.__getitem__,
                    cache_delitem=Cache.__delitem__):
        _, link = cache_getitem(self, key)
        cache_delitem(self, key)
        link.prev.next = link.next
        link.next.prev = link.prev
        del link.next
        del link.prev

    def __repr__(self, cache_getitem=Cache.__getitem__):
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            [(key, cache_getitem(self, key)[0]) for key in self],
            self.maxsize,
            self.currsize,
        )

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used."""
        root = self.__root
        link = root.next
        if link is root:
            raise KeyError('cache is empty')
        key = link.data
        return (key, self.pop(key))


class TTLCache(LRUCache):
    """Cache implementation with per-item time-to-live (TTL) value.

    This class associates a time-to-live value with each item.  Items
    that expire because they have exceeded their time-to-live will be
    removed automatically.  If no expired items are there to remove,
    the least recently used items will be discarded first to make
    space when necessary.

    """

    def __init__(self, maxsize, ttl, getsizeof=None, timer=time.time):
        if getsizeof is not None:
            LRUCache.__init__(self, maxsize, lambda e: getsizeof(e[0]))
        else:
            LRUCache.__init__(self, maxsize)
        root = _Link()
        root.prev = root.next = root
        self.__root = root
        self.__timer = timer
        self.__ttl = ttl

    def __getitem__(self, key,
                    cache_getitem=LRUCache.__getitem__,
                    cache_delitem=LRUCache.__delitem__):
        value, link = cache_getitem(self, key)
        if self.__timer() < link.data[1]:
            return value
        root = self.__root
        head = root.next
        link = link.next
        while head is not link:
            cache_delitem(self, head.data[0])
            head.next.prev = root
            head = root.next = head.next
        raise KeyError('%r has expired' % key)

    def __setitem__(self, key, value,
                    cache_getitem=LRUCache.__getitem__,
                    cache_setitem=LRUCache.__setitem__,
                    cache_delitem=LRUCache.__delitem__):
        root = self.__root
        head = root.next
        time = self.__timer()
        while head is not root and head.data[1] < time:
            cache_delitem(self, head.data[0])
            head.next.prev = root
            head = root.next = head.next
        try:
            _, link = cache_getitem(self, key)
        except KeyError:
            link = _Link()
        cache_setitem(self, key, (value, link))
        try:
            link.prev.next = link.next
            link.next.prev = link.prev
        except AttributeError:
            pass
        link.data = (key, time + self.__ttl)
        link.prev = tail = root.prev
        link.next = root
        tail.next = root.prev = link

    def __delitem__(self, key,
                    cache_getitem=LRUCache.__getitem__,
                    cache_delitem=LRUCache.__delitem__):
        _, link = cache_getitem(self, key)
        cache_delitem(self, key)
        link.prev.next = link.next
        link.next.prev = link.prev

    def __repr__(self, cache_getitem=LRUCache.__getitem__):
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            [(key, cache_getitem(self, key)[0]) for key in self],
            self.maxsize,
            self.currsize,
        )

    def pop(self, key, default=_marker):
        try:
            value, link = LRUCache.__getitem__(self, key)
        except KeyError:
            if default is not _marker:
                return default
            raise
        LRUCache.__delitem__(self, key)
        link.prev.next = link.next
        link.next.prev = link.prev
        del link.next
        del link.prev
        return value


CacheInfo = collections.namedtuple('CacheInfo', 'hits misses maxsize currsize')


def _makekey(args, kwargs):
    return (args, tuple(sorted(kwargs.items())))


def _makekey_typed(args, kwargs):
    key = _makekey(args, kwargs)
    key += tuple(type(v) for v in args)
    key += tuple(type(v) for k, v in sorted(kwargs.items()))
    return key


def _cachedfunc(cache, makekey, lock):
    def decorator(func):
        stats = [0, 0]

        def wrapper(*args, **kwargs):
            key = makekey(args, kwargs)
            with lock:
                try:
                    result = cache[key]
                    stats[0] += 1
                    return result
                except KeyError:
                    stats[1] += 1
            result = func(*args, **kwargs)
            with lock:
                cache[key] = result
            return result

        def cache_info():
            with lock:
                hits, misses = stats
                maxsize = cache.maxsize
                currsize = cache.currsize
            return CacheInfo(hits, misses, maxsize, currsize)

        def cache_clear():
            with lock:
                cache.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return functools.update_wrapper(wrapper, func)

    return decorator


def lru_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Recently Used (LRU)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(LRUCache(maxsize, getsizeof), makekey, lock())


def lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Least Frequently Used (LFU)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(LFUCache(maxsize, getsizeof), makekey, lock())


def rr_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    makekey = _makekey_typed if typed else _makekey
    return _cachedfunc(RRCache(maxsize, getsizeof), makekey, lock())


def cachedmethod(cache, typed=False):
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a (possibly shared) cache.

    """
    makekey = _makekey_typed if typed else _makekey

    def decorator(method):
        def wrapper(self, *args, **kwargs):
            # TODO: `shared`, locking...
            key = makekey((method,) + args, kwargs)
            mapping = cache(self)
            try:
                return mapping[key]
            except KeyError:
                pass
            result = method(self, *args, **kwargs)
            mapping[key] = result
            return result

        return functools.update_wrapper(wrapper, method)

    return decorator
