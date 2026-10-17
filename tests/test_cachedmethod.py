import unittest
from collections.abc import Callable

from cachetools import Cache, cachedmethod, keys

from . import CountedCondition, CountedLock, SimplifiedTestCaseProtocol


class Cached:
    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count
        self.lock = CountedLock()
        self.cond = CountedCondition()

    def __get(self, _value):
        result = self.count
        self.count += 1
        return result

    @cachedmethod(lambda self: self.cache)
    def get(self, value):
        """docstring"""

        return self.__get(value)

    @cachedmethod(lambda self: self.cache, key=keys.typedmethodkey)
    def get_typed(self, value):
        return self.__get(value)

    @cachedmethod(lambda self: self.cache, info=True)
    def get_info(self, value):
        return self.__get(value)

    @cachedmethod(lambda self: self.cache, lock=lambda self: self.lock)
    def get_lock(self, value):
        return self.__get(value)

    @cachedmethod(lambda self: self.cache, lock=lambda self: self.lock, info=True)
    def get_lock_info(self, value):
        return self.__get(value)

    @cachedmethod(lambda self: self.cache, condition=lambda self: self.cond)
    def get_cond(self, value):
        return self.__get(value)

    @cachedmethod(lambda self: self.cache, condition=lambda self: self.cond, info=True)
    def get_cond_info(self, value):
        return self.__get(value)

    @cachedmethod(
        lambda self: self.cache,
        lock=lambda self: self.lock,
        condition=lambda self: self.cond,
    )
    def get_lock_cond(self, value):
        return self.__get(value)

    @cachedmethod(
        lambda self: self.cache,
        lock=lambda self: self.lock,
        condition=lambda self: self.cond,
        info=True,
    )
    def get_lock_cond_info(self, value):
        return self.__get(value)

    @cachedmethod(lambda self: self.cache, condition=lambda self: self.cond)
    def get_cond_error(self, _value):
        raise ValueError("test error")

    get_aliased = cachedmethod(lambda self: self.cache)(__get)


class CachedChild(Cached):
    def __init__(self, cache, child_cache):
        super().__init__(cache)
        self.child_cache = child_cache

    @cachedmethod(lambda self: self.child_cache, info=True)
    def get_info(self, value):
        return super().get_info(value) + 1


class Unhashable(Cached):
    # https://github.com/tkem/cachetools/issues/107
    def __hash__(self):
        raise TypeError("unhashable type")


