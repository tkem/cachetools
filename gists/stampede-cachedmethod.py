# https://github.com/tkem/cachetools/issues/294
import threading
from time import sleep

import cachetools

NUM_VALUES = 5
NUM_THREADS = 1000
SLEEP_SECONDS = 1.0
TTL_SECONDS = 3600
# INFO = True


class Cached:

    def __init__(self):
        self.cache = cachetools.TTLCache(maxsize=NUM_VALUES, ttl=TTL_SECONDS)
        self.cond = threading.Condition()

    @cachetools.cachedmethod(lambda self: self.cache, condition=lambda self: self.cond)
    def get_value(self, n):
        print("get_value:", n)
        sleep(SLEEP_SECONDS)
        return n


class MyThread(threading.Thread):
    def __init__(self, id, cached, value):
        threading.Thread.__init__(self)
        self.thread_name = str(id)
        self.thread_ID = id
        self.cached = cached
        self.value = value

    def run(self):
        self.cached.get_value(self.value)


cached = Cached()
threads = []
for i in range(0, NUM_THREADS):
    t = MyThread(i, cached, i % NUM_VALUES)
    threads.append(t)
    t.start()
for t in threads:
    t.join()
