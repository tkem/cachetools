import unittest

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

    def test_typed_decorator(self):
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

    def test_nosize_decorator(self):
        cached = self.decorator(maxsize=0)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 2, 0, 0))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (0, 3, 0, 0))

    def test_cache_clear(self):
        cached = self.decorator(maxsize=2)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        cached.cache_clear()
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))


class LFUDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    def decorator(self, maxsize, typed=False, lock=None):
        return cachetools.func.lfu_cache(maxsize, typed=typed, lock=lock)


class LRUDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    def decorator(self, maxsize, typed=False, lock=None):
        return cachetools.func.lru_cache(maxsize, typed=typed, lock=lock)


class RRDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    def decorator(self, maxsize, typed=False, lock=None):
        return cachetools.func.rr_cache(maxsize, typed=typed, lock=lock)


class TTLDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    def decorator(self, maxsize, typed=False, lock=None):
        return cachetools.func.ttl_cache(maxsize, typed=typed, lock=lock)
