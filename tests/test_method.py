import operator
import unittest

from cachetools import LRUCache, cachedmethod


class Cached(object):

    count = 0

    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

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

    def test_dict(self):
        cached = Cached({})
        self.assertEqual(cached.cache, cached.get.cache(cached))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_typed_dict(self):
        cached = Cached(LRUCache(maxsize=2))
        self.assertEqual(cached.cache, cached.get_typed.cache(cached))

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)
        self.assertEqual(cached.get_typed(0), 4)

    def test_lru(self):
        cached = Cached(LRUCache(maxsize=2))
        self.assertEqual(cached.cache, cached.get.cache(cached))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_typed_lru(self):
        cached = Cached(LRUCache(maxsize=2))
        self.assertEqual(cached.cache, cached.get_typed.cache(cached))

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)
        self.assertEqual(cached.get_typed(0), 4)

    def test_nospace(self):
        cached = Cached(LRUCache(maxsize=0))
        self.assertEqual(cached.cache, cached.get.cache(cached))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(1.0), 4)

    def test_nocache(self):
        cached = Cached(None)
        self.assertEqual(None, cached.get.cache(cached))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(1.0), 4)

    def test_weakref(self):
        import weakref
        import fractions

        # in Python 3.4, `int` does not support weak references even
        # when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):
                return Int(fractions.Fraction.__add__(self, other))

        cached = Cached(weakref.WeakValueDictionary(), Int(0))
        self.assertEqual(cached.cache, cached.get.cache(cached))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(0), 1)

        ref = cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)

        ref = cached.get_typed(1)
        self.assertEqual(ref, 3)
        self.assertEqual(cached.get_typed(1), 3)
        self.assertEqual(cached.get_typed(1.0), 4)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 5)
