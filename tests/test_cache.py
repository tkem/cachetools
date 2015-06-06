import unittest

from cachetools import Cache

from . import CacheTestMixin


class CacheTest(unittest.TestCase, CacheTestMixin):

    def cache(self, maxsize, missing=None, getsizeof=None):
        return Cache(maxsize, missing=missing, getsizeof=getsizeof)
