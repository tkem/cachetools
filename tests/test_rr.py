import random
import unittest

from cachetools import RRCache, rr_cache

from . import CacheTestMixin, DecoratorTestMixin


class RRCacheTest(unittest.TestCase, CacheTestMixin, DecoratorTestMixin):

    def cache(self, maxsize, choice=random.choice, missing=None,
              getsizeof=None):
        return RRCache(maxsize, choice=choice, missing=missing,
                       getsizeof=getsizeof)

    def decorator(self, maxsize, choice=random.choice, typed=False, lock=None):
        return rr_cache(maxsize, choice=choice, typed=typed, lock=lock)

    def test_choice(self):
        cache = self.cache(maxsize=2, choice=min)
        self.assertEqual(min, cache.choice)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])
        self.assertNotIn(1, cache)

        cache[0] = 0
        self.assertEqual(2, len(cache))
        self.assertEqual(0, cache[0])
        self.assertEqual(3, cache[3])
        self.assertNotIn(2, cache)

        cache[4] = 4
        self.assertEqual(2, len(cache))
        self.assertEqual(3, cache[3])
        self.assertEqual(4, cache[4])
        self.assertNotIn(0, cache)

    def test_rr_pickle(self):
        import pickle

        cache = self.cache(maxsize=3)
        with self.assertRaises(pickle.PicklingError):
            # The cache's random choice function cannot be pickled.
            # Try dill instead.
            pickle.dumps(cache, -1)
