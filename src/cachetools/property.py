"""TTL-aware cached property descriptor.

Implements a :class:`cached_property` variant that expires after a
configurable time-to-live (TTL).  Unlike :func:`functools.cached_property`,
the cached value is automatically invalidated once the TTL has elapsed and
recomputed on the next access.

Feature requested in issue #354.

Examples:
    >>> import time
    >>> from cachetools.property import cached_property
    >>>
    >>> class Config:
    ...     @cached_property(ttl=5)
    ...     def settings(self):
    ...         return load_settings()   # expensive I/O, cached for 5 s
    >>>
    >>> cfg = Config()
    >>> cfg.settings   # computed
    >>> cfg.settings   # returned from cache
    >>> time.sleep(6)
    >>> cfg.settings   # TTL expired — recomputed
"""

from __future__ import annotations

__all__ = ("cached_property",)

import threading
import time as _time
from typing import Any, Callable, Generic, TypeVar, overload

_T = TypeVar("_T")
_S = TypeVar("_S")


class cached_property(Generic[_T]):
    """A property that is computed once per instance and cached until *ttl* seconds elapse.

    Behaves like :func:`functools.cached_property` but adds a per-instance
    expiry timer.  When the TTL expires the next attribute access recomputes
    the value and resets the timer.

    The implementation is **thread-safe**: concurrent accesses during a
    recompute are serialised by a per-instance :class:`threading.Lock` so
    that the wrapped function is called exactly once even under contention.

    Args:
        ttl:
            Time-to-live in seconds.  Must be a positive number.
        timer:
            Callable that returns the current time as a float.
            Defaults to :func:`time.monotonic`.  Use :func:`time.time` if you
            need wall-clock expiry (e.g. for serialisation or across process
            restarts).

    Examples:
        >>> class DataFetcher:
        ...     @cached_property(ttl=30)
        ...     def remote_data(self):
        ...         return fetch()   # cached for 30 s, then refreshed

        Invalidate manually (e.g. after a config change):

        >>> del fetcher.remote_data   # next access triggers a recompute

        Inspect internals:

        >>> fetcher.remote_data.cache_info()
        CacheInfo(cached=True, expires_at=..., ttl=30)

    Note:
        Objects whose class uses ``__slots__`` must include the attribute
        name in ``__slots__``, or the descriptor will raise
        :exc:`AttributeError` when trying to store the cached value.

    Raises:
        ValueError: If *ttl* is not a positive number.
        TypeError: If *func* is not callable.
    """

    # Storage layout per instance:
    #   obj.__dict__[attrname] = _Entry(value, expires_at, lock)
    # On expiry the _Entry is replaced with a fresh one.

    class _Entry:
        """Per-instance cache entry holding the value, expiry time, and lock."""

        __slots__ = ("value", "expires_at", "lock")

        def __init__(self, value: Any, expires_at: float) -> None:
            self.value      = value
            self.expires_at = expires_at
            self.lock       = threading.Lock()

        @property
        def expired(self) -> bool:
            return _time.monotonic() >= self.expires_at

    # sentinel — distinguishes "not yet computed" from a computed value of None
    _MISSING: Any = object()

    def __init__(
        self,
        func: Callable[..., _T] | None = None,
        *,
        ttl: float,
        timer: Callable[[], float] = _time.monotonic,
    ) -> None:
        if func is not None and not callable(func):
            raise TypeError(f"cached_property requires a callable, got {type(func)!r}")
        if ttl <= 0:
            raise ValueError(f"ttl must be a positive number, got {ttl!r}")

        self._func    = func
        self._ttl     = ttl
        self._timer   = timer
        self._attrname: str | None = None
        self._lock    = threading.Lock()  # class-level lock for __set_name__

        if func is not None:
            self.__doc__  = func.__doc__
            self.__name__ = func.__name__
            self.__module__ = func.__module__

    # ── Decorator support ─────────────────────────────────────────────────────

    def __call__(self, func: Callable[..., _T]) -> "cached_property[_T]":
        """Allow use as ``@cached_property(ttl=N)`` (called with arguments)."""
        if self._func is not None:
            raise TypeError("cached_property already wraps a function")
        self._func    = func
        self.__doc__  = func.__doc__
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        return self

    # ── Descriptor protocol ───────────────────────────────────────────────────

    def __set_name__(self, owner: type, name: str) -> None:
        with self._lock:
            if self._attrname is None:
                self._attrname = name
            elif name != self._attrname:
                raise TypeError(
                    f"Cannot assign the same @cached_property to two different names "
                    f"({self._attrname!r} and {name!r})."
                )

    @overload
    def __get__(self, obj: None, objtype: type) -> "cached_property[_T]": ...
    @overload
    def __get__(self, obj: object, objtype: type | None = None) -> _T: ...

    def __get__(
        self,
        obj: object | None,
        objtype: type | None = None,
    ) -> "cached_property[_T] | _T":
        if obj is None:
            return self  # type: ignore[return-value]

        if self._func is None:
            raise TypeError("cached_property has no wrapped function")
        if self._attrname is None:
            raise TypeError(
                "Cannot use cached_property without calling __set_name__. "
                "Assign the descriptor to a class attribute."
            )

        try:
            instance_dict = obj.__dict__
        except AttributeError:
            raise AttributeError(
                f"No '__dict__' attribute on {type(obj).__name__!r} instance "
                f"to cache {self._attrname!r}. "
                "Add the attribute name to __slots__ or remove the cached_property."
            ) from None

        # Fast path — value cached and not expired
        entry: cached_property._Entry | None = instance_dict.get(self._attrname)
        if entry is not None and not entry.expired:
            return entry.value  # type: ignore[return-value]

        # Slow path — compute (or recompute) under a per-instance, per-attribute lock.
        # The lock key is stored in instance_dict under a private name so that
        # concurrent threads serialise on the same lock object.
        lock_key = f"__cached_property_lock_{self._attrname}__"
        lock: threading.Lock = instance_dict.setdefault(lock_key, threading.Lock())

        with lock:
            # Double-check: another thread may have computed the value while we waited
            entry = instance_dict.get(self._attrname)
            if entry is not None and not entry.expired:
                return entry.value  # type: ignore[return-value]

            value = self._func(obj)  # type: ignore[misc]
            instance_dict[self._attrname] = self._Entry(value, self._timer() + self._ttl)

        return value  # type: ignore[return-value]

    def __delete__(self, obj: object) -> None:
        """Invalidate the cached value for *obj* (force recompute on next access)."""
        try:
            obj.__dict__.pop(self._attrname, None)  # type: ignore[union-attr]
        except AttributeError:
            pass

    # ── Introspection ─────────────────────────────────────────────────────────

    def cache_info(self, obj: object) -> dict:
        """Return a dict describing the cache state for *obj*.

        Returns:
            A dict with keys ``cached`` (bool), ``expires_at`` (float or None),
            and ``ttl`` (float).
        """
        entry = getattr(obj, "__dict__", {}).get(self._attrname)
        if entry is None:
            return {"cached": False, "expires_at": None, "ttl": self._ttl}
        return {
            "cached":     not entry.expired,
            "expires_at": entry.expires_at,
            "ttl":        self._ttl,
        }

    def __repr__(self) -> str:
        fname = getattr(self._func, "__qualname__", repr(self._func))
        return f"cached_property({fname!s}, ttl={self._ttl})"
