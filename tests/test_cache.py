import unittest

import cachetools
import collections


@cachetools.cache
class DictCache(dict):
    pass


@cachetools.cache
class OrderedDictCache(collections.OrderedDict):
    pass


class CacheTest(unittest.TestCase):

    def test_dict_cache(self):
        cache = DictCache(maxsize=2)

        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        self.assertEqual(len(cache), 2)
        self.assertTrue('a' in cache or ('b' in cache and 'c' in cache))
        self.assertTrue('b' in cache or ('a' in cache and 'c' in cache))
        self.assertTrue('c' in cache or ('a' in cache and 'b' in cache))

    def test_ordered_dict_cache(self):
        cache = OrderedDictCache(maxsize=2)

        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        self.assertEqual(len(cache), 2)
        self.assertNotIn('a', cache)
        self.assertEqual(cache['b'], 2)
        self.assertEqual(cache['c'], 3)
