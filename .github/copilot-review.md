# Code Review — cachetools 8.0.0 (development)

**Date:** 2026-11-01
**Reviewed:** `develop` at `a698a1d` ("Improve cachetools.func tests."), rebased onto
`master` after v7.2.8 plus `c5b7564` (Fix #451, a positional-only `self` in the
`_ClassMethodDescriptor.__call__` that 8.0 removes) and `454e112` (setup-python bump);
code and docs unchanged since `94e26f9` "Prepare v8.0.0." (`__version__` 8.0.0,
CHANGELOG has the unreleased 8.0.0 section).

**CI status:** All `tox` environments pass locally on CPython 3.14.4: `py` (412
passed), `docs`, `doctest`, `pyright` (0 errors, 0 warnings), `ruff`, `ruff-format`;
`py` also passes on CPython 3.11 and 3.12. GitHub Actions is green for `develop` at
`43b9289`, the last pushed commit, on all nine matrix jobs (CPython 3.11–3.15,
3.13t–3.15t, PyPy 3.11); `a698a1d` has no run yet.

**Coverage:** 100% on Python < 3.13 (branches included); on 3.13+ only
`_descriptor.py:36` is uncovered, the pre-3.13 path where `@classmethod` calls
`__get__(cls, type(cls))` on a descriptor without `__set_name__`. The matrix covers
both.

