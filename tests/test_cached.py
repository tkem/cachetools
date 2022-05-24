import unittest

import cachetools
import cachetools.keys


class CountedLock:
    def __init__(self):
        self.count = 0

    def __enter__(self):
        self.count += 1

    def __exit__(self, *exc):
        pass


class DecoratorTestMixin:
    def cache(self, minsize):
        raise NotImplementedError

    def func(self, *args, **kwargs):
        if hasattr(self, "count"):
            self.count += 1
        else:
            self.count = 0
        return self.count

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

    def test_decorator_attributes_lock(self):
        cache = self.cache(2)
        lock = CountedLock()
        wrapper = cachetools.cached(cache, lock=lock)(self.func)

        self.assertIs(wrapper.cache, cache)
        self.assertIs(wrapper.cache_key, cachetools.keys.hashkey)
        self.assertIs(wrapper.cache_lock, lock)

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

    def test_decorator_clear_none(self):
        cache = None
        wrapper = cachetools.cached(cache)(self.func)
        wrapper.cache_clear()  # no-op


class CacheWrapperTest(unittest.TestCase, DecoratorTestMixin):
    def cache(self, minsize):
        return cachetools.Cache(maxsize=minsize)

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


class DictWrapperTest(unittest.TestCase, DecoratorTestMixin):
    def cache(self, minsize):
        return dict()


class NoneWrapperTest(unittest.TestCase):
    def func(self, *args, **kwargs):
        return args + tuple(kwargs.items())

    def test_decorator(self):
        wrapper = cachetools.cached(None)(self.func)

        self.assertEqual(wrapper(0), (0,))
        self.assertEqual(wrapper(1), (1,))
        self.assertEqual(wrapper(1, foo="bar"), (1, ("foo", "bar")))
