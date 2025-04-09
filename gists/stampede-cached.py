import threading
from time import sleep

import cachetools

NUM_THREADS = 1000
CACHE_TTL_SECONDS = 3600  # one hour
INFO = True


@cachetools.cached(
    cache=cachetools.TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS),
    condition=threading.Condition(),
    info=INFO,
)
def get_value():
    print("get_value")
    sleep(1)
    return 42


class MyThread(threading.Thread):
    def __init__(self, id):
        threading.Thread.__init__(self)
        self.thread_name = str(id)
        self.thread_ID = id

    def run(self):
        get_value()


threads = []
for i in range(0, NUM_THREADS):
    t = MyThread(i)
    threads.append(t)
    t.start()
for t in threads:
    t.join()
print(get_value.cache_info())
