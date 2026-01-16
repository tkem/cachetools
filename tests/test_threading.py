import threading
import time
import unittest
from os import environ

from cachetools import LRUCache, cached, cachedmethod


@unittest.skipUnless(environ.get("THREADING_TESTS", False), "THREADING_TESTS not set")
class ThreadingTest(unittest.TestCase):

    NTHREADS = 10

    cache = LRUCache(1)

    cond = threading.Condition()

    count = 0

    @cached(cache=LRUCache(1), condition=threading.Condition(), info=True)
    def func(self):
        time.sleep(1.0)
        return 42

    @cachedmethod(cache=lambda self: self.cache, condition=lambda self: self.cond)
    def meth(self):
        time.sleep(1.0)
        self.count += 1
        return 42

    def test_cached_stampede(self):
        threads = [threading.Thread(target=self.func) for i in range(0, self.NTHREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        info = self.func.cache_info()
        self.assertEqual(info.hits, self.NTHREADS - 1)
        self.assertEqual(info.misses, 1)

    def test_cachedmethod_stampede(self):
        threads = [threading.Thread(target=self.meth) for i in range(0, self.NTHREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(self.count, 1)
