# Code Review — cachetools 8.0.0

**Date:** 2026-11-10
**Reviewed:** `develop`, i.e. `master` at `1ce79ef` ("Add AGENTS.md, update Copilot
instructions and review.", tagged v8.0.0) plus "Exclude AGENTS.md from source
distribution." and this review commit; `__version__` 8.0.0, changelog dated 2026-11-06.

**CI status:** All `tox` environments pass locally on CPython 3.14.4 (`py`: 416 passed;
pyright 0 errors, 0 warnings); `py` also passes on 3.11.15 and 3.12.13. GitHub Actions
is green for the reviewed code on the full matrix (CPython 3.11–3.15, 3.13t–3.15t,
PyPy 3.11); not run for this review commit, which changes only Markdown files.
**Coverage:** 100% on 3.11 and 3.12; on 3.14 only `_descriptor.py:36`, the pre-3.13
`@classmethod` path.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Medium | `LFUCache._Link` | `copy.deepcopy()` of an `LFUCache` holding 165 or more distinct use counts raises `RecursionError`, as does `pickle.dumps()` on Python 3.11 from 247 (fine up to 3000 on 3.12 and 3.14; 3.13, 3.15 and PyPy not run): the links are copied recursively along `next`/`prev`. Not a regression, 7.2.8 behaves the same. Suggested fix, as in `TTLCache`: a `_Link.__reduce__` that drops `next`/`prev` and an `LFUCache.__setstate__` that relinks by ascending count; monkeypatched in a probe, deep copies and pickles then keep the eviction order at 1000 counts. |
| 2 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place desyncs `currsize`. Documented footgun. |
| 3 | Low | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` via `@cachedmethod` | Pending sets are per wrapper, so two instances sharing one cache and condition do not coordinate pending keys. |
| 4 | Low | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key hangs on its own pending marker, where the `lock` variants raise `RecursionError`. Suggested fix: make the pending set a dict of key to `threading.get_ident()` and let the owning thread call the function uncached instead of waiting; the hit path stays unchanged, a miss pays one `get_ident()` call (unmeasured). |
| 5 | Low | `Cache` (inherited `items()` / `values()`) | Both views read through `__getitem__`, so iterating them (or `dict(cache)`) counts as a use of every item: `LRUCache` and `TLRUCache` fall back to insertion order and every `LFUCache` count increments. `keys()`, `in` and `repr()` do not. Undocumented. Suggested fix: document it in the `Cache` section, or in a major release override `items()` and `values()` with views that read via `Cache.__getitem__` for each key of `iter(self)`, a potentially breaking change since subclass `__getitem__` overrides would no longer see iteration (untested). |
| 6 | Info | `_cached.py` `_WrapperBase.__reduce__` | Pickling by `__qualname__` means a wrapper rebound under another name, or whose original name was deleted, unpickles to the wrong object or fails. A wrapped callable without `__qualname__` (e.g. a `functools.partial`) fails with `AttributeError`, also for `copy.copy()` and `copy.deepcopy()` of the wrapper or of anything holding it. |
| 7 | Info | `_descriptor.py` `_Unbound.__call__` / `_MethodDescriptor.__call__` | By design, autospec'd instances accept any arguments, so autospec no longer checks arity. A wrong receiver (`Cls.method(1)`) raises `TypeError` "No `__dict__` attribute on 'int' instance"; `@staticmethod`, `@property` or any function decorator that calls the descriptor directly reports the "class methods" message. |
| 8 | Info | `_MethodDescriptor.__get__` | A descriptor assigned after class creation (e.g. by a class decorator) never receives `__set_name__`, so any access, `hasattr(Cls, name)` included, raises `TypeError` until `__set_name__` is called by hand. In the 8.0.0 changelog but not in the docs; asserted by `test_decorator_no_set_name`. After `del Cls.method` an already obtained class callable keeps working through the `super()` path (`test_class_call_after_delete`). |
| 9 | Info | `cachedmethod()` / `_cachedmethod.py` `_WrapperBase` properties | Unlike `cached(None)`, a non-callable `cache` such as `cachedmethod(None)` is accepted at decoration and at attribute access, and fails at the first call with `'NoneType' object is not callable`; `cache(self)` returning `None` (unsupported since 7.0) fails at the first call with `'NoneType' object is not subscriptable`. Both are `TypeError`s, only later and less specific. |

## Performance

CPython 3.14.4, ns per operation, best of 7 (`timeit`, one pinned core, about ±5%),
measured 2026-11-10 on bare metal. Caches hold 100 items (`maxsize=100` for evicting
inserts, new keys from `itertools.count()`, 18 ns included); decorators use
`LRUCache(1024)`, method hits include the attribute lookup (`obj.method(1)`).

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 13 | 25 | 61 | 131 | 171 | 172 |
| contains | 12 | 34 | 34 | 34 | 127 | 126 |
| get miss (`KeyError`) | 63 | 247 | 322 | 322 | 411 | 416 |
| set, existing key | 13 | 61 | 108 | 162 | 383 | 615 |
| set, evicting | 122 | 326 | 492 | 456 | 1022 | 1498 |

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 226 | 1335 |
| `@cached(lock=Lock())` | 294 | 1583 |
| `@cached(condition=Condition())` | 395 | 2078 |
| `@cached(info=True)` | 274 | 1410 |
| `@cached` on a method (bound) | 335 | |
| `@cachedmethod` | 307 | 1464 |
| `@cachedmethod(condition=...)` | 599 | 2292 |
| `@cachedmethod(info=True)` | 356 | 1495 |
| `cachetools.func.lru_cache` | 443 | 2112 |
| `functools.lru_cache` (C) | 26 | 77 |

`FIFOCache` evicting 395, `RRCache` 533, `Cache` update with `getsizeof` 125;
`hashkey(1, 2, 3)` 44, `hashkey(1, 2, a=3)` 205, `typedkey(1, 2, 3)` 147.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `LRUCache.__touch` | Catches `KeyError` for every new key, against the hot-path rule in `AGENTS.md`. Testing `key in order` first takes an evicting insert from 488 to 408 ns and an update of an existing key from 106 to 119 (patched copy, same run). |
| 2 | Info | `_cached.py` `_WrapperBase.__get__` | A hit through a method costs 335 ns against 226 for a direct call: each attribute access runs the Python-level `__get__` and builds a `types.MethodType`, where a plain function binds at C level. The price of wrapper objects over closures. |
| 3 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1022 ns against 492 for `LRUCache` (TLRU 1498): `expire()` runs twice, the `_Timer` is entered twice and `del self[key]` re-checks expiry. Skipping `popitem()`'s own `expire()` and bypassing `__delitem__` would save more, but a direct `popitem()` could then return an expired item and subclass `__delitem__` overrides would no longer see evictions. |
| 4 | Info | `_cachedmethod.py` `_WrapperBase` properties | A `@cachedmethod` hit costs 307 ns against 226 for `@cached` (295 through a prebound wrapper): the `cache` (and `cache_lock`) properties call the user's `cache(self)` lambda on every call, and the key goes through `functools.partial`. First call on a new instance 1779 ns including `M(cache)` at 53 (first attribute access alone 1266); class call 2030 (*Maintainer Decisions*). Inherent to the per-instance design. |
| 5 | Info | `LFUCache.__touch` | A hit that moves its key to the next use-count link costs 218 ns (cycling over 100 keys) against 131 for a key alone in its link, the table's figure: one `OrderedDict` insert and delete per move. Evicting inserts stay flat with size, 503 ns at `maxsize` 10 000 and 499 at 100 000. |

## Type Stubs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` takes the receiver positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` (`test_class_call_keyword_receiver`). |
| 2 | Info | `@classmethod` over `@cached`/`func.*_cache` reports a false "Argument missing" error; pyright does not bind through the wrapper's `__get__`. Rare. |
| 3 | Info | `Cache.setdefault` mirrors typeshed's `dict` overloads: `cache.setdefault(key)` without a default is an error unless the value type is `X \| None`, which also rejects it for `Cache[K, object]`. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | The `self` keyword tests (`test_self_keyword`, #451) cover the default `@cached` and `@cachedmethod` wrappers and the class call only; the positional-only receivers of the lock, condition and `info` mixin `__call__` methods remain unguarded. |
| 2 | Info | `__repr__` on timed caches is never asserted to expire on its own, and `currsize` only indirectly, through `cache_info()` in `test_func.py`'s `test_ttl_expire`; the cache tests assert both after `len()`, `clear()` or `__setitem__`. |
| 3 | Info | `NoneMethodTest.test_none_info` asserts only that `cache_info()` raises `TypeError` when `cache(self)` returns `None`; that the call itself fails, and that `cachedmethod(None)` fails at the first call (Code #9), is unasserted. |
| 4 | Info | No test deep-copies a cache, and `test_pickle_maxsize` pickles every cache freshly filled, which for `LFUCache` is a single use-count link (Code #1). |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods, which now bind explicitly through `__get__`; a one-line caveat that cache and counters are then shared across instances would help. |
| 2 | Low | The `cached` section still speaks of a "memoizing wrapper function" whose "wrapped function is instrumented", while the result is a callable object; and `cache_lock` is described as exposing the `lock` parameter, but with `condition` alone it is the condition object (asserted by tests). |
| 3 | Info | The `README.rst` example is a plain `code-block`, outside the Sphinx doctest run, and its `fib` and PyOWM snippets have no doctested counterpart in `docs/index.rst`; it runs correctly on this tree with `urlopen` and `pyowm` stubbed, but only the by-hand sync rule in `AGENTS.md` guards it. |
