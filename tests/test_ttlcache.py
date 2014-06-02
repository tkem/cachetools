import unittest

from . import CacheTestMixin
from cachetools import TTLCache


class TTLCacheTest(unittest.TestCase, CacheTestMixin):

    def make_cache(self, maxsize, getsizeof=None, ttl=86400):
        return TTLCache(maxsize, ttl, getsizeof)

    def test_ttl_insert(self):
        cache = self.make_cache(maxsize=2)

        cache[1] = 1
        cache[2] = 2
        #cache[1] = 1
        cache[3] = 3

        self.assertEqual(len(cache), 2)
        #self.assertEqual(cache[1], 1)
        #self.assertTrue(2 in cache or 3 in cache)
        #self.assertTrue(2 not in cache or 3 not in cache)

        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[4], 4)
        #self.assertEqual(cache[1], 1)

    def test_ttl_getsizeof(self):
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

    def test_ttl_expire(self):
        cache = self.make_cache(maxsize=2, ttl=0)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        with self.assertRaises(KeyError):
            cache[1]
        with self.assertRaises(KeyError):
            cache[2]
        with self.assertRaises(KeyError):
            cache[3]

#
#        self.assertEqual(len(cache), 2)
#        self.assertEqual(cache[1], 1)
#        self.assertTrue(2 in cache or 3 in cache)
#        self.assertTrue(2 not in cache or 3 not in cache)
#
#        cache[4] = 4
#        self.assertEqual(len(cache), 2)
#        self.assertEqual(cache[4], 4)
#        self.assertEqual(cache[1], 1)
