# Code Review — cachetools 7.2.7

**Date:** 2026-10-28
**Reviewed:** `dev/v7.2.7` at `2e82602` ("Release v7.2.7", `__version__` 7.2.7,
changelog dated 2026-10-28).

**CI status:** All `tox` environments pass locally on CPython 3.14.4: `py` (385
passed), `docs`, `doctest`, `pyright` (0 errors), `ruff`, `ruff-format`. GitHub
Actions not checked.

**Coverage:** 100% except two lines that only run on Python < 3.13, where
`@classmethod` over `@cachedmethod` calls `__get__` with the class as `obj`
(`_cachedmethod.py:22`, `_descriptor.py:79`); on < 3.13 the `_ClassMethodDescriptor`
`__call__`/`cache_clear` bodies and `classmethod_wrapper` are uncovered instead. The
CI matrix covers both.

**Verified:** the `Cache` size paths by a randomized test of all seven cache classes
(default, `v % 4` and negative `getsizeof`, `maxsize` 0 to 10, 20000 operations each,
checking items, results, exceptions, `currsize` and `len` after every step); wrapper
reuse by counting `Wrapper.__init__` calls; the timed-cache insert paths by the
existing TTL/TLRU tests with 100% branch coverage; performance by the benchmarks below.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place desyncs `currsize`. Documented footgun. |
| 2 | Low | `_cachedmethod.py` `_condition_info` / `_condition` | Pending sets are per instance, so two instances sharing one cache and condition do not coordinate pending keys. |
| 3 | Info | `_MethodDescriptor.__get__` (class-access path) | `Cls.method(obj, ...)` builds and discards a `Wrapper` per call before `obj.__dict__.setdefault()` returns the stored one: 2458 ns per hit against 565 through the instance and 1093 via `super()`, which reuses its stored wrapper (*Maintainer Decisions*). |
| 4 | Info | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key deadlocks (`wait()` on its own pending marker). |
| 5 | Info | `_MethodDescriptor.__get_unbound` | Lazy creation of the `_Unbound` object is unsynchronized; concurrent first class accesses may briefly see distinct, equivalent objects. Benign. |
| 6 | Info | `_descriptor.py` `_Unbound.__call__` | By design, autospec'd instances accept any arguments, so autospec no longer checks arity. A wrong receiver (`Cls.method(1)`) raises `TypeError` "No `__dict__` attribute on 'int' instance" with `info=True`; with `info=False` it only warns (`DeprecationWarning`) and then fails inside `cache(self)`. |
| 7 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a present-but-expired key removes it and raises `KeyError`, consistent with `key in cache`; `pop(key, default)` and `del` differ around the expiry instant. Intentional. |
| 8 | Info | `cachedmethod` `make_info` | A non-mapping `cache(self)` is only reported, as `TypeError`, from `cache_info()`. Acceptable. |
| 9 | Info | `_cachedmethod.py` `Wrapper.__call__` | Stacked `@cachedmethod` calls the inner *descriptor*: `TypeError` with `info=True`, a misleading `@classmethod` `DeprecationWarning` plus a throwaway wrapper with `info=False`. Unsupported (*Maintainer Decisions*). |
| 10 | Info | `_WrapperBase.__reduce__` | Unpickling and deep-copying rebuild wrappers through their descriptor, so `info=True` counters reset (asserted by tests). Acceptable. |
| 11 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | `_lookup` must stay importable and resolves through the owner's *current* class dict, so a pickle loaded while `Cls.method` is patched yields the patched attribute. A descriptor without `__set_name__` (deprecated pre-3.13 `@classmethod`) pickles but fails to load with `AttributeError`. |

No implementation bugs found beyond the items above.

## Performance

Hot-path costs at v7.2.7, measured on 2026-10-28 on CPython 3.14.4, ns per
operation, best of 7 (`timeit`, one pinned core; run-to-run noise about ±5%). Caches
hold 100 items for reads and updates and are full (`maxsize=100`) for evicting
inserts, with new keys from `itertools.count()` (19 ns included); decorators use
`LRUCache(1024)` and a one-argument function.

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 13 | 26 | 64 | 139 | 176 | 174 |
| contains | 13 | 35 | 35 | 36 | 129 | 129 |
| get miss (`KeyError`) | 66 | 251 | 335 | 338 | 422 | 417 |
| set, existing key | 14 | 64 | 109 | 170 | 389 | 633 |
| set, evicting | 109 | 327 | 506 | 579 | 1044 | 1537 |

