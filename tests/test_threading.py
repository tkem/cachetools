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


class ThreadingTest(unittest.TestCase):
    NTHREADS = 10

    TIMEOUT = 10

    cache: LRUCache[Any, int] = LRUCache(1)

    cond = threading.Condition()

    count = 0

    @cachedmethod(
        cache=lambda self: self.cache, condition=lambda self: self.cond, info=True
    )
    def meth(self):
        time.sleep(1.0)
        self.count += 1
        return 42

    def test_cached_stampede(self):
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
        threads = [threading.Thread(target=self.meth) for i in range(0, self.NTHREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=self.TIMEOUT)
            self.assertFalse(t.is_alive())

        self.assertEqual(self.count, 1)

        info = self.meth.cache_info()
        self.assertEqual(info.hits, self.NTHREADS - 1)
        self.assertEqual(info.misses, 1)
