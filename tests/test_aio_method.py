import operator

from cachetools import LRUCache, cachedmethod, keys

import pytest


class Cached:
    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

    @cachedmethod(operator.attrgetter("cache"))
    async def get(self, value):
        count = self.count
        self.count += 1
        return count

    @cachedmethod(operator.attrgetter("cache"), key=keys.typedkey)
    async def get_typed(self, value):
        count = self.count
        self.count += 1
        return count

    # https://github.com/tkem/cachetools/issues/107
    def __hash__(self):
        raise TypeError("unhashable type")


class Locked:
    def __init__(self, cache):
        self.cache = cache
        self.count = 0

    @cachedmethod(operator.attrgetter("cache"), lock=lambda self: self)
    async def get(self, value):
        return self.count

    def __enter__(self):
        self.count += 1

    def __exit__(self, *exc):
        pass


@pytest.mark.asyncio
async def test_dict():
    cached = Cached({})

    assert await cached.get(0) == 0
    assert await cached.get(1) == 1
    assert await cached.get(1) == 1
    assert await cached.get(1.0) == 1
    assert await cached.get(1.0) == 1

    cached.cache.clear()
    assert await cached.get(1) == 2


@pytest.mark.asyncio
async def test_typed_dict():
    cached = Cached(LRUCache(maxsize=2))

    assert await cached.get_typed(0) == 0
    assert await cached.get_typed(1) == 1
    assert await cached.get_typed(1) == 1
    assert await cached.get_typed(1.0) == 2
    assert await cached.get_typed(1.0) == 2
    assert await cached.get_typed(0.0) == 3
    assert await cached.get_typed(0) == 4


@pytest.mark.asyncio
async def test_lru():
    cached = Cached(LRUCache(maxsize=2))

    assert await cached.get(0) == 0
    assert await cached.get(1) == 1
    assert await cached.get(1) == 1
    assert await cached.get(1.0) == 1
    assert await cached.get(1.0) == 1

    cached.cache.clear()
    assert await cached.get(1) == 2


@pytest.mark.asyncio
async def test_typed_lru():
    cached = Cached(LRUCache(maxsize=2))

    assert await cached.get_typed(0) == 0
    assert await cached.get_typed(1) == 1
    assert await cached.get_typed(1) == 1
    assert await cached.get_typed(1.0) == 2
    assert await cached.get_typed(1.0) == 2
    assert await cached.get_typed(0.0) == 3
    assert await cached.get_typed(0) == 4


@pytest.mark.asyncio
async def test_nospace():
    cached = Cached(LRUCache(maxsize=0))

    assert await cached.get(0) == 0
    assert await cached.get(1) == 1
    assert await cached.get(1) == 2
    assert await cached.get(1.0) == 3
    assert await cached.get(1.0) == 4


@pytest.mark.asyncio
async def test_nocache():
    cached = Cached(None)

    assert await cached.get(0) == 0
    assert await cached.get(1) == 1
    assert await cached.get(1) == 2
    assert await cached.get(1.0) == 3
    assert await cached.get(1.0) == 4


@pytest.mark.asyncio
async def test_weakref():
    import weakref
    import fractions
    import gc

    # in Python 3.4, `int` does not support weak references even
    # when subclassed, but Fraction apparently does...
    class Int(fractions.Fraction):
        def __add__(self, other):
            return Int(fractions.Fraction.__add__(self, other))

    cached = Cached(weakref.WeakValueDictionary(), count=Int(0))

    assert await cached.get(0) == 0
    gc.collect()
    assert await cached.get(0) == 1

    ref = await cached.get(1)
    assert ref == 2
    assert await cached.get(1) == 2
    assert await cached.get(1.0) == 2

    ref = await cached.get_typed(1)
    assert ref == 3
    assert await cached.get_typed(1) == 3
    assert await cached.get_typed(1.0) == 4

    cached.cache.clear()
    assert await cached.get(1) == 5


@pytest.mark.asyncio
async def test_locked_dict():
    cached = Locked({})

    assert await cached.get(0) == 1
    assert await cached.get(1) == 3
    assert await cached.get(1) == 3
    assert await cached.get(1.0) == 3
    assert await cached.get(2.0) == 7


@pytest.mark.asyncio
async def test_locked_nocache():
    cached = Locked(None)

    assert await cached.get(0) == 0
    assert await cached.get(1) == 0
    assert await cached.get(1) == 0
    assert await cached.get(1.0) == 0
    assert await cached.get(1.0) == 0


@pytest.mark.asyncio
async def test_locked_nospace():
    cached = Locked(LRUCache(maxsize=0))

    assert await cached.get(0) == 1
    assert await cached.get(1) == 3
    assert await cached.get(1) == 5
    assert await cached.get(1.0) == 7
    assert await cached.get(1.0) == 9
