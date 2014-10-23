class CacheTestMixin(object):

    def make_cache(self, maxsize, getsizeof=None):
        raise NotImplementedError

    def test_defaults(self):
        cache = self.make_cache(maxsize=1)
        self.assertEqual(0, len(cache))
        self.assertEqual(1, cache.maxsize)
        self.assertEqual(0, cache.currsize)
        self.assertEqual(1, cache.getsizeof(None))
        self.assertEqual(1, cache.getsizeof(''))
        self.assertEqual(1, cache.getsizeof(0))

    def test_insert(self):
        cache = self.make_cache(maxsize=2)

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
        cache = self.make_cache(maxsize=2)

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

    def test_delete(self):
        cache = self.make_cache(maxsize=2)

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

    def test_pop(self):
        cache = self.make_cache(maxsize=2)

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
        cache = self.make_cache(maxsize=2)

        cache.update({1: 1, 2: 2})
        self.assertIn(cache.pop(1), {1: 1, 2: 2})
        self.assertEqual(1, len(cache))
        self.assertIn(cache.pop(2), {1: 1, 2: 2})
        self.assertEqual(0, len(cache))

        with self.assertRaises(KeyError):
            cache.popitem()

    def test_getsizeof(self):
        cache = self.make_cache(maxsize=3, getsizeof=lambda x: x)
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
            cache[4] = 4
        self.assertEqual(1, len(cache))
        self.assertEqual(3, cache.currsize)
        self.assertEqual(3, cache[3])


class LRUCacheTestMixin(CacheTestMixin):

    def test_lru_insert(self):
        cache = self.make_cache(maxsize=2)

        cache[1] = 1
        cache[2] = 2
        cache[3] = 3

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[2], 2)
        self.assertEqual(cache[3], 3)
        self.assertNotIn(1, cache)

        cache[2]
        cache[4] = 4
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[2], 2)
        self.assertEqual(cache[4], 4)
        self.assertNotIn(3, cache)

        cache[5] = 5
        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[4], 4)
        self.assertEqual(cache[5], 5)
        self.assertNotIn(2, cache)

    def test_lru_getsizeof(self):
        cache = self.make_cache(maxsize=3, getsizeof=lambda x: x)

        cache[1] = 1
        cache[2] = 2

        self.assertEqual(len(cache), 2)
        self.assertEqual(cache[1], 1)
        self.assertEqual(cache[2], 2)

        cache[3] = 3

        self.assertEqual(len(cache), 1)
        self.assertEqual(cache[3], 3)
        self.assertNotIn(1, cache)
        self.assertNotIn(2, cache)

        with self.assertRaises(ValueError):
            cache[4] = 4
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache[3], 3)
