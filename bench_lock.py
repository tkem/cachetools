import threading
import timeit

import cachetools
from cachetools import cached

print(f"cachetools {cachetools.__version__}")


class DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass


def make(**kwargs):
    @cached(cache={}, **kwargs)
    def fib(n):
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    return fib


COLD_N, HOT_N, REPEAT = 2000, 200_000, 7

for label, kwargs in [
    ("no lock", {}),
    ("Lock", {"lock": threading.Lock()}),
    ("RLock", {"lock": threading.RLock()}),
    ("DummyLock", {"lock": DummyLock()}),
    ("Condition", {"condition": threading.Condition()}),
    ("info", {"info": True}),
    ("Lock + info", {"lock": threading.Lock(), "info": True}),
    ("RLock + info", {"lock": threading.RLock(), "info": True}),
    ("DummyLock + info", {"lock": DummyLock(), "info": True}),
    ("Condition + info", {"condition": threading.Condition(), "info": True}),
]:
    fib = make(**kwargs)

    def cold():
        fib.cache_clear()
        return fib(42)

    t_cold = min(timeit.repeat(cold, number=COLD_N, repeat=REPEAT)) / COLD_N
    fib(42)  # warm
    t_hot = min(timeit.repeat(lambda: fib(42), number=HOT_N, repeat=REPEAT)) / HOT_N
    print(f"{label:10} cold fib(42): {t_cold * 1e6:6.1f} us    hot fib(42): {t_hot * 1e9:5.0f} ns")
