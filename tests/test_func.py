import unittest
import warnings

import cachetools.func


class DecoratorTestMixin(object):

    def decorator(self, maxsize, typed=False, lock=None):
        raise NotImplementedError

    def test_decorator(self):
        cached = self.decorator(maxsize=2)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, 2, 1))

    def test_decorator_clear(self):
        cached = self.decorator(maxsize=2)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        cached.cache_clear()
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))

    def test_decorator_nosize(self):
        cached = self.decorator(maxsize=0)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 2, 0, 0))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (0, 3, 0, 0))

    def test_decorator_typed(self):
        cached = self.decorator(maxsize=2, typed=True)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (1, 2, 2, 2))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 2, 2, 2))

    def test_decorator_lock(self):
        class Lock(object):
            count = 0

            def __enter__(self):
                Lock.count += 1

            def __exit__(self, *exc):
                pass

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            cached = self.decorator(maxsize=2, lock=Lock)(lambda n: n)
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)

        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(Lock.count, 1)
        self.assertEqual(cached(1), 1)
        self.assertEqual(Lock.count, 3)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(Lock.count, 4)
        self.assertEqual(cached(1), 1)
        self.assertEqual(Lock.count, 5)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(Lock.count, 6)
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(Lock.count, 7)
        self.assertEqual(cached.cache_info(), (2, 1, 2, 1))
        self.assertEqual(Lock.count, 8)

    def test_decorator_nolock(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            cached = self.decorator(maxsize=2, lock=None)(lambda n: n)
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)

        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, 2, 1))


class LFUDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    def decorator(self, maxsize, **kwargs):
        return cachetools.func.lfu_cache(maxsize, **kwargs)


class LRUDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    def decorator(self, maxsize, **kwargs):
        return cachetools.func.lru_cache(maxsize, **kwargs)


class RRDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    def decorator(self, maxsize, **kwargs):
        return cachetools.func.rr_cache(maxsize, **kwargs)


class TTLDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    def decorator(self, maxsize, **kwargs):
        return cachetools.func.ttl_cache(maxsize, **kwargs)
