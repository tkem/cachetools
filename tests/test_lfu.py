import copy
import io
import pickle
import unittest

from cachetools import LFUCache

from . import CacheTestMixin


def _many_counts_cache(n=200):
    cache = LFUCache[int, int](maxsize=n)
    for key in range(n):
        cache[key] = key
        for _ in range(key):
            cache[key]  # key ends up with use count key + 1
    return cache


def _assert_same_eviction_order(test, restored, original):
    test.assertEqual(list(restored), list(original))
    test.assertEqual(restored.currsize, original.currsize)
    # Keys were given distinct use counts key + 1, so popitem() must
    # remove them in ascending key order on both caches.
    while len(restored):
        test.assertEqual(restored.popitem(), original.popitem())
    test.assertEqual(0, len(restored))
    test.assertEqual(0, len(original))


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

    def test_deepcopy_many_distinct_counts(self):
        cache = _many_counts_cache()
        restored = copy.deepcopy(cache)
        _assert_same_eviction_order(self, restored, cache)

    def test_pickle_many_distinct_counts(self):
        cache = _many_counts_cache()
        for pickler in (pickle.Pickler, pickle._Pickler):
            for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
                with self.subTest(pickler=pickler, protocol=protocol):
                    stream = io.BytesIO()
                    pickler(stream, protocol=protocol).dump(cache)
                    restored = pickle.loads(stream.getvalue())
                    _assert_same_eviction_order(self, restored, _many_counts_cache())

    def test_restored_cache_keeps_ties_and_stays_usable(self):
        cache = LFUCache[int, int](maxsize=3)
        cache[1] = 1
        cache[2] = 2
        cache[3] = 3
        cache[3]  # count 2; keys 1 and 2 stay tied at count 1

        restored = pickle.loads(pickle.dumps(cache))
        restored[4] = 4  # must evict 1, the oldest of the tied keys
        self.assertNotIn(1, restored)
        self.assertIn(2, restored)
        self.assertIn(3, restored)
        self.assertIn(4, restored)

        restored[2]  # raise key 2 above the tied keys 3 and 4
        restored[2]
        restored[3]  # raise key 3 above key 4 as well
        restored[5] = 5  # must evict 4, the only remaining count-1 key
        self.assertNotIn(4, restored)
        self.assertIn(2, restored)
        self.assertIn(3, restored)
        self.assertIn(5, restored)

        # A restored cache must itself survive another round trip.
        restored = pickle.loads(pickle.dumps(restored))
        self.assertEqual([2, 3, 5], list(restored))