class MethodDecoratorTestMixin(SimplifiedTestCaseProtocol):
    def cache(self, _minsize, **_kwargs):
        raise NotImplementedError

    def test_decorator(self):
        cached = Cached(self.cache(2))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_decorator_typed(self):
        cached = Cached(self.cache(3))

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)

    def test_decorator_unhashable(self):
        cached = Unhashable(self.cache(2))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_decorator_lock(self):
        cached = Cached(self.cache(2))

        self.assertEqual(cached.get_lock(0), 0)
        self.assertEqual(cached.lock.count, 2)
        self.assertEqual(cached.get_lock(1), 1)
        self.assertEqual(cached.lock.count, 4)
        self.assertEqual(cached.get_lock(1), 1)
        self.assertEqual(cached.lock.count, 5)
        self.assertEqual(cached.get_lock(1.0), 1)
        self.assertEqual(cached.lock.count, 6)
        self.assertEqual(cached.get_lock(1.0), 1)
        self.assertEqual(cached.lock.count, 7)

        cached.cache.clear()
        self.assertEqual(cached.get_lock(1), 2)
        self.assertEqual(cached.lock.count, 9)

    def test_decorator_cond(self):
        cached = Cached(self.cache(2))

        self.assertEqual(cached.get_cond(0), 0)
        self.assertEqual(cached.cond.count, 3)
        self.assertEqual(cached.cond.wait_count, 1)
        self.assertEqual(cached.cond.notify_count, 1)
        self.assertEqual(cached.get_cond(1), 1)
        self.assertEqual(cached.cond.count, 6)
        self.assertEqual(cached.cond.wait_count, 2)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(cached.get_cond(1), 1)
        self.assertEqual(cached.cond.count, 7)
        self.assertEqual(cached.cond.wait_count, 3)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(cached.get_cond(1.0), 1)
        self.assertEqual(cached.cond.count, 8)
        self.assertEqual(cached.cond.wait_count, 4)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(cached.get_cond(1.0), 1)
        self.assertEqual(cached.cond.count, 9)
        self.assertEqual(cached.cond.wait_count, 5)
        self.assertEqual(cached.cond.notify_count, 2)

        cached.cache.clear()
        self.assertEqual(cached.get_cond(1), 2)
        self.assertEqual(cached.cond.count, 12)
        self.assertEqual(cached.cond.wait_count, 6)
        self.assertEqual(cached.cond.notify_count, 3)

    def test_decorator_info(self):
        cache = self.cache(2)
        cached = Cached(cache)
        wrapper = cached.get_info

        maxsize = cache.maxsize if isinstance(cache, Cache) else None

        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(wrapper.cache_info(), (0, 2, maxsize, 2))
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(wrapper.cache_info(), (1, 2, maxsize, 2))
        wrapper.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(wrapper(0), 2)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(wrapper(0), 2)
        self.assertEqual(wrapper.cache_info(), (1, 1, maxsize, 1))

        # assert hits/misses are counted per instance
        cached = Cached(self.cache(2))
        self.assertEqual(cached.get_info(0), 0)
        self.assertEqual(cached.get_info.cache_info(), (0, 1, maxsize, 1))

    def test_decorator_lock_info(self):
        cache = self.cache(2)
        cached = Cached(cache)
        wrapper = cached.get_lock_info

        maxsize = cache.maxsize if isinstance(cache, Cache) else None

        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(cached.lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(cached.lock.count, 3)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(cached.lock.count, 4)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(cached.lock.count, 6)
        self.assertEqual(wrapper.cache_info(), (0, 2, maxsize, 2))
        self.assertEqual(cached.lock.count, 7)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(cached.lock.count, 8)
        self.assertEqual(wrapper.cache_info(), (1, 2, maxsize, 2))
        self.assertEqual(cached.lock.count, 9)

        wrapper.cache_clear()
        self.assertEqual(cached.lock.count, 10)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.lock.count, 10)
        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(cached.lock.count, 11)
        self.assertEqual(wrapper(0), 2)
        self.assertEqual(cached.lock.count, 13)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(cached.lock.count, 14)
        self.assertEqual(wrapper(0), 2)
        self.assertEqual(cached.lock.count, 15)
        self.assertEqual(wrapper.cache_info(), (1, 1, maxsize, 1))
        self.assertEqual(cached.lock.count, 16)

        # assert hits/misses are counted per instance
        cached = Cached(self.cache(2))
        self.assertEqual(cached.get_lock_info(0), 0)
        self.assertEqual(cached.get_lock_info.cache_info(), (0, 1, maxsize, 1))

    def test_decorator_cond_info(self):
        cache = self.cache(2)
        cached = Cached(cache)
        wrapper = cached.get_cond_info

        maxsize = cache.maxsize if isinstance(cache, Cache) else None

        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(cached.cond.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(cached.cond.count, 4)
        self.assertEqual(cached.cond.wait_count, 1)
        self.assertEqual(cached.cond.notify_count, 1)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(cached.cond.count, 5)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(cached.cond.count, 8)
        self.assertEqual(cached.cond.wait_count, 2)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(wrapper.cache_info(), (0, 2, maxsize, 2))
        self.assertEqual(cached.cond.count, 9)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(cached.cond.count, 10)
        self.assertEqual(cached.cond.wait_count, 3)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(wrapper.cache_info(), (1, 2, maxsize, 2))
        self.assertEqual(cached.cond.count, 11)
        wrapper.cache_clear()
        self.assertEqual(cached.cond.count, 12)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.cond.count, 12)
        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(cached.cond.count, 13)
        self.assertEqual(wrapper(0), 2)
        self.assertEqual(cached.cond.count, 16)
        self.assertEqual(cached.cond.wait_count, 4)
        self.assertEqual(cached.cond.notify_count, 3)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(cached.cond.count, 17)
        self.assertEqual(wrapper(0), 2)
        self.assertEqual(cached.cond.count, 18)
        self.assertEqual(cached.cond.wait_count, 5)
        self.assertEqual(cached.cond.notify_count, 3)
        self.assertEqual(wrapper.cache_info(), (1, 1, maxsize, 1))
        self.assertEqual(cached.cond.count, 19)

        # assert hits/misses are counted per instance
        cached = Cached(self.cache(2))
        self.assertEqual(cached.get_cond_info(0), 0)
        self.assertEqual(cached.get_cond_info.cache_info(), (0, 1, maxsize, 1))

    def test_decorator_lock_cond_info(self):
        cache = self.cache(2)
        cached = Cached(cache)
        wrapper = cached.get_lock_cond_info

        maxsize = cache.maxsize if isinstance(cache, Cache) else None

        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(cached.lock.count, 1)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(cached.lock.count, 4)
        self.assertEqual(cached.cond.wait_count, 1)
        self.assertEqual(cached.cond.notify_count, 1)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(cached.lock.count, 5)
        self.assertEqual(wrapper(1), 1)
        self.assertEqual(cached.lock.count, 8)
        self.assertEqual(cached.cond.wait_count, 2)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(wrapper.cache_info(), (0, 2, maxsize, 2))
        self.assertEqual(cached.lock.count, 9)
        self.assertEqual(wrapper(0), 0)
        self.assertEqual(cached.lock.count, 10)
        self.assertEqual(cached.cond.wait_count, 3)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(wrapper.cache_info(), (1, 2, maxsize, 2))
        self.assertEqual(cached.lock.count, 11)
        wrapper.cache_clear()
        self.assertEqual(cached.lock.count, 12)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.lock.count, 12)
        self.assertEqual(wrapper.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(cached.lock.count, 13)
        self.assertEqual(wrapper(0), 2)
        self.assertEqual(cached.lock.count, 16)
        self.assertEqual(cached.cond.wait_count, 4)
        self.assertEqual(cached.cond.notify_count, 3)
        self.assertEqual(wrapper.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(cached.lock.count, 17)
        self.assertEqual(wrapper(0), 2)
        self.assertEqual(cached.lock.count, 18)
        self.assertEqual(cached.cond.wait_count, 5)
        self.assertEqual(cached.cond.notify_count, 3)
        self.assertEqual(wrapper.cache_info(), (1, 1, maxsize, 1))
        self.assertEqual(cached.lock.count, 19)

        # assert hits/misses are counted per instance
        cached = Cached(self.cache(2))
        self.assertEqual(cached.get_lock_cond_info(0), 0)
        self.assertEqual(cached.get_lock_cond_info.cache_info(), (0, 1, maxsize, 1))

    def test_decorator_cond_error(self):
        cached = Cached(self.cache(2))

        with self.assertRaises(ValueError):
            cached.get_cond_error(0)
        self.assertEqual(cached.cond.count, 2)
        self.assertEqual(cached.cond.wait_count, 1)
        self.assertEqual(cached.cond.notify_count, 1)

        # verify pending set is cleaned up, otherwise this might deadlock
        with self.assertRaises(ValueError):
            cached.get_cond_error(0)
        self.assertEqual(cached.cond.count, 4)
        self.assertEqual(cached.cond.wait_count, 2)
        self.assertEqual(cached.cond.notify_count, 2)

    def test_decorator_wrapped(self):
        cache = self.cache(2)
        cached = Cached(cache)

        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.get.__wrapped__(cached, 0), 0)
        self.assertEqual(cached.get.__name__, "get")
        self.assertEqual(cached.get.__qualname__, "Cached.get")
        self.assertEqual((cached.get.__doc__ or "").strip(), "docstring")
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)

    def test_decorator_attributes(self):
        cache = self.cache(2)
        cached = Cached(cache)

        self.assertIs(cached.get.cache, cache)
        self.assertEqual(cached.get.cache_key(42), keys.methodkey(cached, 42))
        self.assertIs(cached.get.cache_lock, None)
        self.assertIs(cached.get.cache_condition, None)
        self.assertFalse(hasattr(cached.get, "cache_info"))

        self.assertIs(cached.get_lock.cache, cache)
        self.assertEqual(cached.get_lock.cache_key(42), keys.methodkey(cached, 42))
        self.assertIs(cached.get_lock.cache_lock, cached.lock)
        self.assertIs(cached.get_lock.cache_condition, None)
        self.assertFalse(hasattr(cached.get_lock, "cache_info"))

        self.assertIs(cached.get_cond.cache, cache)
        self.assertEqual(cached.get_cond.cache_key(42), keys.methodkey(cached, 42))
        self.assertIs(cached.get_cond.cache_lock, cached.cond)
        self.assertIs(cached.get_cond.cache_condition, cached.cond)
        self.assertFalse(hasattr(cached.get_cond, "cache_info"))

        self.assertIs(cached.get_lock_cond_info.cache, cache)
        self.assertEqual(
            cached.get_lock_cond_info.cache_key(42), keys.methodkey(cached, 42)
        )
        self.assertIs(cached.get_lock_cond_info.cache_lock, cached.lock)
        self.assertIs(cached.get_lock_cond_info.cache_condition, cached.cond)
        self.assertTrue(hasattr(cached.get_lock_cond_info, "cache_info"))

    def test_decorator_clear(self):
        cache = self.cache(2)
        cached = Cached(cache)

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(len(cache), 1)
        cached.get.cache_clear()
        self.assertEqual(len(cache), 0)

    def test_decorator_lock_clear(self):
        cache = self.cache(2)
        cached = Cached(cache)

        self.assertEqual(cached.get_lock(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.lock.count, 2)
        cached.get_lock.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.lock.count, 3)

    def test_decorator_cond_clear(self):
        cache = self.cache(2)
        cached = Cached(cache)

        self.assertEqual(cached.get_cond(0), 0)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.cond.count, 3)
        cached.get_cond.cache_clear()
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.cond.count, 4)

    def test_decorator_pickle(self):
        import pickle

        cache = self.cache(3)
        cached = Cached(cache)
        self.assertEqual(len(cache), 0)

        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(len(unpickled.get_cond.cache), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(unpickled.get_cond(0), 0)
        self.assertEqual(len(unpickled.get_cond.cache), 1)
        self.assertEqual(len(cache), 0)
        self.assertEqual(unpickled.get_cond(1), 1)
        self.assertEqual(len(unpickled.get_cond.cache), 2)
        self.assertEqual(len(cache), 0)

        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.get_cond(0), 0)
        self.assertEqual(len(cache), 1)

        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(len(unpickled.get_cond.cache), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(unpickled.get_cond(0), 0)
        self.assertEqual(len(unpickled.get_cond.cache), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(unpickled.get_cond(1), 1)
        self.assertEqual(len(unpickled.get_cond.cache), 2)
        self.assertEqual(len(cache), 1)

    def test_decorator_pickle_info(self):
        import pickle

        cache = self.cache(3)
        cached = Cached(cache)
        maxsize = cache.maxsize if isinstance(cache, Cache) else None
        self.assertEqual(len(cache), 0)

        # hits and misses will be reset when unpickling - since these
        # are primarily used for debugging/tuning, this is probably OK
        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(unpickled.get_cond_info.cache_info(), (0, 0, maxsize, 0))
        self.assertEqual(unpickled.get_cond_info(0), 0)
        self.assertEqual(unpickled.get_cond_info.cache_info(), (0, 1, maxsize, 1))
        self.assertEqual(unpickled.get_cond_info(1), 1)
        self.assertEqual(unpickled.get_cond_info.cache_info(), (0, 2, maxsize, 2))
        self.assertEqual(len(cache), 0)

        self.assertEqual(cached.get_cond_info(0), 0)
        self.assertEqual(len(cache), 1)

        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(unpickled.get_cond_info.cache_info(), (0, 0, maxsize, 1))
        self.assertEqual(unpickled.get_cond_info(0), 0)
        self.assertEqual(unpickled.get_cond_info.cache_info(), (1, 0, maxsize, 1))
        self.assertEqual(unpickled.get_cond_info(1), 1)
        self.assertEqual(unpickled.get_cond_info.cache_info(), (1, 1, maxsize, 2))
        self.assertEqual(unpickled.get_cond_info(0), 0)
        self.assertEqual(unpickled.get_cond_info.cache_info(), (2, 1, maxsize, 2))
        self.assertEqual(len(cache), 1)

    def test_decorator_pickle_super(self):
        import pickle

        self._test_copy_super(lambda obj: pickle.loads(pickle.dumps(obj)))

    def test_decorator_deepcopy_super(self):
        import copy

        self._test_copy_super(copy.deepcopy)

    def _test_copy_super(self, copyfunc: Callable[[CachedChild], CachedChild]):
        base_cache = self.cache(3)
        maxsize = base_cache.maxsize if isinstance(base_cache, Cache) else None
        cached = CachedChild(base_cache, self.cache(3))
        self.assertEqual(cached.get_info(0), 1)

        copied = copyfunc(cached)
        child = copied.get_info
        base = super(CachedChild, copied).get_info
        self.assertIsNot(base, child)
        self.assertIs(base, super(CachedChild, copied).get_info)
        self.assertIs(child.cache, copied.child_cache)
        self.assertIs(base.cache, copied.cache)
        self.assertEqual(len(vars(copied)["__cachetools_cachedmethods"]), 1)
        # hits and misses are reset
        self.assertEqual(child.cache_info(), (0, 0, maxsize, 1))
        self.assertEqual(base.cache_info(), (0, 0, maxsize, 1))

        self.assertEqual(copied.get_info(0), 1)
        self.assertEqual(child.cache_info(), (1, 0, maxsize, 1))
        self.assertEqual(base.cache_info(), (0, 0, maxsize, 1))
        self.assertEqual(copied.get_info(1), 2)
        self.assertEqual(child.cache_info(), (1, 1, maxsize, 2))
        self.assertEqual(base.cache_info(), (0, 1, maxsize, 2))
        self.assertEqual(len(vars(copied)["__cachetools_cachedmethods"]), 1)
        self.assertEqual(len(base_cache), 1)

    def test_decorator_pickle_aliased(self):
        import pickle

        cache = self.cache(3)
        cached = Cached(cache)
        self.assertEqual(len(cache), 0)

        self.assertEqual(cached.get_aliased(0), 0)
        self.assertEqual(len(cache), 1)

        unpickled = pickle.loads(pickle.dumps(cached))
        self.assertEqual(len(unpickled.get_aliased.cache), 1)
        self.assertEqual(unpickled.get_aliased(0), 0)
        self.assertEqual(len(unpickled.get_aliased.cache), 1)
        self.assertEqual(len(cache), 1)

    def test_decorator_slots(self):

        class Slots:
            __slots__ = ("cache",)

            def __init__(self, cache):
                self.cache = cache

            @cachedmethod(lambda self: self.cache)
            def get(self, value):
                return value

            @cachedmethod(lambda self: self.cache, info=True)
            def get_info(self, value):
                return value

        cache = self.cache(2)
        cached = Slots(cache)

        with self.assertRaises(TypeError):
            cached.get_info(42)

        with self.assertRaises(TypeError):
            cached.get(0)

    def test_decorator_immutable_dict(self):

        class ReadOnlyDict(dict):
            def __setitem__(self, _key, _value):
                raise TypeError("Modification not supported")

            def setdefault(self, _key, _value=None):
                raise TypeError("Modification not supported")

        class Immutable:
            def __init__(self, cache):
                self.cache = cache
                self.__dict__ = ReadOnlyDict(self.__dict__)

            @cachedmethod(lambda self: self.cache)
            def get(self, value):
                return value

            @cachedmethod(lambda self: self.cache, info=True)
            def get_info(self, value):
                return value

        cache = self.cache(2)
        cached = Immutable(cache)

        with self.assertRaises(TypeError):
            cached.get_info(42)

        with self.assertRaises(TypeError):
            self.assertEqual(cached.get(0), 0)

    def test_decorator_different_names(self):
        # RuntimeError for Python < 3.12, TypeError otherwise
        with self.assertRaisesRegex(Exception, "bar"):

            class Cached:
                @cachedmethod(lambda _: self.cache(2))
                def foo(_self):
                    pass

                bar = foo

    def test_decorator_same_name(self):
        # assigning to a second owner under the same name is accepted
        class Other(Cached):
            get = Cached.__dict__["get"]

        other = Other(self.cache(2))

        self.assertEqual(other.get(0), 0)
        self.assertEqual(other.get(0), 0)
        self.assertEqual(other.get(1), 1)

    def test_decorator_no_set_name(self):
        class Cached:
            def foo(_self):
                pass

        Cached.bar = cachedmethod(lambda _: self.cache(2))(Cached.foo)  # type: ignore
        Cached.baz = cachedmethod(lambda _: self.cache(2), info=True)(Cached.foo)  # type: ignore

        cached = Cached()

        with self.assertRaises(TypeError):
            cached.bar()  # type: ignore

        with self.assertRaises(TypeError):
            cached.baz()  # type: ignore


class CacheMethodTest(unittest.TestCase, MethodDecoratorTestMixin):
    def cache(self, minsize, **kwargs):
        return Cache(maxsize=minsize, **kwargs)

    def test_nospace(self):
        cached = Cached(self.cache(0))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(1.0), 4)

        self.assertEqual(cached.get_typed(0), 5)
        self.assertEqual(cached.get_typed(1), 6)
        self.assertEqual(cached.get_typed(1.0), 7)

        self.assertEqual(cached.get_info(0), 8)
        self.assertEqual(cached.get_info(1), 9)
        self.assertEqual(cached.get_info(1.0), 10)

    def test_lock_nospace(self):
        cached = Cached(self.cache(0))

        self.assertEqual(cached.get_lock(0), 0)
        self.assertEqual(cached.lock.count, 2)
        self.assertEqual(cached.get_lock(1), 1)
        self.assertEqual(cached.lock.count, 4)
        self.assertEqual(cached.get_lock(1), 2)
        self.assertEqual(cached.lock.count, 6)
        self.assertEqual(cached.get_lock(1.0), 3)
        self.assertEqual(cached.lock.count, 8)
        self.assertEqual(cached.get_lock(1.0), 4)
        self.assertEqual(cached.lock.count, 10)

        self.assertEqual(cached.get_lock_info(0), 5)
        self.assertEqual(cached.lock.count, 12)
        self.assertEqual(cached.get_lock_info(1), 6)
        self.assertEqual(cached.lock.count, 14)
        self.assertEqual(cached.get_lock_info(1.0), 7)
        self.assertEqual(cached.lock.count, 16)

    def test_cond_nospace(self):
        cached = Cached(self.cache(0))

        self.assertEqual(cached.get_cond(0), 0)
        self.assertEqual(cached.cond.count, 3)
        self.assertEqual(cached.cond.wait_count, 1)
        self.assertEqual(cached.cond.notify_count, 1)
        self.assertEqual(cached.get_cond(1), 1)
        self.assertEqual(cached.cond.count, 6)
        self.assertEqual(cached.cond.wait_count, 2)
        self.assertEqual(cached.cond.notify_count, 2)
        self.assertEqual(cached.get_cond(1), 2)
        self.assertEqual(cached.cond.count, 9)
        self.assertEqual(cached.cond.wait_count, 3)
        self.assertEqual(cached.cond.notify_count, 3)
        self.assertEqual(cached.get_cond(1.0), 3)
        self.assertEqual(cached.cond.count, 12)
        self.assertEqual(cached.cond.wait_count, 4)
        self.assertEqual(cached.cond.notify_count, 4)
        self.assertEqual(cached.get_cond(1.0), 4)
        self.assertEqual(cached.cond.count, 15)
        self.assertEqual(cached.cond.wait_count, 5)
        self.assertEqual(cached.cond.notify_count, 5)

        self.assertEqual(cached.get_cond_info(0), 5)
        self.assertEqual(cached.cond.count, 18)
        self.assertEqual(cached.cond.wait_count, 6)
        self.assertEqual(cached.cond.notify_count, 6)
        self.assertEqual(cached.get_cond_info(1), 6)
        self.assertEqual(cached.cond.count, 21)
        self.assertEqual(cached.cond.wait_count, 7)
        self.assertEqual(cached.cond.notify_count, 7)
        self.assertEqual(cached.get_cond(1.0), 7)
        self.assertEqual(cached.cond.count, 24)
        self.assertEqual(cached.cond.wait_count, 8)
        self.assertEqual(cached.cond.notify_count, 8)

    def test_shared_cache(self):
        cache = self.cache(2)
        cached1 = Cached(cache)
        cached2 = Cached(cache)

        self.assertEqual(cached1.get_info.cache_info(), (0, 0, 2, 0))
        self.assertEqual(cached2.get_info.cache_info(), (0, 0, 2, 0))

        # hits/misses are counted by instance
        self.assertEqual(cached1.get_info(0), 0)
        self.assertEqual(cached1.get_info.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached2.get_info.cache_info(), (0, 0, 2, 1))

        # default methodkey discards "self", so results will be shared
        # across instances
        self.assertEqual(cached2.get_info(0), 0)
        self.assertEqual(cached1.get_info.cache_info(), (0, 1, 2, 1))
        self.assertEqual(cached2.get_info.cache_info(), (1, 0, 2, 1))
        self.assertEqual(cached1.get_info(0), 0)
        self.assertEqual(cached1.get_info.cache_info(), (1, 1, 2, 1))
        self.assertEqual(cached2.get_info.cache_info(), (1, 0, 2, 1))
        self.assertEqual(cached1.get_info(1), 1)
        self.assertEqual(cached1.get_info.cache_info(), (1, 2, 2, 2))
        self.assertEqual(cached2.get_info.cache_info(), (1, 0, 2, 2))
        self.assertEqual(cached2.get_info(1), 1)
        self.assertEqual(cached1.get_info.cache_info(), (1, 2, 2, 2))
        self.assertEqual(cached2.get_info.cache_info(), (2, 0, 2, 2))

    def test_value_too_large(self):
        cache = self.cache(1, getsizeof=lambda x: x)
        cached = Cached(cache)
        self.assertEqual(cached.get(0), 0)
        self.assertIn(0, cache.values())
        self.assertEqual(cached.get(1), 1)
        self.assertIn(1, cache.values())
        self.assertEqual(cached.get(2), 2)
        self.assertNotIn(2, cache.values())

    def test_undecorated_override(self):
        class Child(Cached):
            def get_info(self, value):  # type: ignore
                return super().get_info(value) + 1

        cache = self.cache(2)
        cached = Child(cache)
        self.assertEqual(cached.get_info(0), 1)
        self.assertEqual(cached.get_info(0), 1)
        self.assertEqual(super(Child, cached).get_info(0), 0)
        self.assertEqual(cached.get_info(1), 2)
        self.assertEqual(super(Child, cached).get_info(1), 1)
        self.assertNotIn("get_info", vars(cached))
        self.assertEqual(super(Child, cached).get_info.cache_info(), (3, 2, 2, 2))

    def test_decorated_override(self):
        class Child(Cached):
            def __init__(self, base_cache, child_cache):
                super().__init__(base_cache)
                self.child_cache = child_cache

            @cachedmethod(lambda self: self.child_cache, info=True)
            def get_info(self, value):
                return super().get_info(value) + 1

        cached = Child(self.cache(2), self.cache(2))
        self.assertEqual(cached.get_info(0), 1)
        self.assertEqual(cached.get_info(0), 1)
        self.assertEqual(super(Child, cached).get_info(0), 0)
        self.assertEqual(cached.get_info(1), 2)
        self.assertEqual(super(Child, cached).get_info(1), 1)
        self.assertIn("get_info", vars(cached))
        self.assertEqual(cached.get_info.cache_info(), (1, 2, 2, 2))
        self.assertEqual(super(Child, cached).get_info.cache_info(), (2, 2, 2, 2))
        cached.get_info.cache_clear()
        self.assertEqual(cached.get_info.cache_info(), (0, 0, 2, 0))
        self.assertEqual(super(Child, cached).get_info.cache_info(), (2, 2, 2, 2))
        self.assertEqual(cached.get_info(0), 1)
        self.assertEqual(cached.get_info.cache_info(), (0, 1, 2, 1))
        self.assertEqual(super(Child, cached).get_info.cache_info(), (3, 2, 2, 2))
        super(Child, cached).get_info.cache_clear()
        self.assertEqual(cached.get_info.cache_info(), (0, 1, 2, 1))
        self.assertEqual(super(Child, cached).get_info.cache_info(), (0, 0, 2, 0))

    def test_multilevel_override(self):
        class Child(Cached):
            @cachedmethod(lambda self: self.cache, key=keys.typedmethodkey)
            def get_typed(self, value):
                return super().get_typed(float(value)) + 1

        class GrandChild(Child):
            @cachedmethod(lambda self: self.cache, key=keys.typedmethodkey, info=True)
            def get_typed(self, value):
                return super().get_typed(int(value)) + 1

        cache = self.cache(5)  # shared cache, but different key types
        cached = GrandChild(cache)
        self.assertEqual(cached.get_typed("0"), 2)
        self.assertEqual(cached.get_typed("0"), 2)
        self.assertEqual(cached.get_typed.cache_info(), (1, 1, 5, 3))
        self.assertEqual(super(GrandChild, cached).get_typed(0), 1)
        self.assertEqual(super(Child, cached).get_typed(0.0), 0)


class DictMethodTest(unittest.TestCase, MethodDecoratorTestMixin):
    def cache(self, minsize, **_kwargs):
        return {}


class WeakRefMethodTest(unittest.TestCase):
    def test_weakref(self):
        import fractions
        import gc
        import weakref

        # at least with Python 3.11, `int` does not support weak references
        # even when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):  # type: ignore
                return Int(fractions.Fraction.__add__(self, other))

        cache = weakref.WeakValueDictionary()
        cached = Cached(cache, count=Int(0))  # type: ignore

        self.assertEqual(cached.get(0), 0)
        gc.collect()
        self.assertEqual(cached.get(0), 1)

        ref = cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)

        ref = cached.get_typed(2)
        self.assertEqual(ref, 3)
        self.assertEqual(cached.get_typed(1), 4)
        self.assertEqual(cached.get_typed(1.0), 5)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 6)


