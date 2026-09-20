import unittest

import cachetools
import cachetools.keys

from . import CountedCondition, CountedLock, _TestCaseProtocol


class DecoratorTestMixin(_TestCaseProtocol):
    def cache(self, minsize):
        raise NotImplementedError

    def func(self, *args, **kwargs):
        if hasattr(self, "count"):
            self.count += 1
        else:
            self.count = 0
        return self.count

    def error_func(self, *args, **kwargs):
        raise ValueError("test error")

    def test_decorator(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertNotIn(cachetools.keys.hashkey(1), cache)
        self.assertNotIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.hashkey(0), cache)
        self.assertIn(cachetools.keys.hashkey(1), cache)
        self.assertIn(cachetools.keys.hashkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 1)
        self.assertEqual(len(cache), 2)

    def test_decorator_typed(self):
        cache = self.cache(3)
        key = cachetools.keys.typedkey
        wrapper = cachetools.cached(cache, key=key)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertNotIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertNotIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 2)
        self.assertEqual(len(cache), 3)
        self.assertIn(cachetools.keys.typedkey(0), cache)
        self.assertIn(cachetools.keys.typedkey(1), cache)
        self.assertIn(cachetools.keys.typedkey(1.0), cache)

        self.assertEqual(wrapper(1.0), 2)
        self.assertEqual(len(cache), 3)

    def test_decorator_lock(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 2)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 5)

    def test_decorator_cond(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 3)
        self.assertEqual(cond.wait_count, 1)
        self.assertEqual(cond.notify_count, 1)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 6)
        self.assertEqual(cond.wait_count, 2)
        self.assertEqual(cond.notify_count, 2)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 7)
        self.assertEqual(cond.wait_count, 3)
        self.assertEqual(cond.notify_count, 2)

    def test_decorator_lock_cond(self):
        cache = self.cache(2)
        lock = CountedLock()
        cond = CountedCondition()
        wrapper = cachetools.cached(cache, lock=lock, condition=cond)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 3)
        self.assertEqual(cond.wait_count, 1)
        self.assertEqual(cond.notify_count, 1)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 6)
        self.assertEqual(cond.wait_count, 2)
        self.assertEqual(cond.notify_count, 2)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 7)
        self.assertEqual(cond.wait_count, 3)
        self.assertEqual(cond.notify_count, 2)

    def test_decorator_cond_error(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.error_func)

        with self.assertRaises(ValueError):
            wrapper(0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 2)
        self.assertEqual(cond.wait_count, 1)
        self.assertEqual(cond.notify_count, 1)

        # verify pending set is cleaned up, otherwise this might deadlock
        with self.assertRaises(ValueError):
            wrapper(0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 4)
        self.assertEqual(cond.wait_count, 2)
        self.assertEqual(cond.notify_count, 2)

    def test_decorator_wrapped(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertEqual(wrapper.__wrapped__, self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(wrapper(0), 1)
        self.assertEqual(len(cache), 1)

    def test_decorator_attributes(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertIs(wrapper.cache, cache)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertIs(wrapper.cache_lock, None)
        self.assertIs(wrapper.cache_condition, None)
        self.assertFalse(hasattr(wrapper, "cache_info"))

    def test_decorator_attributes_lock(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)

        self.assertIs(wrapper.cache, cache)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertIs(wrapper.cache_lock, lock)
        self.assertIs(wrapper.cache_condition, None)
        self.assertFalse(hasattr(wrapper, "cache_info"))

    def test_decorator_attributes_cond(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.func)

        self.assertIs(wrapper.cache, cache)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertIs(wrapper.cache_lock, lock)
        self.assertIs(wrapper.cache_condition, cond)
        self.assertFalse(hasattr(wrapper, "cache_info"))

    def test_decorator_clear(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)

    def test_decorator_clear_lock(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertEqual(lock.count, 2)
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 3)

    def test_decorator_clear_cond(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.func)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertEqual(lock.count, 3)
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 4)


class CacheWrapperTest(unittest.TestCase, DecoratorTestMixin):
    def cache(self, minsize):
        return cachetools.Cache(maxsize=minsize)

    def test_decorator_info(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))

    def test_decorator_lock_info(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 3)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 6)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(lock.count, 7)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 8)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        self.assertEqual(lock.count, 9)
        wrapper.cache_clear()
        self.assertEqual(lock.count, 10)
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 11)

    def test_decorator_cond_info(self):
        cache = self.cache(2)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(lock.count, 5)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 8)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(lock.count, 9)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 10)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        self.assertEqual(lock.count, 11)
        wrapper.cache_clear()
        self.assertEqual(lock.count, 12)
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 13)

    def test_decorator_lock_cond_info(self):
        cache = self.cache(2)
        lock = CountedLock()
        cond = CountedCondition()
        wrapper = cachetools.cached(cache, lock=lock, condition=cond, info=True)(
            self.func
        )
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper.cache_info(), (0, 1, 2, 1))
        self.assertEqual(lock.count, 5)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(lock.count, 8)
        self.assertEqual(wrapper.cache_info(), (0, 2, 2, 2))
        self.assertEqual(lock.count, 9)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(lock.count, 10)
        self.assertEqual(wrapper.cache_info(), (1, 2, 2, 2))
        self.assertEqual(lock.count, 11)
        wrapper.cache_clear()
        self.assertEqual(lock.count, 12)
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 2, 0))
        self.assertEqual(lock.count, 13)

    def test_zero_size_cache_decorator(self):
        cache = self.cache(0)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)

    def test_zero_size_cache_decorator_lock(self):
        cache = self.cache(0)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 2)

    def test_zero_size_cache_decorator_cond(self):
        cache = self.cache(0)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 3)

    def test_zero_size_cache_decorator_info(self):
        cache = self.cache(0)
        wrapper = cachetools.cached(cache, info=True)(self.func)

        self.assertEqual(wrapper.cache_info(), (0, 0, 0, 0))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, 0, 0))

    def test_zero_size_cache_decorator_lock_info(self):
        cache = self.cache(0)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock, info=True)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 0, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 3)
        self.assertEqual(wrapper.cache_info(), (0, 1, 0, 0))
        self.assertEqual(lock.count, 4)

    def test_zero_size_cache_decorator_cond_info(self):
        cache = self.cache(0)
        lock = cond = CountedCondition()
        wrapper = cachetools.cached(cache, condition=cond, info=True)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, 0, 0))
        self.assertEqual(lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(lock.count, 4)
        self.assertEqual(wrapper.cache_info(), (0, 1, 0, 0))
        self.assertEqual(lock.count, 5)


class DictTest(unittest.TestCase, DecoratorTestMixin):
    def cache(self, minsize):
        return {}

    def test_decorator_info(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache, info=True)(self.func)
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, None, 1))
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, None, 2))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, None, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))


class CustomCacheTest(unittest.TestCase, DecoratorTestMixin):
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

    def test_decorator_info(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache, info=True)(self.func)  # type: ignore
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, None, 1))
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, None, 2))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, None, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, None, 0))


class InvalidCacheTest(unittest.TestCase):
    def func(self, *args, **kwargs):
        return args + tuple(kwargs.items())

    def test_decorator(self):
        # passing cache=None is no longer supported since v8.0.0
        with self.assertRaisesRegex(TypeError, "None"):
            cachetools.cached(None)  # type: ignore

    def test_decorator_info(self):
        # passing cache=None is no longer supported since v8.0.0
        with self.assertRaisesRegex(TypeError, "None"):
            cachetools.cached(None, info=True)  # type: ignore
