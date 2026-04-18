import math
import unittest

from cachetools import TLRUCache

from . import CacheTestMixin


def default_ttu(_key, _value, _time):
    return math.inf


class Timer:
    def __init__(self, auto=False):
        self.auto = auto
        self.time = 0

    def __call__(self):
        if self.auto:
            self.time += 1
        return self.time

    def tick(self):
        self.time += 1


class TLRUTestCache(TLRUCache):
    def __init__(self, maxsize, ttu=default_ttu, **kwargs):
        TLRUCache.__init__(self, maxsize, ttu, timer=Timer(), **kwargs)


class TLRUCacheTest(unittest.TestCase, CacheTestMixin):
    Cache = TLRUTestCache

    def test_ttu(self):
        cache = TLRUCache[int, int, int](
            maxsize=6, ttu=lambda _, v, t: t + v + 1, timer=Timer()
        )
        self.assertEqual(0, cache.timer())
        self.assertEqual(3, cache.ttu(0, 1, 1))

        cache[1] = 1
        self.assertEqual(1, cache[1])
        self.assertEqual(1, len(cache))
        self.assertEqual({1}, set(cache))

        cache.timer.tick()
        self.assertEqual(1, cache[1])
        self.assertEqual(1, len(cache))
        self.assertEqual({1}, set(cache))

        cache[2] = 2
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(2, len(cache))
        self.assertEqual({1, 2}, set(cache))

        cache.timer.tick()
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(1, len(cache))
        self.assertEqual({2}, set(cache))

        cache[3] = 3
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])
        self.assertEqual(2, len(cache))
        self.assertEqual({2, 3}, set(cache))

        cache.timer.tick()
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])
        self.assertEqual(2, len(cache))
        self.assertEqual({2, 3}, set(cache))

        cache[1] = 1
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])
        self.assertEqual(3, len(cache))
        self.assertEqual({1, 2, 3}, set(cache))

        cache.timer.tick()
        self.assertEqual(1, cache[1])
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])
        self.assertEqual(2, len(cache))
        self.assertEqual({1, 3}, set(cache))

        cache.timer.tick()
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])
        self.assertEqual(1, len(cache))
        self.assertEqual({3}, set(cache))

        cache.timer.tick()
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

        with self.assertRaises(KeyError):
            del cache[1]
        with self.assertRaises(KeyError):
            cache.pop(2)
        with self.assertRaises(KeyError):
            del cache[3]

        self.assertEqual(0, len(cache))
        self.assertEqual(set(), set(cache))

    def test_ttu_lru(self):
        def ttu(_k, _v, t):
            return t + 1

        cache = TLRUCache[int, int, int](maxsize=2, ttu=ttu, timer=Timer())
        self.assertEqual(0, cache.timer())
        self.assertEqual(2, cache.ttu(0, 0, 1))

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(len(cache), 2)
        self.assertNotIn(1, cache)
        self.assertEqual(cache[2], 2)
        self.assertEqual(cache[3], 3)

        cache[2]
        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertNotIn(1, cache)
        self.assertEqual(cache[2], 2)
        self.assertNotIn(3, cache)
        self.assertEqual(cache[4], 4)

        cache[5] = 5
        self.assertEqual(len(cache), 2)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)
        self.assertEqual(cache[4], 4)
        self.assertEqual(cache[5], 5)

    def test_ttu_expire(self):
        def ttu(_k, _v, t):
            return t + 3

        cache = TLRUCache[int, int, int](maxsize=3, ttu=ttu, timer=Timer())
        with cache.timer as time:
            self.assertEqual(time, cache.timer())

        cache[1] = 1
        cache.timer.tick()
        cache[2] = 2
        cache.timer.tick()
        cache[3] = 3
        self.assertEqual(2, cache.timer())

        self.assertEqual({1, 2, 3}, set(cache))
        self.assertEqual(3, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        items = cache.expire()
        self.assertEqual(set(), set(items))
        self.assertEqual({1, 2, 3}, set(cache))
        self.assertEqual(3, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        items = cache.expire(3)
        self.assertEqual({(1, 1)}, set(items))
        self.assertEqual({2, 3}, set(cache))
        self.assertEqual(2, len(cache))
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        items = cache.expire(4)
        self.assertEqual({(2, 2)}, set(items))
        self.assertEqual({3}, set(cache))
        self.assertEqual(1, len(cache))
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])

        items = cache.expire(5)
        self.assertEqual({(3, 3)}, set(items))
        self.assertEqual(set(), set(cache))
        self.assertEqual(0, len(cache))
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

    def test_ttu_expired(self):
        cache = TLRUCache[int, None, int](
            maxsize=1, ttu=lambda k, _, t: t + k, timer=Timer()
        )
        cache[1] = None
        self.assertEqual(cache[1], None)
        self.assertEqual(1, len(cache))
        cache[0] = None
        self.assertNotIn(0, cache)
        self.assertEqual(cache[1], None)
        self.assertEqual(1, len(cache))
        cache[-1] = None
        self.assertNotIn(-1, cache)
        self.assertNotIn(0, cache)
        self.assertEqual(cache[1], None)
        self.assertEqual(1, len(cache))

    def test_ttu_atomic(self):
        cache = TLRUCache[int, int, int](
            maxsize=1, ttu=lambda k, v, t: t + 2, timer=Timer(auto=True)
        )
        cache[1] = 1
        self.assertEqual(1, cache[1])
        cache[1] = 1
        self.assertEqual(1, cache.get(1))
        cache[1] = 1
        self.assertEqual(1, cache.pop(1))
        cache[1] = 1
        self.assertEqual(1, cache.setdefault(1))
        cache[1] = 1
        cache.clear()
        self.assertEqual(0, len(cache))

    def test_ttu_tuple_key(self):
        cache = TLRUCache[tuple[int, ...], int, int](
            maxsize=1, ttu=lambda k, v, t: t + 1, timer=Timer()
        )

        cache[(1, 2, 3)] = 42
        self.assertEqual(42, cache[(1, 2, 3)])
        cache.timer.tick()
        with self.assertRaises(KeyError):
            cache[(1, 2, 3)]
        self.assertNotIn((1, 2, 3), cache)

    def test_ttu_reverse_insert(self):
        def ttu(_k, v, t):
            return t + v

        cache = TLRUCache[int, int, int](maxsize=4, ttu=ttu, timer=Timer())
        self.assertEqual(0, cache.timer())

        cache[3] = 3
        cache[2] = 2
        cache[1] = 1
        cache[0] = 0

        self.assertEqual({1, 2, 3}, set(cache))
        self.assertEqual(3, len(cache))
        self.assertNotIn(0, cache)
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        cache.timer.tick()

        self.assertEqual({2, 3}, set(cache))
        self.assertEqual(2, len(cache))
        self.assertNotIn(0, cache)
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        cache.timer.tick()

        self.assertEqual({3}, set(cache))
        self.assertEqual(1, len(cache))
        self.assertNotIn(0, cache)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])

        cache.timer.tick()

        self.assertEqual(set(), set(cache))
        self.assertEqual(0, len(cache))
        self.assertNotIn(0, cache)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

    def test_ttu_heap_cleanup(self):
        def ttu(_k, _v, t):
            return t + 1

        cache = TLRUCache[int, int, int](maxsize=4, ttu=ttu, timer=Timer())
        self.assertEqual(0, cache.timer())

        cache[1] = 1
        cache[2] = 2

        # replace items to accumulate removed entries in the internal heap
        for i in range(5):
            cache[1] = 10 + i
            cache[2] = 20 + i

        # this should compact the internal heap
        expired = cache.expire()
        self.assertEqual([], expired)

        # verify cache is functional after cleanup
        self.assertEqual(2, len(cache))
        self.assertEqual(14, cache[1])
        self.assertEqual(24, cache[2])
        cache[3] = 3
        cache[4] = 4
        self.assertEqual(4, len(cache))

        cache.timer.tick()
        expired = cache.expire()
        self.assertEqual(4, len(expired))
        self.assertEqual(0, len(cache))

    def test_tlru_datetime(self):
        from datetime import datetime, timedelta

        def ttu(_k, _v, t):
            return t + timedelta(days=1)

        cache = TLRUCache[int, int, datetime](maxsize=1, ttu=ttu, timer=datetime.now)

        cache[1] = 1
        self.assertEqual(1, len(cache))
        items = cache.expire(datetime.now())
        self.assertEqual([], list(items))
        self.assertEqual(1, len(cache))
        items = cache.expire(datetime.now() + timedelta(days=1))
        self.assertEqual([(1, 1)], list(items))
        self.assertEqual(0, len(cache))

    def test_tlru_clear(self):
        def ttu(_k, _v, t):
            return t + 2

        cache = TLRUCache[int, int, int](maxsize=2, ttu=ttu, timer=Timer())

        cache[1] = 1
        cache[2] = 2
        cache.clear()

        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)

        # verify LRU eviction order is reset after clear
        cache[3] = 3
        cache[4] = 4
        cache[3]  # access 3 to make it most recently used
        cache[5] = 5  # should evict 4 (least recently used)

        self.assertEqual(2, len(cache))
        self.assertIn(3, cache)
        self.assertIn(5, cache)
        self.assertNotIn(4, cache)

        # verify TLRU expiry still works after clear
        cache[42] = 42
        cache.timer.tick()
        cache.timer.tick()
        cache.timer.tick()  # past TTL
        self.assertNotIn(42, cache)
