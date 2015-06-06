import unittest

from cachetools import TTLCache, ttl_cache

from . import CacheTestMixin, DecoratorTestMixin


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


class TTLCacheTest(unittest.TestCase, CacheTestMixin, DecoratorTestMixin):

    def cache(self, maxsize, ttl=0, missing=None, getsizeof=None):
        return TTLCache(maxsize, ttl, timer=Timer(), missing=missing,
                        getsizeof=getsizeof)

    def decorator(self, maxsize, ttl=0, typed=False, lock=None):
        return ttl_cache(maxsize, ttl, timer=Timer(), typed=typed, lock=lock)

    def test_lru(self):
        cache = self.cache(maxsize=2)

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

    def test_ttl(self):
        cache = self.cache(maxsize=2, ttl=1)
        self.assertEqual(0, cache.timer())
        self.assertEqual(1, cache.ttl)

        cache[1] = 1
        self.assertEqual({1}, set(cache))
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache.currsize)
        self.assertEqual(1, cache[1])

        cache.timer.tick()
        self.assertEqual({1}, set(cache))
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache.currsize)
        self.assertEqual(1, cache[1])

        cache[2] = 2
        self.assertEqual({1, 2}, set(cache))
        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache.timer.tick()
        self.assertEqual({2}, set(cache))
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])

        cache[3] = 3
        self.assertEqual({2, 3}, set(cache))
        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        cache.timer.tick()
        self.assertEqual({3}, set(cache))
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])

        cache.timer.tick()
        self.assertEqual(set(), set(cache))
        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

        with self.assertRaises(KeyError):
            del cache[1]
        with self.assertRaises(KeyError):
            cache.pop(2)

    def test_expire(self):
        cache = self.cache(maxsize=3, ttl=2)
        with cache.timer as time:
            self.assertEqual(time, cache.timer())
        self.assertEqual(2, cache.ttl)

        cache[1] = 1
        cache.timer.tick()
        cache[2] = 2
        cache.timer.tick()
        cache[3] = 3
        self.assertEqual(2, cache.timer())

        self.assertEqual({1, 2, 3}, set(cache))
        self.assertEqual(3, len(cache))
        self.assertEqual(3, cache.currsize)
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        cache.expire()
        self.assertEqual({1, 2, 3}, set(cache))
        self.assertEqual(3, len(cache))
        self.assertEqual(3, cache.currsize)
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        cache.expire(3)
        self.assertEqual({2, 3}, set(cache))
        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        cache.expire(4)
        self.assertEqual({3}, set(cache))
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])

        cache.expire(5)
        self.assertEqual(set(), set(cache))
        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

    def test_atomic(self):
        cache = TTLCache(maxsize=1, ttl=1, timer=Timer(auto=True))
        cache[1] = 1
        self.assertEqual(1, cache[1])
        cache[1] = 1
        self.assertEqual(1, cache.get(1))
        cache[1] = 1
        self.assertEqual(1, cache.pop(1))
        cache[1] = 1
        self.assertEqual(1, cache.setdefault(1))

    def test_tuple_key(self):
        cache = self.cache(maxsize=1, ttl=0)
        self.assertEqual(0, cache.ttl)

        cache[(1, 2, 3)] = 42
        self.assertEqual(42, cache[(1, 2, 3)])
        cache.timer.tick()
        with self.assertRaises(KeyError):
            cache[(1, 2, 3)]
        self.assertNotIn((1, 2, 3), cache)
