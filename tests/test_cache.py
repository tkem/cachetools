import unittest

import cachetools

from . import CacheTestMixin

#AI
class CacheTest(unittest.TestCase, CacheTestMixin):
    Cache = cachetools.Cache
