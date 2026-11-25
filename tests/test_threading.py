import unittest
from threading import Barrier, Condition, Event, Lock, Thread

from cachetools import LRUCache, cached, cachedmethod


class WaitCondition(Condition):
    def __init__(self, lock=None):
        super().__init__(lock)
        self.waiting = Event()

    def wait(self, timeout=None):
        self.waiting.set()
        return super().wait(timeout)


class ThreadingTest(unittest.TestCase):
    NTHREADS = 10

    TIMEOUT = 10

    def test_cached_lock(self):
        for info in (False, True):
            with self.subTest(info=info):
                barrier = Barrier(self.NTHREADS, timeout=self.TIMEOUT)
                cache = LRUCache(1)

                @cached(cache, lock=Lock(), info=info)
                def func(barrier=barrier):
                    result = object()
                    barrier.wait()
                    return result

                self.run_lock_test(func, cache, info)

    def test_cachedmethod_lock(self):
        for info in (False, True):
            with self.subTest(info=info):
                barrier = Barrier(self.NTHREADS, timeout=self.TIMEOUT)
                cache = LRUCache(1)
                lock = Lock()

                class Cached:
                    @cachedmethod(lambda _: cache, lock=lambda _: lock, info=info)
                    def method(self, barrier=barrier):
                        result = object()
                        barrier.wait()
                        return result

                self.run_lock_test(Cached().method, cache, info)

    def test_cached_cond(self):
        for info in (False, True):
            with self.subTest(info=info):
                cache = LRUCache(1)
                cond = WaitCondition()
                started = Event()
                release = Event()
                calls = []

                @cached(cache, condition=cond, info=info)
                def func(calls=calls, started=started, release=release):
                    calls.append(None)
                    started.set()
                    release.wait(self.TIMEOUT)
                    return object()

                self.run_cond_wait_test(func, cond, started, release, calls)

    def test_cachedmethod_cond(self):
        for info in (False, True):
            with self.subTest(info=info):
                cache = LRUCache(1)
                cond = WaitCondition()
                started = Event()
                release = Event()
                calls = []

                class Cached:
                    @cachedmethod(lambda _: cache, condition=lambda _: cond, info=info)
                    def method(
                        self,
                        calls=calls,
                        started=started,
                        release=release,
                        timeout=self.TIMEOUT,
                    ):
                        calls.append(None)
                        started.set()
                        release.wait(timeout)
                        return object()

                func = Cached().method
                self.run_cond_wait_test(func, cond, started, release, calls)

    def test_cached_lock_cond(self):
        for info in (False, True):
            with self.subTest(info=info):
                cache = LRUCache(1)
                lock = Lock()
                cond = WaitCondition(lock)
                started = Event()
                release = Event()
                calls = []

                @cached(cache, lock=lock, condition=cond, info=info)
                def func(calls=calls, started=started, release=release):
                    calls.append(None)
                    started.set()
                    release.wait(self.TIMEOUT)
                    return object()

                self.run_cond_wait_test(func, cond, started, release, calls)

    def test_cachedmethod_lock_cond(self):
        for info in (False, True):
            with self.subTest(info=info):
                cache = LRUCache(1)
                lock = Lock()
                cond = WaitCondition(lock)
                started = Event()
                release = Event()
                calls = []

                class Cached:
                    @cachedmethod(
                        lambda _: cache,
                        lock=lambda _: lock,
                        condition=lambda _: cond,
                        info=info,
                    )
                    def method(
                        self,
                        calls=calls,
                        started=started,
                        release=release,
                        timeout=self.TIMEOUT,
                    ):
                        calls.append(None)
                        started.set()
                        release.wait(timeout)
                        return object()

                func = Cached().method
                self.run_cond_wait_test(func, cond, started, release, calls)

    def test_cached_unrelated_lock_cond(self):
        # a condition variable not created with the lock fails on
        # the first cache miss, even without concurrent calls
        for info in (False, True):
            with self.subTest(info=info):

                @cached(LRUCache(1), lock=Lock(), condition=Condition(), info=info)
                def func():
                    return object()

                with self.assertRaises(RuntimeError):
                    func()

    def test_cachedmethod_unrelated_lock_cond(self):
        for info in (False, True):
            with self.subTest(info=info):
                cache = LRUCache(1)
                lock = Lock()
                cond = Condition()

                class Cached:
                    @cachedmethod(
                        lambda _: cache,
                        lock=lambda _: lock,
                        condition=lambda _: cond,
                        info=info,
                    )
                    def method(self):
                        return object()

                with self.assertRaises(RuntimeError):
                    Cached().method()

    def test_cached_cond_recursion(self):
        for info in (False, True):
            with self.subTest(info=info):
                calls = []

                @cached(LRUCache(1), condition=Condition(), info=info)
                def func(calls=calls):
                    calls.append(None)
                    return func() + 1 if len(calls) < 3 else 0

                self.run_cond_recursion_test(func, calls, info)

    def test_cachedmethod_cond_recursion(self):
        for info in (False, True):
            with self.subTest(info=info):
                cache = LRUCache(1)
                cond = Condition()
                calls = []

                class Cached:
                    @cachedmethod(lambda _: cache, condition=lambda _: cond, info=info)
                    def method(self, calls=calls):
                        calls.append(None)
                        return self.method() + 1 if len(calls) < 3 else 0

                self.run_cond_recursion_test(Cached().method, calls, info)

    def run_cond_recursion_test(self, func, calls, info):
        results = []
        # a daemon thread, so a recursive call waiting forever for its
        # own pending call fails the test instead of blocking the exit
        thread = Thread(target=lambda: results.append(func()), daemon=True)
        thread.start()
        thread.join(timeout=self.TIMEOUT)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results, [2])

        # only the outermost call's result is cached
        self.assertEqual(func(), 2)
        self.assertEqual(len(calls), 3)
        if info:
            cache_info = func.cache_info()
            self.assertEqual((cache_info.hits, cache_info.misses), (1, 3))

    def test_cached_cond_recursive_error(self):
        for info in (False, True):
            with self.subTest(info=info):
                cond = WaitCondition()

                @cached(LRUCache(1), key=lambda call: (), condition=cond, info=info)
                def func(call):
                    return call()

                self.run_cond_recursive_error_test(func, cond)

    def test_cachedmethod_cond_recursive_error(self):
        for info in (False, True):
            with self.subTest(info=info):
                cache = LRUCache(1)
                cond = WaitCondition()

                class Cached:
                    @cachedmethod(
                        lambda _: cache,
                        key=lambda self, call: (),
                        condition=lambda _: cond,
                        info=info,
                    )
                    def method(self, call):
                        return call()

                self.run_cond_recursive_error_test(Cached().method, cond)

    def run_cond_recursive_error_test(self, func, cond):
        error = ValueError("recursive call failed")
        results = {}

        def inner():
            waiter.start()
            if not cond.waiting.wait(self.TIMEOUT):
                raise TimeoutError("second caller did not wait")
            raise error

        def run(name, call):
            try:
                results[name] = func(call)
            except ValueError as exc:
                results[name] = exc

        owner = Thread(target=run, args=("owner", lambda: func(inner)), daemon=True)
        waiter = Thread(target=run, args=("waiter", lambda: 42), daemon=True)
        owner.start()
        for thread in (owner, waiter):
            thread.join(timeout=self.TIMEOUT)
            self.assertFalse(thread.is_alive())
        self.assertEqual(results, {"owner": error, "waiter": 42})
        self.assertEqual(func.cache[()], 42)

    def run_cond_wait_test(self, func, cond, started, release, calls):
        results = [None] * 2

        def run(index):
            results[index] = func()

        first = Thread(target=run, args=[0])
        first.start()
        self.assertTrue(started.wait(self.TIMEOUT))
        second = Thread(target=run, args=[1])
        second.start()
        # second caller must block on the pending key
        self.assertTrue(cond.waiting.wait(self.TIMEOUT))
        release.set()
        for thread in (first, second):
            thread.join(timeout=self.TIMEOUT)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(calls), 1)
        self.assertIsNotNone(results[0])
        self.assertIs(results[0], results[1])

    def run_lock_test(self, func, cache, info):
        self.run_threading_test(func, cache)

        if info:
            cache_info = func.cache_info()
            self.assertEqual(cache_info.hits + cache_info.misses, self.NTHREADS)
            self.assertGreaterEqual(cache_info.misses, 1)

    def run_threading_test(self, func, cache):
        results = [None] * self.NTHREADS

        def run(index):
            results[index] = func()

        threads = [Thread(target=run, args=[i]) for i in range(self.NTHREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=self.TIMEOUT)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(cache), 1)

        # multiple threads may compute the value, but the first one
        # should always win and all concurrent invocations should
        # return the same result
        cached_result = next(iter(cache.values()))
        for result in results:
            self.assertIs(result, cached_result)
