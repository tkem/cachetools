"""Extensible memoizing collections and decorators."""

__all__ = (
    "Cache",
    "FIFOCache",
    "LFUCache",
    "LRUCache",
    "RRCache",
    "TLRUCache",
    "TTLCache",
    "cached",
    "cachedmethod",
)

__version__ = "7.2.7"

import collections
import collections.abc
import functools
import heapq
import random
import time

from . import keys


class Cache(collections.abc.MutableMapping):
    """Mutable mapping to serve as a simple cache or cache base class."""

    __marker = object()

    __size = None

    def __init__(self, maxsize, getsizeof=None):
        if maxsize < 0:
            raise ValueError("maxsize must be non-negative")
        if getsizeof is not None:
            self.getsizeof = getsizeof
        if self.getsizeof is not Cache.getsizeof:
            self.__size = {}
        self.__data = {}
        self.__currsize = 0
        self.__maxsize = maxsize

    def __repr__(self):
        return "%s(%s, maxsize=%r, currsize=%r)" % (
            type(self).__name__,
            repr(self.__data),
            self.__maxsize,
            self.__currsize,
        )

    def __getitem__(self, key):
        try:
            return self.__data[key]
        except KeyError:
            return self.__missing__(key)

    def __setitem__(self, key, value):
        data = self.__data
        size = self.__size
        maxsize = self.__maxsize
        if size is None:
            if maxsize < 1:
                raise ValueError("value too large")
            elif key in data:
                data[key] = value
            else:
                while self.__currsize + 1 > maxsize:
                    self.popitem()
                data[key] = value
                self.__currsize += 1
        else:
            itemsize = self.getsizeof(value)
            if itemsize > maxsize:
                raise ValueError("value too large")
            if itemsize < 0:
                raise ValueError("value size must be non-negative")
            if key not in data:
                diffsize = itemsize
                while self.__currsize + diffsize > maxsize:
                    self.popitem()
            else:
                diffsize = itemsize - size[key]
                while self.__currsize + diffsize > maxsize:
                    self.popitem()
                    if key not in data:
                        diffsize = itemsize
            data[key] = value
            size[key] = itemsize
            self.__currsize += diffsize

    def __delitem__(self, key):
        size = self.__size
        if size is None:
            del self.__data[key]
            self.__currsize -= 1
        else:
            itemsize = size.pop(key)
            del self.__data[key]
            self.__currsize -= itemsize

    def __contains__(self, key):
        return key in self.__data

    def __missing__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    # Note that we cannot simply inherit get(), pop() and setdefault()
    # from MutableMapping, since these rely on __getitem__ throwing a
    # KeyError on cache miss.  This is not the case if __missing__ is
    # implemented for a Cache subclass, so we have to roll our own,
    # somewhat less elegant versions.

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default

    def pop(self, key, default=__marker):
        if key in self:
            value = self[key]
            del self[key]
        elif default is self.__marker:
            raise KeyError(key)
        else:
            value = default
        return value

    def setdefault(self, key, default=None):
        if key in self:
            value = self[key]
        else:
            self[key] = value = default
        return value

    # Although the MutableMapping.clear() default implementation works
    # perfectly well, it calls popitem() in a loop until the cache is
    # empty, resulting in O(n) complexity.  For large caches, this
    # becomes a significant performance bottleneck, so we provide an
    # optimized version for each Cache subclass.

    def clear(self):
        size = self.__size
        if size is not None:
            size.clear()
        self.__data.clear()
        self.__currsize = 0

    @property
    def maxsize(self):
        """The maximum size of the cache."""
        return self.__maxsize

    @property
    def currsize(self):
        """The current size of the cache."""
        return self.__currsize

    @staticmethod
    def getsizeof(value):
        """Return the size of a cache element's value."""
        return 1


