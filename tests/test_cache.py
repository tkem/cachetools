import unittest

from . import CacheTestMixin
from cachetools import Cache


class CacheTest(unittest.TestCase, CacheTestMixin):

    def cache(self, maxsize, missing=None, getsizeof=None):
        return Cache(maxsize, missing=missing, getsizeof=getsizeof)
