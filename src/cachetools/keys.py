"""Key functions for memoizing decorators."""

__all__ = ("hashkey", "methodkey", "typedkey", "typedmethodkey")


class _HashedTuple(tuple):
    """A tuple subclass used for cache keys.

    Unlike _HashedSeq in the standard library functools implementation,
    the hash value is not cached: the built-in tuple hash is faster than
    a Python-level __hash__ that caches it.

    """

    # A Python-level __hash__ that caches the hash costs more than it
    # saves: hashing a 2-tuple three times takes 161 ns as _HashedTuple
    # and 49 ns as a plain tuple (C tuple hash, 18 ns each); a dict
    # lookup keyed by one takes 50 vs 12 ns.  Every cache operation
    # hashes the key again (3 __hash__ calls per @cached hit, 12 per
    # evicting miss by cProfile, 11.5% of miss time in __hash__ alone).
    # The cached hash does not pay off even for a key wrapping a 200-int
    # tuple (166 vs 49 ns for three hashes), only for elements whose own
    # __hash__ is slow.
    #
    # __hashvalue = None  # default value, set in instance on first use
    #
    # def __hash__(self, hash=tuple.__hash__):
    #     hashvalue = self.__hashvalue
    #     if hashvalue is None:
    #         self.__hashvalue = hashvalue = hash(self)
    #     return hashvalue

    def __add__(self, other, add=tuple.__add__):
        return _HashedTuple(add(self, other))

    def __radd__(self, other, add=tuple.__add__):
        return _HashedTuple(add(other, self))

    def __getstate__(self):
        return {}


# A sentinel for separating args from kwargs.  Using the class itself
# ensures uniqueness and preserves identity when pickling/unpickling.
_kwmark = (_HashedTuple,)


def hashkey(*args, **kwargs):
    """Return a cache key for the specified hashable arguments."""

    if kwargs:
        return _HashedTuple(args + _kwmark + tuple(sorted(kwargs.items())))
    else:
        return _HashedTuple(args)


def methodkey(self, *args, **kwargs):
    """Return a cache key for use with cached methods."""
    return hashkey(*args, **kwargs)


def typedkey(*args, **kwargs):
    """Return a typed cache key for the specified hashable arguments."""

    if kwargs:
        sorted_kwargs = tuple(sorted(kwargs.items()))
        key = _HashedTuple(args + _kwmark + sorted_kwargs)
        key += tuple(type(v) for _, v in sorted_kwargs)
    else:
        key = _HashedTuple(args)
    key += tuple(type(v) for v in args)
    return key


def typedmethodkey(self, *args, **kwargs):
    """Return a typed cache key for use with cached methods."""
    return typedkey(*args, **kwargs)
