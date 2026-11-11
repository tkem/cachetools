"""Regression test for issue #466.

Since 7.0.0, accessing a ``@cachedmethod`` on an instance stores a wrapper
bound to that instance in the instance's ``__dict__``.  ``copy.copy`` copies
``__dict__`` by reference, so a shallow copy inherits the *original* instance's
bound wrapper and therefore calls the method on the original, ignoring the
copy's own attributes and cache.
"""

import copy

from cachetools import cachedmethod


class Scaler:
    def __init__(self, factor):
        self.factor = factor
        self.cache = {}

    @cachedmethod(lambda self: self.cache)
    def scale(self, x):
        return self.factor * x


def test_copy_uses_its_own_attributes_and_cache():
    a = Scaler(1)
    assert a.scale(2) == 2
    assert len(a.cache) == 1

    b = copy.copy(a)
    b.factor = 10
    b.cache = {}  # give the copy its own empty cache

    # the copy must call the method on itself, not on the original
    assert b.scale(3) == 30
    # each instance keeps its own cache
    assert len(a.cache) == 1
    assert len(b.cache) == 1
