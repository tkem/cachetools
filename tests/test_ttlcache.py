import unittest

from . import LRUCacheTestMixin
from cachetools import TTLCache, ttl_cache


@ttl_cache(maxsize=2)
def cached(n):
    return n


@ttl_cache(maxsize=2, typed=True, lock=None)
def cached_typed(n):
    return n


class TTLCacheTest(unittest.TestCase, LRUCacheTestMixin):

    def make_cache(self, maxsize, getsizeof=None):
        return TTLCache(maxsize, ttl=0, timer=lambda: 0, getsizeof=getsizeof)

    def make_ttl_cache(self, maxsize, ttl):
        class Timer:
            def __init__(self):
                self.__time = 0

            def __call__(self):
                return self.__time

            def inc(self):
                self.__time = self.__time + 1

        return TTLCache(maxsize, ttl, timer=Timer())

    def test_ttl_insert(self):
        cache = self.make_ttl_cache(maxsize=2, ttl=2)
        self.assertEqual(cache.ttl, 2)

        cache[1] = 1

        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache[1])

        cache.timer.inc()
        cache[2] = 2

        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache.timer.inc()
        cache[1]
        cache[3] = 3

        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])

    def test_ttl_expire(self):
        cache = self.make_ttl_cache(maxsize=3, ttl=0)
        self.assertEqual(cache.ttl, 0)

        cache[1] = 1
        self.assertEqual(1, cache[1])
        cache.timer.inc()
        with self.assertRaises(TTLCache.ExpiredError):
            cache[1]
        cache[2] = 2
        self.assertEqual(2, cache[2])
        cache.timer.inc()
        with self.assertRaises(TTLCache.ExpiredError):
            cache[2]
        cache[3] = 3
        self.assertEqual(3, cache[3])

        cache.expire(1)
        self.assertNotIn(1, cache)
        self.assertEqual(3, cache[3])

        cache.expire(2)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])

        cache.timer.inc()
        cache.expire()
        self.assertEqual(0, len(cache))
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

    def test_ttl_tuple_key(self):
        cache = self.make_ttl_cache(maxsize=1, ttl=0)

        cache[(1, 2, 3)] = 42
        self.assertEqual(42, cache[(1, 2, 3)])
        cache.timer.inc()
        with self.assertRaises(TTLCache.ExpiredError):
            cache[(1, 2, 3)]
        cache.expire()
        self.assertNotIn((1, 2, 3), cache)

    def test_decorator(self):
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, 2, 1))

        cached.cache_clear()
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (2, 2, 2, 1))

    def test_typed_decorator(self):
        self.assertEqual(cached_typed(1), 1)
        self.assertEqual(cached_typed.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached_typed(1), 1)
        self.assertEqual(cached_typed.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached_typed(1.0), 1.0)
        self.assertEqual(cached_typed.cache_info(), (1, 2, 2, 2))
        self.assertEqual(cached_typed(1.0), 1.0)
        self.assertEqual(cached_typed.cache_info(), (2, 2, 2, 2))
