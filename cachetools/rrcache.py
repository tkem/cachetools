from .cache import Cache
from .decorators import cachedfunc
from .lock import RLock

import random


class RRCache(Cache):
    """Random Replacement (RR) cache implementation.

    This class randomly selects candidate items and discards them to
    make space when necessary.

    """

    def popitem(self):
        """Remove and return a random `(key, value)` pair."""
        try:
            key = random.choice(list(self))
        except IndexError:
            raise KeyError('cache is empty')
        return (key, self.pop(key))


def rr_cache(maxsize=128, typed=False, getsizeof=None, lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    return cachedfunc(RRCache(maxsize, getsizeof), typed, lock)
