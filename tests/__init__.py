import math
from collections.abc import Container, Iterable
from typing import Any, Generic, Protocol, TypeVar

from cachetools import Cache, TLRUCache, TTLCache

C = TypeVar("C", bound=Cache)
S = TypeVar("S", bound=Cache)
T = TypeVar("T", bound=TLRUCache[Any, Any, Any] | TTLCache[Any, Any, Any])


class CountedLock:
    def __init__(self):
        self.count = 0

    def __enter__(self):
        self.count += 1

    def __exit__(self, *exc):
        pass


class CountedCondition(CountedLock):
    def __init__(self):
        super().__init__()
        self.wait_count = 0
        self.notify_count = 0

    def wait(self, timeout=None):
        self.wait_count += 1
        return True

    def wait_for(self, predicate, timeout=None):
        res = predicate()
        self.wait_count += 1
        return res

    def notify(self, n=1):
        self.notify_count += 1

    def notify_all(self):
        self.notify_count += 1


class SimplifiedTestCaseProtocol(Protocol):
    def assertEqual(self, first: Any, second: Any, msg: Any = None) -> None: ...
    def assertNotEqual(self, first: Any, second: Any, msg: Any = None) -> None: ...
    def assertTrue(self, expr: Any, msg: Any = None) -> None: ...
    def assertFalse(self, expr: Any, msg: Any = None) -> None: ...
    def assertIs(self, expr1: object, expr2: object, msg: Any = None) -> None: ...
    def assertIsNot(self, expr1: object, expr2: object, msg: Any = None) -> None: ...
    def assertIsNone(self, obj: object, msg: Any = None) -> None: ...

    def assertIn(
        self, member: Any, container: Iterable[Any] | Container[Any], msg: Any = None
    ) -> None: ...

    def assertNotIn(
        self, member: Any, container: Iterable[Any] | Container[Any], msg: Any = None
    ) -> None: ...

    def assertRaises(self, expected_exception: type[BaseException]) -> Any: ...

    def assertRaisesRegex(
        self, expected_exception: type[BaseException], expected_regex: str
    ) -> Any: ...


