# Code Review — cachetools 8.0.0 (development)

**Date:** 2026-10-30
**Reviewed:** `develop` at `02ab20b` ("Speed up decorator hot paths."; `__version__`
still 7.2.7, no 8.0.0 changelog section yet).

**CI status:** All `tox` environments pass locally on CPython 3.14.4: `py` (398
passed), `docs`, `doctest`, `pyright` (0 errors), `ruff`, `ruff-format`; `py` also
passes on CPython 3.11 and 3.12. GitHub Actions on `tkem/cachetools` is green for
`develop` at `400b91c`, the last pushed state, on all nine matrix jobs (CPython
3.11–3.15, 3.13t–3.15t, PyPy 3.11); the local branch has been rebased since (ahead
4, behind 4) and `02ab20b` has no run yet.

**Coverage:** 100% on Python < 3.13 (branches included); on 3.13+ only
`_descriptor.py:36` is uncovered, the pre-3.13 path where `@classmethod` calls
`__get__(cls, type(cls))` on a descriptor without `__set_name__`. The matrix covers
both.

**Verified:** by a probe script on 3.11, 3.12 and 3.14: `@cached` on instance, static
and class methods binds through `__get__` (autospec asserted by `test_autospec`);
module-level and class-attribute `@cached` wrappers pickle and deep-copy to themselves,
local ones raise what plain local functions raise (`AttributeError` before 3.14,
`PicklingError` since); `cached(None)` raises before decorating; a custom cache without
`len()` fails only in `cache_info()`; a parameter named `pending` works with
`condition` on both decorators; `@cachedmethod` wrappers expose `cache_key` as a
`partial` and `__wrapped__` as the original function. Keys pickled by 7.2.7
(`_HashedTuple`, eight shapes with kwargs and types) load into `LRUCache` and
`TTLCache` and are found by the new plain-tuple keys without duplicate entries. Cache
semantics by a differential trace of 100800 random operations on all seven cache
classes (default and `len` sizes, `maxsize` 0, 1, 3, 10, 2.5 and infinity, timer
advances) under a fixed `PYTHONHASHSEED`: identical to v7.2.7 (see Code #14 for why
the seed matters). The `__repr__`s (`<cached f>`, `<cachedmethod f of <obj>>`,
`<cachedmethod f>` on class access) are asserted by `test_decorator_repr` in both
decorator test modules. Performance by the benchmarks below.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place desyncs `currsize`. Documented footgun. |
| 2 | Low | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` via `@cachedmethod` | Pending sets are per wrapper, so two instances sharing one cache and condition do not coordinate pending keys. |
| 3 | Info | `_MethodDescriptor.__get__` (class-access path) | `Cls.method(obj, ...)` builds and discards a wrapper per call before `obj.__dict__.setdefault()` returns the stored one: 2022 ns per hit against 305 through the instance and 569 via `super()`, which reuses its stored wrapper (*Maintainer Decisions*). |
| 4 | Info | `_cachedmethod.py` `_wrapper` | `update_wrapper(descriptor, method)` runs *after* `_MethodDescriptor(wrapper)`, so a stacked `@cachedmethod` copies the inner descriptor's `__dict__` (factory, owner, name) over the outer's and the pair silently acts as the inner decorator alone. Calling `update_wrapper()` first would turn this into a `TypeError`, though with the misleading "class methods" message. Unsupported (*Maintainer Decisions*). |
| 5 | Info | `_cached.py` `_WrapperBase.__reduce__` | Pickling by `__qualname__` means a wrapper rebound under another name, or whose original name was deleted, unpickles to the wrong object or fails; wrappers on local functions fail like plain local functions. |
| 6 | Info | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key deadlocks (`wait()` on its own pending marker). |
| 7 | Info | `_MethodDescriptor.__get_unbound` | Lazy creation of the `_Unbound` object is unsynchronized; concurrent first class accesses may briefly see distinct, equivalent objects. Benign. |
| 8 | Info | `_descriptor.py` `_Unbound.__call__` | By design, autospec'd instances accept any arguments, so autospec no longer checks arity. A wrong receiver (`Cls.method(1)`) raises `TypeError` "No `__dict__` attribute on 'int' instance". |
| 9 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a present-but-expired key removes it and raises `KeyError`, consistent with `key in cache`; `pop(key, default)` and `del` differ around the expiry instant. Intentional. |
| 10 | Info | `CacheInfo._make_info` | A cache without `__len__` is only reported, as `TypeError` from `len()`, when `cache_info()` runs; documented requirement. |
| 11 | Info | `_cachedmethod.py` `_WrapperBase.__reduce__` | Unpickling and deep-copying rebuild wrappers through their descriptor, so `info=True` counters reset (asserted by tests, documented). Acceptable. |
| 12 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | `_lookup` must stay importable and resolves through the owner's *current* class dict, so a pickle loaded while `Cls.method` is patched yields the patched attribute. A descriptor that never saw `__set_name__` pickles but fails to load with `AttributeError`. |
| 13 | Info | `_MethodDescriptor.__get__` | A descriptor assigned after class creation never receives `__set_name__`, so any access, class access included, raises `TypeError`; in 7.x `info=False` descriptors fell back to a throwaway wrapper there. Undocumented use, asserted by `test_decorator_no_set_name`. After `del Cls.method` an already obtained class callable keeps working through the `super()` path (`test_class_call_after_delete`). |
| 14 | Info | `LFUCache.popitem` | Among equally used keys the victim is `next(iter(link.keys))`, so with `str` keys it varies between processes under hash randomization. Documented in code as arbitrary. |

No implementation bugs found beyond the items above.

## Performance

Hot-path costs measured on 2026-10-30 at `02ab20b` on CPython 3.14.4, ns per
operation, best of 7 (`timeit`, one pinned core; repeat runs agree within about 5%).
Caches hold 100 items for reads and updates and are full (`maxsize=100`) for evicting
inserts, with new keys from `itertools.count()` (18 ns included); decorators use
`LRUCache(1024)` and a one-argument function.

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 13 | 26 | 61 | 131 | 170 | 170 |
| contains | 13 | 34 | 34 | 34 | 126 | 126 |
| get miss (`KeyError`) | 63 | 250 | 316 | 315 | 401 | 405 |
| set, existing key | 13 | 61 | 103 | 162 | 382 | 616 |
| set, evicting | 106 | 319 | 474 | 567 | 1038 | 1485 |

`FIFOCache` evicting 369, `RRCache` 506; with a custom `getsizeof` (size-dict path)
`Cache` updates cost 120. The `dict` evicting row includes `del d[next(iter(d))]`.

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 222 | 1321 |
| `@cached(lock=Lock())` | 293 | 1535 |
| `@cached(condition=Condition())` | 392 | 2045 |
| `@cached(info=True)` | 263 | 1354 |
| `@cached` on a method (bound) | 328 | |
| `@cachedmethod` | 304 | 1456 |
| `@cachedmethod(condition=...)` | 567 | 2269 |
| `@cachedmethod(info=True)` | 335 | 1468 |
| `cachetools.func.lru_cache` | 429 | 2085 |
| `functools.lru_cache` (C) | 25 | 75 |

Key functions: `hashkey(1, 2, 3)` 43, `hashkey(1, 2, a=3)` 197, `typedkey(1, 2, 3)`
143, `methodkey(obj, 1, 2, 3)` 45.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1038 ns against 474 for `LRUCache` (TLRU 1485): `expire()` runs twice, the `_Timer` is entered twice and `del self[key]` re-checks expiry. Skipping `popitem()`'s own `expire()` and bypassing `__delitem__` would save more, but a direct `popitem()` could then return an expired item and subclass `__delitem__` overrides would no longer see evictions. |
| 2 | Info | `_decorator.py` mixin `__call__` | A `@cached` hit costs 222 ns: instance `__call__` dispatch plus the `self.cache` / `self.cache_key` attribute loads that a closure would hold as cell variables. Price of the shared mixins. |
| 3 | Info | `_cached.py` `_WrapperBase.__get__` | A hit through a bound method costs 328 ns against 222 for a plain call: each attribute access builds a `types.MethodType`, as for `functools.lru_cache`. Inherent. |
| 4 | Info | `_cachedmethod.py` `_WrapperBase` properties | A `@cachedmethod` hit costs 304 ns against 222 for `@cached`: the `cache` (and `cache_lock`) properties call the user's `cache(self)` lambda on every call, and the key goes through `functools.partial`. First access per instance 2647 ns including `M()` at 732; class call 2022 (Code #3). Inherent to the per-instance design. |
| 5 | Info | `cachetools.func` | `lru_cache` hit 429 ns against 25 for `functools.lru_cache`, since every `func` decorator uses `condition=Condition()` and `info=True`. By design. |

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` takes the receiver positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` (`test_class_call_keyword_receiver`). |
| 2 | Info | `@classmethod` over `@cached`/`func.*_cache` reports a false "Argument missing" error; pyright does not bind through the wrapper's `__get__`. Rare. |
| 3 | Info | `_cached_wrapper_info.__get__` needs `# pyright: ignore[reportIncompatibleMethodOverride]`; the override is sound. |

