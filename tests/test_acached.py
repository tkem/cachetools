import unittest

import cachetools
import cachetools.aio
import cachetools.keys

from . import _TestCaseProtocol


class AsyncDecoratorTestMixin(_TestCaseProtocol):
    def cache(self, minsize):
        raise NotImplementedError

    async def func(self, *args, **kwargs):
        if hasattr(self, "count"):
            self.count += 1
        else:
            self.count = 0
        return self.count

    async def error_func(self, *args, **kwargs):
        raise ValueError("test error")

    async def test_decorator(self):
        cache = self.cache(2)
        wrapper = cachetools.aio.acached(cache)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertNotIn(cachetools.keys.hashkey(1), cache)
        self.assertNotIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual(await wrapper(1), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertIn(cachetools.keys.hashkey(1), cache)
        self.assertIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual(await wrapper(1), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(await wrapper(1.0), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(await wrapper(1.0), 1)
        self.assertEqual(len(cache), 2)

    async def test_decorator_typed(self):
        cache = self.cache(3)
        key = cachetools.keys.typedkey
        wrapper = cachetools.aio.acached(cache, key=key)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertNotIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(await wrapper(1), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(await wrapper(1), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(await wrapper(1.0), 2)
        self.assertEqual(len(cache), 3)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(await wrapper(1.0), 2)
        self.assertEqual(len(cache), 3)

    async def test_decorator_wrapped(self):
        cache = self.cache(2)
        wrapper = cachetools.aio.acached(cache)(self.func)

        self.assertEqual(wrapper.__wrapped__, self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(await wrapper.__wrapped__(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(await wrapper(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(await wrapper(0), 1)
        self.assertEqual(len(cache), 1)

    async def test_decorator_attributes(self):
        cache = self.cache(2)
        wrapper = cachetools.aio.acached(cache)(self.func)

        self.assertIs(wrapper.cache, cache)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertFalse(hasattr(wrapper, "cache_info"))

    async def test_decorator_clear(self):
        cache = self.cache(2)
        wrapper = cachetools.aio.acached(cache)(self.func)
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)


class AsyncCacheTest(unittest.IsolatedAsyncioTestCase, AsyncDecoratorTestMixin):
    def cache(self, minsize):
        return cachetools.Cache(maxsize=minsize)

    async def test_decorator_info(self):
        cache = self.cache(2)
        wrapper = cachetools.aio.acached(cache, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(await wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))

    async def test_zero_size_cache_decorator(self):
        cache = self.cache(0)
        wrapper = cachetools.aio.acached(cache)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(len(cache), 0)

    async def test_zero_size_cache_decorator_info(self):
        cache = self.cache(0)
        wrapper = cachetools.aio.acached(cache, info=True)(self.func)

        self.assertEqual(wrapper.cache_info(), (0, 0, 0, 0))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, 0, 0))


class AsyncDictTest(unittest.IsolatedAsyncioTestCase, AsyncDecoratorTestMixin):
    def cache(self, minsize):
        return {}

    async def test_decorator_info(self):
        cache = self.cache(2)
        wrapper = cachetools.aio.acached(cache, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, None, 1))
        self.assertEqual(await wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, None, 2))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, None, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))


class AsyncCustomCacheTest(unittest.IsolatedAsyncioTestCase, AsyncDecoratorTestMixin):
    class CustomCache:
        """Duck-typed cache that is not a `collections.abc.Mapping` instance."""

        def __init__(self):
            self.__data = {}

        def __contains__(self, key):
            return key in self.__data

        def __getitem__(self, key):
            return self.__data[key]

        def __setitem__(self, key, value):
            self.__data[key] = value

        def __len__(self):
            return len(self.__data)

        def setdefault(self, key, value=None):
            return self.__data.setdefault(key, value)

        def clear(self):
            self.__data.clear()

    def cache(self, minsize):
        return self.CustomCache()

    async def test_decorator_info(self):
        cache = self.cache(2)
        wrapper = cachetools.aio.acached(cache, info=True)(self.func)  # type: ignore
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, None, 1))
        self.assertEqual(await wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, None, 2))
        self.assertEqual(await wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, None, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))


class AsyncInvalidCacheTest(unittest.IsolatedAsyncioTestCase):
    async def func(self, *args, **kwargs):
        return args + tuple(kwargs.items())

    async def test_decorator(self):
        # passing cache=None is no longer supported since v8.0.0
        with self.assertRaisesRegex(TypeError, "None"):
            cachetools.aio.acached(None)  # type: ignore

    async def test_decorator_info(self):
        # passing cache=None is no longer supported since v8.0.0
        with self.assertRaisesRegex(TypeError, "None"):
            cachetools.aio.acached(None, info=True)  # type: ignore
