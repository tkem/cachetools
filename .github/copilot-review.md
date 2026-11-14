# Code Review — cachetools 7.3.2

**Date:** 2026-11-14
**Reviewed:** `dev/v7.3.x` at `804cbe3` ("Release v7.3.2", `__version__` 7.3.2,
changelog dated 2026-11-14).

**CI status:** All `tox` environments pass locally on CPython 3.14.4: `py` (443
passed), `docs`, `doctest`, `pyright` (0 errors, 0 warnings), `ruff`, `ruff-format`;
`py` also passes on 3.10.20, 3.11.15 and 3.12.13. GitHub Actions run for `804cbe3`
succeeded on all 11 jobs (CPython 3.10–3.15, 3.13t–3.15t, PyPy 3.10 and 3.11).

**Coverage:** 100% except two lines that only run on Python < 3.13, where
`@classmethod` over `@cachedmethod` calls `__get__` with the class as `obj`
(`_cachedmethod.py:22`, `_descriptor.py:79`); on < 3.13 the `_ClassMethodDescriptor`
`__call__`/`cache_clear` bodies and `classmethod_wrapper` are uncovered instead. The
CI matrix covers both.

**Verified:** shallow copies by a random trace of a used cache against its copy (all
seven classes, with and without `getsizeof`, 300 seeds each) with identical results,
order and sizes and no effect of one on the other, by the #473 reproducers and by 19
one-line breakages of the `__copy__` code, all of which fail the suite; every other
operation by a 210 000-step trace against v7.3.1 with identical results and state; an
`LFUCache` with 600 use counts deep-copied and pickled (protocols 0, 2 and 5, C and
pure-Python pickler) evicting like its source. Copy probes ran on 3.10, 3.11, 3.12 and
3.14, the v7.3.1 trace on 3.10 and 3.14; performance by the benchmarks below.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place desyncs `currsize`. Documented footgun. |
| 2 | Low | `_cachedmethod.py` `_condition_info` / `_condition` | Pending sets are per instance, so two instances sharing one cache and condition do not coordinate pending keys. |
| 3 | Low | `Cache` (inherited `items()` / `values()`) | Both views read through `__getitem__`, so iterating them (or `dict(cache)`) counts as a use of every item: `LRUCache` and `TLRUCache` fall back to insertion order and every `LFUCache` count increments. `keys()`, `in` and `repr()` do not. Undocumented. |
| 4 | Low | `Cache.__copy__` and its seven overrides (#473) | A shallow copy shares every instance attribute and replaces only the cache classes' own state. It takes attributes from `__dict__` only, so those a subclass declares in `__slots__` are missing from the copy (`AttributeError` on first use), where `copy.deepcopy()` keeps them. A subclass that tracks keys in an attribute of its own shares that with the copy until it extends `__copy__` (*Maintainer Decisions*); undocumented (Docs #1). |
| 5 | Info | `_MethodDescriptor.__get__` (class-access path) | `Cls.method(obj, ...)` builds and discards a `Wrapper` per call before `obj.__dict__.setdefault()` returns the stored one: 2532 ns per hit against 559 through the instance and 1108 via `super()`, which reuses its stored wrapper (*Maintainer Decisions*). |
| 6 | Info | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key deadlocks (`wait()` on its own pending marker). |
| 7 | Info | `_MethodDescriptor.__get_unbound` | Lazy creation of the `_Unbound` object is unsynchronized; concurrent first class accesses may briefly see distinct, equivalent objects. Benign. |
| 8 | Info | `_descriptor.py` `_Unbound.__call__` | By design, autospec'd instances accept any arguments, so autospec no longer checks arity. A wrong receiver (`Cls.method(1)`) raises `TypeError` "No `__dict__` attribute on 'int' instance" with `info=True`; with `info=False` it only warns (`DeprecationWarning`) and then fails inside `cache(self)`. |
| 9 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a present-but-expired key removes it and raises `KeyError`, consistent with `key in cache`; `pop(key, default)` and `del` differ around the expiry instant. Intentional. |
| 10 | Info | `cachedmethod` `make_info` | A non-mapping `cache(self)` is only reported, as `TypeError`, from `cache_info()`. Acceptable. |
| 11 | Info | `_cachedmethod.py` `Wrapper.__call__` | Stacked `@cachedmethod` calls the inner *descriptor*: `TypeError` with `info=True`, a misleading `@classmethod` `DeprecationWarning` plus a throwaway wrapper with `info=False`. Unsupported (*Maintainer Decisions*). |
| 12 | Info | `_WrapperBase.__reduce__` | Unpickling and deep-copying rebuild wrappers through their descriptor, so `info=True` counters reset (asserted by tests). Acceptable. |
| 13 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | `_lookup` must stay importable and resolves through the owner's *current* class dict, so a pickle loaded while `Cls.method` is patched yields the patched attribute. A descriptor without `__set_name__` (deprecated pre-3.13 `@classmethod`) pickles but fails to load with `AttributeError`. |
| 14 | Info | `LFUCache._Link.keys` | An `LFUCache` pickled with 7.2.8 or earlier loads, then raises `TypeError` on first use, since its links still hold a `set`. Pickling caches is unsupported (*Maintainer Decisions*). |
| 15 | Info | `TTLCache.__setstate__` / `RRCache` | `list()` of a deep-copied or unpickled `TTLCache` can differ in order from the original's, as links are rebuilt by expiry time with ties in LRU order; keys and eviction order match, and a shallow copy keeps the order. A deep-copied or unpickled `RRCache` with the default `choice` gets a clone of the `random` module's generator (`random.choice` is a bound method) and replays its sequence. |

No implementation bugs found beyond the items above.

## Performance

Hot-path costs at v7.3.2, measured on 2026-11-14 on CPython 3.14.4, ns per
operation, best of 7 (`timeit`, one pinned core; run-to-run noise about ±5%). Caches
hold 100 items for reads and updates and are full (`maxsize=100`) for evicting
inserts, with new keys from `itertools.count()` (19 ns included); decorators use
`LRUCache(1024)` and a one-argument function.

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 13 | 26 | 64 | 138 | 175 | 176 |
| contains | 13 | 35 | 35 | 35 | 131 | 132 |
| get miss (`KeyError`) | 65 | 255 | 325 | 325 | 419 | 419 |
| set, existing key | 13 | 64 | 108 | 168 | 403 | 638 |
| set, evicting | 111 | 323 | 503 | 469 | 1093 | 1558 |

`FIFOCache` evicting 405, `RRCache` 538; with a custom `getsizeof` (size-dict path)
`Cache` updates cost 127. The `dict` evicting row includes `del d[next(iter(d))]`.

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 249 | 1418 |
| `@cached(lock=Lock())` | 319 | 1657 |
| `@cached(condition=Condition())` | 412 | 2126 |
| `@cached(info=True)` | 269 | 1445 |
| `@cachedmethod` | 559 | 1896 |
| `@cachedmethod(condition=...)` | 767 | 2695 |
| `cachetools.func.lru_cache` | 436 | 2145 |
| `functools.lru_cache` (C) | 27 | 80 |

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1093 ns against 503 for `LRUCache` (TLRU 1558): `expire()` runs twice, the `_Timer` is entered twice and `del self[key]` re-checks expiry; the `_Link.insert()` call new in `TTLCache.__setitem__` adds about 20 ns (measured on `develop`, same code). Skipping `popitem()`'s own `expire()` and bypassing `__delitem__` would be faster (unmeasured here), but a direct `popitem()` could then return an expired item and subclass `__delitem__` overrides would no longer see evictions. |
| 2 | Info | `_cachedmethod.py` `Wrapper.__call__` | A `@cachedmethod` hit costs 559 ns against 249 for `@cached`: `__call__` dispatch, the module-level `wrapper()` hop, the `cache(self)` lambda and `partial(methodkey, obj)`. First access per instance 2306 ns including object creation (55); class call 2532 (Code #5). Inherent to the per-instance design. |
| 3 | Info | `LFUCache.__touch` | A hit that moves its key to the next use-count link costs 223 ns (cycling over 100 keys) against 138 for a key alone in its link, the table's figure: one `OrderedDict` insert and delete per move. Evicting inserts stay flat with size, 528 ns at `maxsize` 10 000 and 523 at 100 000. |
| 4 | Info | `cachetools.func` | `lru_cache` hit 436 ns against 27 for `functools.lru_cache`, 16x, since every `func` decorator uses `condition=Condition()` and `info=True`. By design. |
| 5 | Info | `keys.typedkey` | 440 ns against 94 for `hashkey(1, 2, 3)`: two `_HashedTuple` allocations and a generator; `tuple(map(type, args))` and a single concatenation would trim it. Rarely hot. |

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
| 5 | Info | `test_lfu_copy_use_counts` pickles with the default protocol and the C pickler only, which on 3.14.4 also passes without the #474 fix (checked on the 8.0 line, same `LFUCache` code), so there only its deep-copy arm guards it; `pickle._Pickler` fails without the fix. No test copies a subclass with `__slots__` (Code #4). |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | Shallow copies of caches are not mentioned: that `copy.copy()` shares all attributes, keys and values with the original but none of the cache's own state, and that a subclass with mutable state of its own must extend `__copy__` (Code #4). Only the `@cachedmethod` note from #466 speaks of shallow copies. |
| 2 | Low | The `@cachedmethod` docs do not mention that class access yields a callable without `cache_clear()`/`cache_info()` taking the receiver positionally or by name, or that pickling resets `cache_info()` counters (Code #12). |
| 3 | Info | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods; a one-line caveat that cache and counters are then shared across instances would help. |

The `LFUCache` paragraph and its `versionchanged:: 7.3` note match the implementation;
iteration counting as use (Code #3) would fit next to it.

## `CHANGELOG.rst`

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | The `self` keyword fix (#451) appears in no section. Instance calls were fixed in 7.2.8, `@classmethod` use on Python ≥ 3.13 in 7.3.0 (commit "Fix #451"); both failed with `TypeError` in every release back to at least 5.5.0, so no "broken since" tag applies. Suggested for 7.3.0: "Fix ``@cachedmethod`` for methods taking a ``self`` keyword argument." |
| 2 | Info | The `LFUCache` entry names the implementation (``OrderedDict``), not the documented change: ties now discard the least recently used item. Which item leaves on a tie changes for existing code, so "(potentially breaking change)" may apply. |

Otherwise fine: the 7.3.2 section is dated 2026-11-14, its single entry matches the
release's fix commit and the style rules ("broken since v7.3.1", the release whose
`__copy__` deep-copied attributes), and two blank lines precede the previous section.

## Keys & Func Modules

No issues found. `_HashedTuple` uses the C tuple hash (rationale kept in a comment),
every `func.py` decorator is built on `cached(..., condition=Condition(), info=True)`,
and `_UnboundTTLCache` handles `maxsize=None`.
