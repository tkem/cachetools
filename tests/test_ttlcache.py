import unittest

from . import CacheTestMixin
from cachetools import ExpiredError, TTLCache, ttl_cache


@ttl_cache(maxsize=2)
def cached(n):
    return n


@ttl_cache(maxsize=2, typed=True, lock=None)
def cached_typed(n):
    return n


class Timer:
    def __init__(self):
        self.__time = 0

    def __call__(self):
        return self.__time

    def inc(self):
        self.__time = self.__time + 1


class TTLCacheTest(unittest.TestCase, CacheTestMixin):

    def make_cache(self, maxsize, getsizeof=None, ttl=0):
        return TTLCache(maxsize, ttl, timer=Timer(), getsizeof=getsizeof)

    def test_ttl_insert(self):
        cache = self.make_cache(maxsize=2, ttl=2)
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
        cache = self.make_cache(maxsize=3, ttl=0)
        self.assertEqual(cache.ttl, 0)

        cache[1] = 1
        self.assertEqual(1, cache[1])
        cache.timer.inc()
        with self.assertRaises(ExpiredError):
            cache[1]
        cache[2] = 2
        self.assertEqual(2, cache[2])
        cache.timer.inc()
        with self.assertRaises(ExpiredError):
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
        cache = self.make_cache(maxsize=1, ttl=0)

        cache[(1, 2, 3)] = 42
        self.assertEqual(42, cache[(1, 2, 3)])
        cache.timer.inc()
        with self.assertRaises(ExpiredError):
            cache[(1, 2, 3)]
        cache.expire()
        self.assertNotIn((1, 2, 3), cache)

    def test_lru_insert(self):
        cache = self.make_cache(maxsize=2)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[2], 2)
        self.assertEqual(cache[3], 3)
        self.assertNotIn(1, cache)

        cache[2]
        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[2], 2)
        self.assertEqual(cache[4], 4)
        self.assertNotIn(3, cache)

        cache[5] = 5
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[4], 4)
        self.assertEqual(cache[5], 5)
        self.assertNotIn(2, cache)

    def test_lru_getsizeof(self):
        cache = self.make_cache(maxsize=3, getsizeof=lambda x: x)

        cache[1] = 1
        cache[2] = 2

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[1], 1)
        self.assertEqual(cache[2], 2)

        cache[3] = 3

        self.assertEqual(len(cache), 1)
        self.assertEqual(cache[3], 3)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)

        with self.assertRaises(ValueError):
            cache[4] = 4
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache[3], 3)

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
