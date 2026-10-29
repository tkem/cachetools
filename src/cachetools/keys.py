"""Key functions for memoizing decorators."""

__all__ = ("hashkey", "methodkey", "typedkey", "typedmethodkey")


class _HashedTuple(tuple):
    """A tuple subclass formerly used for cache keys.

    Keys are now plain tuples: the key functions return their argument
    tuple as is, saving a copy into a subclass instance on every call.
    The class remains as the kwargs separator and for loading keys
    pickled by earlier versions, which compare equal to plain tuples.

    """


# A sentinel for separating args from kwargs.  Using the class itself
# ensures uniqueness and preserves identity when pickling/unpickling.
_kwmark = (_HashedTuple,)


def hashkey(*args, **kwargs):
    """Return a cache key for the specified hashable arguments."""

    if kwargs:
        return args + _kwmark + tuple(sorted(kwargs.items()))
    else:
        return args


def methodkey(self, *args, **kwargs):
    """Return a cache key for use with cached methods."""

    if kwargs:
        return args + _kwmark + tuple(sorted(kwargs.items()))
    else:
        return args


def typedkey(*args, **kwargs):
    """Return a typed cache key for the specified hashable arguments."""

    if kwargs:
        sorted_kwargs = tuple(sorted(kwargs.items()))
        key = args + _kwmark + sorted_kwargs
        key += tuple([type(v) for _, v in sorted_kwargs])
    else:
        key = args
    return key + tuple(map(type, args))


def typedmethodkey(self, *args, **kwargs):
    """Return a typed cache key for use with cached methods."""

    if kwargs:
        sorted_kwargs = tuple(sorted(kwargs.items()))
        key = args + _kwmark + sorted_kwargs
        key += tuple([type(v) for _, v in sorted_kwargs])
    else:
        key = args
    return key + tuple(map(type, args))