class FIFOCache(Cache):
    """First In First Out (FIFO) cache implementation."""

    def __init__(self, maxsize, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__order = collections.OrderedDict()

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        if key in self.__order:
            self.__order.move_to_end(key)
        else:
            self.__order[key] = None

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        del self.__order[key]

    def popitem(self):
        """Remove and return the `(key, value)` pair first inserted."""
        try:
            key = next(iter(self.__order))
        except StopIteration:
            raise KeyError("%s is empty" % type(self).__name__) from None
        else:
            value = Cache.__getitem__(self, key)
            del self[key]
            return (key, value)

    def clear(self):
        Cache.clear(self)
        self.__order.clear()


class LFUCache(Cache):
    """Least Frequently Used (LFU) cache implementation."""

    class _Link:
        __slots__ = ("count", "keys", "next", "prev")

        def __init__(self, count):
            self.count = count
            self.keys = set()

        def unlink(self):
            next = self.next
            prev = self.prev
            prev.next = next
            next.prev = prev

    def __init__(self, maxsize, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__root = root = LFUCache._Link(0)  # sentinel
        root.prev = root.next = root
        self.__links = {}

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value = cache_getitem(self, key)
        if key in self.__links:  # __missing__ may not store item
            self.__touch(key)
        return value

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        if key in self.__links:
            self.__touch(key)
            return
        root = self.__root
        link = root.next
        if link.count != 1:
            link = LFUCache._Link(1)
            link.next = root.next
            root.next = link.next.prev = link
            link.prev = root
        link.keys.add(key)
        self.__links[key] = link

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        link = self.__links.pop(key)
        link.keys.remove(key)
        if not link.keys:
            link.unlink()

    def popitem(self):
        """Remove and return the `(key, value)` pair least frequently used."""
        root = self.__root
        curr = root.next
        if curr is root:
            raise KeyError("%s is empty" % type(self).__name__) from None
        key = next(iter(curr.keys))  # remove an arbitrary element
        value = Cache.__getitem__(self, key)
        del self[key]
        return (key, value)

    def clear(self):
        Cache.clear(self)
        root = self.__root
        root.prev = root.next = root
        self.__links.clear()

    def __touch(self, key):
        """Increment use count."""
        link = self.__links[key]
        curr = link.next
        if curr.count != link.count + 1:
            if len(link.keys) == 1:
                link.count += 1
                return
            curr = LFUCache._Link(link.count + 1)
            curr.next = link.next
            link.next = curr.next.prev = curr
            curr.prev = link
        curr.keys.add(key)
        link.keys.remove(key)
        if not link.keys:
            link.unlink()
        self.__links[key] = curr


class LRUCache(Cache):
    """Least Recently Used (LRU) cache implementation."""

    def __init__(self, maxsize, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__order = collections.OrderedDict()

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        value = cache_getitem(self, key)
        try:
            self.__order.move_to_end(key)
        except KeyError:  # __missing__ may not store item
            pass
        return value

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        self.__touch(key)

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        del self.__order[key]

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used."""
        try:
            key = next(iter(self.__order))
        except StopIteration:
            raise KeyError("%s is empty" % type(self).__name__) from None
        else:
            value = Cache.__getitem__(self, key)
            del self[key]
            return (key, value)

    def clear(self):
        Cache.clear(self)
        self.__order.clear()

    def __touch(self, key):
        """Mark as recently used."""
        try:
            self.__order.move_to_end(key)
        except KeyError:
            self.__order[key] = None


class RRCache(Cache):
    """Random Replacement (RR) cache implementation."""

    def __init__(self, maxsize, choice=random.choice, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__choice = choice
        self.__index = {}
        self.__keys = []

    @property
    def choice(self):
        """The `choice` function used by the cache."""
        return self.__choice

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        cache_setitem(self, key, value)
        if key not in self.__index:
            self.__index[key] = len(self.__keys)
            self.__keys.append(key)

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        index = self.__index.pop(key)
        if index != len(self.__keys) - 1:
            last = self.__keys[-1]
            self.__keys[index] = last
            self.__index[last] = index
        self.__keys.pop()

    def popitem(self):
        """Remove and return a random `(key, value)` pair."""
        keys = self.__keys
        if not keys:
            raise KeyError("%s is empty" % type(self).__name__) from None
        key = self.__choice(keys)
        value = Cache.__getitem__(self, key)
        del self[key]
        return (key, value)

    def clear(self):
        Cache.clear(self)
        self.__index.clear()
        del self.__keys[:]


class _TimedCache(Cache):
    """Base class for time-aware cache implementations."""

    class _Timer:
        def __init__(self, timer):
            self.__timer = timer
            self.__nesting = 0

        def __call__(self):
            if self.__nesting == 0:
                return self.__timer()
            else:
                return self.__time

        def __enter__(self):
            if self.__nesting == 0:
                self.__time = time = self.__timer()
            else:
                time = self.__time
            self.__nesting += 1
            return time

        def __exit__(self, *exc):
            self.__nesting -= 1

        def __reduce__(self):
            return _TimedCache._Timer, (self.__timer,)

        def __getattr__(self, name):
            return getattr(self.__timer, name)

    def __init__(self, maxsize, timer, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        self.__timer = _TimedCache._Timer(timer)

    def __repr__(self, cache_repr=Cache.__repr__):
        with self.__timer as time:
            self.expire(time)
            return cache_repr(self)

    def __len__(self, cache_len=Cache.__len__):
        with self.__timer as time:
            self.expire(time)
            return cache_len(self)

    @property
    def currsize(self):
        with self.__timer as time:
            self.expire(time)
            return super().currsize

    @property
    def timer(self):
        """The timer function used by the cache."""
        return self.__timer

    def get(self, *args, **kwargs):
        with self.__timer:
            return Cache.get(self, *args, **kwargs)

    def pop(self, *args, **kwargs):
        with self.__timer:
            return Cache.pop(self, *args, **kwargs)

    def setdefault(self, *args, **kwargs):
        with self.__timer:
            return Cache.setdefault(self, *args, **kwargs)

    def clear(self):
        # Subclasses must override to also reset their own time-tracking
        # structures; we do not call expire() here since clear() should
        # be O(1) regardless of cache contents.
        Cache.clear(self)

    def expire(self, time=None):  # pragma: no cover
        raise NotImplementedError


class TTLCache(_TimedCache):
    """LRU Cache implementation with per-item time-to-live (TTL) value."""

    class _Link:
        __slots__ = ("expires", "key", "next", "prev")

        def __init__(self, key=None, expires=None):
            self.key = key
            self.expires = expires

        def __reduce__(self):
            return TTLCache._Link, (self.key, self.expires)

        def unlink(self):
            next = self.next
            prev = self.prev
            prev.next = next
            next.prev = prev

    def __init__(self, maxsize, ttl, timer=time.monotonic, getsizeof=None):
        _TimedCache.__init__(self, maxsize, timer, getsizeof)
        self.__root = root = TTLCache._Link()
        root.prev = root.next = root
        self.__links = collections.OrderedDict()
        self.__ttl = ttl

    def __contains__(self, key):
        try:
            link = self.__links[key]  # no reordering
        except KeyError:
            return False
        else:
            return self.timer() < link.expires

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        links = self.__links
        try:
            link = links[key]
        except KeyError:
            return cache_getitem(self, key)
        links.move_to_end(key)
        if self.timer() < link.expires:
            return cache_getitem(self, key)
        else:
            return self.__missing__(key)

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        with self.timer as time:
            expires = time + self.__ttl
            self.expire(time)
            cache_setitem(self, key, value)
        links = self.__links
        link = links.get(key)
        if link is None:
            links[key] = link = TTLCache._Link(key)
        else:
            links.move_to_end(key)
            link.unlink()
        link.expires = expires
        link.next = root = self.__root
        link.prev = prev = root.prev
        prev.next = root.prev = link

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        cache_delitem(self, key)
        link = self.__links.pop(key)
        link.unlink()
        if not (self.timer() < link.expires):
            raise KeyError(key)

    def __iter__(self):
        root = self.__root
        curr = root.next
        while curr is not root:
            # "freeze" time for iterator access
            with self.timer as time:
                if time < curr.expires:
                    yield curr.key
            curr = curr.next

    def __setstate__(self, state):
        self.__dict__.update(state)
        root = self.__root
        root.prev = root.next = root
        for link in sorted(self.__links.values(), key=lambda obj: obj.expires):
            link.next = root
            link.prev = prev = root.prev
            prev.next = root.prev = link
        self.expire(self.timer())

    @property
    def ttl(self):
        """The time-to-live value of the cache's items."""
        return self.__ttl

    def expire(self, time=None):
        """Remove expired items from the cache and return an iterable of the
        expired `(key, value)` pairs.

        """
        if time is None:
            time = self.timer()
        root = self.__root
        curr = root.next
        if curr is root or time < curr.expires:
            return []  # fast path: nothing has expired
        links = self.__links
        expired = []
        cache_delitem = Cache.__delitem__
        cache_getitem = Cache.__getitem__
        while curr is not root and not (time < curr.expires):
            expired.append((curr.key, cache_getitem(self, curr.key)))
            cache_delitem(self, curr.key)
            del links[curr.key]
            next = curr.next
            curr.unlink()
            curr = next
        return expired

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used that
        has not already expired.

        """
        with self.timer as time:
            self.expire(time)
            try:
                key = next(iter(self.__links))
            except StopIteration:
                raise KeyError("%s is empty" % type(self).__name__) from None
            else:
                value = Cache.__getitem__(self, key)
                del self[key]
                return (key, value)

    def clear(self):
        _TimedCache.clear(self)
        root = self.__root
        root.prev = root.next = root
        self.__links.clear()


class TLRUCache(_TimedCache):
    """Time-aware Least Recently Used (TLRU) cache implementation."""

    __HEAP_CLEANUP_FACTOR = 2  # clean up the heap if size > N * len(items)

    @functools.total_ordering
    class _Item:
        __slots__ = ("expires", "key", "removed")

        def __init__(self, key=None, expires=None):
            self.key = key
            self.expires = expires
            self.removed = False

        def __lt__(self, other):
            return self.expires < other.expires

    def __init__(self, maxsize, ttu, timer=time.monotonic, getsizeof=None):
        _TimedCache.__init__(self, maxsize, timer, getsizeof)
        self.__items = collections.OrderedDict()
        self.__order = []
        self.__ttu = ttu

    def __contains__(self, key):
        try:
            item = self.__items[key]  # no reordering
        except KeyError:
            return False
        else:
            return self.timer() < item.expires

    def __getitem__(self, key, cache_getitem=Cache.__getitem__):
        items = self.__items
        try:
            item = items[key]
        except KeyError:
            return cache_getitem(self, key)
        items.move_to_end(key)
        if self.timer() < item.expires:
            return cache_getitem(self, key)
        else:
            return self.__missing__(key)

    def __setitem__(self, key, value, cache_setitem=Cache.__setitem__):
        with self.timer as time:
            self.expire(time)
            expires = self.__ttu(key, value, time)
            if not (time < expires):
                # updating an existing item with an already expired
                # one should remove the existing item
                return self.__delitem(key)
            cache_setitem(self, key, value)
        # removing an existing item would break the heap structure, so
        # only mark it as removed for now
        items = self.__items
        item = items.get(key)
        if item is not None:
            item.removed = True
            items.move_to_end(key)
        items[key] = item = TLRUCache._Item(key, expires)
        heapq.heappush(self.__order, item)

    def __delitem__(self, key, cache_delitem=Cache.__delitem__):
        with self.timer as time:
            # no self.expire() for performance reasons, e.g. self.clear() [#67]
            cache_delitem(self, key)
        item = self.__items.pop(key)
        item.removed = True
        if not (time < item.expires):
            raise KeyError(key)

    def __iter__(self):
        for curr in self.__order:
            # "freeze" time for iterator access
            with self.timer as time:
                if time < curr.expires and not curr.removed:
                    yield curr.key

    @property
    def ttu(self):
        """The time-to-use function used by the cache."""
        return self.__ttu

    def expire(self, time=None):
        """Remove expired items from the cache and return an iterable of the
        expired `(key, value)` pairs.

        """
        if time is None:
            time = self.timer()
        items = self.__items
        order = self.__order
        # clean up the heap if too many items are marked as removed
        if len(order) > len(items) * self.__HEAP_CLEANUP_FACTOR:
            self.__order = order = [item for item in order if not item.removed]
            heapq.heapify(order)
        if not order or (not order[0].removed and time < order[0].expires):
            return []  # fast path: nothing has expired
        expired = []
        cache_delitem = Cache.__delitem__
        cache_getitem = Cache.__getitem__
        while order and (order[0].removed or not (time < order[0].expires)):
            item = heapq.heappop(order)
            if not item.removed:
                expired.append((item.key, cache_getitem(self, item.key)))
                cache_delitem(self, item.key)
                del items[item.key]
        return expired

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used that
        has not already expired.

        """
        with self.timer as time:
            self.expire(time)
            try:
                key = next(iter(self.__items))
            except StopIteration:
                raise KeyError("%s is empty" % type(self).__name__) from None
            else:
                value = Cache.__getitem__(self, key)
                del self[key]
                return (key, value)

    def clear(self):
        _TimedCache.clear(self)
        self.__items.clear()
        del self.__order[:]

    def __delitem(self, key, cache_delitem=Cache.__delitem__):
        try:
            self.__items.pop(key).removed = True
        except KeyError:
            pass
        else:
            cache_delitem(self, key)


# note that the runtime __name__ is "CacheInfo", as in stdlib:
# https://github.com/python/cpython/blob/3.14/Lib/functools.py#L520
_CacheInfo = collections.namedtuple(
    "CacheInfo", ["hits", "misses", "maxsize", "currsize"]
)


def cached(cache, key=keys.hashkey, lock=None, condition=None, info=False):
    """Decorator to wrap a function with a memoizing callable that saves
    results in a cache.

    """
    from ._cached import _wrapper

    def decorator(func):
        if info:
            if isinstance(cache, Cache):

                def make_info(hits, misses):
                    return _CacheInfo(hits, misses, cache.maxsize, cache.currsize)

            elif isinstance(cache, collections.abc.Mapping):

                def make_info(hits, misses):
                    return _CacheInfo(hits, misses, None, len(cache))

            else:

                def make_info(hits, misses):
                    return _CacheInfo(hits, misses, 0, 0)

            return _wrapper(func, cache, key, lock, condition, info=make_info)
        else:
            return _wrapper(func, cache, key, lock, condition)

    return decorator


def cachedmethod(cache, key=keys.methodkey, lock=None, condition=None, info=False):
    """Decorator to wrap a method with a memoizing callable that saves
    results in a cache.

    """
    from ._cachedmethod import _wrapper

    def decorator(method):
        if info:

            def make_info(cache, hits, misses):
                if isinstance(cache, Cache):
                    return _CacheInfo(hits, misses, cache.maxsize, cache.currsize)
                elif isinstance(cache, collections.abc.Mapping):
                    return _CacheInfo(hits, misses, None, len(cache))
                else:
                    raise TypeError("cache(self) must return a mutable mapping")

            return _wrapper(method, cache, key, lock, condition, info=make_info)
        else:
            return _wrapper(method, cache, key, lock, condition)

    return decorator
