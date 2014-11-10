import unittest

from . import CacheTestMixin
from cachetools import Cache


class CacheTest(unittest.TestCase, CacheTestMixin):

    def cache(self, maxsize, getsizeof=None):
        return Cache(maxsize, getsizeof=getsizeof)
