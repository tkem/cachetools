import unittest

from cachetools import LFUCache

from . import CacheTestMixin


class LFUCacheTest(unittest.TestCase, CacheTestMixin):
    Cache = LFUCache

    def test_lfu(self):
        cache = LFUCache(maxsize=2)

        cache[1] = 1
        cache[1]
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[1], 1)
        self.assertTrue(2 in cache or 3 in cache)
        self.assertTrue(2 not in cache or 3 not in cache)

        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[4], 4)
        self.assertEqual(cache[1], 1)

    def test_lfu_getsizeof(self):
        cache = LFUCache(maxsize=3, getsizeof=lambda x: x)

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

    def test_lfu_tie_breaker_lru(self):
        cache = LFUCache(maxsize=2)
        cache[1] = "one"
        cache[2] = "two"
        cache[3] = "three"

        self.assertEqual(len(cache), 2)
        self.assertNotIn(1, cache, "oldest key with equal freq should be evicted")
        self.assertIn(2, cache)
        self.assertIn(3, cache)

    def test_lfu_frequency_drives_eviction(self):
        cache = LFUCache(maxsize=2)

        cache[1] = "one"
        cache[2] = "two"

        for _ in range(5):
            _ = cache[1]

        cache[3] = "three"
        self.assertIn(1, cache)
        self.assertIn(3, cache)
        self.assertNotIn(2, cache)

    def test_lfu_popitem_returns_least_frequent(self):
        cache = LFUCache(maxsize=3)
        cache.update({1: "a", 2: "b", 3: "c"})
        cache[2]

        popped_key, popped_val = cache.popitem()
        self.assertEqual(popped_key, 1)
        self.assertEqual(popped_val, "a")
        self.assertNotIn(1, cache)
        self.assertEqual(len(cache), 2)

    def test_lfu_resize_with_getsizeof(self):
        cache = LFUCache(maxsize=5, getsizeof=lambda v: v)

        cache[1] = 2
        cache[2] = 3
        cache[3] = 2
        self.assertEqual(cache.currsize, 5)
        self.assertIn(2, cache)
        self.assertIn(3, cache)
        self.assertNotIn(1, cache)

    def test_lfu_update_keeps_frequency(self):
        cache = LFUCache(maxsize=2)

        cache[1] = "a"
        _ = cache[1]
        cache[1] = "aa"

        cache[2] = "b"
        cache[3] = "c"

        self.assertIn(1, cache)
        self.assertIn(3, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(cache[1], "aa")

    def test_lfu_clear_and_iter(self):
        cache = LFUCache(maxsize=4)
        cache.update({1: "a", 2: "b", 3: "c"})
        self.assertEqual(set(cache.keys()), {1, 2, 3})

        cache.clear()
        self.assertEqual(len(cache), 0)
        self.assertFalse(list(cache))
