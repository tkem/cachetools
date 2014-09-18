import unittest

from . import LRUCacheTestMixin
from cachetools import TTLCache


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
        with self.assertRaises(KeyError):
            cache[1]
        cache[2] = 2
        self.assertEqual(2, cache[2])
        cache.timer.inc()
        with self.assertRaises(KeyError):
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
