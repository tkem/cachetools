import functools
import time

from .cache import Cache


class _Link(object):

    __slots__ = (
        'key', 'value', 'expire', 'size',
        'ttl_prev', 'ttl_next',
        'lru_prev', 'lru_next'
    )

    def unlink(self):
        ttl_next = self.ttl_next
        ttl_prev = self.ttl_prev
        ttl_prev.ttl_next = ttl_next
        ttl_next.ttl_prev = ttl_prev

        lru_next = self.lru_next
        lru_prev = self.lru_prev
        lru_prev.lru_next = lru_next
        lru_next.lru_prev = lru_prev


class _NestedTimer(object):

    def __init__(self, timer):
        self.__timer = timer
        self.__nesting = 0

    def __enter__(self):
        if self.__nesting == 0:
            self.__time = self.__timer()
        self.__nesting += 1
        return self.__time

    def __exit__(self, *exc):
        self.__nesting -= 1

    def __call__(self):
        if self.__nesting == 0:
            return self.__timer()
        else:
            return self.__time

    def __getattr__(self, name):
        return getattr(self.__timer, name)

    def __getstate__(self):
        return (self.__timer, self.__nesting)

    def __setstate__(self, state):
        self.__timer, self.__nesting = state


class TTLCache(Cache):
    """LRU Cache implementation with per-item time-to-live (TTL) value."""

    def __init__(self, maxsize, ttl, timer=time.time, missing=None,
                 getsizeof=None):
        Cache.__init__(self, maxsize, missing, getsizeof)
        root = self.__root = _Link()
        root.ttl_prev = root.ttl_next = root
        root.lru_prev = root.lru_next = root
        self.__timer = _NestedTimer(timer)
        self.__ttl = ttl

    def __repr__(self, cache_getitem=Cache.__getitem__):
        # prevent item reordering/expiration
        return '%s(%r, maxsize=%d, currsize=%d)' % (
            self.__class__.__name__,
            [(key, cache_getitem(self, key).value) for key in self],
            self.maxsize,
            self.currsize,
        )

    def __getitem__(self, key,
                    cache_getitem=Cache.__getitem__,
                    cache_missing=Cache.__missing__):
        with self.__timer as time:
            link = cache_getitem(self, key)
            if link.expire < time:
                return cache_missing(self, key).value
            next = link.lru_next
            prev = link.lru_prev
            prev.lru_next = next
            next.lru_prev = prev
            link.lru_next = root = self.__root
            link.lru_prev = tail = root.lru_prev
            tail.lru_next = root.lru_prev = link
            return link.value

    def __setitem__(self, key, value,
                    cache_contains=Cache.__contains__,
                    cache_getitem=Cache.__getitem__,
                    cache_setitem=Cache.__setitem__,
                    cache_getsizeof=Cache.getsizeof):
        with self.__timer as time:
            self.expire(time)
            if cache_contains(self, key):
                oldlink = cache_getitem(self, key)
            else:
                oldlink = None
            link = _Link()
            link.key = key
            link.value = value
            link.expire = time + self.__ttl
            link.size = cache_getsizeof(self, value)
            cache_setitem(self, key, link)
            if oldlink:
                oldlink.unlink()
            link.ttl_next = root = self.__root
            link.ttl_prev = tail = root.ttl_prev
            tail.ttl_next = root.ttl_prev = link
            link.lru_next = root
            link.lru_prev = tail = root.lru_prev
            tail.lru_next = root.lru_prev = link

    def __delitem__(self, key,
                    cache_contains=Cache.__contains__,
                    cache_getitem=Cache.__getitem__,
                    cache_delitem=Cache.__delitem__):
        with self.__timer as time:
            self.expire(time)
            if not cache_contains(self, key):
                raise KeyError(key)
            link = cache_getitem(self, key)
            cache_delitem(self, key)
            link.unlink()

    def __contains__(self, key,
                     cache_contains=Cache.__contains__,
                     cache_getitem=Cache.__getitem__):
        with self.__timer as time:
            if not cache_contains(self, key):
                return False
            elif cache_getitem(self, key).expire < time:
                return False
            else:
                return True

    def __iter__(self):
        timer = self.__timer
        root = self.__root
        curr = root.ttl_next
        while curr is not root:
            with timer as time:
                if not (curr.expire < time):
                    yield curr.key
            curr = curr.ttl_next

    def __len__(self, cache_len=Cache.__len__):
        root = self.__root
        head = root.ttl_next
        expired = 0
        with self.__timer as time:
            while head is not root and head.expire < time:
                expired += 1
                head = head.ttl_next
        return cache_len(self) - expired

    @property
    def currsize(self):
        root = self.__root
        head = root.ttl_next
        expired = 0
        with self.__timer as time:
            while head is not root and head.expire < time:
                expired += head.size
                head = head.ttl_next
        return super(TTLCache, self).currsize - expired

    @property
    def timer(self):
        """The timer function used by the cache."""
        return self.__timer

    @property
    def ttl(self):
        """The time-to-live value of the cache's items."""
        return self.__ttl

    def expire(self, time=None):
        """Remove expired items from the cache."""
        if time is None:
            time = self.__timer()
        root = self.__root
        head = root.ttl_next
        cache_delitem = Cache.__delitem__
        while head is not root and head.expire < time:
            cache_delitem(self, head.key)
            next = head.ttl_next
            head.unlink()
            head = next

    def getsizeof(self, value):
        """Return the size of a cache element's value."""
        if isinstance(value, _Link):
            return value.size
        else:
            return Cache.getsizeof(self, value)

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used that
        has not already expired.

        """
        with self.__timer as time:
            self.expire(time)
            root = self.__root
            link = root.lru_next
            if link is root:
                raise KeyError('cache is empty')
            key = link.key
            Cache.__delitem__(self, key)
            link.unlink()
            return (key, link.value)

    # mixin methods

    def __nested(method):
        def wrapper(self, *args, **kwargs):
            with self.__timer:
                return method(self, *args, **kwargs)
        return functools.update_wrapper(wrapper, method)

    get = __nested(Cache.get)
    pop = __nested(Cache.pop)
    setdefault = __nested(Cache.setdefault)
