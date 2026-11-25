# Code Review — cachetools 8.0.3

**Date:** 2026-11-25, `__version__` 8.0.3 (changelog dated 2026-11-25, not tagged yet)
**Reviewed:** `develop` at `8bd4a69` "Release v8.0.3.", plus this review commit.

**CI status:** `tox -p auto` passes on CPython 3.14.4 (480 tests, pyright 0 errors, 0
warnings), `py` on 3.11.15, 3.12.13 and PyPy 7.3.21; 3.13 not run here. Actions is green
for `8bd4a69` (3.11–3.15, 3.13t–3.15t, PyPy 3.11).
**Coverage:** 100% on 3.11, 3.12 and PyPy; 3.14 lacks `_descriptor.py:36`.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Info | `Cache` (inherited `items()` / `values()`) | Iterating either view (or `dict(cache)`, or comparing caches with `==`) reads through `__getitem__` and counts as a use of every item; `keys()`, `in` and `repr()` do not. In practice only `LRUCache` is affected (it then evicts in insertion order, as documented): `TTLCache` and `TLRUCache` only while they evict by least recent use, `LFUCache` only in ties, the other classes not at all; reading without counting as a use would be a potentially breaking change. |
| 2 | Info | `_decorator.py:72, 191` via `@cachedmethod` | Pending keys are tracked per instance wrapper, not per cache or condition, so sharing both does not prevent duplicate work. An event-controlled probe with deliberately colliding keys and different results returned both values and left the last writer's result cached. |
| 3 | Info | `TTLCache.__iter__` / `TLRUCache.__iter__` (#469) | Both yield inside `with self.timer`, so while an iterator is suspended the whole cache sees the frozen time: expired items stay visible and an item set meanwhile takes its expiry from it. Yielding outside the freeze could make `for key in cache: cache[key]` raise `KeyError`, a potentially breaking change; undocumented. |

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
| `@cached(condition=Condition())` | 425 | 2076 |
| `@cached(info=True)` | 292 | 1401 |
| `@cached` on a method (bound) | 365 | |
| `@cachedmethod` | 331 | 1472 |
| `@cachedmethod(condition=...)` | 616 | 2392 |
| `@cachedmethod(info=True)` | 375 | 1537 |
| `cachetools.func.lru_cache` | 408 | 1873 |
| `functools.lru_cache` (C) | 28 | 82 |

`FIFOCache` evicting 413, `RRCache` 556, `Cache` update with `getsizeof` 132;
`hashkey(1, 2, 3)` 46, `hashkey(1, 2, a=3)` 212, `typedkey(1, 2, 3)` 155. `copy.copy()`
of 1000 items, in µs: `dict` 2.4, `Cache` 2.8, `FIFOCache` 36, `LRUCache` 36, `LFUCache`
80, `RRCache` 7, `TTLCache` 248, `TLRUCache` 246. `list()` of 1000 items (2026-11-18):
3.7 for the untimed cache classes, `TTLCache` 195, `TLRUCache` 197. The condition and
`func.lru_cache` rows and the class-call figure are from 2026-11-25, after the 8.0.3
fixes (best of three runs; the other decorator rows agree within 4%). Timed-cache hit
and contains figures vary by 20 ns between processes.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Info | `_cached.py` `_WrapperBase.__get__` | A hit through a method costs 365 ns against 247 for a direct call: each attribute access runs the Python-level `__get__` and builds a `types.MethodType`. |
| 2 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1152 ns against 396 for `LRUCache` (TLRU 1674): `expire()` runs twice, the `_Timer` is entered twice (three times in `TLRUCache`) and `del self[key]` re-checks expiry. Skipping these would let a direct `popitem()` return an expired item or hide evictions from `__delitem__` overrides. |
| 3 | Info | `_cachedmethod.py` `_WrapperBase` properties | A `@cachedmethod` hit costs 331 ns against 247 for `@cached`: the user's `cache(self)` is called on every call and the key goes through `functools.partial`. First call on a new instance 1967 ns, class call 2249. |
| 4 | Info | `LFUCache.__touch` | A hit that moves its key to the next use-count link costs 232 ns against 143 for a key alone in its link. Evicting inserts stay flat with size: 543 ns at `maxsize` 10 000, 541 at 100 000. |
| 5 | Info | `TTLCache.__iter__` / `TLRUCache.__iter__` | Listing a timed cache costs about 195 ns per key against 4 for the other classes: each key from the snapshot is looked up again and enters the timer. |
| 6 | Info | condition variants of `@cached` / `@cachedmethod` | With `condition` alone, every `with` on the lock runs the Python-level `Condition.__enter__()` and `__exit__()`, about 50 ns each time (once per hit, three times per miss). Passing `lock=` and `condition=Condition(lock)` avoids it, as `func.py` does since #485 and the `cached` docs now note. |

## Type Stubs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` takes the receiver positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` ("Expected 1 more positional argument"). |
| 2 | Info | `@classmethod` over `@cached` or `func.*_cache` type-checks falsely: calls through the class or an instance report "Argument missing for parameter" (pyright), though they work at runtime. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | Of the decorators that the new `@cachedmethod` error message names, only an outer function decorator is tested (`test_outer_decorator`), not `@staticmethod` or `@property`. |
| 2 | Info | `test_self_keyword` (#451) covers the default `@cached` and `@cachedmethod` wrappers and the class call only, not the lock, condition and `info` variants. |
| 3 | Info | `__repr__` on timed caches is never asserted to expire on its own, and `currsize` only indirectly through `cache_info()`. |
| 4 | Info | `NoneMethodTest.test_none_info` asserts only that `cache_info()` raises `TypeError` when `cache(self)` returns `None`; that the call itself fails with `TypeError` is unasserted. |
| 5 | Info | `test_lfu_copy_use_counts` pickles with the default protocol and the C pickler only, which without the #474 fix fails on 3.11 only (from 247 use counts), so elsewhere only its deep-copy arm guards that fix. |
| 6 | Info | No test covers #485: `test_func.py` never looks at `cache_lock` or `cache_condition`, so passing the condition alone again would only show in the benchmark. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods, where cache and counters are shared across instances. |
| 2 | Low | The `cached` and `cachedmethod` sections describe `cache_lock` as the `lock` parameter, though with `condition` alone it is the condition object. The `cached` section also calls the wrapper a function rather than a callable object. |
| 3 | Low | New in 8.0.1 and undocumented: what a shallow copy of a cache shares (keys, values and attributes) and that a subclass with mutable state of its own must extend `__copy__`; that `@cached` wrappers copy and deep-copy as themselves; and that `@cachedmethod` must be the outermost decorator, where the docs name only `classmethod`. |
| 4 | Low | Since 8.0.2, `TTLCache` and `TLRUCache` snapshot keys when iteration starts: brand-new keys are skipped, missing or expired keys are filtered, and a deleted then reinserted key can still be visited in its original position. Document this and the suspended-iterator behavior (Code #3). |
| 5 | Info | The `README.rst` PyOWM and `get_pep` snippets are outside the Sphinx doctest run and were not rerun here. |
