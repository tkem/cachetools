# https://github.com/tkem/cachetools/issues/294
import threading
from time import sleep

import cachetools.func

NUM_VALUES = 5
NUM_THREADS = 1000
SLEEP_SECONDS = 1.0
TTL_SECONDS = 3600


@cachetools.func.ttl_cache(maxsize=NUM_VALUES, ttl=TTL_SECONDS)
def get_value(n):
    print("get_value:", n)
    sleep(SLEEP_SECONDS)
    return n


class MyThread(threading.Thread):
    def __init__(self, id, value):
        threading.Thread.__init__(self)
        self.thread_name = str(id)
        self.thread_ID = id
        self.value = value

    def run(self):
        get_value(self.value)


threads = []
for i in range(0, NUM_THREADS):
    t = MyThread(i, i % NUM_VALUES)
    threads.append(t)
    t.start()
for t in threads:
    t.join()
print(get_value.cache_info())
