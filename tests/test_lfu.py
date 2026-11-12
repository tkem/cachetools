import copy
import io
import pickle
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

    def test_deepcopy_many_counts(self):
        cache = LFUCache[int, int](maxsize=200)
        for key in range(200):
            cache[key] = key
            for _ in range(key):
                cache[key]
        restored = copy.deepcopy(cache)
        self.assertEqual(list(restored), list(cache))
        self.assertEqual(restored.currsize, cache.currsize)
        for key in range(200):
            self.assertEqual(restored.popitem(), (key, key))
        self.assertEqual(len(cache), 200)

    def test_pickle_many_counts(self):
        cache = LFUCache[int, int](maxsize=200)
        for key in range(200):
            cache[key] = key
            for _ in range(key):
                cache[key]
        for pickler in (pickle.Pickler, pickle._Pickler):
            for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
                with self.subTest(pickler=pickler, protocol=protocol):
                    stream = io.BytesIO()
                    pickler(stream, protocol=protocol).dump(cache)
                    restored = pickle.loads(stream.getvalue())
                    self.assertEqual(list(restored), list(cache))
                    self.assertEqual(restored.currsize, cache.currsize)
                    for key in range(200):
                        self.assertEqual(restored.popitem(), (key, key))
        self.assertEqual(len(cache), 200)

    def test_restored_ties_and_mutation(self):
        cache = LFUCache[int, int](maxsize=6)
        for key in (6, 5, 4, 3, 2, 1):
            cache[key] = key
        for key in (3, 6, 1):
            cache[key]
        for key in (4, 5):
            cache[key]
            cache[key]
        for restore in (copy.deepcopy, lambda obj: pickle.loads(pickle.dumps(obj))):
            with self.subTest(restore=restore):
                restored = restore(cache)
                self.assertEqual(restored.popitem(), (2, 2))
                self.assertEqual(restored.popitem(), (3, 3))
                restored[6]
                restored[0] = 0
                del restored[4]
                self.assertEqual(restored.popitem(), (0, 0))
                self.assertEqual(restored.popitem(), (1, 1))
                self.assertEqual(restored.popitem(), (5, 5))
                self.assertEqual(restored.popitem(), (6, 6))
                with self.assertRaises(KeyError):
                    restored.popitem()
                restored[7] = 7
                restored.clear()
                restored[8] = 8
                self.assertEqual(restored.popitem(), (8, 8))
                self.assertEqual(list(cache), [6, 5, 4, 3, 2, 1])

    def test_deepcopy_mutable_values(self):
        cache = LFUCache[int, list[int]](maxsize=4, getsizeof=len)
        cache[1] = [1, 2]
        cache[2] = [3]
        cache[1]
        restored = copy.deepcopy(cache)
        self.assertEqual(restored.maxsize, cache.maxsize)
        self.assertEqual(restored.currsize, cache.currsize)
        restored[1].append(4)
        self.assertEqual(cache[1], [1, 2])
        restored[3] = [5, 6]
        self.assertNotIn(2, restored)
        self.assertIn(2, cache)

    def test_restored_empty_and_single_count(self):
        for count in (0, 1, 2000):
            cache = LFUCache[int, int](maxsize=2000)
            for key in range(count):
                cache[key] = key
            for restore in (copy.deepcopy, lambda obj: pickle.loads(pickle.dumps(obj))):
                with self.subTest(count=count, restore=restore):
                    restored = restore(cache)
                    for key in range(count):
                        self.assertEqual(restored.popitem(), (key, key))
                    restored[1] = 1
                    self.assertEqual(restored.popitem(), (1, 1))
