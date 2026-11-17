"""Benchmark behind the performance figures in copilot-review.md.

Prints nanoseconds per operation (microseconds for copies), best of 7
(timeit).  Run it on bare metal with one pinned core, for this tree or
for a git worktree of the previous release:

    PYTHONPATH=src taskset -c 3 python3 .github/copilot-bench.py

"""

import copy
import functools
import itertools
import threading
import timeit

import cachetools
import cachetools.func
from cachetools.keys import hashkey, typedkey

# new keys for evicting inserts and misses; its cost is included
nxt = itertools.count(1000).__next__

MISS = "try:\n    c[-1]\nexcept KeyError:\n    pass"


def best(stmt, number=200000, **names):
    times = timeit.repeat(stmt, globals=names, number=number, repeat=7)
    return round(min(times) / number * 1e9)


def report(label, *values):
    print("%-36s" % label + "".join("%7d" % value for value in values))


def ttu(key, value, now):
    return now + 3600


def filled(cache):
    cache.update((i, i) for i in range(100))
    return cache


def bench_caches():
    print("%-36s" % "cache" + "    hit     in   miss update  evict")
    caches = {
        "dict": {},
        "Cache": cachetools.Cache(100),
        "LRUCache": cachetools.LRUCache(100),
        "LFUCache": cachetools.LFUCache(100),
        "TTLCache": cachetools.TTLCache(100, ttl=3600),
        "TLRUCache": cachetools.TLRUCache(100, ttu=ttu),
    }
    for name, c in caches.items():
        filled(c)
        if name == "dict":
            evict = "c[nxt()] = 1\ndel c[next(iter(c))]"
        else:
            evict = "c[nxt()] = 1"
        report(
            name,
            best("c[50]", c=c),
            best("50 in c", c=c),
            best(MISS, c=c),
            best("c[50] = 1", c=c),
            best(evict, c=c, nxt=nxt),
        )
    print()
    report("count next", best("nxt()", 1000000, nxt=nxt))
    for cls in (cachetools.FIFOCache, cachetools.RRCache):
        c = filled(cls(100))
        report(cls.__name__ + " evict", best("c[nxt()] = 1", c=c, nxt=nxt))
    c = filled(cachetools.Cache(1000, getsizeof=lambda value: 1))
    report("Cache update with getsizeof", best("c[50] = 1", c=c))


def bench_keys():
    names = {"hashkey": hashkey, "typedkey": typedkey}
    for stmt in ("hashkey(1, 2, 3)", "hashkey(1, 2, a=3)", "typedkey(1, 2, 3)"):
        report(stmt, best(stmt, **names))


def bench_function(label, decorator):
    @decorator
    def f(x):
        return x

    for i in range(1024):  # fill the cache
        f(-i - 1)
    f(1)
    report(label, best("f(1)", f=f), best("f(nxt())", f=f, nxt=nxt))


def bench_functions():
    print("%-36s" % "decorator call" + "    hit   miss (evicting)")

    def cache():
        return cachetools.LRUCache(1024)

    cached = cachetools.cached
    bench_function("@cached", cached(cache()))
    bench_function("@cached(lock=Lock())", cached(cache(), lock=threading.Lock()))
    bench_function(
        "@cached(condition=Condition())",
        cached(cache(), condition=threading.Condition()),
    )
    bench_function("@cached(info=True)", cached(cache(), info=True))
    bench_function("cachetools.func.lru_cache", cachetools.func.lru_cache(1024))
    bench_function("functools.lru_cache (C)", functools.lru_cache(1024))

    class Bound:
        @cachetools.cached(cache())
        def method(self, x):
            return x

    obj = Bound()
    obj.method(1)
    report("@cached on a method (bound)", best("obj.method(1)", obj=obj))


def method_class(**kwargs):
    class M:
        def __init__(self, cache):
            self.cache = cache

        @cachetools.cachedmethod(lambda self: self.cache, **kwargs)
        def method(self, x):
            return x

    return M


def bench_method(label, cls):
    obj = cls(cachetools.LRUCache(1024))
    for i in range(1024):  # fill the cache
        obj.method(-i - 1)
    obj.method(1)
    report(
        label,
        best("obj.method(1)", obj=obj),
        best("obj.method(nxt())", obj=obj, nxt=nxt),
    )
    return obj


def bench_methods():
    condition = threading.Condition()
    M = method_class()
    obj = bench_method("@cachedmethod", M)
    bench_method(
        "@cachedmethod(condition=...)",
        method_class(condition=lambda self: condition),
    )
    bench_method("@cachedmethod(info=True)", method_class(info=True))
    print()
    method = obj.method
    cache = obj.cache
    report("@cachedmethod prebound hit", best("method(1)", method=method))
    report("@cachedmethod class call", best("M.method(obj, 1)", M=M, obj=obj))
    report("M(cache)", best("M(cache)", M=M, cache=cache))
    report("M(cache).method", best("M(cache).method", M=M, cache=cache))
    report("M(cache).method(1)", best("M(cache).method(1)", M=M, cache=cache))


def bench_lfu():
    c = filled(cachetools.LFUCache(100))
    cyc = itertools.cycle(range(100)).__next__
    report("cycle next", best("cyc()", 1000000, cyc=cyc))
    report("LFUCache moving hit", best("c[cyc()]", c=c, cyc=cyc))
    for maxsize in (10000, 100000):
        c = cachetools.LFUCache(maxsize)
        c.update((i, i) for i in range(maxsize))
        label = "LFUCache evict, maxsize=%d" % maxsize
        report(label, best("c[nxt()] = 1", c=c, nxt=nxt))


def bench_copies():
    print("%-36s" % "copy.copy(), 1000 items" + "     µs")
    caches = [
        {},
        cachetools.Cache(1000),
        cachetools.FIFOCache(1000),
        cachetools.LRUCache(1000),
        cachetools.LFUCache(1000),
        cachetools.RRCache(1000),
        cachetools.TTLCache(1000, ttl=3600),
        cachetools.TLRUCache(1000, ttu=ttu),
    ]
    for c in caches:
        c.update((i, i) for i in range(1000))
        ns = best("copy(c)", 2000, c=c, copy=copy.copy)
        print("%-36s%7.1f" % (type(c).__name__, ns / 1000))


if __name__ == "__main__":
    bench_caches()
    bench_keys()
    print()
    bench_functions()
    bench_methods()
    print()
    bench_lfu()
    print()
    bench_copies()
