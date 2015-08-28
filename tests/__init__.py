import cachetools


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
        import sys

        cache = self.cache(maxsize=2)
        cache.update({1: 1, 2: 2})
        if sys.version_info < (3, 0):
            cache = pickle.loads(pickle.dumps(cache, -1))
        else:
            cache = pickle.loads(pickle.dumps(cache))
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


class DecoratorTestMixin(object):

    def cache(self, minsize):
        raise NotImplementedError

    def func(self, *args, **kwargs):
        if hasattr(self, 'count'):
            self.count += 1
        else:
            self.count = 0
        return self.count

    def test_decorator(self):
        cache = self.cache(2)
        wrapper = cachetools.cached(cache)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.func)

        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(cachetools.hashkey(0), cache)
        self.assertNotIn(cachetools.hashkey(1), cache)
        self.assertNotIn(cachetools.hashkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(cachetools.hashkey(0), cache)
        self.assertIn(cachetools.hashkey(1), cache)
        self.assertIn(cachetools.hashkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 1)
        self.assertEqual(len(cache), 2)

    def test_decorator_typed(self):
        cache = self.cache(3)

        def typedkey(*args, **kwargs):
            key = cachetools.hashkey(*args, **kwargs)
            key += tuple(type(v) for v in args)
            key += tuple(type(v) for _, v in sorted(kwargs.items()))
            return key
        wrapper = cachetools.cached(cache, key=typedkey)(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.func)

        self.assertEqual(wrapper(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertIn(typedkey(0), cache)
        self.assertNotIn(typedkey(1), cache)
        self.assertNotIn(typedkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)
        self.assertIn(typedkey(0), cache)
        self.assertIn(typedkey(1), cache)
        self.assertNotIn(typedkey(1.0), cache)

        self.assertEqual(wrapper(1), 1)
        self.assertEqual(len(cache), 2)

        self.assertEqual(wrapper(1.0), 2)
        self.assertEqual(len(cache), 3)
        self.assertIn(typedkey(0), cache)
        self.assertIn(typedkey(1), cache)
        self.assertIn(typedkey(1.0), cache)

        self.assertEqual(wrapper(1.0), 2)
        self.assertEqual(len(cache), 3)

    def test_decorator_lock(self):
        class Lock(object):

            count = 0

            def __enter__(self):
                Lock.count += 1

            def __exit__(self, *exc):
                pass

        cache = self.cache(2)
        wrapper = cachetools.cached(cache, lock=Lock())(self.func)

        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.__wrapped__, self.func)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(Lock.count, 2)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(Lock.count, 4)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(Lock.count, 5)
