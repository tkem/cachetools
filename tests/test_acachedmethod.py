import sys
import unittest
import unittest.mock

from cachetools import Cache, keys
from cachetools.aio import acachedmethod

from . import _TestCaseProtocol


class Cached:
    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

    async def __get(self, _value):
        result = self.count
        self.count += 1
        return result

    @acachedmethod(lambda self: self.cache)
    async def get(self, value):
        """docstring"""

        return await self.__get(value)

    @acachedmethod(lambda self: self.cache, key=keys.typedmethodkey)
    async def get_typed(self, value):
        return await self.__get(value)

    @acachedmethod(lambda self: self.cache, info=True)
    async def get_info(self, value):
        return await self.__get(value)

    get_aliased = acachedmethod(lambda self: self.cache)(__get)


class Unhashable(Cached):
    # https://github.com/tkem/cachetools/issues/107
    def __hash__(self):
        raise TypeError("unhashable type")


class AsyncMethodDecoratorTestMixin(_TestCaseProtocol):
    def cache(self, _minsize, **_kwargs):
        raise NotImplementedError

    async def test_decorator(self):
        cached = Cached(self.cache(2))

        self.assertEqual(await cached.get(0), 0)
        self.assertEqual(await cached.get(1), 1)
        self.assertEqual(await cached.get(1), 1)
        self.assertEqual(await cached.get(1.0), 1)
        self.assertEqual(await cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(await cached.get(1), 2)

    async def test_decorator_typed(self):
        cached = Cached(self.cache(3))

        self.assertEqual(await cached.get_typed(0), 0)
        self.assertEqual(await cached.get_typed(1), 1)
        self.assertEqual(await cached.get_typed(1), 1)
        self.assertEqual(await cached.get_typed(1.0), 2)
        self.assertEqual(await cached.get_typed(1.0), 2)
        self.assertEqual(await cached.get_typed(0.0), 3)

    async def test_decorator_unhashable(self):
        cached = Unhashable(self.cache(2))

        self.assertEqual(await cached.get(0), 0)
        self.assertEqual(await cached.get(1), 1)
        self.assertEqual(await cached.get(1), 1)
        self.assertEqual(await cached.get(1.0), 1)
        self.assertEqual(await cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(await cached.get(1), 2)

    async def test_decorator_info(self):
        cache = self.cache(2)
        cached = Cached(cache)
        wrapper = cached.get_info

        maxsize = cache.maxsize if isinstance(cache, Cache) else None

        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(await wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, maxsize, 2))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, maxsize, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(await wrapper(0), 2)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(await wrapper(0), 2)
        self.assertEqual(wrapper.cache_info(), (1, 1, maxsize, 1))

        # assert hits/misses are counted per instance
        cached = Cached(self.cache(2))
        self.assertEqual(await cached.get_info(0), 0)
        self.assertEqual(cached.get_info.cache_info(), (0, 1, maxsize, 1))

    async def test_decorator_wrapped(self):
        cache = self.cache(2)
        cached = Cached(cache)

        self.assertEqual(len(cache), 0)
        self.assertEqual(await cached.get.__wrapped__(cached, 0), 0)
        self.assertEqual(cached.get.__name__, "get")
        self.assertEqual((cached.get.__doc__ or "").strip(), "docstring")
        self.assertEqual(len(cache), 0)
        self.assertEqual(await cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(await cached.get(0), 1)
        self.assertEqual(len(cache), 1)

    async def test_decorator_attributes(self):
        cache = self.cache(2)
        cached = Cached(cache)

        self.assertIs(cached.get.cache, cache)
        self.assertEqual(cached.get.cache_key(42), keys.methodkey(cached, 42))
        self.assertFalse(hasattr(cached.get, "cache_info"))

        self.assertIs(cached.get_info.cache, cache)
        self.assertEqual(cached.get_info.cache_key(42), keys.methodkey(cached, 42))
        self.assertTrue(hasattr(cached.get_info, "cache_info"))

    async def test_decorator_clear(self):
        cache = self.cache(2)
        cached = Cached(cache)

        self.assertEqual(await cached.get(0), 0)
        self.assertEqual(len(cache), 1)
        cached.get.cache_clear()
        self.assertEqual(len(cache), 0)

    async def test_decorator_pickle(self):
        import pickle

        cache = self.cache(3)
        cached = Cached(cache)
        self.assertEqual(len(cache), 0)

        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(len(unpickled.get.cache), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(await unpickled.get(0), 0)
        self.assertEqual(len(unpickled.get.cache), 1)
        self.assertEqual(len(cache), 0)
        self.assertEqual(await unpickled.get(1), 1)
        self.assertEqual(len(unpickled.get.cache), 2)
        self.assertEqual(len(cache), 0)

        self.assertEqual(len(cache), 0)
        self.assertEqual(await cached.get(0), 0)
        self.assertEqual(len(cache), 1)

        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(len(unpickled.get.cache), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(await unpickled.get(0), 0)
        self.assertEqual(len(unpickled.get.cache), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(await unpickled.get(1), 1)
        self.assertEqual(len(unpickled.get.cache), 2)
        self.assertEqual(len(cache), 1)

    async def test_decorator_pickle_info(self):
        import pickle

        cache = self.cache(3)
        cached = Cached(cache)
        maxsize = cache.maxsize if isinstance(cache, Cache) else None
        self.assertEqual(len(cache), 0)

        # hits and misses will be reset when unpickling - since these
        # are primarily used for debugging/tuning, this is probably OK
        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(unpickled.get_info.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(await unpickled.get_info(0), 0)
        self.assertEqual(unpickled.get_info.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(await unpickled.get_info(1), 1)
        self.assertEqual(unpickled.get_info.cache_info(), (0, 2, maxsize, 2))
        self.assertEqual(len(cache), 0)

        self.assertEqual(await cached.get_info(0), 0)
        self.assertEqual(len(cache), 1)

        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(unpickled.get_info.cache_info(), (0, 0, maxsize, 1))
        self.assertEqual(await unpickled.get_info(0), 0)
        self.assertEqual(unpickled.get_info.cache_info(), (1, 0, maxsize, 1))
        self.assertEqual(await unpickled.get_info(1), 1)
        self.assertEqual(unpickled.get_info.cache_info(), (1, 1, maxsize, 2))
        self.assertEqual(await unpickled.get_info(0), 0)
        self.assertEqual(unpickled.get_info.cache_info(), (2, 1, maxsize, 2))
        self.assertEqual(len(cache), 1)

    async def test_decorator_pickle_aliased(self):
        import pickle

        cache = self.cache(3)
        cached = Cached(cache)
        self.assertEqual(len(cache), 0)

        self.assertEqual(await cached.get_aliased(0), 0)
        self.assertEqual(len(cache), 1)

        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(len(unpickled.get_aliased.cache), 1)
        self.assertEqual(await unpickled.get_aliased(0), 0)
        self.assertEqual(len(unpickled.get_aliased.cache), 1)
        self.assertEqual(len(cache), 1)

    async def test_decorator_pickle_class_access(self):
        import pickle

        # decorated methods can no longer be pickled at class level
        with self.assertRaisesRegex(TypeError, "get_info"):
            pickle.dumps(Cached.get_info)

        with self.assertRaisesRegex(TypeError, "get_aliased"):
            pickle.dumps(Cached.get_aliased)

    async def test_decorator_slots(self):

        class Slots:
            __slots__ = ("cache",)

            def __init__(self, cache):
                self.cache = cache

            @acachedmethod(lambda self: self.cache)
            async def get(self, value):
                return value

            @acachedmethod(lambda self: self.cache, info=True)
            async def get_info(self, value):
                return value

        cache = self.cache(2)
        cached = Slots(cache)

        with self.assertRaises(TypeError):
            await cached.get_info(42)

        with self.assertRaises(TypeError):
            await cached.get(0)

    async def test_decorator_immutable_dict(self):

        class ReadOnlyDict(dict):
            def __setitem__(self, _key, _value):
                raise TypeError("Modification not supported")

            def setdefault(self, _key, _value=None):
                raise TypeError("Modification not supported")

        class Immutable:
            def __init__(self, cache):
                self.cache = cache
                self.__dict__ = ReadOnlyDict(self.__dict__)

            @acachedmethod(lambda self: self.cache)
            async def get(self, value):
                return value

            @acachedmethod(lambda self: self.cache, info=True)
            async def get_info(self, value):
                return value

        cache = self.cache(2)
        cached = Immutable(cache)

        with self.assertRaises(TypeError):
            await cached.get_info(42)

        with self.assertRaises(TypeError):
            self.assertEqual(await cached.get(0), 0)

    async def test_decorator_different_names(self):
        # RuntimeError for Python < 3.12, TypeError otherwise
        with self.assertRaisesRegex(Exception, "bar"):

            class Cached:
                @acachedmethod(lambda _: self.cache(2))
                async def foo(_self):
                    pass

                bar = foo

    async def test_decorator_no_set_name(self):
        class Cached:
            async def foo(_self):
                pass

        Cached.bar = acachedmethod(lambda _: self.cache(2))(Cached.foo)  # type: ignore
        Cached.baz = acachedmethod(lambda _: self.cache(2), info=True)(Cached.foo)  # type: ignore

        cached = Cached()

        with self.assertRaises(TypeError):
            await cached.bar()  # type: ignore

        with self.assertRaises(TypeError):
            await cached.baz()  # type: ignore


class AsyncCacheMethodTest(
    unittest.IsolatedAsyncioTestCase, AsyncMethodDecoratorTestMixin
):
    def cache(self, minsize, **kwargs):
        return Cache(maxsize=minsize, **kwargs)

    async def test_nospace(self):
        cached = Cached(self.cache(0))

        self.assertEqual(await cached.get(0), 0)
        self.assertEqual(await cached.get(1), 1)
        self.assertEqual(await cached.get(1), 2)
        self.assertEqual(await cached.get(1.0), 3)
        self.assertEqual(await cached.get(1.0), 4)

        self.assertEqual(await cached.get_typed(0), 5)
        self.assertEqual(await cached.get_typed(1), 6)
        self.assertEqual(await cached.get_typed(1.0), 7)

        self.assertEqual(await cached.get_info(0), 8)
        self.assertEqual(await cached.get_info(1), 9)
        self.assertEqual(await cached.get_info(1.0), 10)

    async def test_shared_cache(self):
        cache = self.cache(2)
        cached1 = Cached(cache)
        cached2 = Cached(cache)

        self.assertEqual(cached1.get_info.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached2.get_info.cache_info(), (0, 0, 2, 0))

        # hits/misses are counted by instance
        self.assertEqual(await cached1.get_info(0), 0)
        self.assertEqual(cached1.get_info.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached2.get_info.cache_info(), (0, 0, 2, 1))

        # default methodkey discards "self", so results will be shared
        # across instances
        self.assertEqual(await cached2.get_info(0), 0)
        self.assertEqual(cached1.get_info.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached2.get_info.cache_info(), (1, 0, 2, 1))
        self.assertEqual(await cached1.get_info(0), 0)
        self.assertEqual(cached1.get_info.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached2.get_info.cache_info(), (1, 0, 2, 1))
        self.assertEqual(await cached1.get_info(1), 1)
        self.assertEqual(cached1.get_info.cache_info(), (1, 2, 2, 2))
        self.assertEqual(cached2.get_info.cache_info(), (1, 0, 2, 2))
        self.assertEqual(await cached2.get_info(1), 1)
        self.assertEqual(cached1.get_info.cache_info(), (1, 2, 2, 2))
        self.assertEqual(cached2.get_info.cache_info(), (2, 0, 2, 2))

    async def test_value_too_large(self):
        cache = self.cache(1, getsizeof=lambda x: x)
        cached = Cached(cache)
        self.assertEqual(await cached.get(0), 0)
        self.assertIn(0, cache.values())
        self.assertEqual(await cached.get(1), 1)
        self.assertIn(1, cache.values())
        self.assertEqual(await cached.get(2), 2)
        self.assertNotIn(2, cache.values())


class DictMethodTest(unittest.IsolatedAsyncioTestCase, AsyncMethodDecoratorTestMixin):
    def cache(self, minsize, **_kwargs):
        return {}


class WeakRefMethodTest(unittest.IsolatedAsyncioTestCase):
    async def test_weakref(self):
        import fractions
        import gc
        import weakref

        # at least with Python 3.11, `int` does not support weak references
        # even when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):  # type: ignore
                return Int(fractions.Fraction.__add__(self, other))

        cache = weakref.WeakValueDictionary()
        cached = Cached(cache, count=Int(0))  # type: ignore

        self.assertEqual(await cached.get(0), 0)
        gc.collect()
        self.assertEqual(await cached.get(0), 1)

        ref = await cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual(await cached.get(1), 2)
        self.assertEqual(await cached.get(1.0), 2)

        ref = await cached.get_typed(2)
        self.assertEqual(ref, 3)
        self.assertEqual(await cached.get_typed(1), 4)
        self.assertEqual(await cached.get_typed(1.0), 5)

        cached.cache.clear()
        self.assertEqual(await cached.get(1), 6)


class NoneMethodTest(unittest.IsolatedAsyncioTestCase):
    async def test_none_info(self):
        cached = Cached(None)
        wrapper = cached.get_info

        with self.assertRaises(TypeError):
            wrapper.cache_info()


@unittest.skip("FIXME: create_autospec returns AsyncMock for async _functions_")
class AutospecTest(unittest.IsolatedAsyncioTestCase):
    async def test_autospec(self):
        cached = unittest.mock.create_autospec(Cached, instance=True)
        self.assertIsNotNone(await cached.get(0))
        self.assertIsNotNone(cached.get_info(0))


class ClassMethodTest(unittest.IsolatedAsyncioTestCase):
    class Cached(Cached):
        @classmethod
        @acachedmethod(lambda cls: {})
        async def get_class(cls, value):
            return 42

    async def test_classmethod_basic(self):
        cached = self.Cached({})

        with self.assertRaises(TypeError):
            cached.get_class(42)

    @unittest.skipIf(sys.version_info < (3, 13), "only supported with Python >= 3.13")
    async def test_classmethod(self):
        cached = self.Cached({})

        with self.assertRaisesRegex(TypeError, "class method"):
            cached.get_class(42)
