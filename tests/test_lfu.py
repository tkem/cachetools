import random
import unittest
import unittest.mock

import cachetools
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
        self.assertTrue(2 in cache or 3 in cache)
        self.assertTrue(2 not in cache or 3 not in cache)

        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[4], 4)
        self.assertEqual(cache[1], 1)

        cache[1]
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[1], 1)
        self.assertEqual(cache[4], 4)

    def test_lfu_tie(self):
        cache = LFUCache[int, int](maxsize=3)

        cache[1] = 1
        cache[1]
        cache[2] = 2
        cache[3] = 3
        cache[4] = 4

        self.assertEqual(len(cache), 3)
        self.assertIn(1, cache)
        self.assertIn(4, cache)
        self.assertTrue(2 in cache or 3 in cache)
        self.assertTrue(2 not in cache or 3 not in cache)

        cache[5] = 5
        self.assertEqual(len(cache), 3)
        self.assertIn(1, cache)
        self.assertIn(5, cache)
        self.assertTrue(2 in cache or 3 in cache or 4 in cache)

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

    def test_lfu_popitem_least_used(self):
        # cover both ways of picking among tied keys on any implementation
        for set_pop in (True, False):
            with (
                self.subTest(set_pop=set_pop),
                # create=True lets this test run against older releases too
                unittest.mock.patch.object(
                    cachetools, "_SET_POP_IS_ARBITRARY", set_pop, create=True
                ),
            ):
                self._check_popitem_least_used()

    def _check_popitem_least_used(self):
        evicted = []

        class Cache(LFUCache[int, int]):
            def __delitem__(self, key):
                evicted.append(key)
                super().__delitem__(key)

        cache = Cache(maxsize=100)
        counts = {}
        rnd = random.Random(0)

        # many ties: 300 keys competing for 100 slots
        for _ in range(20000):
            key = rnd.randrange(300)
            if key in cache:
                self.assertEqual(cache[key], -key)
                counts[key] += 1
            else:
                least = min(counts.values(), default=0)
                full = len(cache) == cache.maxsize
                cache[key] = -key
                if full:
                    # evicted through __delitem__, with a least-used key
                    self.assertEqual(least, counts.pop(evicted[-1]))
                counts[key] = 1
            self.assertEqual(set(counts), set(cache))

        # draining yields keys in order of use count
        drained = []
        while cache:
            key, value = cache.popitem()
            self.assertEqual(value, -key)
            self.assertEqual(key, evicted[-1])
            drained.append(counts.pop(key))
        self.assertEqual(drained, sorted(drained))
        self.assertEqual(0, cache.currsize)
        with self.assertRaises(KeyError):
            cache.popitem()

        # still usable after being emptied
        cache[1] = 1
        cache[1]
        cache[2] = 2
        self.assertEqual((2, 2), cache.popitem())
