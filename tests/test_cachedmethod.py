import unittest
import operator

from cachetools import LRUCache, cachedmethod


class Cached(object):

    count = 0

    def __init__(self, cache):
        self.cache = cache

    @cachedmethod(operator.attrgetter('cache'))
    def get(self, value):
        count = self.count
        self.count += 1
        return count

    @cachedmethod(operator.attrgetter('cache'), typed=True)
    def get_typed(self, value):
        count = self.count
        self.count += 1
        return count


class CachedMethodTest(unittest.TestCase):

    def test_decorator(self):
        cached = Cached(LRUCache(maxsize=2))
        self.assertEqual(cached.cache, cached.get.cache(cached))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_typed_decorator(self):
        cached = Cached(LRUCache(maxsize=2))
        self.assertEqual(cached.cache, cached.get_typed.cache(cached))

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)
        self.assertEqual(cached.get_typed(0), 4)

    def test_decorator_nocache(self):
        cached = Cached(None)
        self.assertEqual(None, cached.get.cache(cached))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(1.0), 4)
