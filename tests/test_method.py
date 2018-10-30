import asyncio
import operator
import unittest

from cachetools import LRUCache, cachedmethod, keys

from . import sync


class Cached(object):

    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

    @cachedmethod(operator.attrgetter('cache'))
    def get(self, value):
        count = self.count
        self.count += 1
        return count

    @cachedmethod(operator.attrgetter('cache'), key=keys.typedkey)
    def get_typed(self, value):
        count = self.count
        self.count += 1
        return count

    @cachedmethod(operator.attrgetter('cache'))
    async def coroget(self, value):
        count = self.count
        self.count += 1
        await asyncio.sleep(0)
        return count

    @cachedmethod(operator.attrgetter('cache'), key=keys.typedkey)
    async def coroget_typed(self, value):
        count = self.count
        self.count += 1
        await asyncio.sleep(0)
        return count


class Locked(object):

    def __init__(self, cache):
        self.cache = cache
        self.count = 0

    @cachedmethod(operator.attrgetter('cache'), lock=lambda self: self)
    def get(self, value):
        return self.count

    @cachedmethod(operator.attrgetter('cache'), lock=lambda self: self)
    async def coroget(self, value):
        await asyncio.sleep(0)
        return self.count

    def __enter__(self):
        self.count += 1

    def __exit__(self, *exc):
        pass


class CachedMethodTest(unittest.TestCase):

    def test_dict(self):
        cached = Cached({})

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_typed_dict(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)
        self.assertEqual(cached.get_typed(0), 4)

    def test_lru(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_typed_lru(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)
        self.assertEqual(cached.get_typed(0), 4)

    def test_nospace(self):
        cached = Cached(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(1.0), 4)

    def test_nocache(self):
        cached = Cached(None)

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(1.0), 4)

    def test_weakref(self):
        import weakref
        import fractions
        import gc

        # in Python 3.4, `int` does not support weak references even
        # when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):
                return Int(fractions.Fraction.__add__(self, other))

        cached = Cached(weakref.WeakValueDictionary(), count=Int(0))

        self.assertEqual(cached.get(0), 0)
        gc.collect()
        self.assertEqual(cached.get(0), 1)

        ref = cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)

        ref = cached.get_typed(1)
        self.assertEqual(ref, 3)
        self.assertEqual(cached.get_typed(1), 3)
        self.assertEqual(cached.get_typed(1.0), 4)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 5)

    def test_locked_dict(self):
        cached = Locked({})

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(2.0), 7)

    def test_locked_nocache(self):
        cached = Locked(None)

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 0)
        self.assertEqual(cached.get(1), 0)
        self.assertEqual(cached.get(1.0), 0)
        self.assertEqual(cached.get(1.0), 0)

    def test_locked_nospace(self):
        cached = Locked(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.get(1), 5)
        self.assertEqual(cached.get(1.0), 7)
        self.assertEqual(cached.get(1.0), 9)

    @sync
    async def test_dict_async(self):
        cached = Cached({})

        self.assertEqual((await cached.coroget(0)), 0)
        self.assertEqual((await cached.coroget(1)), 1)
        self.assertEqual((await cached.coroget(1)), 1)
        self.assertEqual((await cached.coroget(1.0)), 1)
        self.assertEqual((await cached.coroget(1.0)), 1)

        cached.cache.clear()
        self.assertEqual((await cached.coroget(1)), 2)

    @sync
    async def test_typed_dict_async(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual((await cached.coroget_typed(0)), 0)
        self.assertEqual((await cached.coroget_typed(1)), 1)
        self.assertEqual((await cached.coroget_typed(1)), 1)
        self.assertEqual((await cached.coroget_typed(1.0)), 2)
        self.assertEqual((await cached.coroget_typed(1.0)), 2)
        self.assertEqual((await cached.coroget_typed(0.0)), 3)
        self.assertEqual((await cached.coroget_typed(0)), 4)

    @sync
    async def test_lru_async(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual((await cached.coroget(0)), 0)
        self.assertEqual((await cached.coroget(1)), 1)
        self.assertEqual((await cached.coroget(1)), 1)
        self.assertEqual((await cached.coroget(1.0)), 1)
        self.assertEqual((await cached.coroget(1.0)), 1)

        cached.cache.clear()
        self.assertEqual((await cached.coroget(1)), 2)

    @sync
    async def test_typed_lru_async(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual((await cached.coroget_typed(0)), 0)
        self.assertEqual((await cached.coroget_typed(1)), 1)
        self.assertEqual((await cached.coroget_typed(1)), 1)
        self.assertEqual((await cached.coroget_typed(1.0)), 2)
        self.assertEqual((await cached.coroget_typed(1.0)), 2)
        self.assertEqual((await cached.coroget_typed(0.0)), 3)
        self.assertEqual((await cached.coroget_typed(0)), 4)

    @sync
    async def test_nospace_async(self):
        cached = Cached(LRUCache(maxsize=0))

        self.assertEqual((await cached.coroget(0)), 0)
        self.assertEqual((await cached.coroget(1)), 1)
        self.assertEqual((await cached.coroget(1)), 2)
        self.assertEqual((await cached.coroget(1.0)), 3)
        self.assertEqual((await cached.coroget(1.0)), 4)

    @sync
    async def test_nocache_async(self):
        cached = Cached(None)

        self.assertEqual((await cached.coroget(0)), 0)
        self.assertEqual((await cached.coroget(1)), 1)
        self.assertEqual((await cached.coroget(1)), 2)
        self.assertEqual((await cached.coroget(1.0)), 3)
        self.assertEqual((await cached.coroget(1.0)), 4)

    @sync
    async def test_weakref_async(self):
        import weakref
        import fractions
        import gc

        # in Python 3.4, `int` does not support weak references even
        # when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):
                return Int(fractions.Fraction.__add__(self, other))

        cached = Cached(weakref.WeakValueDictionary(), count=Int(0))

        self.assertEqual((await cached.coroget(0)), 0)
        gc.collect()
        self.assertEqual((await cached.coroget(0)), 1)

        ref = cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual((await cached.coroget(1)), 2)
        self.assertEqual((await cached.coroget(1.0)), 2)

        ref = cached.get_typed(1)
        self.assertEqual(ref, 3)
        self.assertEqual((await cached.coroget_typed(1)), 3)
        self.assertEqual((await cached.coroget_typed(1.0)), 4)

        cached.cache.clear()
        self.assertEqual((await cached.coroget(1)), 5)

    @sync
    async def test_locked_dict_async(self):
        cached = Locked({})

        self.assertEqual((await cached.coroget(0)), 1)
        self.assertEqual((await cached.coroget(1)), 3)
        self.assertEqual((await cached.coroget(1)), 3)
        self.assertEqual((await cached.coroget(1.0)), 3)
        self.assertEqual((await cached.coroget(2.0)), 7)

    @sync
    async def test_locked_nocache_async(self):
        cached = Locked(None)

        self.assertEqual((await cached.coroget(0)), 0)
        self.assertEqual((await cached.coroget(1)), 0)
        self.assertEqual((await cached.coroget(1)), 0)
        self.assertEqual((await cached.coroget(1.0)), 0)
        self.assertEqual((await cached.coroget(1.0)), 0)

    @sync
    async def test_locked_nospace_async(self):
        cached = Locked(LRUCache(maxsize=0))

        self.assertEqual((await cached.coroget(0)), 1)
        self.assertEqual((await cached.coroget(1)), 3)
        self.assertEqual((await cached.coroget(1)), 5)
        self.assertEqual((await cached.coroget(1.0)), 7)
        self.assertEqual((await cached.coroget(1.0)), 9)