Otherwise fine: `ParamSpec`/`Concatenate[Any, _P]` preserve signatures, the
keyword-only `info: Literal[True]` overload precedes the `Literal[False]` default,
`Cache.setdefault` has the `None`-default overload, `CacheInfo` is exported, the key
functions are typed as returning `tuple[Hashable, ...]`, and `func.pyi` covers both
`@lru_cache` and `@lru_cache(...)`.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `UnboundMethodTest` exercises class access (`Cls.method(obj, ...)`) only for the plain and `info=True` variants; the lock and condition variants are covered through the instance alone. Class access dispatches through the same `_Unbound` object for every variant, so the gap is small. |
| 2 | Info | `CacheTestMixin` checks key existence rather than the eviction victim, since it is shared across cache types; policy checks live per cache. No action needed. |
| 3 | Info | `test_func.py` calls decorators through `Callable[..., Any]`; `FIFODecoratorTest.test_method_typed` covers the stubs, enough since all five decorators share one wrapper type. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods, which now bind explicitly through `__get__`; a one-line caveat that cache and counters are then shared across instances would help. |
| 2 | Info | The `versionchanged:: 8.0` notes cover `cache=None`, `@classmethod`, immutable `__dict__` and `CacheInfo`; the Python 3.11 floor and the wrapper-object change are not mentioned, which is fine for the reference. The new class-access paragraph says the receiver may be passed by keyword, which holds only for a positional-or-keyword first parameter; acceptable. |

## `CHANGELOG.rst`

No 8.0.0 section yet (release-only). Breaking changes to tag when it is written: Python
3.10 dropped; `@cachedmethod` with `@classmethod`, without a mutable `__dict__` or on a
descriptor assigned after class creation (Code #13) raises `TypeError`;
`@cached(cache=None)` raises `TypeError`; `info=True` requires `len()` on custom
caches; `CacheInfo` is public; `@cached` wrappers are callable objects rather than
functions. Non-breaking: `__repr__` on `@cached` and `@cachedmethod` wrappers; key
functions return plain tuples ("Various performance improvements.").

## Keys & Func Modules

No issues found. The key functions return plain tuples, and `methodkey` /
`typedmethodkey` repeat the `hashkey` / `typedkey` bodies on purpose (a delegating call
cost more); `_HashedTuple` stays as the `_kwmark` sentinel and keeps 7.x pickles
loadable (verified above). Every `func.py` decorator is built on `cached(...,
condition=Condition(), info=True)`, and `_UnboundTTLCache` handles `maxsize=None`.
