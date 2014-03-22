import unittest

from cachetools import LRUCache, lru_cache


@lru_cache(maxsize=2)
def cached(n):
    return n


class LRUCacheTest(unittest.TestCase):

    def test_insert(self):
        cache = LRUCache(maxsize=2)
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        self.assertEqual(cache['b'], 2)
        self.assertEqual(cache['c'], 3)
        self.assertNotIn('a', cache)

        cache['a'] = 4
        self.assertEqual(cache['a'], 4)
        self.assertEqual(cache['c'], 3)
        self.assertNotIn('b', cache)

        cache['b'] = 5
        self.assertEqual(cache['b'], 5)
        self.assertEqual(cache['c'], 3)
        self.assertNotIn('a', cache)

    def test_decorator(self):
        self.assertEqual(cached(1), 1)
        self.assertItemsEqual(cached.cache_info(), [0, 1, 2, 1])
        self.assertEqual(cached(1), 1)
        self.assertItemsEqual(cached.cache_info(), [1, 1, 2, 1])
