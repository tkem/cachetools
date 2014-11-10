import unittest

from . import CacheTestMixin, DecoratorTestMixin
from cachetools import ExpiredError, TTLCache, ttl_cache


class Timer:
    def __init__(self):
        self.__time = 0

    def __call__(self):
        return self.__time

    def tick(self):
        self.__time += 1


class TTLCacheTest(unittest.TestCase, CacheTestMixin, DecoratorTestMixin):

    def cache(self, maxsize, ttl=0, getsizeof=None):
        return TTLCache(maxsize, ttl, timer=Timer(), getsizeof=getsizeof)

    def decorator(self, maxsize, ttl=0, typed=False, lock=None):
        return ttl_cache(maxsize, ttl, timer=Timer(), typed=typed, lock=lock)

    def test_ttl(self):
        cache = self.cache(maxsize=2, ttl=2)
        self.assertEqual(cache.ttl, 2)

        cache[1] = 1

        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache[1])

        cache.timer.tick()
        cache[2] = 2

        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache.timer.tick()
        cache[1]
        cache[3] = 3

        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])

    def test_lru(self):
        cache = self.cache(maxsize=2)

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

    def test_expire(self):
        cache = self.cache(maxsize=3, ttl=0)
        self.assertEqual(cache.ttl, 0)

        cache[1] = 1
        self.assertEqual(1, cache[1])
        cache.timer.tick()
        with self.assertRaises(ExpiredError):
            cache[1]
        cache[2] = 2
        self.assertEqual(2, cache[2])
        cache.timer.tick()
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

        cache.timer.tick()
        cache.expire()
        self.assertEqual(0, len(cache))
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

    def test_tuple_key(self):
        cache = self.cache(maxsize=1, ttl=0)

        cache[(1, 2, 3)] = 42
        self.assertEqual(42, cache[(1, 2, 3)])
        cache.timer.tick()
        with self.assertRaises(ExpiredError):
            cache[(1, 2, 3)]
        cache.expire()
        self.assertNotIn((1, 2, 3), cache)
