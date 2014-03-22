import unittest

from cachetools import LFUCache, lfu_cache


@lfu_cache(maxsize=2)
def cached(n):
    return n


class LFUCacheTest(unittest.TestCase):

    def test_insert(self):
        cache = LFUCache(maxsize=2)
        cache['a'] = 0
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        self.assertEqual(cache['a'], 1)
        self.assertTrue('b' in cache or 'c' in cache)
        self.assertTrue('b' not in cache or 'c' not in cache)

        cache['a'] = 4
        self.assertEqual(cache['a'], 4)

    def test_decorator(self):
        self.assertEqual(cached(1), 1)
        self.assertItemsEqual(cached.cache_info(), [0, 1, 2, 1])
        self.assertEqual(cached(1), 1)
        self.assertItemsEqual(cached.cache_info(), [1, 1, 2, 1])
