import unittest
import operator

from cachetools import LRUCache, cachedmethod


class Cached(object):

    cache = LRUCache(maxsize=2)

    count = 0

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


class MethodTest(unittest.TestCase):

    def test_decorator(self):
        cached = Cached()

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_typed_decorator(self):
        cached = Cached()

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)
        self.assertEqual(cached.get_typed(0), 4)
