from collections.abc import Awaitable, Callable, MutableMapping
from typing import (
    Any,
    Concatenate,
    Final,
    Generic,
    Literal,
    ParamSpec,
    TypeVar,
    overload,
    type_check_only,
)

from . import CacheInfo

__all__: Final = ("acached", "acachedmethod")

_P = ParamSpec("_P")
_R = TypeVar("_R")
_KT = TypeVar("_KT")

@type_check_only
class _acached_wrapper(Generic[_P, _R]):
    __wrapped__: Callable[_P, Awaitable[_R]]
    __name__: str
    __doc__: str | None
    cache: MutableMapping[Any, Any]
    cache_key: Callable[..., Any] = ...
    def __call__(self, /, *args: _P.args, **kwargs: _P.kwargs) -> Awaitable[_R]: ...
    def cache_clear(self) -> None: ...

@type_check_only
class _acached_wrapper_info(_acached_wrapper[_P, _R]):
    def cache_info(self) -> CacheInfo: ...

@overload
def acached(
    cache: MutableMapping[_KT, Any],
    key: Callable[..., _KT] = ...,
    *,
    info: Literal[True],
) -> Callable[[Callable[_P, Awaitable[_R]]], _acached_wrapper_info[_P, _R]]: ...
@overload
def acached(
    cache: MutableMapping[_KT, Any],
    key: Callable[..., _KT] = ...,
    *,
    info: Literal[False] = ...,
) -> Callable[[Callable[_P, Awaitable[_R]]], _acached_wrapper[_P, _R]]: ...

@type_check_only
class _acachedmethod_wrapper(Generic[_P, _R]):
    __wrapped__: Callable[Concatenate[Any, _P], Awaitable[_R]]
    __name__: str
    __doc__: str | None
    cache: MutableMapping[Any, Any]
    cache_key: Callable[..., Any] = ...
    def __set_name__(self, owner: type, name: str) -> None: ...
    def __get__(
        self, obj: Any, objtype: type | None = None
    ) -> _acachedmethod_wrapper[_P, _R]: ...
    def __call__(self, /, *args: _P.args, **kwargs: _P.kwargs) -> Awaitable[_R]: ...
    def __reduce__(self) -> tuple[Any, ...]: ...
    def cache_clear(self) -> None: ...

@type_check_only
class _acachedmethod_wrapper_info(_acachedmethod_wrapper[_P, _R]):
    def __get__(
        self, obj: Any, objtype: type | None = None
    ) -> _acachedmethod_wrapper_info[_P, _R]: ...
    def cache_info(self) -> CacheInfo: ...

@overload
def acachedmethod(
    cache: Callable[[Any], MutableMapping[_KT, Any]],
    key: Callable[..., _KT] = ...,
    *,
    info: Literal[True],
) -> Callable[
    [Callable[Concatenate[Any, _P], Awaitable[_R]]], _acachedmethod_wrapper_info[_P, _R]
]: ...
@overload
def acachedmethod(
    cache: Callable[[Any], MutableMapping[_KT, Any]],
    key: Callable[..., _KT] = ...,
    *,
    info: Literal[False] = ...,
) -> Callable[
    [Callable[Concatenate[Any, _P], Awaitable[_R]]], _acachedmethod_wrapper[_P, _R]
]: ...
