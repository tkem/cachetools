import random
import timeit

import cachetools

caches = {
    "dict": lambda _: {},
    "FIFO": cachetools.FIFOCache,
    "LFU": cachetools.LFUCache,
    "LRU": cachetools.LRUCache,
    "RR": cachetools.RRCache,
    "TTL": lambda n: cachetools.TTLCache(n, 10),
    "TLRU": lambda n: cachetools.TLRUCache(n, lambda k, v, t: t + 10),
}

for n in [1000, 2000, 5000, 10000]:
    tset = tget = 0

    for name, c in caches.items():
        cache = c(1000)

        def set(cache=cache, n=n):
            i = random.randint(1, n)
            cache[i] = i

        def get(cache=cache, n=n):
            i = random.randint(1, n)
            cache.get(i)

        t = timeit.timeit(set)
        if name == "dict":
            tset = t
            print("%4s.set(%d): %.3fs" % (name, n, t))
        else:
            print("%4s.set(%d): %.3fs (%.2f * dict)" % (name, n, t, t / tset))

        t = timeit.timeit(get)
        if name == "dict":
            tget = t
            print("%4s.get(%d): %.3fs" % (name, n, t))
        else:
            print("%4s.get(%d): %.3fs (%.2f * dict)" % (name, n, t, t / tget))
