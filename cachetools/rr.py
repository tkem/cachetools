from .cache import Cache
from .decorators import cachedfunc
from .lock import RLock

import random


class RRCache(Cache):
    """Random Replacement (RR) cache implementation.

    This class randomly selects candidate items and discards them to
    make space when necessary.

    By default, items are selected from the list of cache keys using
    :func:`random.choice`.  The optional argument `choice` may specify
    an alternative function that returns an arbitrary element from a
    non-empty sequence.

    """

    def __init__(self, maxsize, choice=random.choice, missing=None,
                 getsizeof=None):
        Cache.__init__(self, maxsize, missing, getsizeof)
        self.__choice = choice

    def popitem(self):
        """Remove and return a random `(key, value)` pair."""
        try:
            key = self.__choice(list(self))
        except IndexError:
            raise KeyError('cache is empty')
        return (key, self.pop(key))


def rr_cache(maxsize=128, choice=random.choice, typed=False, getsizeof=None,
             lock=RLock):
    """Decorator to wrap a function with a memoizing callable that saves
    up to `maxsize` results based on a Random Replacement (RR)
    algorithm.

    """
    return cachedfunc(RRCache(maxsize, choice, getsizeof), typed, lock)
