import random

from .cache import Cache


class RRCache(Cache):
    """Random Replacement (RR) cache implementation."""

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

    @property
    def choice(self):
        """The `choice` function used by the cache."""
        return self.__choice
