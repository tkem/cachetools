import cachetools

import pytest


async def target(val):
    return val


@pytest.mark.asyncio
async def test_no_cache():
    cache = None  # In this case we expect simple passthrough
    wrapper = cachetools.cached(cache)(target)
    assert await wrapper(0) == 0
    assert await wrapper(1) == 1


@pytest.mark.asyncio
async def test_decorator():
    cache = {}
    wrapper = cachetools.cached(cache)(target)

    assert len(cache) == 0
    assert wrapper.__wrapped__ == target

    assert await wrapper(0) == 0
    assert len(cache) == 1
    assert cachetools.keys.hashkey(0) in cache
    assert cachetools.keys.hashkey(1) not in cache
    assert cachetools.keys.hashkey(1.0) not in cache

    assert await wrapper(1) == 1
    assert len(cache) == 2
    assert cachetools.keys.hashkey(0) in cache
    assert cachetools.keys.hashkey(1) in cache
    assert cachetools.keys.hashkey(1.0) in cache

    assert await wrapper(1) == 1
    assert len(cache) == 2

    assert await wrapper(1.0) == 1.0
    assert len(cache) == 2

    assert await wrapper(1.0) == 1.0
    assert len(cache) == 2


@pytest.mark.asyncio
async def test_decorator_typed():
    cache = dict()
    key = cachetools.keys.typedkey
    wrapper = cachetools.cached(cache, key=key)(target)

    assert len(cache) == 0
    assert wrapper.__wrapped__ == target

    assert await wrapper(0) == 0
    assert len(cache) == 1
    assert cachetools.keys.typedkey(0) in cache
    assert cachetools.keys.typedkey(1) not in cache
    assert cachetools.keys.typedkey(1.0) not in cache

    assert await wrapper(1) == 1
    assert len(cache) == 2
    assert cachetools.keys.typedkey(0) in cache
    assert cachetools.keys.typedkey(1) in cache
    assert cachetools.keys.typedkey(1.0) not in cache

    assert await wrapper(1) == 1
    assert len(cache) == 2

    assert await wrapper(1.0) == 1.0
    assert len(cache) == 3
    assert cachetools.keys.typedkey(0) in cache
    assert cachetools.keys.typedkey(1) in cache
    assert cachetools.keys.typedkey(1.0) in cache

    assert await wrapper(1.0) == 1.0
    assert len(cache) == 3


@pytest.mark.asyncio
async def test_decorator_lock():
    class Lock:

        count = 0

        def __enter__(self):
            Lock.count += 1

        def __exit__(self, *exc):
            pass

    cache = {}
    wrapper = cachetools.cached(cache, lock=Lock())(target)

    assert len(cache) == 0
    assert wrapper.__wrapped__ == target
    assert await wrapper(0) == 0
    assert Lock.count == 2
    assert await wrapper(1) == 1
    assert Lock.count == 4
    assert await wrapper(1) == 1
    assert Lock.count == 5