`FIFOCache` evicting 384, `RRCache` 530; with a custom `getsizeof` (size-dict path)
`Cache` updates cost 125. The `dict` evicting row includes `del d[next(iter(d))]`.

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 248 | 1476 |
| `@cached(lock=Lock())` | 313 | 1709 |
| `@cached(condition=Condition())` | 399 | 2123 |
| `@cached(info=True)` | 271 | 1520 |
| `@cachedmethod` | 536 | 1907 |
| `@cachedmethod(condition=...)` | 729 | 2678 |
| `cachetools.func.lru_cache` | 417 | 2130 |
| `functools.lru_cache` (C) | 27 | 79 |

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1044 ns against 506 for `LRUCache` (TLRU 1537): `expire()` runs twice, the `_Timer` is entered twice and `del self[key]` re-checks expiry. Skipping `popitem()`'s own `expire()` and bypassing `__delitem__` would save ~13% more, but a direct `popitem()` could then return an expired item and subclass `__delitem__` overrides would no longer see evictions. |
| 2 | Info | `_cachedmethod.py` `Wrapper.__call__` | A `@cachedmethod` hit costs 536 ns against 248 for `@cached`: `__call__` dispatch, the module-level `wrapper()` hop, the `cache(self)` lambda and `partial(methodkey, obj)`. First access per instance 2772 ns including object creation (`Wrapper` construction alone 785); class call 2458 (Code #3). Inherent to the per-instance design. |
| 3 | Info | `cachetools.func` | `lru_cache` hit 417 ns against 27 for `functools.lru_cache`, 15x, since every `func` decorator uses `condition=Condition()` and `info=True`. By design. |
| 4 | Info | `keys.typedkey` | 441 ns against 92 for `hashkey(1, 2, 3)`: two `_HashedTuple` allocations and a generator; `tuple(map(type, args))` and a single concatenation would trim it. Rarely hot. |

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` keeps a receiver-less overload for deprecated `@classmethod` calls, so a missing instance on a regular `Cls.method(arg)` is not reported; drop it with `@classmethod` support. The receiver is positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` (`test_class_call_keyword_receiver`). |
| 2 | Info | `@cached(info=False)` wrappers have `cache_info = None` at runtime, but `_cached_wrapper` does not declare it. `_cached_wrapper.cache` is `MutableMapping \| None` for the deprecated `cache=None`; tighten both when that support is removed. |
| 3 | Info | `@classmethod` over `@cached`/`func.*_cache` reports a false "Argument missing" error; pyright does not bind through the wrapper's `__get__`. Rare. |
| 4 | Info | `_cached_wrapper_info.__get__` needs `# pyright: ignore[reportIncompatibleMethodOverride]`; the override is sound. |

Otherwise fine: `ParamSpec`/`Concatenate[Any, _P]` preserve signatures, overload order
is `Literal[False]` first, `func.pyi` covers both `@lru_cache` and `@lru_cache(...)`.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `UnboundMethodTest` does not assert that class access exposes no `cache_clear`/`cache_info`, nor class access for the lock/condition variants. |
| 2 | Info | `CacheTestMixin` checks key existence rather than the eviction victim, since it is shared across cache types; policy checks live per cache. No action needed. |
| 3 | Info | `test_func.py` calls decorators through `Callable[..., Any]`; `FIFODecoratorTest.test_method_typed` covers the stubs, enough since all five decorators share one wrapper type. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | The `@cachedmethod` docs do not mention that class access yields a callable without `cache_clear()`/`cache_info()` taking the receiver positionally or by name, or that pickling resets `cache_info()` counters (Code #10). |
| 2 | Info | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods; a one-line caveat that cache and counters are then shared across instances would help. |

## `CHANGELOG.rst`

No issues found. The 7.2.7 section (dated 2026-10-28) has "Various performance
improvements." and "Minor unit test improvements.", matching the release's commits
(no API or behavior change, so no tags), with two blank lines before the previous
section.

## Keys & Func Modules

No issues found. `_HashedTuple` uses the C tuple hash (rationale kept in a comment),
every `func.py` decorator is built on `cached(..., condition=Condition(), info=True)`,
and `_UnboundTTLCache` handles `maxsize=None`.
