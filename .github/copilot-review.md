# Code Review — cachetools 7.3.0

**Date:** 2026-11-05
**Reviewed:** `dev/v7.3.0` at `50c3e71` ("Release v7.3.0", `__version__` 7.3.0,
changelog dated 2026-11-05).

**CI status:** All `tox` environments pass locally on CPython 3.14.4: `py` (397
passed), `docs`, `doctest`, `pyright` (0 errors), `ruff`, `ruff-format`. GitHub
Actions run for `50c3e71` succeeded on all 11 jobs (CPython 3.10–3.15, 3.13t–3.15t,
PyPy 3.10 and 3.11).

**Coverage:** 100% except two lines that only run on Python < 3.13, where
`@classmethod` over `@cachedmethod` calls `__get__` with the class as `obj`
(`_cachedmethod.py:22`, `_descriptor.py:79`); on < 3.13 the `_ClassMethodDescriptor`
`__call__`/`cache_clear` bodies and `classmethod_wrapper` are uncovered instead. The
CI matrix covers both.

**Verified:** `LFUCache` against a reference model (lowest use count, then least
recently used) over 36000 random operations with default and `v % 4` `getsizeof` and
`maxsize` 0 to 10, with no mismatch; the other six cache classes by the same trace
against v7.2.8, with identical results, exceptions, keys, `currsize` and `len` at
every step; the `self` keyword fix by probes on CPython 3.14 and 3.10; the
`setdefault` stubs by a pyright probe; performance by the benchmarks below.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place desyncs `currsize`. Documented footgun. |
| 2 | Low | `_cachedmethod.py` `_condition_info` / `_condition` | Pending sets are per instance, so two instances sharing one cache and condition do not coordinate pending keys. |
| 3 | Low | `Cache` (inherited `items()` / `values()`) | Both views read through `__getitem__`, so iterating them (or `dict(cache)`) counts as a use of every item: `LRUCache` and `TLRUCache` fall back to insertion order and every `LFUCache` count increments. `keys()`, `in` and `repr()` do not. Undocumented. |
| 4 | Info | `_MethodDescriptor.__get__` (class-access path) | `Cls.method(obj, ...)` builds and discards a `Wrapper` per call before `obj.__dict__.setdefault()` returns the stored one: 2456 ns per hit against 549 through the instance and 1095 via `super()`, which reuses its stored wrapper (*Maintainer Decisions*). |
| 5 | Info | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key deadlocks (`wait()` on its own pending marker). |
| 6 | Info | `_MethodDescriptor.__get_unbound` | Lazy creation of the `_Unbound` object is unsynchronized; concurrent first class accesses may briefly see distinct, equivalent objects. Benign. |
| 7 | Info | `_descriptor.py` `_Unbound.__call__` | By design, autospec'd instances accept any arguments, so autospec no longer checks arity. A wrong receiver (`Cls.method(1)`) raises `TypeError` "No `__dict__` attribute on 'int' instance" with `info=True`; with `info=False` it only warns (`DeprecationWarning`) and then fails inside `cache(self)`. |
| 8 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a present-but-expired key removes it and raises `KeyError`, consistent with `key in cache`; `pop(key, default)` and `del` differ around the expiry instant. Intentional. |
| 9 | Info | `cachedmethod` `make_info` | A non-mapping `cache(self)` is only reported, as `TypeError`, from `cache_info()`. Acceptable. |
| 10 | Info | `_cachedmethod.py` `Wrapper.__call__` | Stacked `@cachedmethod` calls the inner *descriptor*: `TypeError` with `info=True`, a misleading `@classmethod` `DeprecationWarning` plus a throwaway wrapper with `info=False`. Unsupported (*Maintainer Decisions*). |
| 11 | Info | `_WrapperBase.__reduce__` | Unpickling and deep-copying rebuild wrappers through their descriptor, so `info=True` counters reset (asserted by tests). Acceptable. |
| 12 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | `_lookup` must stay importable and resolves through the owner's *current* class dict, so a pickle loaded while `Cls.method` is patched yields the patched attribute. A descriptor without `__set_name__` (deprecated pre-3.13 `@classmethod`) pickles but fails to load with `AttributeError`. |
| 13 | Info | `LFUCache._Link.keys` | An `LFUCache` pickled with 7.2.8 or earlier loads, then raises `TypeError` on first use, since its links still hold a `set`. Pickling caches is unsupported (*Maintainer Decisions*). |

No implementation bugs found beyond the items above.

## Performance

Hot-path costs at v7.3.0, measured on 2026-11-05 on CPython 3.14.4, ns per
operation, best of 7 (`timeit`, one pinned core; run-to-run noise about ±5%). Caches
hold 100 items for reads and updates and are full (`maxsize=100`) for evicting
inserts, with new keys from `itertools.count()` (18 ns included); decorators use
`LRUCache(1024)` and a one-argument function.

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 12 | 26 | 62 | 134 | 171 | 173 |
| contains | 13 | 37 | 35 | 37 | 130 | 129 |
| get miss (`KeyError`) | 64 | 251 | 321 | 320 | 409 | 411 |
| set, existing key | 13 | 63 | 105 | 164 | 384 | 615 |
| set, evicting | 109 | 324 | 487 | 464 | 1058 | 1592 |

