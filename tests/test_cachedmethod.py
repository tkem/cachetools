import unittest
import warnings


from cachetools import LRUCache, cachedmethod, keys

from . import CountedCondition, CountedLock


class Cached:
    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

    @cachedmethod(lambda self: self.cache)
    def get(self, value, *args):
        self.count += 1
        return self.count

    @cachedmethod(lambda self: self.cache, key=keys.typedmethodkey)
    def get_typedmethod(self, value):
        self.count += 1
        return self.count


class Locked:
    def __init__(self, cache):
        self.cache = cache
        self.count = 0
        self.lock = CountedLock()

    @cachedmethod(lambda self: self.cache, lock=lambda self: self.lock)
    def get(self, value):
        self.count += 1
        return self.count


class Conditioned:
    def __init__(self, cache):
        self.cache = cache
        self.count = 0
        self.lock = self.cond = CountedCondition()

    @cachedmethod(lambda self: self.cache, condition=lambda self: self.cond)
    def get(self, value):
        self.count += 1
        return self.count

    @cachedmethod(
        lambda self: self.cache,
        lock=lambda self: self.lock,
        condition=lambda self: self.cond,
    )
    def get_with_lock(self, value):
        self.count += 1
        return self.count


class Unhashable:
    def __init__(self, cache):
        self.cache = cache

    @cachedmethod(lambda self: self.cache)
    def get_default(self, value):
        return value

    @cachedmethod(lambda self: self.cache, key=keys.hashkey)
    def get_hashkey(self, value):
        return value

    # https://github.com/tkem/cachetools/issues/107
    def __hash__(self):
        raise TypeError("unhashable type")


