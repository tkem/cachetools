import functools
import math
import unittest

from cachetools import TLRUCache

from . import TimedCacheTestMixin


class TLRUCacheTest(unittest.TestCase, TimedCacheTestMixin[TLRUCache]):
    Cache = TLRUCache

    @staticmethod
    def ttl_ttu(ttl, _key, _value, time):
        return time + ttl

    def typed_cache(self, cls, maxsize: float, *, ttl=math.inf, timer=None, **kwargs):
        if timer is None:
            timer = TimedCacheTestMixin.Timer()
        ttu = functools.partial(self.ttl_ttu, ttl)  # picklable, unlike a lambda
        return cls(maxsize, ttu=ttu, timer=timer, **kwargs)

    def test_ttu(self):
        cache = TLRUCache[int, int, int](
            maxsize=6, ttu=lambda _, v, t: t + v + 1, timer=self.Timer()
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

    def test_overwrite_existing_with_expired(self):
        # Overwriting an existing key with an already-expired value must not
        # silently retain the previous value: the assignment cannot store the
        # new (dead-on-arrival) value, so the key has to be evicted instead.
        def ttu(_k, value, t):
            return t + value

        cache = TLRUCache[int, int, int](maxsize=2, ttu=ttu, timer=self.Timer())
        cache[1] = 5
        self.assertEqual(cache[1], 5)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.currsize, 1)

        cache[1] = 0  # ttu -> t, i.e. not (t < t): immediately expired
        self.assertNotIn(1, cache)
        self.assertIsNone(cache.get(1))
        self.assertEqual(len(cache), 0)
        self.assertEqual(cache.currsize, 0)
        self.assertEqual(set(cache), set())

    def test_ttu_expired(self):
        cache = TLRUCache[int, None, int](
            maxsize=1, ttu=lambda k, _, t: t + k, timer=self.Timer()
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

    def test_ttu_reverse_insert(self):
        def ttu(_k, v, t):
            return t + v

        cache = TLRUCache[int, int, int](maxsize=4, ttu=ttu, timer=self.Timer())
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

        cache = TLRUCache[int, int, int](maxsize=4, ttu=ttu, timer=self.Timer())
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

    def test_tlru_default_timer_stubs(self):
        # type stubs must infer key and value types with the default timer
        def ttu(_key: str, value: int, now: float) -> float:
            return now + value

        cache: TLRUCache[str, int] = TLRUCache(maxsize=2, ttu=ttu)

        cache["a"] = 3600
        self.assertEqual(3600, cache["a"])
        self.assertEqual(1, len(cache))
        self.assertIn("a", cache)

        sized: TLRUCache[str, str] = TLRUCache(
            maxsize=10, ttu=lambda _k, _v, now: now + 3600, getsizeof=len
        )

        sized["abc"] = "abc"
        self.assertEqual("abc", sized["abc"])
        self.assertEqual(3, sized.currsize)

    def test_tlru_datetime_stubs(self):
        # type stubs must accept a datetime ttu with a datetime timer
        from datetime import datetime, timedelta

        def ttu(_key: int, _value: int, now: datetime) -> datetime:
            return now + timedelta(days=1)

        cache: TLRUCache[int, int, datetime] = TLRUCache(
            maxsize=1, ttu=ttu, timer=datetime.now
        )

        cache[1] = 1
        self.assertEqual([], cache.expire(datetime.now()))
        self.assertEqual([(1, 1)], cache.expire(datetime.now() + timedelta(days=1)))

    def test_tlru_copy(self):
        import copy

        source = TLRUCache[int, int, int](
            maxsize=3, ttu=lambda _key, value, time: time + value, timer=self.Timer()
        )
        source[1] = 3
        source[2] = 1
        source[3] = 2
        source[1] = 2  # leaves a removed item behind, least recently used is 2

        cache = copy.copy(source)
        self.assertEqual(list(source), list(cache))

        # the copy evicts as its source would, on its own
        cache[4] = 5
        self.assertEqual([1, 3, 4], sorted(cache))
        self.assertEqual([1, 2, 3], sorted(source))

        # items expire in the copy as in its source
        cache.timer.tick()
        self.assertEqual([1, 3], sorted(source))
        self.assertEqual([1, 3, 4], sorted(cache))
        source.timer.tick()
        self.assertEqual([], list(source))
        self.assertEqual([4], list(cache))
