import unittest

from . import CacheTestMixin
from cachetools import Cache


class CacheTest(unittest.TestCase, CacheTestMixin):

    def cache(self, maxsize, missing=None, getsizeof=None):
        return Cache(maxsize, missing=missing, getsizeof=getsizeof)

    def test_getsize(self):
        # Cache.getsize is deprecated
        cache = self.cache(maxsize=3, getsizeof=lambda x: x)
        cache.update({1: 1, 2: 2})

        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(1, cache.getsize(1))
            self.assertEqual(1, len(w))
            self.assertEqual(w[0].category, DeprecationWarning)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(2, cache.getsize(2))
            self.assertEqual(1, len(w))
            self.assertEqual(w[0].category, DeprecationWarning)