class NoneMethodTest(unittest.TestCase):
    def test_none_info(self):
        cached = Cached(None)
        wrapper = cached.get_info

        with self.assertRaises(TypeError):
            wrapper.cache_info()


class UnboundMethodTest(unittest.TestCase):
    def test_class_call(self):
        cached = Cached(Cache(2))
        self.assertEqual(Cached.get(cached, 1), 0)
        self.assertEqual(cached.get(1), 0)
        self.assertEqual(Cached.get(cached, 2), 1)
        self.assertEqual(cached.get(2), 1)
        self.assertEqual(cached.count, 2)
        other = Cached(Cache(2), count=10)
        self.assertEqual(Cached.get(other, 1), 10)
        self.assertEqual(cached.get(1), 0)

    def test_class_call_info(self):
        cached = Cached(Cache(2))
        self.assertEqual(Cached.get_info(cached, 1), 0)
        self.assertEqual(cached.get_info(1), 0)
        self.assertEqual(Cached.get_info(cached, 2), 1)
        self.assertEqual(cached.get_info(2), 1)
        self.assertEqual(cached.count, 2)
        self.assertEqual(cached.get_info.cache_info(), (2, 2, 2, 2))
        other = Cached(Cache(2), count=10)
        self.assertEqual(Cached.get_info(other, 1), 10)
        self.assertEqual(cached.get_info(1), 0)

    def test_base_class_call(self):
        cached = Unhashable(Cache(2))
        self.assertEqual(Cached.get(cached, 1), 0)
        self.assertEqual(cached.get(1), 0)
        self.assertEqual(cached.count, 1)

    def test_class_call_without_instance(self):
        with self.assertRaises(TypeError):
            Cached.get()  # type: ignore

    def test_class_access_identity(self):
        self.assertIs(Cached.get, Cached.get)
        self.assertIs(Cached.get_info, Cached.get_info)
        self.assertIs(Unhashable.get, Cached.get)
        self.assertIsNot(Cached.get, Cached.get_info)

    def test_wrapped_method(self):
        cached = Cached(Cache(2))
        self.assertIs(Cached.get.__wrapped__, cached.get.__wrapped__)
        self.assertEqual(Cached.get.__name__, "get")
        self.assertEqual(Cached.get.__qualname__, "Cached.get")
        self.assertEqual(Cached.get.__wrapped__(cached, 1), 0)
        self.assertEqual(Cached.get.__wrapped__(cached, 1), 1)
        self.assertEqual(len(cached.cache), 0)

    def test_class_access_pickle(self):
        import pickle

        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(proto=proto):
                self.assertIs(pickle.loads(pickle.dumps(Cached.get, proto)), Cached.get)

    def test_class_access_copy(self):
        import copy

        self.assertIs(copy.copy(Cached.get), Cached.get)
        self.assertIs(copy.deepcopy(Cached.get), Cached.get)

    def test_class_access_alias(self):
        class Alias(Cached):
            alias = Cached.get

        self.assertIs(Alias.alias, Cached.get)
        cached = Alias(Cache(2))
        self.assertEqual(cached.alias(1), 0)
        self.assertEqual(cached.alias(1), 0)
        self.assertIs(cached.alias, cached.get)
        self.assertEqual(len(cached.cache), 1)

    def test_autospec(self):
        import unittest.mock

        mock = unittest.mock.create_autospec(Cached, instance=True)
        mock.get.return_value = 42
        self.assertEqual(mock.get(1), 42)
        mock.get.assert_called_with(1)
        self.assertEqual(mock.get(value=1), 42)
        mock.get.assert_called_with(value=1)


class ClassMethodTest(unittest.TestCase):
    class Cached(Cached):
        @classmethod
        @cachedmethod(lambda cls: {})
        def get_class(cls, value):
            return 42

    def test_classmethod(self):
        cached = self.Cached({})

        with self.assertRaisesRegex(TypeError, "class method"):
            cached.get_class(42)
