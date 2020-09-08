import random

from .cache import Cache


# random.choice cannot be pickled in Python 2.7
def _choice(seq):
    return random.choice(seq)


class RRCache(Cache):
    """Random Replacement (RR) cache implementation."""

    def __init__(self, maxsize, choice=random.choice, getsizeof=None):
        Cache.__init__(self, maxsize, getsizeof)
        # TODO: use None as default, assing to self.choice directly?
        if choice is random.choice:
            self._choice = _choice
        else:
            self._choice = choice

    @property
    def choice(self):
        """The `choice` function used by the cache."""
        return self._choice

    def popitem(self):
        """Remove and return a random `(key, value)` pair."""
        try:
            key = self._choice(list(self))
        except IndexError:
            msg = '%s is empty' % self.__class__.__name__
            raise KeyError(msg) from None
        else:
            return (key, self.pop(key))
