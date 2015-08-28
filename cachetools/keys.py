__all__ = ('hashkey', 'typedkey')


class _HashedSequence(tuple):

    # nonempty __slots__ not supported for subtype of 'tuple'

    def __init__(self, iterable):
        self.__hash = tuple.__hash__(self)

    def __hash__(self):
        return self.__hash

    def __add__(self, other):
        return _HashedSequence(tuple.__add__(self, other))

    def __radd__(self, other):
        return _HashedSequence(tuple.__add__(other, self))


def hashkey(*args, **kwargs):
    """Return a cache key for the specified hashable arguments."""

    # TODO: profile flattened tuple w/marker object(s)
    return _HashedSequence((args, tuple(sorted(kwargs.items()))))


def typedkey(*args, **kwargs):
    """Return a typed cache key for the specified hashable arguments."""

    key = hashkey(*args, **kwargs)
    key += tuple(type(v) for v in args)
    key += tuple(type(v) for _, v in sorted(kwargs.items()))
    return key
