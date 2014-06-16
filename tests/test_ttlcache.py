import unittest

from . import CacheTestMixin
from cachetools import TTLCache


class TTLCacheTest(unittest.TestCase, CacheTestMixin):

    def make_cache(self, maxsize, getsizeof=None, ttl=86400):
        return TTLCache(maxsize, ttl, getsizeof)

    def test_ttl(self):
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
