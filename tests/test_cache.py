import unittest

import cachetools
import collections


class CacheTest(unittest.TestCase):

    def test_dict_cache(self):
        cache = cachetools._Cache({'a': 1, 'b': 2}, maxsize=2)

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache['a'], 1)
        self.assertEqual(cache['b'], 2)

        cache['c'] = 3

        self.assertEqual(len(cache), 2)
        self.assertTrue('a' in cache or 'b' in cache)
        self.assertEqual(cache['c'], 3)

        cache.maxsize = 1

        self.assertEqual(len(cache), 1)
        self.assertTrue('a' in cache or 'b' in cache or 'c' in cache)

    def test_ordered_dict_cache(self):
        cache = cachetools._Cache(collections.OrderedDict(), maxsize=2)

        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache['b'], 2)
        self.assertEqual(cache['c'], 3)

        cache.maxsize = 1

        self.assertEqual(len(cache), 1)
        self.assertEqual(cache['c'], 3)
