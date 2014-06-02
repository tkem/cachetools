import unittest

from . import CacheTestMixin
from cachetools import LRUCache, lru_cache


@lru_cache(maxsize=2)
def cached(n):
    return n


@lru_cache(maxsize=2, typed=True)
def cached_typed(n):
    return n


class LRUCacheTest(unittest.TestCase, CacheTestMixin):

    def make_cache(self, maxsize, getsizeof=None):
        return LRUCache(maxsize, getsizeof)

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
