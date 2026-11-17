# Code Review — cachetools 8.0.1

**Date:** 2026-11-17, `__version__` 8.0.1 (changelog dated 2026-11-17, not tagged yet)
**Reviewed:** `develop` at `0828f54` "Release v8.0.1.", plus this review commit.

**CI status:** `tox -p auto` passes on CPython 3.14.4 (465 tests, pyright 0 errors, 0
warnings), `py` on 3.11.15, 3.12.13 and PyPy 7.3.21; 3.13 not run here. Actions is green
for `0828f54` (3.11–3.15, 3.13t–3.15t, PyPy 3.11).
**Coverage:** 100% on 3.11, 3.12 and PyPy; 3.14 lacks `_descriptor.py:36`.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` via `@cachedmethod` | Pending sets are per wrapper, so two instances sharing one cache and condition do not coordinate pending keys. |
| 2 | Low | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key hangs on its own pending marker, where the `lock` variants raise `RecursionError`. Suggested fix (unmeasured): record the owning thread per pending key and let it call the function uncached. |
| 3 | Low | `Cache` (inherited `items()` / `values()`) | Iterating either view (or `dict(cache)`) reads through `__getitem__` and counts as a use of every item: `LRUCache`, `TTLCache` and `TLRUCache` fall back to insertion order, every `LFUCache` count increments. Undocumented; `keys()`, `in` and `repr()` are unaffected. |
| 4 | Low | `_TimedCache._Timer.__getattr__` | Known issue: `copy.deepcopy()` of a `TTLCache` or `TLRUCache` whose timer object defines `__deepcopy__` yields a copy holding the bare timer, whose first insert raises `TypeError`. Suggested fix (tested, not applied): a `_Timer.__deepcopy__` that wraps a deep copy of the timer. |
| 5 | Low | `TTLCache.__iter__` / `TLRUCache.__iter__` | Modifying a timed cache while iterating over it is not detected, where the other classes raise `RuntimeError` like `dict`. Updating an existing key in the loop, which is safe for the others, ends a `TTLCache` iteration after the first key and makes a `TLRUCache` yield keys repeatedly; inserting new keys keeps a `TTLCache` loop going, and after `clear()` it still yields the removed keys. Suggested fix (tried on 3.14.4, not applied): iterate over a snapshot of the keys and skip those no longer present. |
| 6 | Info | `Cache.__copy__`; `LFUCache.__setstate__` / `TTLCache.__setstate__` | Unsupported by decision (*Maintainer Decisions*): once a subclass sets a `__slots__` attribute, a shallow copy lacks it (`AttributeError` on use), and deep-copying or pickling such an `LFUCache` or `TTLCache` subclass raises `ValueError`. Empty or unset slots are unaffected; the subclass provides its own `__copy__` and `__setstate__`. `__slots__` gains nothing there: every `Cache` instance has a `__dict__` anyway, so a slot saves no memory and does not restrict attributes. |
| 7 | Info | `_cached.py` `_WrapperBase.__reduce__` | Wrappers pickle by `__qualname__`: pickling raises `pickle.PicklingError` once that name is rebound or deleted, and `AttributeError` for a callable without `__qualname__` (e.g. a `functools.partial`). |
| 8 | Info | `TTLCache.__setstate__` / `RRCache` | A deep-copied or unpickled `TTLCache` can iterate in a different order (ties in expiry time), so evictions can differ once `items()` or `values()` was iterated (Code #3). A deep-copied or unpickled `RRCache` with the default `choice` replays a clone of the `random` module's generator, and its pickle carries about 4 kB of generator state. An `LFUCache` pickled here does not load in v8.0.0 (`_Link` has no `next`); v8.0.0 pickles load here. |
| 9 | Info | `TTLCache.__iter__` / `TLRUCache.__iter__` (#469) | Both yield inside `with self.timer`, so while an iterator is suspended the whole cache sees the frozen time: expired items stay visible and an item set meanwhile takes its expiry from it. Yielding outside the freeze could make `for key in cache: cache[key]` raise `KeyError`, a potentially breaking change; undocumented. |

## Performance

CPython 3.14.4, ns per operation, best of 7 (`timeit`, one pinned core, about ±5%),
measured 2026-11-15 on bare metal with `.github/copilot-bench.py`. Caches hold 100
items (`maxsize=100` for evicting inserts, new keys from `itertools.count()`, 20 ns
included); decorators use `LRUCache(1024)`, method calls include the attribute lookup
(`obj.method(1)`).

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 13 | 27 | 65 | 143 | 180 | 184 |
| contains | 13 | 36 | 36 | 36 | 135 | 137 |
| get miss (`KeyError`) | 66 | 257 | 339 | 341 | 433 | 440 |
| set, existing key | 14 | 66 | 107 | 173 | 418 | 662 |
| set, evicting | 111 | 336 | 396 | 492 | 1152 | 1674 |

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 247 | 1337 |
| `@cached(lock=Lock())` | 326 | 1599 |
| `@cached(condition=Condition())` | 426 | 2057 |
| `@cached(info=True)` | 292 | 1401 |
| `@cached` on a method (bound) | 365 | |
| `@cachedmethod` | 331 | 1472 |
| `@cachedmethod(condition=...)` | 637 | 2337 |
| `@cachedmethod(info=True)` | 375 | 1537 |
| `cachetools.func.lru_cache` | 476 | 2131 |
| `functools.lru_cache` (C) | 28 | 82 |

`FIFOCache` evicting 413, `RRCache` 556, `Cache` update with `getsizeof` 132;
`hashkey(1, 2, 3)` 46, `hashkey(1, 2, a=3)` 212, `typedkey(1, 2, 3)` 155. `copy.copy()`
of 1000 items, in µs: `dict` 2.4, `Cache` 2.8, `FIFOCache` 36, `LRUCache` 36, `LFUCache`
80, `RRCache` 7, `TTLCache` 248, `TLRUCache` 246.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Info | `_cached.py` `_WrapperBase.__get__` | A hit through a method costs 365 ns against 247 for a direct call: each attribute access runs the Python-level `__get__` and builds a `types.MethodType`. |
| 2 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1152 ns against 396 for `LRUCache` (TLRU 1674): `expire()` runs twice, the `_Timer` is entered twice (three times in `TLRUCache`) and `del self[key]` re-checks expiry. Skipping these would let a direct `popitem()` return an expired item or hide evictions from `__delitem__` overrides. |
| 3 | Info | `_cachedmethod.py` `_WrapperBase` properties | A `@cachedmethod` hit costs 331 ns against 247 for `@cached`: the user's `cache(self)` is called on every call and the key goes through `functools.partial`. First call on a new instance 1967 ns, class call 2136. |
| 4 | Info | `LFUCache.__touch` | A hit that moves its key to the next use-count link costs 232 ns against 143 for a key alone in its link. Evicting inserts stay flat with size: 543 ns at `maxsize` 10 000, 541 at 100 000. |

## Type Stubs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` takes the receiver positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` ("Expected 1 more positional argument"). |
| 2 | Info | `@classmethod` over `@cached` or `func.*_cache` type-checks falsely: calls through the class or an instance report "Argument missing for parameter" (pyright), though they work at runtime. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | No test modifies a timed cache while iterating over it (Code #5); the mixin could assert for every class that updating existing keys in a loop visits each key once. |
| 2 | Info | Of the decorators that the new `@cachedmethod` error message names, only an outer function decorator is tested (`test_outer_decorator`), not `@staticmethod` or `@property`. |
| 3 | Info | `test_self_keyword` (#451) covers the default `@cached` and `@cachedmethod` wrappers and the class call only, not the lock, condition and `info` variants. |
| 4 | Info | `__repr__` on timed caches is never asserted to expire on its own, and `currsize` only indirectly through `cache_info()`. |
| 5 | Info | `NoneMethodTest.test_none_info` asserts only that `cache_info()` raises `TypeError` when `cache(self)` returns `None`; that the call itself fails with `TypeError` is unasserted. |
| 6 | Info | `test_lfu_copy_use_counts` pickles with the default protocol and the C pickler only, which without the #474 fix fails on 3.11 only (from 247 use counts), so elsewhere only its deep-copy arm guards that fix. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods, where cache and counters are shared across instances. |
| 2 | Low | The `cached` section still speaks of a "memoizing wrapper function", while the result is a callable object, and describes `cache_lock` as the `lock` parameter, though with `condition` alone it is the condition object. |
| 3 | Low | New in 8.0.1 and undocumented: what a shallow copy of a cache shares (keys, values and attributes) and that a subclass with mutable state of its own must extend `__copy__`; that `@cached` wrappers copy and deep-copy as themselves; and that `@cachedmethod` must be the outermost decorator, where the docs name only `classmethod`. |
| 4 | Info | The `README.rst` example is outside the Sphinx doctest run, and its PyOWM and `get_pep` snippets have no doctested counterpart; it runs on this tree with `urlopen` and `pyowm` stubbed (not rerun in this review). |
