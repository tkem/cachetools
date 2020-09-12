from concurrent import futures
import threading
import unittest

import cachetools.func


class DecoratorTestMixin(object):

    def decorator(self, maxsize, **kwargs):
        return self.DECORATOR(maxsize, **kwargs)

    def test_decorator(self):
        cached = self.decorator(maxsize=2)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {
            'maxsize': 2, 'typed': False
        })
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, 2, 1))

    def test_decorator_clear(self):
        cached = self.decorator(maxsize=2)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {
            'maxsize': 2, 'typed': False
        })
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        cached.cache_clear()
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))

    def test_decorator_nocache(self):
        cached = self.decorator(maxsize=0)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {
            'maxsize': 0, 'typed': False
        })
        self.assertEqual(cached.cache_info(), (0, 0, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 0, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 2, 0, 0))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (0, 3, 0, 0))

    def test_decorator_unbound(self):
        cached = self.decorator(maxsize=None)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {
            'maxsize': None, 'typed': False
        })
        self.assertEqual(cached.cache_info(), (0, 0, None, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, None, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, None, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, None, 1))

    def test_decorator_typed(self):
        cached = self.decorator(maxsize=2, typed=True)(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {
            'maxsize': 2, 'typed': True
        })
        self.assertEqual(cached.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (1, 2, 2, 2))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 2, 2, 2))

    def test_decorator_user_function(self):
        cached = self.decorator(lambda n: n)
        self.assertEqual(cached.cache_parameters(), {
            'maxsize': 128, 'typed': False
        })
        self.assertEqual(cached.cache_info(), (0, 0, 128, 0))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (0, 1, 128, 1))
        self.assertEqual(cached(1), 1)
        self.assertEqual(cached.cache_info(), (1, 1, 128, 1))
        self.assertEqual(cached(1.0), 1.0)
        self.assertEqual(cached.cache_info(), (2, 1, 128, 1))

    def test_decorator_prefers_existing(self):
        turn_lock = threading.Lock()
        turn = [0]
        def take_number():
            with turn_lock:
                mine = turn[0]
                turn[0] += 1
            return mine

        # The values to return on each call to interlocked_calculate.
        zero = 'zero'
        one = 'one'
        values = (zero, one)
        calculated = [False, False]

        # Set up barriers for the control thread (this one) and the test threads
        # to rendezvous.
        entered_barriers = [threading.Barrier(2), threading.Barrier(2)]
        calculated_barriers = [threading.Barrier(2), threading.Barrier(2)]

        def interlocked_calculate():
            mine = take_number()
            entered_barriers[mine].wait()
            calculated[mine] = True
            calculated_barriers[mine].wait()
            return values[mine]

        cached = self.decorator(maxsize=None)(interlocked_calculate)

        # 'results' is a dictionary to emphasize that the ordering of threads
        # ('a' and 'b') does not necessarily correspond with which calculation
        # (0 and 1) will execute first.
        results = {}

        def perform_access(thread_id):
            results[thread_id] = cached()

        # Invert thread order: first thread to arrive gets its calculation last.
        filo = threading.Thread(target=lambda: perform_access('filo'))
        lifo = threading.Thread(target=lambda: perform_access('lifo'))

        filo.start()
        entered_barriers[0].wait()
        # Ensure that filo has its ticket before starting and ending lifo.
        lifo.start()
        entered_barriers[1].wait()
        calculated_barriers[1].wait()
        lifo.join()
        # Now that lifo has returned, let the second calculation complete.
        calculated_barriers[0].wait()
        filo.join()

        # Lastly, ensure that both results are from the last-in-first out entry,
        # using object identity tests.
        self.assertIs(one, results['filo'])
        self.assertIs(one, results['lifo'])


class LFUDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    DECORATOR = staticmethod(cachetools.func.lfu_cache)


class LRUDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    DECORATOR = staticmethod(cachetools.func.lru_cache)


class RRDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    DECORATOR = staticmethod(cachetools.func.rr_cache)


class TTLDecoratorTest(unittest.TestCase, DecoratorTestMixin):

    DECORATOR = staticmethod(cachetools.func.ttl_cache)
