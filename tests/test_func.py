import unittest
from collections.abc import Callable
from typing import Any

import cachetools.func

from . import SimplifiedTestCaseProtocol


class DecoratorTestMixin(SimplifiedTestCaseProtocol):
    DECORATOR: Callable[..., Any]

    def decorator(self, maxsize, **kwargs):
        return self.DECORATOR(maxsize, **kwargs)

    def test_decorator(self):
        cached = self.decorator(maxsize=2)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {"maxsize": 2, "typed": False})
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, 2, 1))

    def test_decorator_clear(self):
        cached = self.decorator(maxsize=2)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {"maxsize": 2, "typed": False})
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        cached.cache_clear()
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))

    def test_decorator_nocache(self):
        cached = self.decorator(maxsize=0)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {"maxsize": 0, "typed": False})
        self.assertEqual(cached.cache_info(), (0, 0, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 2, 0, 0))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (0, 3, 0, 0))

    def test_decorator_unbound(self):
        cached = self.decorator(maxsize=None)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {"maxsize": None, "typed": False})
        self.assertEqual(cached.cache_info(), (0, 0, None, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, None, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, None, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, None, 1))

    def test_decorator_typed(self):
        cached = self.decorator(maxsize=2, typed=True)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {"maxsize": 2, "typed": True})
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (1, 2, 2, 2))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 2, 2, 2))

    def test_decorator_user_function(self):
        cached = self.decorator(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {"maxsize": 128, "typed": False})
        self.assertEqual(cached.cache_info(), (0, 0, 128, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 128, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 128, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, 128, 1))

    def test_decorator_needs_rlock(self):
        """This will deadlock on a cache that uses a regular lock.
        https://github.com/python/cpython/blob/3.13/Lib/test/test_functools.py#L1791

        """

        cached = self.decorator(lambda n: n)

        class RecursiveEquals:
            def __init__(self, use_cache):
                self._use_cache = use_cache

            def __hash__(self):
                return hash(self._use_cache)

            def __eq__(self, other):
                if self._use_cache:
                    # This call will happen while the cache-lock is held,
                    # requiring a reentrant lock to avoid deadlock.
                    cached(self)
                return self._use_cache == other._use_cache

        # Prime the cache.
        cached(RecursiveEquals(False))
        cached(RecursiveEquals(True))
        # Then do a call which will cause a deadlock with a non-reentrant lock.
        self.assertEqual(cached(RecursiveEquals(True)), RecursiveEquals(True))

    def test_decorator_method(self):
        """Though it is not encouraged, like functools.lru_cache, the
        cachetools.func decorators may be used on methods, too.

        """

        decorator = self.decorator(maxsize=2)

        class Cached:
            @decorator
            def get(self, n):
                return n

        cached = Cached()
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(Cached.get(cached, 1), 1)
        self.assertEqual(cached.get.cache_info(), (2, 1, 2, 1))
        self.assertEqual(Cached.get.cache_info(), (2, 1, 2, 1))
        cached.get.cache_clear()
        self.assertEqual(cached.get.cache_info(), (0, 0, 2, 0))
        self.assertEqual(Cached.get.cache_info(), (0, 0, 2, 0))

    def test_stacked_decorators(self):
        inner_wrapper = self.decorator(maxsize=2)(lambda n: n)
        outer_wrapper = self.decorator(maxsize=3, typed=True)(inner_wrapper)
        self.assertIs(outer_wrapper.__wrapped__, inner_wrapper)
        self.assertEqual(
            inner_wrapper.cache_parameters(), {"maxsize": 2, "typed": False}
        )
        self.assertEqual(
            outer_wrapper.cache_parameters(), {"maxsize": 3, "typed": True}
        )
        self.assertEqual(outer_wrapper(1), 1)
        self.assertEqual(outer_wrapper(1), 1)
        self.assertEqual(outer_wrapper.cache_info(), (1, 1, 3, 1))
        self.assertEqual(inner_wrapper.cache_info(), (0, 1, 2, 1))
        outer_wrapper.cache_clear()
        self.assertEqual(outer_wrapper.cache_info(), (0, 0, 3, 0))
        self.assertEqual(inner_wrapper.cache_info(), (0, 1, 2, 1))


class FIFODecoratorTest(unittest.TestCase, DecoratorTestMixin):
    DECORATOR = staticmethod(cachetools.func.fifo_cache)

    def test_method_typed(self):
        """Type-checked by pyright via the stub __get__ overloads."""

        class Cached:
            @cachetools.func.fifo_cache(maxsize=2)
            def get(self, n: int) -> int:
                return n

            @cachetools.func.fifo_cache
            def get_bare(self, n: int) -> int:
                return n

            @staticmethod
            @cachetools.func.fifo_cache
            def get_static(n: int) -> int:
                return n

        cached = Cached()
        result: int = cached.get(1)
        self.assertEqual(result, 1)
        self.assertEqual(Cached.get(cached, 1), 1)
        self.assertEqual(cached.get.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached.get_bare(1), 1)
        self.assertEqual(cached.get_static(1), 1)
        self.assertEqual(Cached.get_static(1), 1)


class LFUDecoratorTest(unittest.TestCase, DecoratorTestMixin):
    DECORATOR = staticmethod(cachetools.func.lfu_cache)


class LRUDecoratorTest(unittest.TestCase, DecoratorTestMixin):
    DECORATOR = staticmethod(cachetools.func.lru_cache)


class RRDecoratorTest(unittest.TestCase, DecoratorTestMixin):
    DECORATOR = staticmethod(cachetools.func.rr_cache)


class TTLDecoratorTest(unittest.TestCase, DecoratorTestMixin):
    DECORATOR = staticmethod(cachetools.func.ttl_cache)

    def test_ttl_datetime(self):
        from datetime import datetime, timedelta

        cached = self.decorator(maxsize=2, ttl=timedelta(days=1), timer=datetime.now)(
            lambda n: n
        )
        self.assertEqual(cached.cache_parameters(), {"maxsize": 2, "typed": False})
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, 2, 1))
