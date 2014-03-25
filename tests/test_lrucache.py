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

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache['b'], 2)
        self.assertEqual(cache['c'], 3)
        self.assertNotIn('a', cache)

        cache['b']
        cache['d'] = 4
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache['b'], 2)
        self.assertEqual(cache['d'], 4)
        self.assertNotIn('c', cache)

        cache['e'] = 5
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache['d'], 4)
        self.assertEqual(cache['e'], 5)
        self.assertNotIn('b', cache)

    def test_decorator(self):
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