class CacheTestMixin(SimplifiedTestCaseProtocol, Generic[C]):
    Cache: type[C]

    def cache(self, maxsize: float, **kwargs) -> C:
        return self.typed_cache(self.Cache, maxsize, **kwargs)

    def typed_cache(self, cls: type[S], maxsize: float, **kwargs) -> S:
        return cls(maxsize, **kwargs)

    def test_defaults(self):
        cache = self.cache(maxsize=1)
        self.assertEqual(0, len(cache))
        self.assertEqual(1, cache.maxsize)
        self.assertEqual(0, cache.currsize)
        self.assertEqual(1, cache.getsizeof(None))
        self.assertEqual(1, cache.getsizeof(""))
        self.assertEqual(1, cache.getsizeof(0))
        self.assertTrue(repr(cache).startswith(cache.__class__.__name__))

    def test_maxsize_negative(self):
        with self.assertRaises(ValueError):
            self.cache(maxsize=-1)

        with self.assertRaises(ValueError):
            self.cache(maxsize=-math.inf)

    def test_maxsize_zero(self):
        cache = self.cache(maxsize=0)

        self.assertEqual(0, cache.maxsize)
        with self.assertRaises(ValueError):
            cache[1] = 1
        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)

    def test_maxsize_infinite(self):
        cache = self.cache(maxsize=math.inf)

        cache.update((i, i) for i in range(100))
        self.assertEqual(100, len(cache))
        self.assertEqual(100, cache.currsize)

    def test_insert(self):
        cache = self.cache(maxsize=2)

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache[3] = 3
        self.assertEqual(2, len(cache))
        self.assertEqual(3, cache[3])
        self.assertTrue(1 in cache or 2 in cache)

        cache[4] = 4
        self.assertEqual(2, len(cache))
        self.assertEqual(4, cache[4])
        self.assertTrue(1 in cache or 2 in cache or 3 in cache)

    def test_update(self):
        cache = self.cache(maxsize=2)

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache.update({1: "a", 2: "b"})
        self.assertEqual(2, len(cache))
        self.assertEqual("a", cache[1])
        self.assertEqual("b", cache[2])

    def test_delete(self):
        cache = self.cache(maxsize=2)

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        del cache[2]
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache[1])
        self.assertNotIn(2, cache)

        del cache[1]
        self.assertEqual(0, len(cache))
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)

        with self.assertRaises(KeyError):
            del cache[1]
        self.assertEqual(0, len(cache))
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)

    def test_pop(self):
        cache = self.cache(maxsize=2)

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, cache.pop(2))
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache.pop(1))
        self.assertEqual(0, len(cache))

        with self.assertRaises(KeyError):
            cache.pop(2)
        with self.assertRaises(KeyError):
            cache.pop(1)
        with self.assertRaises(KeyError):
            cache.pop(0)

        self.assertEqual(None, cache.pop(2, None))
        self.assertEqual(None, cache.pop(1, None))
        self.assertEqual(None, cache.pop(0, None))

    def test_popitem(self):
        cache = self.cache(maxsize=2)

        cache.update({1: 1, 2: 2})

        key, _ = cache.popitem()
        self.assertIn(key, {1, 2})
        self.assertEqual(1, len(cache))
        key, _ = cache.popitem()
        self.assertIn(key, {1, 2})
        self.assertEqual(0, len(cache))

        with self.assertRaises(KeyError):
            cache.popitem()

    def test_popitem_exception_context(self):
        # since Python 3.7, MutableMapping.popitem() suppresses
        # exception context as implementation detail
        with self.assertRaises(KeyError) as cm:
            self.cache(maxsize=2).popitem()
        e = cm.exception
        self.assertIsNone(e.__cause__)
        self.assertTrue(e.__suppress_context__)

    def test_missing(self):
        class DefaultCache(self.Cache):
            def __missing__(self, key):
                self[key] = key
                return key

        cache = self.typed_cache(DefaultCache, maxsize=2)

        self.assertEqual(0, cache.currsize)
        self.assertEqual(2, cache.maxsize)
        self.assertEqual(0, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(2, len(cache))
        self.assertTrue(1 in cache and 2 in cache)

        self.assertEqual(3, cache[3])
        self.assertEqual(2, len(cache))
        self.assertTrue(3 in cache)
        self.assertTrue(1 in cache or 2 in cache)
        self.assertTrue(1 not in cache or 2 not in cache)

        self.assertEqual(4, cache[4])
        self.assertEqual(2, len(cache))
        self.assertTrue(4 in cache)
        self.assertTrue(1 in cache or 2 in cache or 3 in cache)

        # verify __missing__() is *not* called for any operations
        # besides __getitem__()

        self.assertEqual(4, cache.get(4))
        self.assertEqual(None, cache.get(5))
        self.assertEqual(5 * 5, cache.get(5, 5 * 5))
        self.assertEqual(2, len(cache))

        self.assertEqual(4, cache.pop(4))
        with self.assertRaises(KeyError):
            cache.pop(5)
        self.assertEqual(None, cache.pop(5, None))
        self.assertEqual(5 * 5, cache.pop(5, 5 * 5))
        self.assertEqual(1, len(cache))

        cache.clear()
        cache[1] = 1 + 1
        self.assertEqual(1 + 1, cache.setdefault(1))
        self.assertEqual(1 + 1, cache.setdefault(1, 1))
        self.assertEqual(1 + 1, cache[1])
        self.assertEqual(2 + 2, cache.setdefault(2, 2 + 2))
        self.assertEqual(2 + 2, cache.setdefault(2, None))
        self.assertEqual(2 + 2, cache.setdefault(2))
        self.assertEqual(2 + 2, cache[2])
        self.assertEqual(2, len(cache))
        self.assertTrue(1 in cache and 2 in cache)
        self.assertEqual(None, cache.setdefault(3))
        self.assertEqual(2, len(cache))
        self.assertTrue(3 in cache)
        self.assertTrue(1 in cache or 2 in cache)
        self.assertTrue(1 not in cache or 2 not in cache)

    def test_missing_getsizeof(self):
        class DefaultCache(self.Cache):
            def __missing__(self, key):
                try:
                    self[key] = key
                except ValueError:
                    pass  # not stored
                return key

        cache = self.typed_cache(DefaultCache, maxsize=2, getsizeof=lambda x: x)

        self.assertEqual(0, cache.currsize)
        self.assertEqual(2, cache.maxsize)

        self.assertEqual(1, cache[1])
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache.currsize)
        self.assertIn(1, cache)

        self.assertEqual(2, cache[2])
        self.assertEqual(1, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertIn(2, cache)

        self.assertEqual(3, cache[3])  # not stored
        self.assertEqual(1, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertEqual(1, cache[1])
        self.assertEqual(1, len(cache))
        self.assertEqual(1, cache.currsize)
        self.assertEqual((1, 1), cache.popitem())

    def _test_getsizeof(self, cache):
        self.assertEqual(0, cache.currsize)
        self.assertEqual(3, cache.maxsize)
        self.assertEqual(1, cache.getsizeof(1))
        self.assertEqual(2, cache.getsizeof(2))
        self.assertEqual(3, cache.getsizeof(3))

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, len(cache))
        self.assertEqual(3, cache.currsize)
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache[1] = 2
        self.assertEqual(1, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertEqual(2, cache[1])
        self.assertNotIn(2, cache)

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, len(cache))
        self.assertEqual(3, cache.currsize)
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache[3] = 3
        self.assertEqual(1, len(cache))
        self.assertEqual(3, cache.currsize)
        self.assertEqual(3, cache[3])
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)

        with self.assertRaises(ValueError):
            cache[3] = 4
        self.assertEqual(1, len(cache))
        self.assertEqual(3, cache.currsize)
        self.assertEqual(3, cache[3])

        with self.assertRaises(ValueError):
            cache[4] = 4
        self.assertEqual(1, len(cache))
        self.assertEqual(3, cache.currsize)
        self.assertEqual(3, cache[3])

    def test_getsizeof_param(self):
        self._test_getsizeof(self.cache(maxsize=3, getsizeof=lambda x: x))

    def test_getsizeof_replace_grow(self):
        cache = self.cache(maxsize=10, getsizeof=lambda x: x)

        cache[3] = 3
        cache[4] = 4
        self.assertEqual(2, len(cache))
        self.assertEqual(7, cache.currsize)

        # growing an existing entry must only reserve the additional size
        cache[4] = 7
        self.assertEqual(2, len(cache))
        self.assertEqual(10, cache.currsize)
        self.assertEqual(3, cache[3])
        self.assertEqual(7, cache[4])

        # growing an existing entry may have to evict other entries
        cache[4] = 9
        self.assertEqual(1, len(cache))
        self.assertEqual(9, cache.currsize)
        self.assertNotIn(3, cache)
        self.assertEqual(9, cache[4])

    def test_getsizeof_replace_same_size(self):
        cache = self.cache(maxsize=10, getsizeof=lambda x: x)

        cache[3] = 3
        cache[4] = 4
        self.assertEqual(7, cache.currsize)

        cache[4] = 4
        self.assertEqual(2, len(cache))
        self.assertEqual(7, cache.currsize)
        self.assertEqual(3, cache[3])
        self.assertEqual(4, cache[4])

    def test_getsizeof_replace_shrink(self):
        cache = self.cache(maxsize=10, getsizeof=lambda x: x)

        cache[3] = 3
        cache[4] = 4
        self.assertEqual(7, cache.currsize)

        cache[4] = 1
        self.assertEqual(2, len(cache))
        self.assertEqual(4, cache.currsize)
        self.assertEqual(3, cache[3])
        self.assertEqual(1, cache[4])

    def test_getsizeof_negative(self):
        cache = self.cache(maxsize=3, getsizeof=lambda x: -1)

        with self.assertRaises(ValueError):
            cache[1] = 1

        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)

    def test_getsizeof_subclass(self):
        class Cache(self.Cache):
            @staticmethod
            def getsizeof(value):
                return value

        self._test_getsizeof(self.typed_cache(Cache, maxsize=3))

    def test_clear(self):
        cache = self.cache(maxsize=2)
        cache.update({1: 1, 2: 2})

        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache.currsize)

        cache.clear()

        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)

        # verify cache can be reused after clear
        cache[3] = 3
        cache[4] = 4
        self.assertEqual(2, len(cache))
        self.assertEqual(3, cache[3])
        self.assertEqual(4, cache[4])

        # verify eviction still works after clear
        cache[5] = 5
        self.assertEqual(2, len(cache))
        self.assertIn(5, cache)

    def test_clear_empty(self):
        cache = self.cache(maxsize=2)
        cache.clear()  # should not raise
        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)

    def test_clear_getsizeof(self):
        cache = self.cache(maxsize=10, getsizeof=lambda x: x)
        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(3, len(cache))
        self.assertEqual(6, cache.currsize)

        cache.clear()

        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)

        # verify cache can be reused with getsizeof after clear
        cache[4] = 4
        self.assertEqual(1, len(cache))
        self.assertEqual(4, cache.currsize)

    def test_iter_update(self):
        cache = self.cache(maxsize=3)
        cache.update({1: 1, 2: 2, 3: 3})

        # updating items while iterating visits each key once, in order
        keys = []
        for key in cache:
            keys.append(key)
            cache[key] = key * 10
        self.assertEqual([1, 2, 3], keys)
        self.assertEqual([10, 20, 30], list(cache.values()))

    def test_pickle(self):
        import pickle

        source = self.cache(maxsize=2)
        source.update({1: 1, 2: 2})

        cache = pickle.loads(pickle.dumps(source))
        self.assertIsNot(source, cache)
        self.assertEqual(source, cache)
        self.assertEqual(source.maxsize, cache.maxsize)
        self.assertEqual(source.currsize, cache.currsize)

        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache[3] = 3
        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertEqual(3, cache[3])
        self.assertTrue(1 in cache or 2 in cache)

        self.assertEqual(2, len(source))
        self.assertEqual(2, source.currsize)
        self.assertIn(1, source)
        self.assertIn(2, source)
        self.assertNotIn(3, source)

        self.assertEqual(cache, pickle.loads(pickle.dumps(cache)))

    def test_pickle_maxsize(self):
        import pickle
        import sys

        # test empty cache, single element, large cache (recursion limit)
        for n in [0, 1, sys.getrecursionlimit() * 2]:
            source = self.cache(maxsize=n)
            source.update((i, i) for i in range(n))
            cache = pickle.loads(pickle.dumps(source))
            self.assertEqual(n, len(cache))
            self.assertEqual(source, cache)

    def test_copy(self):
        import copy

        source = self.cache(maxsize=2)
        source.update({1: 1, 2: 2})

        cache = copy.copy(source)
        self.assertIsNot(source, cache)
        self.assertEqual(source, cache)
        self.assertEqual(source.maxsize, cache.maxsize)
        self.assertEqual(source.currsize, cache.currsize)

        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache[3] = 3
        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertEqual(3, cache[3])
        self.assertTrue(1 in cache or 2 in cache)

        self.assertEqual(2, len(source))
        self.assertEqual(2, source.currsize)
        self.assertIn(1, source)
        self.assertIn(2, source)
        self.assertNotIn(3, source)

        self.assertEqual(cache, copy.copy(cache))

    def test_copy_maxsize(self):
        import copy
        import sys

        # test empty cache, single element, large cache (recursion limit)
        for n in [0, 1, sys.getrecursionlimit() * 2]:
            source = self.cache(maxsize=n)
            source.update((i, i) for i in range(n))
            cache = copy.copy(source)
            self.assertEqual(n, len(cache))
            self.assertEqual(source, cache)

    def test_copy_attributes(self):
        import copy
        import threading

        class Cache(self.Cache):
            def __init__(self, maxsize, **kwargs):
                super().__init__(maxsize, **kwargs)
                self.lock = threading.Lock()  # cannot be deep-copied
                self.stats = {"hits": 0}

        source = self.typed_cache(Cache, maxsize=2)
        source.update({1: [1], 2: [2]})

        cache = copy.copy(source)
        self.assertIs(type(source), type(cache))
        # a shallow copy shares attributes and values with its source
        self.assertIs(source.lock, cache.lock)
        self.assertIs(source.stats, cache.stats)
        self.assertIs(source[1], cache[1])
        self.assertIs(source[2], cache[2])

        # but none of the cache's own state
        cache[3] = [3]
        del cache[next(iter(cache))]
        self.assertEqual(1, len(cache))
        self.assertEqual(2, len(source))
        self.assertEqual(2, source.currsize)
        self.assertIn(1, source)
        self.assertIn(2, source)
        self.assertNotIn(3, source)

    def test_copy_getsizeof(self):
        import copy

        class GetSizeOf:
            def __call__(self, value):
                return value

        source = self.cache(maxsize=3, getsizeof=GetSizeOf())
        source.update({1: 1, 2: 2})

        cache = copy.copy(source)
        self.assertIs(source.getsizeof, cache.getsizeof)
        self.assertEqual(3, cache.currsize)

        # item sizes are kept separately for source and copy
        cache[2] = 1
        self.assertEqual(2, cache.currsize)
        self.assertEqual(3, source.currsize)
        del source[2]
        self.assertEqual(1, source.currsize)
        self.assertEqual(2, cache.currsize)
        del cache[2]
        self.assertEqual(1, cache.currsize)

    def test_deepcopy(self):
        import copy

        source = self.cache(maxsize=2)
        source.update({1: 1, 2: 2})

        cache = copy.deepcopy(source)
        self.assertIsNot(source, cache)
        self.assertEqual(source, cache)
        self.assertEqual(source.maxsize, cache.maxsize)
        self.assertEqual(source.currsize, cache.currsize)

        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache[3] = 3
        self.assertEqual(2, len(cache))
        self.assertEqual(2, cache.currsize)
        self.assertEqual(3, cache[3])
        self.assertTrue(1 in cache or 2 in cache)

        self.assertEqual(2, len(source))
        self.assertEqual(2, source.currsize)
        self.assertIn(1, source)
        self.assertIn(2, source)
        self.assertNotIn(3, source)

        self.assertEqual(cache, copy.deepcopy(cache))

    def test_deepcopy_maxsize(self):
        import copy
        import sys

        # test empty cache, single element, large cache (recursion limit)
        for n in [0, 1, sys.getrecursionlimit() * 2]:
            source = self.cache(maxsize=n)
            source.update((i, i) for i in range(n))
            cache = copy.deepcopy(source)
            self.assertEqual(n, len(cache))
            self.assertEqual(source, cache)


