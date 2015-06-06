import unittest

from cachetools import LFUCache, lfu_cache

from . import CacheTestMixin, DecoratorTestMixin


class LFUCacheTest(unittest.TestCase, CacheTestMixin, DecoratorTestMixin):

    def cache(self, maxsize, missing=None, getsizeof=None):
        return LFUCache(maxsize, missing=missing, getsizeof=getsizeof)

    def decorator(self, maxsize, typed=False, lock=None):
        return lfu_cache(maxsize, typed=typed, lock=lock)

    def test_lfu(self):
        cache = self.cache(maxsize=2)

        cache[1] = 1
        cache[1]
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[1], 1)
        self.assertTrue(2 in cache or 3 in cache)
        self.assertTrue(2 not in cache or 3 not in cache)

        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[4], 4)
        self.assertEqual(cache[1], 1)

    def test_lfu_getsizeof(self):
        cache = self.cache(maxsize=3, getsizeof=lambda x: x)

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
