import threading
import time
import unittest
from typing import Any

from cachetools import LRUCache, cached, cachedmethod

count = 0


@cached(cache=LRUCache(1), condition=threading.Condition(), info=True)
def func():
    global count
    time.sleep(1.0)
    count += 1
    return count


@cached(cache=LRUCache(1), lock=threading.Lock(), info=True)
def locked_func():
    global count
    time.sleep(1.0)
    count += 1
    return 42


class ThreadingTest(unittest.TestCase):
    NTHREADS = 10

    TIMEOUT = 10

    cache: LRUCache[Any, int] = LRUCache(1)

    cond = threading.Condition()

    lock = threading.Lock()

    count = 0

    @cachedmethod(
        cache=lambda self: self.cache, condition=lambda self: self.cond, info=True
    )
    def method(self):
        time.sleep(1.0)
        self.count += 1
        return 42

    @cachedmethod(cache=lambda self: self.cache, lock=lambda self: self.lock, info=True)
    def locked_method(self):
        time.sleep(1.0)
        self.count += 1
        return 42

    def test_cached_stampede(self):
        global count
        count = 0
        threads = [threading.Thread(target=func) for i in range(0, self.NTHREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=self.TIMEOUT)
            self.assertFalse(t.is_alive())

        self.assertEqual(count, 1)

        info = func.cache_info()
        self.assertEqual(info.hits, self.NTHREADS - 1)
        self.assertEqual(info.misses, 1)

    def test_cachedmethod_stampede(self):
        self.cache = LRUCache(1)
        self.count = 0
        threads = [
            threading.Thread(target=self.method) for i in range(0, self.NTHREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=self.TIMEOUT)
            self.assertFalse(t.is_alive())

        self.assertEqual(self.count, 1)

        info = self.method.cache_info()
        self.assertEqual(info.hits, self.NTHREADS - 1)
        self.assertEqual(info.misses, 1)

    def test_cached_locked(self):
        global count
        count = 0
        threads = [
            threading.Thread(target=locked_func) for i in range(0, self.NTHREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=self.TIMEOUT)
            self.assertFalse(t.is_alive())

        # Without condition/stampede prevention, func is called by multiple
        # threads, but all return the same cached value (42).
        self.assertGreaterEqual(count, 1)

        info = locked_func.cache_info()
        self.assertEqual(info.hits + info.misses, self.NTHREADS)
        self.assertGreaterEqual(info.misses, 1)

    def test_cachedmethod_locked(self):
        self.cache = LRUCache(1)
        self.count = 0
        threads = [
            threading.Thread(target=self.locked_method) for i in range(0, self.NTHREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=self.TIMEOUT)
            self.assertFalse(t.is_alive())

        # Multiple threads may compute the value, but setdefault ensures
        # the first cached result wins and all return 42.
        self.assertGreaterEqual(self.count, 1)

        info = self.locked_method.cache_info()
        self.assertEqual(info.hits + info.misses, self.NTHREADS)
        self.assertGreaterEqual(info.misses, 1)
