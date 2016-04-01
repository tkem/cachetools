class CacheTestMixin(object):

    def cache(self, maxsize, missing=None, getsizeof=None):
        raise NotImplementedError

    def test_cache_defaults(self):
        cache = self.cache(maxsize=1)
        self.assertEqual(0, len(cache))
        self.assertEqual(1, cache.maxsize)
        self.assertEqual(0, cache.currsize)
        self.assertEqual(1, cache.getsizeof(None))
        self.assertEqual(1, cache.getsizeof(''))
        self.assertEqual(1, cache.getsizeof(0))
        self.assertTrue(repr(cache).startswith(cache.__class__.__name__))

    def test_cache_insert(self):
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

    def test_cache_update(self):
        cache = self.cache(maxsize=2)

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache.update({1: 1, 2: 2})
        self.assertEqual(2, len(cache))
        self.assertEqual(1, cache[1])
        self.assertEqual(2, cache[2])

        cache.update({1: 'a', 2: 'b'})
        self.assertEqual(2, len(cache))
        self.assertEqual('a', cache[1])
        self.assertEqual('b', cache[2])

    def test_cache_delete(self):
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

    def test_cache_pop(self):
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

    def test_cache_popitem(self):
        cache = self.cache(maxsize=2)

        cache.update({1: 1, 2: 2})
        self.assertIn(cache.pop(1), {1: 1, 2: 2})
        self.assertEqual(1, len(cache))
        self.assertIn(cache.pop(2), {1: 1, 2: 2})
        self.assertEqual(0, len(cache))

        with self.assertRaises(KeyError):
            cache.popitem()

    def test_cache_missing(self):
        cache = self.cache(maxsize=2, missing=lambda x: x)

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

        cache = self.cache(maxsize=2, missing=lambda x: x,
                           getsizeof=lambda x: x)
        self.assertEqual(1, cache[1])
        self.assertIn(1, cache)
        self.assertEqual(2, cache[2])
        self.assertNotIn(1, cache)
        self.assertIn(2, cache)
        self.assertEqual(3, cache[3])
        self.assertNotIn(1, cache)
        self.assertIn(2, cache)
        self.assertNotIn(3, cache)

    def test_cache_getsizeof(self):
        cache = self.cache(maxsize=3, getsizeof=lambda x: x)
        self.assertEqual(3, cache.maxsize)
        self.assertEqual(0, cache.currsize)
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

    def test_cache_pickle(self):
        import pickle

        source = self.cache(maxsize=2)
        source.update({1: 1, 2: 2})

        cache = pickle.loads(pickle.dumps(source))
        self.assertEqual(source, cache)

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

        self.assertEqual(cache, pickle.loads(pickle.dumps(cache)))

    def test_cache_pickle_maxsize(self):
        import pickle
        import sys

        # test empty cache, single element, large cache (recursion limit)
        for n in [0, 1, sys.getrecursionlimit() * 2]:
            source = self.cache(maxsize=n)
            source.update((i, i) for i in range(n))
            cache = pickle.loads(pickle.dumps(source))
            self.assertEqual(n, len(cache))
            self.assertEqual(source, cache)