`FIFOCache` evicting 383, `RRCache` 531; with a custom `getsizeof` (size-dict path)
`Cache` updates cost 125. The `dict` evicting row includes `del d[next(iter(d))]`.

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 248 | 1405 |
| `@cached(lock=Lock())` | 310 | 1647 |
| `@cached(condition=Condition())` | 405 | 2073 |
| `@cached(info=True)` | 265 | 1460 |
| `@cachedmethod` | 518 | 1923 |
| `@cachedmethod(condition=...)` | 733 | 2664 |
| `cachetools.func.lru_cache` | 417 | 2113 |
| `functools.lru_cache` (C) | 27 | 81 |

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1058 ns against 487 for `LRUCache` (TLRU 1592): `expire()` runs twice, the `_Timer` is entered twice and `del self[key]` re-checks expiry. Skipping `popitem()`'s own `expire()` and bypassing `__delitem__` would save about 13%, but a direct `popitem()` could then return an expired item and subclass `__delitem__` overrides would no longer see evictions. |
| 2 | Info | `_cachedmethod.py` `Wrapper.__call__` | A `@cachedmethod` hit costs 518 ns against 248 for `@cached`: `__call__` dispatch, the module-level `wrapper()` hop, the `cache(self)` lambda and `partial(methodkey, obj)`. First access per instance 2381 ns including object creation (`Wrapper` construction alone 787); class call 2456 (Code #4). Inherent to the per-instance design. |
| 3 | Info | `LFUCache.__touch` | A hit that moves its key to the next use-count link costs 229 ns (cycling over 100 keys) against 134 for a key alone in its link, the table's figure: one `OrderedDict` insert and delete per move. Evicting inserts stay flat with size, 537 ns at `maxsize` 10 000 and 568 at 100 000. |
| 4 | Info | `cachetools.func` | `lru_cache` hit 417 ns against 27 for `functools.lru_cache`, 15x, since every `func` decorator uses `condition=Condition()` and `info=True`. By design. |
| 5 | Info | `keys.typedkey` | 431 ns against 94 for `hashkey(1, 2, 3)`: two `_HashedTuple` allocations and a generator; `tuple(map(type, args))` and a single concatenation would trim it. Rarely hot. |

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` keeps a receiver-less overload for deprecated `@classmethod` calls, so a missing instance on a regular `Cls.method(arg)` is not reported; drop it with `@classmethod` support. The receiver is positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` (`test_class_call_keyword_receiver`). |
| 2 | Info | `@cached(info=False)` wrappers have `cache_info = None` at runtime, but `_cached_wrapper` does not declare it. `_cached_wrapper.cache` is `MutableMapping \| None` for the deprecated `cache=None`; tighten both when that support is removed. |
| 3 | Info | `@classmethod` over `@cached`/`func.*_cache` reports a false "Argument missing" error; pyright does not bind through the wrapper's `__get__`. Rare. |
| 4 | Info | `_cached_wrapper_info.__get__` needs `# pyright: ignore[reportIncompatibleMethodOverride]`; the override is sound. |
| 5 | Info | `Cache.setdefault` now mirrors typeshed's `dict` overloads: `cache.setdefault(key)` without a default is an error unless the value type is `X \| None`, which also rejects it for `Cache[K, object]`. New errors in user code point at calls that store `None`. |

Otherwise fine: `ParamSpec`/`Concatenate[Any, _P]` preserve signatures, overload order
is `Literal[False]` first, `func.pyi` covers both `@lru_cache` and `@lru_cache(...)`.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | The `self` keyword fix (#451) is tested through the key functions and deprecated `@classmethod` use on the unlocked variant only. No test calls an instance's cached method with a `self` keyword argument, so the positional-only receiver of the other five `Wrapper.__call__` variants is unguarded. |
| 2 | Low | `UnboundMethodTest` covers class access for the unlocked variants only, not for `lock` or `condition`. |
| 3 | Info | `CacheTestMixin` checks key existence rather than the eviction victim, since it is shared across cache types; policy checks live per cache. No action needed. |
| 4 | Info | `test_func.py` calls decorators through `Callable[..., Any]`; `FIFODecoratorTest.test_method_typed` covers the stubs, enough since all five decorators share one wrapper type. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | The `@cachedmethod` docs do not mention that class access yields a callable without `cache_clear()`/`cache_info()` taking the receiver positionally or by name, or that pickling resets `cache_info()` counters (Code #11). |
| 2 | Info | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods; a one-line caveat that cache and counters are then shared across instances would help. |

The `LFUCache` paragraph and its `versionchanged:: 7.3` note match the implementation;
iteration counting as use (Code #3) would fit next to it.

## `CHANGELOG.rst`

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | The `self` keyword fix (#451) appears in no section. Instance calls were fixed in 7.2.8, `@classmethod` use on Python ≥ 3.13 in 7.3.0 (commit "Fix #451"); both failed with `TypeError` in every release back to at least 5.5.0, so no "broken since" tag applies. Suggested for 7.3.0: "Fix ``@cachedmethod`` for methods taking a ``self`` keyword argument." |
| 2 | Info | The `LFUCache` entry names the implementation (``OrderedDict``), not the documented change: ties now discard the least recently used item. Which item leaves on a tie changes for existing code, so "(potentially breaking change)" may apply. |

Otherwise fine: the 7.3.0 section is dated 2026-11-05, its four entries match the
release's commits and the style rules, and two blank lines precede the previous section.

## Keys & Func Modules

No issues found. `_HashedTuple` uses the C tuple hash (rationale kept in a comment),
every `func.py` decorator is built on `cached(..., condition=Condition(), info=True)`,
and `_UnboundTTLCache` handles `maxsize=None`.
