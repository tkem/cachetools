from collections.abc import Hashable
from typing import Final

from _typeshed import Unused

__all__: Final = ("hashkey", "methodkey", "typedkey", "typedmethodkey")

def hashkey(*args: Hashable, **kwargs: Hashable) -> tuple[Hashable, ...]: ...
def methodkey(
    self: Unused, /, *args: Hashable, **kwargs: Hashable
) -> tuple[Hashable, ...]: ...
def typedkey(*args: Hashable, **kwargs: Hashable) -> tuple[Hashable, ...]: ...
def typedmethodkey(
    self: Unused, /, *args: Hashable, **kwargs: Hashable
) -> tuple[Hashable, ...]: ...