class CachedMethodTest(unittest.TestCase):
    def test_dict(self):
        cached = Cached({})

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.get(1.0), 2)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 3)

    def test_typedmethod_dict(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get_typedmethod(0), 1)
        self.assertEqual(cached.get_typedmethod(1), 2)
        self.assertEqual(cached.get_typedmethod(1), 2)
        self.assertEqual(cached.get_typedmethod(1.0), 3)
        self.assertEqual(cached.get_typedmethod(1.0), 3)
        self.assertEqual(cached.get_typedmethod(0.0), 4)
        self.assertEqual(cached.get_typedmethod(0), 5)

    def test_lru(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.get(1.0), 2)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 3)

    def test_typedmethod_lru(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get_typedmethod(0), 1)
        self.assertEqual(cached.get_typedmethod(1), 2)
        self.assertEqual(cached.get_typedmethod(1), 2)
        self.assertEqual(cached.get_typedmethod(1.0), 3)
        self.assertEqual(cached.get_typedmethod(1.0), 3)
        self.assertEqual(cached.get_typedmethod(0.0), 4)
        self.assertEqual(cached.get_typedmethod(0), 5)

    def test_nospace(self):
        cached = Cached(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.get(1.0), 4)
        self.assertEqual(cached.get(1.0), 5)

    def test_weakref(self):
        import weakref
        import fractions
        import gc

        # in Python 3.7, `int` does not support weak references even
        # when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):
                return Int(fractions.Fraction.__add__(self, other))

        cached = Cached(weakref.WeakValueDictionary(), count=Int(0))

        self.assertEqual(cached.get(0), 1)
        gc.collect()
        self.assertEqual(cached.get(0), 1)

        ref = cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)

        ref = cached.get_typedmethod(2)
        self.assertEqual(ref, 3)
        self.assertEqual(cached.get_typedmethod(1), 4)
        self.assertEqual(cached.get_typedmethod(1.0), 5)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 6)

    def test_locked_dict(self):
        cached = Locked({})

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.lock.count, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock.count, 4)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock.count, 5)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.lock.count, 6)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.lock.count, 7)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.lock.count, 9)

    def test_locked_nospace(self):
        cached = Locked(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.lock.count, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock.count, 4)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.lock.count, 6)
        self.assertEqual(cached.get(1.0), 4)
        self.assertEqual(cached.lock.count, 8)
        self.assertEqual(cached.get(1.0), 5)
        self.assertEqual(cached.lock.count, 10)

    def test_condition_dict(self):
        cached = Conditioned({})

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.lock.count, 3)
        self.assertEqual(cached.cond.wait_count, 1)
        self.assertEqual(cached.cond.notify_count, 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock.count, 6)
        self.assertEqual(cached.cond.wait_count, 2)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock.count, 7)
        self.assertEqual(cached.cond.wait_count, 3)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.lock.count, 8)
        self.assertEqual(cached.cond.wait_count, 4)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(cached.get(1.0), 2)
        self.assertEqual(cached.lock.count, 9)
        self.assertEqual(cached.cond.wait_count, 5)
        self.assertEqual(cached.cond.notify_count, 2)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.lock.count, 12)
        self.assertEqual(cached.cond.wait_count, 6)
        self.assertEqual(cached.cond.notify_count, 3)

    def test_condition_nospace(self):
        cached = Conditioned(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.lock.count, 3)
        self.assertEqual(cached.cond.wait_count, 1)
        self.assertEqual(cached.cond.notify_count, 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.lock.count, 6)
        self.assertEqual(cached.cond.wait_count, 2)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.lock.count, 9)
        self.assertEqual(cached.cond.wait_count, 3)
        self.assertEqual(cached.cond.notify_count, 3)
        self.assertEqual(cached.get(1.0), 4)
        self.assertEqual(cached.lock.count, 12)
        self.assertEqual(cached.cond.wait_count, 4)
        self.assertEqual(cached.cond.notify_count, 4)
        self.assertEqual(cached.get(1.0), 5)
        self.assertEqual(cached.lock.count, 15)
        self.assertEqual(cached.cond.wait_count, 5)
        self.assertEqual(cached.cond.notify_count, 5)

    def test_unhashable(self):
        cached = Unhashable(LRUCache(maxsize=0))

        self.assertEqual(cached.get_default(0), 0)
        self.assertEqual(cached.get_default(1), 1)

        with self.assertRaises(TypeError):
            cached.get_hashkey(0)

    def test_wrapped(self):
        cache = {}
        cached = Cached(cache)

        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.get.__wrapped__(cached, 0), 1)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.get(0), 2)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.get(0), 2)
        self.assertEqual(len(cache), 1)

    def test_attributes(self):
        cache = {}
        cached = Cached(cache)

        self.assertIs(cached.get.cache, cache)
        self.assertIs(cached.get.cache_key, keys.methodkey)
        self.assertIs(cached.get.cache_lock, None)
        self.assertIs(cached.get.cache_condition, None)

    def test_attributes_lock(self):
        cache = {}
        cached = Locked(cache)

        self.assertIs(cached.get.cache, cache)
        self.assertIs(cached.get.cache_key, keys.methodkey)
        self.assertIs(cached.get.cache_lock, cached.lock)
        self.assertIs(cached.get.cache_condition, None)

    def test_attributes_cond(self):
        cache = {}
        cached = Conditioned(cache)

        self.assertIs(cached.get.cache, cache)
        self.assertIs(cached.get.cache_key, keys.methodkey)
        self.assertIs(cached.get.cache_lock, cached.lock)
        self.assertIs(cached.get.cache_condition, cached.cond)

    def test_clear(self):
        cache = {}
        cached = Cached(cache)

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        cached.get.cache_clear()
        self.assertEqual(len(cache), 0)

    def test_clear_locked(self):
        cache = {}
        cached = Locked(cache)

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.lock.count, 2)
        cached.get.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.lock.count, 3)

    def test_clear_condition(self):
        cache = {}
        cached = Conditioned(cache)

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.lock.count, 3)
        cached.get.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.lock.count, 4)
