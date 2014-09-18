from .cache import Cache

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
