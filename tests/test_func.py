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

    def test_decorator_clear(self):
        cached = self.decorator(maxsize=2)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        cached.cache_clear()
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))

    def test_decorator_nocache(self):
        cached = self.decorator(maxsize=0)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 2, 0, 0))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (0, 3, 0, 0))

    def test_decorator_unbound(self):
        cached = self.decorator(maxsize=None)(lambda n: n)

        self.assertEqual(cached.cache_info(), (0, 0, None, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, None, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, None, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, None, 1))

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