class TimedCacheTestMixin(CacheTestMixin[T]):
    class Timer:
        def __init__(self, auto=False):
            self.auto = auto
            self.time = 0

        def __call__(self):
            if self.auto:
                self.time += 1
            return self.time

        def tick(self):
            self.time += 1

    def test_timed(self):
        cache = self.cache(maxsize=2, ttl=2)
        self.assertEqual(0, cache.timer())

        cache[1] = 1
        self.assertEqual(1, cache[1])
        self.assertEqual(1, len(cache))
        self.assertEqual({1}, set(cache))

        cache.timer.tick()
        self.assertEqual(1, cache[1])
        self.assertEqual(1, len(cache))
        self.assertEqual({1}, set(cache))

        cache[2] = 2
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(2, len(cache))
        self.assertEqual({1, 2}, set(cache))

        cache.timer.tick()
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(1, len(cache))
        self.assertEqual({2}, set(cache))

        cache[3] = 3
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])
        self.assertEqual(2, len(cache))
        self.assertEqual({2, 3}, set(cache))

        cache.timer.tick()
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])
        self.assertEqual(1, len(cache))
        self.assertEqual({3}, set(cache))

        cache.timer.tick()
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

        with self.assertRaises(KeyError):
            del cache[1]
        with self.assertRaises(KeyError):
            cache.pop(2)
        with self.assertRaises(KeyError):
            del cache[3]

        self.assertEqual(0, len(cache))
        self.assertEqual(set(), set(cache))

    def test_timed_timer(self):
        cache = self.cache(maxsize=2, ttl=2)
        self.assertEqual(cache.timer.time, 0)
        self.assertFalse(cache.timer.auto)

        cache[1] = 1
        cache.timer.tick()
        self.assertEqual(cache.timer.time, 1)
        self.assertEqual(1, cache[1])

        cache.timer.tick()
        self.assertEqual(cache.timer.time, 2)
        self.assertNotIn(1, cache)

    def test_timed_lru(self):
        cache = self.cache(maxsize=2, ttl=1)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(len(cache), 2)
        self.assertNotIn(1, cache)
        self.assertEqual(cache[2], 2)
        self.assertEqual(cache[3], 3)

        cache[2]
        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertNotIn(1, cache)
        self.assertEqual(cache[2], 2)
        self.assertNotIn(3, cache)
        self.assertEqual(cache[4], 4)

        cache[5] = 5
        self.assertEqual(len(cache), 2)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)
        self.assertEqual(cache[4], 4)
        self.assertEqual(cache[5], 5)

    def test_timed_expire(self):
        cache = self.cache(maxsize=3, ttl=3)
        with cache.timer as time:
            self.assertEqual(time, cache.timer())

        cache[1] = 1
        cache.timer.tick()
        cache[2] = 2
        cache.timer.tick()
        cache[3] = 3
        self.assertEqual(2, cache.timer())

        self.assertEqual({1, 2, 3}, set(cache))
        self.assertEqual(3, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        items = cache.expire()
        self.assertEqual(set(), set(items))
        self.assertEqual({1, 2, 3}, set(cache))
        self.assertEqual(3, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        items = cache.expire(3)
        self.assertEqual({(1, 1)}, set(items))
        self.assertEqual({2, 3}, set(cache))
        self.assertEqual(2, len(cache))
        self.assertNotIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertEqual(3, cache[3])

        items = cache.expire(4)
        self.assertEqual({(2, 2)}, set(items))
        self.assertEqual({3}, set(cache))
        self.assertEqual(1, len(cache))
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertEqual(3, cache[3])

        items = cache.expire(5)
        self.assertEqual({(3, 3)}, set(items))
        self.assertEqual(set(), set(cache))
        self.assertEqual(0, len(cache))
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)
        self.assertNotIn(3, cache)

    def test_timed_expire_repr_currsize(self):
        def cache():
            cache = self.cache(maxsize=2, ttl=2)
            cache[1] = 1
            cache.timer.tick()
            cache[2] = 2
            cache.timer.tick()  # 1 has expired, but is still stored
            return cache

        # repr() and currsize remove expired items themselves
        name = self.Cache.__name__
        self.assertEqual(f"{name}({{2: 2}}, maxsize=2, currsize=1)", repr(cache()))
        self.assertEqual(1, cache().currsize)

    def test_timed_iter_atomic(self):
        base: Any = self.Cache  # pyright accepts no union-bound type as base

        class TickingCache(base):
            def __getitem__(self, key):
                self.timer.tick()
                return super().__getitem__(key)

        # time does not advance while an iterator is suspended
        for values in (
            lambda cache: [cache[key] for key in cache],
            lambda cache: [value for _, value in cache.items()],
            lambda cache: list(cache.values()),
        ):
            cache = self.typed_cache(TickingCache, maxsize=2, ttl=1)
            cache.update({1: 1, 2: 2})
            self.assertEqual([1], values(cache))
            self.assertEqual(0, len(cache))

    def test_timed_iter_expired(self):
        cache = self.cache(maxsize=2, ttl=2)
        cache[1] = 1
        cache.timer.tick()
        cache[2] = 2
        cache.timer.tick()
        # a bare for loop skips expired items without removing them
        self.assertEqual([2], [key for key in cache])
        self.assertEqual({(1, 1)}, set(cache.expire()))
        self.assertEqual([2], [key for key in cache])

    def test_timed_iter_modify(self):
        cache = self.cache(maxsize=6, ttl=2)
        cache.update({1: 1, 2: 2, 3: 3})

        # items inserted while iterating are not visited
        keys = []
        for key in cache:
            keys.append(key)
            cache[key + 10] = key
        self.assertEqual([1, 2, 3], keys)
        self.assertEqual([1, 2, 3, 11, 12, 13], list(cache))

        # items removed while iterating are skipped
        keys = []
        for key in cache:
            keys.append(key)
            cache.clear()
        self.assertEqual([1], keys)
        self.assertEqual([], list(cache))

    def test_timed_atomic(self):
        cache = self.cache(maxsize=1, ttl=2, timer=self.Timer(auto=True))
        cache[1] = 1
        self.assertEqual(1, cache[1])
        cache[1] = 1
        self.assertEqual(1, cache.get(1))
        cache[1] = 1
        self.assertEqual(1, cache.pop(1))
        cache[1] = 1
        self.assertEqual(1, cache.setdefault(1))  # implicit default=None
        cache[1] = 1
        cache.clear()
        self.assertEqual(0, len(cache))

    def test_timed_tuple_key(self):
        cache = self.cache(maxsize=1, ttl=1)

        cache[(1, 2, 3)] = 42
        self.assertEqual(42, cache[(1, 2, 3)])
        cache.timer.tick()
        with self.assertRaises(KeyError):
            cache[(1, 2, 3)]
        self.assertNotIn((1, 2, 3), cache)

    def test_timed_datetime(self):
        from datetime import datetime, timedelta

        cache = self.cache(maxsize=1, ttl=timedelta(days=1), timer=datetime.now)

        cache[1] = 1
        self.assertEqual(1, len(cache))
        items = cache.expire(datetime.now())
        self.assertEqual([], list(items))
        self.assertEqual(1, len(cache))
        items = cache.expire(datetime.now() + timedelta(days=1))
        self.assertEqual([(1, 1)], list(items))
        self.assertEqual(0, len(cache))

    def test_timed_datetime_overflow(self):
        from datetime import datetime, timedelta

        cache = self.cache(maxsize=1, ttl=timedelta(days=1), timer=lambda: datetime.max)

        with self.assertRaises(OverflowError):
            cache["overflow"] = 1

        self.assertNotIn("overflow", cache)
        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)
        self.assertEqual([], list(cache))
        self.assertEqual([], cache.expire())

    def test_timed_clear(self):
        cache = self.cache(maxsize=2, ttl=2)

        cache[1] = 1
        cache[2] = 2
        cache.clear()

        self.assertEqual(0, len(cache))
        self.assertEqual(0, cache.currsize)

        # verify LRU eviction order is reset after clear
        cache[3] = 3
        cache[4] = 4
        cache[3]  # access 3 to make it most recently used
        cache[5] = 5  # should evict 4 (least recently used)

        self.assertEqual(2, len(cache))
        self.assertIn(3, cache)
        self.assertIn(5, cache)
        self.assertNotIn(4, cache)

        # verify expiry still works after clear
        cache[42] = 42
        cache.timer.tick()
        cache.timer.tick()
        cache.timer.tick()  # past TTL
        self.assertNotIn(42, cache)

    def test_timed_copy(self):
        import copy

        source = self.cache(maxsize=3, ttl=2)
        source[1] = 1
        source[2] = 2
        source.timer.tick()
        source[3] = 3
        self.assertEqual(1, source[1])  # least recently used is now 2

        cache = copy.copy(source)
        self.assertEqual([1, 2, 3], list(cache))

        # the copy evicts as its source would, on its own
        cache[4] = 4
        self.assertEqual([1, 3, 4], list(cache))
        self.assertEqual([1, 2, 3], list(source))

        # the timer is shared, but not the caches' use of it
        self.assertIsNot(source.timer, cache.timer)
        with source.timer:
            cache.timer.tick()
            self.assertEqual(1, source.timer())
            self.assertEqual(2, cache.timer())
        self.assertEqual(2, source.timer())

        # items expire in the copy as in its source
        self.assertEqual([3, 4], list(cache))
        self.assertEqual([3], list(source))

    def test_timed_deepcopy_timer(self):
        import copy

        class DeepCopyTimer(self.Timer):
            def __deepcopy__(self, memo):
                return copy.copy(self)

        source = self.cache(maxsize=2, ttl=1, timer=DeepCopyTimer())
        source[1] = 1

        # a timer may define __deepcopy__ itself
        cache = copy.deepcopy(source)
        self.assertEqual([1], list(cache))

        # the copy has a timer of its own
        cache.timer.tick()
        self.assertEqual([], list(cache))
        self.assertEqual([1], list(source))
