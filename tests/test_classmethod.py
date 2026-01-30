import threading
import unittest
import warnings


from cachetools import LRUCache, cachedmethod, keys


class Cached:
    cache = LRUCache(2)
    count = 0
    lock = threading.Lock()
    cond = threading.Condition()

    @classmethod
    @cachedmethod(lambda cls: cls.cache)
    def get(cls, value):
        cls.count += 1
        return cls.count

    @classmethod
    @cachedmethod(lambda cls: cls.cache, key=keys.typedmethodkey)
    def get_typed(cls, value):
        cls.count += 1
        return cls.count

    @classmethod
    @cachedmethod(lambda cls: cls.cache, lock=lambda cls: cls.lock)
    def get_locked(cls, value):
        cls.count += 1
        return cls.count

    @classmethod
    @cachedmethod(lambda cls: cls.cache, condition=lambda cls: cls.cond)
    def get_condition(cls, value):
        cls.count += 1
        return cls.count


class CachedClassMethodTest(unittest.TestCase):
    def test(self):
        Cached.cache = LRUCache(2)
        Cached.count = 0
        cached = Cached()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(cached.get(0), 1)
            self.assertEqual(Cached.get(0), 1)
        self.assertEqual(len(w), 2)
        self.assertIs(w[0].category, DeprecationWarning)
        self.assertIs(w[1].category, DeprecationWarning)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertEqual(cached.get(1), 2)
            self.assertEqual(Cached.get(1), 2)
            self.assertEqual(cached.get(1), 2)
            self.assertEqual(Cached.get(1), 2)
            self.assertEqual(cached.get(1.0), 2)
            self.assertEqual(Cached.get(1.0), 2)
            self.assertEqual(cached.get(1.1), 3)
            self.assertEqual(Cached.get(1.1), 3)
            Cached.cache.clear()
            self.assertEqual(Cached.get(1), 4)

    def test_typed(self):
        Cached.cache = LRUCache(2)
        Cached.count = 0
        cached = Cached()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(cached.get_typed(0), 1)
            self.assertEqual(Cached.get_typed(0), 1)
        self.assertEqual(len(w), 2)
        self.assertIs(w[0].category, DeprecationWarning)
        self.assertIs(w[0].category, DeprecationWarning)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertEqual(cached.get_typed(1), 2)
            self.assertEqual(Cached.get_typed(1), 2)
            self.assertEqual(cached.get_typed(1.0), 3)
            self.assertEqual(Cached.get_typed(1.0), 3)
            self.assertEqual(cached.get_typed(0.0), 4)
            self.assertEqual(Cached.get_typed(0.0), 4)
            self.assertEqual(cached.get_typed(0), 5)
            self.assertEqual(Cached.get_typed(0), 5)

    def test_locked(self):
        Cached.cache = LRUCache(2)
        Cached.count = 0
        cached = Cached()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(cached.get_locked(0), 1)
            self.assertEqual(Cached.get_locked(0), 1)
        self.assertEqual(len(w), 2)
        self.assertIs(w[0].category, DeprecationWarning)
        self.assertIs(w[0].category, DeprecationWarning)

    def test_condition(self):
        Cached.cache = LRUCache(2)
        Cached.count = 0
        cached = Cached()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(cached.get_condition(0), 1)
            self.assertEqual(Cached.get_condition(0), 1)
        self.assertEqual(len(w), 2)
        self.assertIs(w[0].category, DeprecationWarning)
        self.assertIs(w[0].category, DeprecationWarning)

    def test_clear(self):
        Cached.cache = LRUCache(2)
        Cached.count = 0
        cached = Cached()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertEqual(cached.get(0), 1)
            self.assertEqual(len(Cached.cache), 1)
            Cached.get.cache_clear(cached)
            self.assertEqual(len(Cached.cache), 0)

    def test_clear_locked(self):
        Cached.cache = LRUCache(2)
        Cached.count = 0
        cached = Cached()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertEqual(cached.get_locked(0), 1)
            self.assertEqual(len(Cached.cache), 1)
            Cached.get_locked.cache_clear(cached)
            self.assertEqual(len(Cached.cache), 0)

    def test_clear_condition(self):
        Cached.cache = LRUCache(2)
        Cached.count = 0
        cached = Cached()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertEqual(cached.get_condition(0), 1)
            self.assertEqual(len(Cached.cache), 1)
            Cached.get_condition.cache_clear(cached)
            self.assertEqual(len(Cached.cache), 0)
