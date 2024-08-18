import unittest
import warnings

from cachetools import MRUCache

from . import CacheTestMixin


class MRUCacheTest(unittest.TestCase, CacheTestMixin):
    # TODO: method to create cache that can be overridden
    Cache = MRUCache

    def test_evict__writes_only(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cache = MRUCache(maxsize=2)
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3  # Evicts 1 because nothing's been used yet

        assert len(cache) == 2
        assert 1 not in cache, "Wrong key was evicted. Should have been '1'."
        assert 2 in cache
        assert 3 in cache

    def test_evict__with_access(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cache = MRUCache(maxsize=2)
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)

        cache[1] = 1
        cache[2] = 2
        cache[1]
        cache[2]
        cache[3] = 3  # Evicts 2
        assert 2 not in cache, "Wrong key was evicted. Should have been '2'."
        assert 1 in cache
        assert 3 in cache

    def test_evict__with_delete(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cache = MRUCache(maxsize=2)
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)

        cache[1] = 1
        cache[2] = 2
        del cache[2]
        cache[3] = 3  # Doesn't evict anything because we just deleted 2

        assert 2 not in cache
        assert 1 in cache

        cache[4] = 4  # Should evict 1 as we just accessed it with __contains__
        assert 1 not in cache
        assert 3 in cache
        assert 4 in cache
