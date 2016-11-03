import unittest

from pickle import dumps, loads

from cachetools import LRUCache

from . import CacheTestMixin


class LRUCachePersistTest(unittest.TestCase, CacheTestMixin):

    def cache(self, maxsize, missing=None, getsizeof=None, data=None):
        return LRUCache(maxsize, missing=missing, getsizeof=getsizeof,
                        data=data)

    def test_lru(self):
        cache = self.cache(maxsize=2)

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

        # pickle/unpickle - check cache persists
        data_pickled = dumps(cache.data)
        data_unpickled = loads(data_pickled)

        cache2 = self.cache(maxsize=2, data=data_unpickled)
        self.assertEqual(len(cache2), 2)
        self.assertEqual(cache2[4], 4)
        self.assertEqual(cache2[5], 5)
        self.assertNotIn(2, cache2)
