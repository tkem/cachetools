from collections.abc import Callable, Sequence
from typing import (
    Any,
    Concatenate,
    Final,
    Generic,
    ParamSpec,
    TypeVar,
    overload,
    type_check_only,
)

from . import _CacheInfo

__all__: Final = ("fifo_cache", "lfu_cache", "lru_cache", "rr_cache", "ttl_cache")

_P = ParamSpec("_P")
_Q = ParamSpec("_Q")
_R = TypeVar("_R")
_S = TypeVar("_S")
_T = TypeVar("_T")

@type_check_only
class _cachetools_cache_wrapper(Generic[_P, _R]):
    __wrapped__: Callable[_P, _R]
    __name__: str
    __qualname__: str
    __doc__: str | None
    @overload  # class access, e.g. Cls.method
    def __get__(
        self, obj: None, objtype: type | None = None
    ) -> _cachetools_cache_wrapper[_P, _R]: ...
    @overload  # instance access binds the first parameter
    def __get__(
        self: _cachetools_cache_wrapper[Concatenate[_S, _Q], _R],
        obj: _S,
        objtype: type | None = None,
    ) -> _cachetools_cache_wrapper[_Q, _R]: ...
    @overload  # fallback, e.g. when wrapped by @staticmethod or @classmethod
    def __get__(
        self, obj: object, objtype: type | None = None
    ) -> _cachetools_cache_wrapper[_P, _R]: ...
    def __call__(self, /, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...
    def cache_info(self) -> _CacheInfo: ...
    def cache_clear(self) -> None: ...
    def cache_parameters(self) -> dict[str, Any]: ...

@overload
def fifo_cache(
    maxsize: int | None = 128, typed: bool = False
) -> Callable[[Callable[_P, _R]], _cachetools_cache_wrapper[_P, _R]]: ...
@overload
def fifo_cache(
    maxsize: Callable[_P, _R], typed: bool = False
) -> _cachetools_cache_wrapper[_P, _R]: ...
@overload
def lfu_cache(
    maxsize: int | None = 128, typed: bool = False
) -> Callable[[Callable[_P, _R]], _cachetools_cache_wrapper[_P, _R]]: ...
@overload
def lfu_cache(
    maxsize: Callable[_P, _R], typed: bool = False
) -> _cachetools_cache_wrapper[_P, _R]: ...
@overload
def lru_cache(
    maxsize: int | None = 128, typed: bool = False
) -> Callable[[Callable[_P, _R]], _cachetools_cache_wrapper[_P, _R]]: ...
@overload
def lru_cache(
    maxsize: Callable[_P, _R], typed: bool = False
) -> _cachetools_cache_wrapper[_P, _R]: ...
@overload
def rr_cache(
    maxsize: int | None = 128,
    choice: Callable[[Sequence[_T]], _T] = ...,
    typed: bool = False,
) -> Callable[[Callable[_P, _R]], _cachetools_cache_wrapper[_P, _R]]: ...
@overload
def rr_cache(
    maxsize: Callable[_P, _R],
    choice: Callable[[Sequence[_T]], _T] = ...,
    typed: bool = False,
) -> _cachetools_cache_wrapper[_P, _R]: ...
@overload
def ttl_cache(
    maxsize: int | None = 128,
    ttl: Any = 600,
    timer: Callable[[], _T] = ...,
    typed: bool = False,
) -> Callable[[Callable[_P, _R]], _cachetools_cache_wrapper[_P, _R]]: ...
@overload
def ttl_cache(
    maxsize: Callable[_P, _R],
    ttl: Any = 600,
    timer: Callable[[], _T] = ...,
    typed: bool = False,
) -> _cachetools_cache_wrapper[_P, _R]: ...
