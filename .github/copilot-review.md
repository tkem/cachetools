# Code Review — cachetools 8.0.0

**Date:** 2026-11-12, `__version__` 8.0.0
**Reviewed:** `develop`, i.e. v8.0.0 (`1ce79ef`) plus "Exclude AGENTS.md from source
distribution.", "Fix #466: Note that shallow copies share cached methods.", "Fix #473:
Add Cache.__copy__() to stop shallow copies sharing internal state.", "Fix #474: Fix
deep-copying and pickling LFUCache with many use counts." and this review commit.

**CI status:** All `tox` environments pass locally on CPython 3.14.4 (`py`: 445 passed;
pyright 0 errors, 0 warnings); `py` also passes on 3.11.15 and 3.12.13. GitHub Actions
has not run for this tree: the last green `develop` run (`2dd5815`) lacks the shared
callables in `__copy__`, unverified on 3.13, 3.15, the free-threaded builds and PyPy.
**Coverage:** 100% on 3.11 and 3.12; on 3.14 only `_descriptor.py:36` (pre-3.13 path).

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__copy__(*shared)` | Shares keys, values, `getsizeof`, `choice`, `timer` and `ttu` with the original and deep-copies everything else, subclass attributes included: a subclass holding a lock raises `TypeError: cannot pickle '_thread.lock' object` unless it overrides `__copy__` to pass the lock as `shared`. That hook is untested and absent from the stubs, and `docs/index.rst` does not mention shallow copies of caches at all. `_TimedCache.__copy__` takes the timer function from `_Timer.__reduce__()[1]`, so it depends on that pickle format. |
| 2 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place desyncs `currsize`. Documented footgun. |
| 3 | Low | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` via `@cachedmethod` | Pending sets are per wrapper, so two instances sharing one cache and condition do not coordinate pending keys. |
| 4 | Low | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key hangs on its own pending marker, where the `lock` variants raise `RecursionError`. Suggested fix: make the pending set a dict of key to `threading.get_ident()` and let the owning thread call the function uncached instead of waiting; the hit path stays unchanged, a miss pays one `get_ident()` call (unmeasured). |
| 5 | Low | `Cache` (inherited `items()` / `values()`) | Both views read through `__getitem__`, so iterating them (or `dict(cache)`) counts as a use of every item: `LRUCache` and `TLRUCache` fall back to insertion order and every `LFUCache` count increments. `keys()`, `in` and `repr()` do not. Undocumented. Suggested fix: document it in the `Cache` section, or in a major release override `items()` and `values()` with views that read via `Cache.__getitem__` for each key of `iter(self)`, a potentially breaking change since subclass `__getitem__` overrides would no longer see iteration (untested). |
| 6 | Info | `_cached.py` `_WrapperBase.__reduce__` | Pickling by `__qualname__` means a wrapper rebound under another name, or whose original name was deleted, unpickles to the wrong object or fails. A wrapped callable without `__qualname__` (e.g. a `functools.partial`) fails with `AttributeError`, also for `copy.copy()` and `copy.deepcopy()` of the wrapper or of anything holding it. |
| 7 | Info | `_descriptor.py` `_Unbound.__call__` / `_MethodDescriptor.__call__` | By design, autospec'd instances accept any arguments, so autospec no longer checks arity. A wrong receiver (`Cls.method(1)`) raises `TypeError` "No `__dict__` attribute on 'int' instance"; `@staticmethod`, `@property` or any function decorator that calls the descriptor directly reports the "class methods" message. |
| 8 | Info | `_MethodDescriptor.__get__` | A descriptor assigned after class creation (e.g. by a class decorator) never receives `__set_name__`, so any access, `hasattr(Cls, name)` included, raises `TypeError` until `__set_name__` is called by hand. In the 8.0.0 changelog but not in the docs; asserted by `test_decorator_no_set_name`. After `del Cls.method` an already obtained class callable keeps working through the `super()` path (`test_class_call_after_delete`). |
| 9 | Info | `cachedmethod()` / `_cachedmethod.py` `_WrapperBase` properties | Unlike `cached(None)`, a non-callable `cache` such as `cachedmethod(None)` is accepted at decoration and at attribute access, and fails at the first call with `'NoneType' object is not callable`; `cache(self)` returning `None` (unsupported since 7.0) fails at the first call with `'NoneType' object is not subscriptable`. Both are `TypeError`s, only later and less specific. |
| 10 | Info | `Cache.__copy__` / `TTLCache.__setstate__` / `RRCache` | A cache holding itself as a value is returned as is by `copy.copy()` (the memo maps it to itself), and a shallow copy costs more than a `deepcopy()`: 297 against 214 µs for a 1000-item `LRUCache`, 1481 against 1348 for a `TTLCache`, 2 µs for a `dict` (3.14.4). `list()` of a copied or unpickled `TTLCache` can differ in order from the original's, as links are rebuilt by expiry time with ties in LRU order; keys and eviction order match. A deep-copied or unpickled `RRCache` with the default `choice` gets a clone of the `random` module's generator (`random.choice` is a bound method) and replays its sequence. |
| 11 | Info | `TTLCache.__iter__` / `TLRUCache.__iter__` (#469) | Both yield inside `with self.timer`, so while a key, value or item iterator is suspended the whole cache sees the frozen time: `get()`, `in`, `len()` and `repr()` still show expired items, and an item set meanwhile takes its expiry from the frozen time. A result of #29, lasting one iteration step; a dropped iterator is closed at once on CPython (not run on PyPy, where it would last until collected). Yielding outside the freeze would let `for key in cache: cache[key]` and `dict(cache)` raise `KeyError` when the timer advances in between, a potentially breaking change; undocumented. |

## Performance

CPython 3.14.4, ns per operation, best of 7 (`timeit`, one pinned core, about ±5%),
measured 2026-11-11 on bare metal. Caches hold 100 items (`maxsize=100` for evicting
inserts, new keys from `itertools.count()`, 19 ns included); decorators use
`LRUCache(1024)`, method calls include the attribute lookup (`obj.method(1)`).

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 13 | 26 | 66 | 138 | 181 | 179 |
| contains | 13 | 35 | 35 | 36 | 132 | 131 |
| get miss (`KeyError`) | 65 | 255 | 332 | 331 | 429 | 432 |
| set, existing key | 14 | 65 | 110 | 172 | 395 | 629 |
| set, evicting | 125 | 335 | 506 | 480 | 1066 | 1529 |

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 235 | 1418 |
| `@cached(lock=Lock())` | 311 | 1616 |
| `@cached(condition=Condition())` | 410 | 2143 |
| `@cached(info=True)` | 284 | 1445 |
| `@cached` on a method (bound) | 348 | |
| `@cachedmethod` | 317 | 1567 |
| `@cachedmethod(condition=...)` | 605 | 2370 |
| `@cachedmethod(info=True)` | 365 | 1602 |
| `cachetools.func.lru_cache` | 459 | 2229 |
| `functools.lru_cache` (C) | 28 | 81 |

`FIFOCache` evicting 406, `RRCache` 541, `Cache` update with `getsizeof` 130;
`hashkey(1, 2, 3)` 45, `hashkey(1, 2, a=3)` 210, `typedkey(1, 2, 3)` 152.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `LRUCache.__touch` | Catches `KeyError` for every new key, against the hot-path rule in `AGENTS.md`. Testing `key in order` first takes an evicting insert from 508 to 425 ns and an update of an existing key from 110 to 125 (patched copy, same run). |
| 2 | Info | `_cached.py` `_WrapperBase.__get__` | A hit through a method costs 348 ns against 235 for a direct call: each attribute access runs the Python-level `__get__` and builds a `types.MethodType`, where a plain function binds at C level. The price of wrapper objects over closures. |
| 3 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1066 ns against 506 for `LRUCache` (TLRU 1529): `expire()` runs twice, the `_Timer` is entered twice and `del self[key]` re-checks expiry. Skipping `popitem()`'s own `expire()` and bypassing `__delitem__` would save more, but a direct `popitem()` could then return an expired item and subclass `__delitem__` overrides would no longer see evictions. |
| 4 | Info | `_cachedmethod.py` `_WrapperBase` properties | A `@cachedmethod` hit costs 317 ns against 235 for `@cached` (305 through a prebound wrapper): the `cache` (and `cache_lock`) properties call the user's `cache(self)` lambda on every call, and the key goes through `functools.partial`. First call on a new instance 1850 ns including `M(cache)` at 59 (first attribute access alone 1335); class call 2031 (*Maintainer Decisions*). Inherent to the per-instance design. |
| 5 | Info | `LFUCache.__touch` | A hit that moves its key to the next use-count link costs 233 ns (cycling over 100 keys) against 138 for a key alone in its link, the table's figure: one `OrderedDict` insert and delete per move. Evicting inserts stay flat with size, 514 ns at `maxsize` 10 000 and 509 at 100 000. |

## Type Stubs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` takes the receiver positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` (`test_class_call_keyword_receiver`). |
| 2 | Info | `@classmethod` over `@cached`/`func.*_cache` reports a false "Argument missing" error; pyright does not bind through the wrapper's `__get__`. Rare. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | No test asserts what a shallow copy shares (#473): the suite passes just the same with `getsizeof`, `choice`, `timer` and `ttu` objects deep-copied, as they were before the `shared` arguments. `test_copy` never asserts that values are shared either (nor `test_deepcopy` that they are not), and no test copies a cache with subclass attributes or through a subclass passing `shared` objects (Code #1). |
| 2 | Info | The `self` keyword tests (`test_self_keyword`, #451) cover the default `@cached` and `@cachedmethod` wrappers and the class call only; the positional-only receivers of the lock, condition and `info` mixin `__call__` methods remain unguarded. |
| 3 | Info | `__repr__` on timed caches is never asserted to expire on its own, and `currsize` only indirectly, through `cache_info()` in `test_func.py`'s `test_ttl_expire`; the cache tests assert both after `len()`, `clear()` or `__setitem__`. |
| 4 | Info | `NoneMethodTest.test_none_info` asserts only that `cache_info()` raises `TypeError` when `cache(self)` returns `None`; that the call itself fails, and that `cachedmethod(None)` fails at the first call (Code #9), is unasserted. |
| 5 | Info | `test_lfu_copy_use_counts` pickles with the default protocol and the C pickler only, which on 3.14.4 passes without the fix too (6000 use counts; not run on other versions), so there only its copy arms guard #474; `pickle._Pickler` fails without it from 150. Protocols 0 and 2 and the pure-Python pickler pass the same check at 3000 use counts in a probe (3.11, 3.12, 3.14). `TTLCache` and `TLRUCache` are copied only freshly filled, never with expired or reordered items. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods, which now bind explicitly through `__get__`; a one-line caveat that cache and counters are then shared across instances would help. |
| 2 | Low | The `cached` section still speaks of a "memoizing wrapper function" whose "wrapped function is instrumented", while the result is a callable object; and `cache_lock` is described as exposing the `lock` parameter, but with `condition` alone it is the condition object (asserted by tests). |
| 3 | Info | The `README.rst` example is a plain `code-block`, outside the Sphinx doctest run, and its `fib` and PyOWM snippets have no doctested counterpart in `docs/index.rst`; it runs correctly on this tree with `urlopen` and `pyowm` stubbed, but only the by-hand sync rule in `AGENTS.md` guards it. |

## Changelog

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | No entry yet for the commits after v8.0.0: the `LFUCache` deep-copy and pickle fix needs one, "(broken since v7.0.0)", the release that introduced the linked list; `Cache.__copy__` needs another, as shallow copies no longer share state with the original (potentially breaking change); the #466 note and the new tests fall under the documentation and test lines. |