**Verified:** by probe scripts rerun on 3.11, 3.12 and 3.14 against this code. `@cached`
on instance, static and class methods binds through `__get__` (autospec asserted by
`test_autospec`); module-level and class-attribute `@cached` wrappers pickle and
deep-copy to themselves, local ones fail like plain local functions (`AttributeError`
before 3.14, `PicklingError` since); `cached(None)` raises before decorating;
parameters named `pending` and `self` pass through both decorators, through the
instance and the class call (via the positional-only `__call__` and key receivers from
v7.2.8); `@cachedmethod` wrappers expose `cache_key` as a `partial` and `__wrapped__`
as the original function, the class callable shares that `__wrapped__`; an exception
under the condition variants releases a waiting thread, which recomputes. Keys pickled
by 7.2.7 (`_HashedTuple`, eight shapes with kwargs and types) load into `LRUCache` and
`TTLCache` and are found by the plain-tuple keys without duplicate entries. Cache
semantics by a differential trace of 100800 random operations on all seven cache
classes (default and `len` sizes, `maxsize` 0, 1, 3, 10, 2.5 and infinity, timer
advances) under a fixed `PYTHONHASHSEED`, run at `94e26f9` with the same code:
identical to v7.2.8 (see Code #11 for why the seed matters). Performance by the
benchmarks below; against the previous release every measured operation is at least as
fast except method access to `@cached` wrappers (Performance #1).

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place desyncs `currsize`. Documented footgun. |
| 2 | Low | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` via `@cachedmethod` | Pending sets are per wrapper, so two instances sharing one cache and condition do not coordinate pending keys. |
| 3 | Low | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key hangs on its own pending marker, where the `lock` variants raise `RecursionError`. |
| 4 | Info | `_MethodDescriptor.__get__` (class-access path) | `Cls.method(obj, ...)` builds and discards a wrapper per call before `obj.__dict__.setdefault()` returns the stored one: 2106 ns per hit against 319 through the instance and 608 via `super()`, which reuses its stored wrapper (*Maintainer Decisions*). |
| 5 | Info | `_cachedmethod.py` `_wrapper` | `update_wrapper(descriptor, method)` runs *after* `_MethodDescriptor(wrapper)`, so a stacked `@cachedmethod` copies the inner descriptor's `__dict__` (factory, owner, name) over the outer's and the pair silently acts as the inner decorator alone. Unsupported (*Maintainer Decisions*). |
| 6 | Info | `_cached.py` `_WrapperBase.__reduce__` | Pickling by `__qualname__` means a wrapper rebound under another name, or whose original name was deleted, unpickles to the wrong object or fails; a wrapped callable without `__qualname__` (e.g. a `functools.partial`) fails with `AttributeError` rather than `PicklingError`. |
| 7 | Info | `_descriptor.py` `_Unbound.__call__` / `_MethodDescriptor.__call__` | By design, autospec'd instances accept any arguments, so autospec no longer checks arity. A wrong receiver (`Cls.method(1)`) raises `TypeError` "No `__dict__` attribute on 'int' instance"; `@staticmethod` or `@property` over `@cachedmethod` report the "class methods" message. |
| 8 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a present-but-expired key removes it and raises `KeyError`, consistent with `key in cache`; `pop(key, default)` and `del` differ around the expiry instant. Intentional. |
| 9 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | `_lookup` must stay importable and resolves through the owner's *current* class dict, so a pickle loaded while `Cls.method` is patched yields the patched attribute, and after `del Cls.method` instances holding the wrapper still call it but no longer pickle (`KeyError`). A descriptor that never saw `__set_name__` pickles but fails to load with `AttributeError`. |
| 10 | Info | `_MethodDescriptor.__get__` | A descriptor assigned after class creation never receives `__set_name__`, so any access, class access included, raises `TypeError`. Undocumented use, asserted by `test_decorator_no_set_name`. After `del Cls.method` an already obtained class callable keeps working through the `super()` path (`test_class_call_after_delete`). |
| 11 | Info | `LFUCache.popitem` | Among equally used keys the victim is `next(iter(link.keys))`, so with `str` keys it varies between processes under hash randomization. Documented in code as arbitrary. |
| 12 | Info | `cachedmethod()` / `_cachedmethod.py` `_WrapperBase` properties | Unlike `cached(None)`, a non-callable `cache` such as `cachedmethod(None)` is accepted at decoration and fails at the first method access with `'NoneType' object is not callable`; `cache(self)` returning `None` (unsupported since 7.0) fails at the first call with `'NoneType' object is not subscriptable`. Both are `TypeError`s, only later and less specific. |
| 13 | Info | `_MethodDescriptor.__call__` | The 3.13+ `@classmethod` error path is the one receiver not taken positional-only (`self, *args, **kwargs`), so `Cls.cm(self=1)` on a class-method-wrapped `@cachedmethod` raises `TypeError: got multiple values for argument 'self'` instead of "Decorating class methods is not supported". Same exception type, misleading message; the counterpart of #451 on the 7.x line. |

## Performance

Hot-path costs measured on 2026-10-31 at `94e26f9` (code unchanged at `a698a1d`) on
CPython 3.14.4, ns per operation, best of 7 (`timeit`, one pinned core; repeat runs
agree within about 5%). Caches hold 100 items for reads and updates and are full
(`maxsize=100`) for evicting inserts, with new keys from `itertools.count()` (19 ns
included); decorators use `LRUCache(1024)` and a one-argument function.

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 13 | 26 | 63 | 135 | 178 | 177 |
| contains | 13 | 34 | 34 | 34 | 129 | 128 |
| get miss (`KeyError`) | 66 | 249 | 323 | 329 | 413 | 418 |
| set, existing key | 13 | 64 | 106 | 170 | 391 | 624 |
| set, evicting | 109 | 325 | 487 | 583 | 1051 | 1526 |

`FIFOCache` evicting 383, `RRCache` 525; with a custom `getsizeof` (size-dict path)
`Cache` updates cost 126. The `dict` evicting row includes `del d[next(iter(d))]`.

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 232 | 1330 |
| `@cached(lock=Lock())` | 311 | 1590 |
| `@cached(condition=Condition())` | 409 | 2068 |
| `@cached(info=True)` | 277 | 1397 |
| `@cached` on a method (bound) | 349 | |
| `@cachedmethod` | 311 | 1485 |
| `@cachedmethod(condition=...)` | 605 | 2368 |
| `@cachedmethod(info=True)` | 363 | 1551 |
| `cachetools.func.lru_cache` | 451 | 2123 |
| `functools.lru_cache` (C) | 27 | 80 |

Key functions: `hashkey(1, 2, 3)` 45, `hashkey(1, 2, a=3)` 208, `typedkey(1, 2, 3)`
151, `methodkey(obj, 1, 2, 3)` 47.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `_cached.py` `_WrapperBase.__get__` | A hit through a method costs 349 ns against 232 for a direct call: the Python-level `__get__` building a `types.MethodType` makes each attribute access about three times a plain function's C-level binding. The price of wrapper objects over closures, and the one measured operation slower than in the previous release. |
| 2 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1051 ns against 487 for `LRUCache` (TLRU 1526): `expire()` runs twice, the `_Timer` is entered twice and `del self[key]` re-checks expiry. Skipping `popitem()`'s own `expire()` and bypassing `__delitem__` would save more, but a direct `popitem()` could then return an expired item and subclass `__delitem__` overrides would no longer see evictions. |
| 3 | Info | `_decorator.py` mixin `__call__` | A `@cached` hit costs 232 ns: instance `__call__` dispatch plus the `self.cache` / `self.cache_key` attribute loads that a closure would hold as cell variables; the `info` counters as instance attributes add about 45. Price of the shared mixins. |
| 4 | Info | `_cachedmethod.py` `_WrapperBase` properties | A `@cachedmethod` hit costs 311 ns against 232 for `@cached`: the `cache` (and `cache_lock`) properties call the user's `cache(self)` lambda on every call, and the key goes through `functools.partial`. First access per instance 2666 ns including `M()` at 760; class call 2106 (Code #4). Inherent to the per-instance design. |
| 5 | Info | `cachetools.func` | `lru_cache` hit 451 ns against 27 for `functools.lru_cache`, since every `func` decorator uses `condition=Condition()` and `info=True`. By design. |

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` takes the receiver positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` (`test_class_call_keyword_receiver`). |
| 2 | Info | `@classmethod` over `@cached`/`func.*_cache` reports a false "Argument missing" error; pyright does not bind through the wrapper's `__get__`. Rare. |
| 3 | Info | `_cached_wrapper_info.__get__` needs `# pyright: ignore[reportIncompatibleMethodOverride]`; the override is sound. |
| 4 | Info | `func.pyi`'s wrapper omits `cache`, `cache_key`, `cache_lock` and `cache_condition`, which exist at runtime but are undocumented for `cachetools.func`. Matches `functools.lru_cache`. |

Otherwise fine: `ParamSpec`/`Concatenate[Any, _P]` preserve signatures, the overload
order is as prescribed, `TTLCache`/`TLRUCache` infer key and value types with the
default timer, and `func.pyi` covers both `@lru_cache` and `@lru_cache(...)`.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | No test passes a keyword argument named `self` through `@cached` or `@cachedmethod`; only `test_keys.py` covers the positional-only receiver, so the 8.0 regression fixed by the positional-only mixin `__call__` is unguarded. |
| 2 | Low | `@cached(info=True)` with a mapping lacking `__len__` is tested only through `@cachedmethod` (`NoneMethodTest`). |
| 3 | Info | `currsize` and `__repr__` on timed caches are never asserted to expire on their own; every such assertion follows `len()`, `clear()` or `__setitem__`. |
| 4 | Info | `UnboundMethodTest` exercises class access (`Cls.method(obj, ...)`) only for the plain and `info=True` variants; class access dispatches through the same `_Unbound` object for every variant, so the gap is small. |
| 5 | Info | `NoneMethodTest.test_none_info` asserts only that `cache_info()` raises `TypeError` when `cache(self)` returns `None`; that the call itself fails, and that `cachedmethod(None)` fails at first access (Code #12), is unasserted. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods, which now bind explicitly through `__get__`; a one-line caveat that cache and counters are then shared across instances would help. |
| 2 | Low | The `cached` section still speaks of a "memoizing wrapper function" whose "wrapped function is instrumented", while the result is a callable object; and `cache_lock` is described as exposing the `lock` parameter, but with `condition` alone it is the condition object (asserted by tests). |
| 3 | Info | The `versionchanged:: 8.0` notes cover `cache=None`, `@classmethod`, immutable `__dict__` and `CacheInfo`; the Python 3.11 floor and the wrapper-object change are not mentioned, which is fine for the reference. The class-access paragraph says the receiver may be passed by keyword, which holds only for a positional-or-keyword first parameter visible in the signature; acceptable. |

## `CHANGELOG.rst`

The 8.0.0 section lists the 3.10 drop, the deprecated `@cachedmethod` features
(`@classmethod`, immutable or missing `__dict__`), `cache=None`, the `__len__`
requirement and public `CacheInfo`. Not mentioned, release-only to add: `@cached`
wrappers are callable objects rather than functions (`inspect.isfunction()` is
`False`, `type()` changed); `info=False` wrappers no longer carry a `cache_info`
attribute set to `None`; a `@cachedmethod` descriptor assigned after class creation
raises `TypeError` (Code #10); and no performance bullet, although key functions return
plain tuples and the decorator hot paths were reworked. `__repr__` on both wrapper kinds
is a non-breaking addition.

## Keys & Func Modules

No issues found. The key functions return plain tuples with a positional-only
receiver, and `methodkey` / `typedmethodkey` repeat the `hashkey` / `typedkey` bodies
on purpose (a delegating call cost more); `_HashedTuple` stays as the `_kwmark`
sentinel and keeps 7.x pickles loadable (verified above). Every `func.py` decorator is
built on `cached(..., condition=Condition(), info=True)`, and `_UnboundTTLCache`
handles `maxsize=None`.
