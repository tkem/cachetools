import random
import unittest

from cachetools import RRCache

from . import CacheTestMixin


# random.choice cannot be pickled...
def choice(seq):
    return random.choice(seq)


class RRTestCache(RRCache):
    def __init__(self, maxsize, choice=choice, missing=None, getsizeof=None):
        RRCache.__init__(self, maxsize, choice=choice,
                         missing=missing, getsizeof=getsizeof)


class RRCacheTest(unittest.TestCase, CacheTestMixin):

    Cache = RRTestCache

    def test_rr_choice(self):
        cache = RRCache(maxsize=2, choice=min)
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
