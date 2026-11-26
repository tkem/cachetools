import math
import unittest

from cachetools import TTLCache

from . import TimedCacheTestMixin


class TTLCacheTest(unittest.TestCase, TimedCacheTestMixin[TTLCache]):
    Cache = TTLCache

    def typed_cache(self, cls, maxsize: float, *, ttl=math.inf, timer=None, **kwargs):
        if timer is None:
            timer = TimedCacheTestMixin.Timer()
        return cls(maxsize, ttl=ttl, timer=timer, **kwargs)

    def test_ttl(self):
        cache = TTLCache[int, int, int](maxsize=2, ttl=2, timer=self.Timer())
        self.assertEqual(2, cache.ttl)

    def test_ttl_default_timer_stubs(self):
        # type stubs must infer key and value types with the default timer
        cache: TTLCache[str, int] = TTLCache(maxsize=2, ttl=math.inf)

        cache["a"] = 1
        self.assertEqual(1, cache["a"])
        self.assertEqual(1, len(cache))
        self.assertIn("a", cache)

        sized: TTLCache[str, str] = TTLCache(maxsize=10, ttl=math.inf, getsizeof=len)

        sized["abc"] = "abc"
        self.assertEqual("abc", sized["abc"])
        self.assertEqual(3, sized.currsize)

    def test_ttl_datetime_stubs(self):
        # type stubs must accept a timedelta ttl with a datetime timer
        from datetime import datetime, timedelta

        cache: TTLCache[int, int, datetime] = TTLCache(
            maxsize=1, ttl=timedelta(days=1), timer=datetime.now
        )

        cache[1] = 1
        self.assertEqual([], cache.expire(datetime.now()))
        self.assertEqual([(1, 1)], cache.expire(datetime.now() + timedelta(days=1)))
