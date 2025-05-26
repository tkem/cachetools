import random
import timeit

import cachetools

NUM_VALUES = 5
NUM_THREADS = 1000
SLEEP_SECONDS = 1.0
TTL_SECONDS = 3600
# INFO = True


class Cached:

    def __init__(self):
        self.cache = cachetools.TTLCache(maxsize=NUM_VALUES, ttl=TTL_SECONDS)

    @cachetools.cachedmethod(lambda self: self.cache)
    def get_value(self, n):
        # print("get_value:", n)
        return n

    def set_value(self, n):
        # print("set_value:", n)
        return n


cached = Cached()
name = "dict"

for n in [1000]:

    # def set(cache=cache, n=n):
    #    i = random.randint(1, n)
    #    cache[i] = i

    def get(cached=cached, n=n):
        i = random.randint(1, n)
        cached.get_value(i)

    # t = timeit.timeit(set)
    # if name == "dict":
    #    tset = t
    #    print("%4s.set(%d): %.3fs" % (name, n, t))
    # else:
    #    print("%4s.set(%d): %.3fs (%.2f * dict)" % (name, n, t, t / tset))

    t = timeit.timeit(get)
    if name == "dict":
        tget = t
        print("%4s.get(%d): %.3fs" % (name, n, t))
    else:
        print("%4s.get(%d): %.3fs (%.2f * dict)" % (name, n, t, t / tget))
