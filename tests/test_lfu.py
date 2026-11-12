import unittest

from cachetools import LFUCache

from . import CacheTestMixin


class LFUCacheTest(unittest.TestCase, CacheTestMixin):
    Cache = LFUCache

    def test_lfu(self):
        cache = LFUCache[int, int](maxsize=2)

        cache[1] = 1
        cache[1]
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[1], 1)
        self.assertNotIn(2, cache)
        self.assertEqual(cache[3], 3)

        cache[3]
        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertNotIn(1, cache)
        self.assertEqual(cache[3], 3)
        self.assertEqual(cache[4], 4)

    def test_lfu_tie(self):
        cache = LFUCache[int, int](maxsize=3)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        cache[3]
        cache[2]
        cache[1]

        # do not use self.assertEqual(cache[1], 1) here, since that
        # would mess up usage counts
        self.assertEqual(len(cache), 3)
        self.assertIn(1, cache)
        self.assertIn(2, cache)
        self.assertIn(3, cache)

        cache[4] = 4
        self.assertEqual(len(cache), 3)
        self.assertIn(1, cache)
        self.assertIn(2, cache)
        self.assertNotIn(3, cache)
        self.assertIn(4, cache)

        cache[4]
        cache[5] = 5
        self.assertEqual(len(cache), 3)
        self.assertIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)
        self.assertIn(4, cache)
        self.assertIn(5, cache)

    def test_lfu_tie_insert_only(self):
        cache = LFUCache[int, int](maxsize=3)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        # items never retrieved are tied at use count 1, so they are
        # evicted in insertion order; the set-based implementation
        # used up to v7.2 only fails this from key 17 on
        for key in range(4, 20):
            cache[key] = key
            self.assertEqual(len(cache), 3)
            self.assertNotIn(key - 3, cache)
            self.assertIn(key - 2, cache)
            self.assertIn(key - 1, cache)
            self.assertIn(key, cache)

    def test_lfu_getsizeof(self):
        cache = LFUCache[int, int](maxsize=3, getsizeof=lambda x: x)

        cache[1] = 1
        cache[2] = 2

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[1], 1)
        self.assertEqual(cache[2], 2)

        cache[3] = 3

        self.assertEqual(len(cache), 1)
        self.assertEqual(cache[3], 3)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)

        with self.assertRaises(ValueError):
            cache[4] = 4
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache[3], 3)

    def test_lfu_update_existing(self):
        cache = LFUCache[int, int | str](maxsize=2)

        cache[1] = 1
        cache[2] = 2
        cache[1] = "updated"
        cache[3] = 3

        self.assertEqual(cache[1], "updated")
        self.assertIn(3, cache)
        self.assertNotIn(2, cache)

    def test_lfu_clear(self):
        cache = LFUCache[int, int](maxsize=2)

        cache[1] = 1
        cache[1]  # increment frequency
        cache[1]  # increment frequency again
        cache[2] = 2

        cache.clear()

        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)

        # verify LFU frequency tracking is reset after clear
        cache[3] = 3
        cache[4] = 4
        cache[3]  # access 3 to increment frequency
        cache[5] = 5  # should evict 4 (least frequently used)

        self.assertEqual(2, len(cache))
        self.assertIn(3, cache)
        self.assertIn(5, cache)
        self.assertNotIn(4, cache)

    def test_lfu_copy_use_counts(self):
        """Regression test for recursion errors from copying and
        pickling LFUCache with many use counts."""
        import copy
        import pickle
        import sys

        n = sys.getrecursionlimit()
        source = LFUCache[int, int](maxsize=n + 1)
        for key in range(n):
            source[key] = key
            for _ in range(key):
                source[key]  # key ends up with use count key + 1
        source[n] = n  # tied with key 0 at use count 1

        for cache in (
            copy.copy(source),
            copy.deepcopy(source),
            pickle.loads(pickle.dumps(source)),
        ):
            # compare keys only, since items() would count as a use
            self.assertEqual(list(source), list(cache))
            # the copy evicts by use count, then by age
            order = [cache.popitem()[0] for _ in range(len(cache))]
            self.assertEqual([0, n, *range(1, n)], order)

        self.assertEqual(n + 1, len(source))
