import unittest

import cachetools

from . import CacheTestMixin


class CacheTest(unittest.TestCase, CacheTestMixin):
    Cache = cachetools.Cache

    def test_setdefault_typed(self):
        cache = cachetools.Cache[str, int](2)
        value: int = cache.setdefault("first", 1)
        self.assertEqual(value, 1)
        value = cache.setdefault(key="first", default=2)
        self.assertEqual(value, 1)
        value = cache.setdefault(key="second", default=2)
        self.assertEqual(value, 2)

    def test_setdefault_optional_typed(self):
        cache = cachetools.Cache[str, int | None](3)
        value: int | None = cache.setdefault("first")
        self.assertIsNone(value)
        value = cache.setdefault(key="second", default=None)
        self.assertIsNone(value)
        value = cache.setdefault(key="third", default=3)
        self.assertEqual(value, 3)
        value = cache.setdefault("third")
        self.assertEqual(value, 3)

    def test_setdefault_none_incompatible_type(self):
        cache = cachetools.Cache[str, int](2)
        # Omitting a default or passing None must be rejected statically when
        # the cache's value type does not include None.
        value = cache.setdefault("first")  # pyright: ignore[reportCallIssue]
        self.assertIsNone(value)
        value = cache.setdefault("second", None)  # pyright: ignore[reportArgumentType]
        self.assertIsNone(value)
