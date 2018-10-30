import asyncio
import functools
import operator
import unittest

import cachetools
from cachetools import LRUCache, cachedmethod, keys


def sync(func):
    """
    Helper to force an async function/method to run synchronously.
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapped


class AsyncTestMixin(object):

    async def coro(self, *args, **kwargs):
        if hasattr(self, 'count'):
            self.count += 1
        else:
            self.count = 0

        await asyncio.sleep(0)

        return self.count

    @sync
    async def test_decorator_async(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.coro)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.coro)

        self.assertEqual((await wrapper(0)), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertNotIn(cachetools.keys.hashkey(1), cache)
        self.assertNotIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertIn(cachetools.keys.hashkey(1), cache)
        self.assertIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual((await wrapper(1.0)), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual((await wrapper(1.0)), 1)
        self.assertEqual(len(cache), 2)

    @sync
    async def test_decorator_typed_async(self):
        cache = self.cache(3)
        key = cachetools.keys.typedkey
        wrapper = cachetools.cached(cache, key=key)(self.coro)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.coro)

        self.assertEqual((await wrapper(0)), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertNotIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual((await wrapper(1.0)), 2)
        self.assertEqual(len(cache), 3)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual((await wrapper(1.0)), 2)
        self.assertEqual(len(cache), 3)

    @sync
    async def test_decorator_lock_async(self):
        class Lock(object):

            count = 0

            def __enter__(self):
                Lock.count += 1

            def __exit__(self, *exc):
                pass

        cache = self.cache(2)
        wrapper = cachetools.cached(cache, lock=Lock())(self.coro)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.coro)
        self.assertEqual((await wrapper(0)), 0)
        self.assertEqual(Lock.count, 2)
        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(Lock.count, 4)
        self.assertEqual((await wrapper(1)), 1)
        self.assertEqual(Lock.count, 5)


class Cached(object):

    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

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
    async def coroget(self, value):
        await asyncio.sleep(0)
        return self.count

    def __enter__(self):
        self.count += 1

    def __exit__(self, *exc):
        pass


class AsyncCachedMethodTest(unittest.TestCase):

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

        self.assertEqual((await cached.coroget(1)), 2)
        self.assertEqual((await cached.coroget(1.0)), 2)

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
