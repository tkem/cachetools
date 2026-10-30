# Code Review — cachetools 8.0.0 (development)

**Date:** 2026-10-31
**Reviewed:** `develop` at `a1e5f45` ("Prepare v8.0.0."; `__version__` 8.0.0, CHANGELOG
has the unreleased 8.0.0 section).

**CI status:** All `tox` environments pass locally on CPython 3.14.4: `py` (398
passed), `docs`, `doctest`, `pyright` (0 errors), `ruff`, `ruff-format`; `py` also
passes on CPython 3.11 and 3.12. GitHub Actions on `tkem/cachetools` is green for
`develop` at `a1e5f45` on all nine matrix jobs (CPython 3.11–3.15, 3.13t–3.15t, PyPy
3.11).

**Coverage:** 100% on Python < 3.13 (branches included); on 3.13+ only
`_descriptor.py:36` is uncovered, the pre-3.13 path where `@classmethod` calls
`__get__(cls, type(cls))` on a descriptor without `__set_name__`. The matrix covers
both.

**Verified:** by probe scripts on 3.11, 3.12 and 3.14, plus two independent review
passes over the decorator code, stubs, tests and docs whose reproductions were rerun
before inclusion. `@cached` on instance, static and class methods binds through
`__get__` (autospec asserted by `test_autospec`); module-level and class-attribute
`@cached` wrappers pickle and deep-copy to themselves, local ones fail like plain local
functions; `cached(None)` raises before decorating; a parameter named `pending` works
with `condition` on both decorators; `@cachedmethod` wrappers expose `cache_key` as a
`partial` and `__wrapped__` as the original function; exceptions under the condition
variants release waiters, which recompute; a real two-thread stampede on one key with
`Condition()` alone or `Condition(lock)` computes once. Keys pickled by 7.2.7
(`_HashedTuple`, eight shapes with kwargs and types) load into `LRUCache` and
`TTLCache` and are found by the new plain-tuple keys without duplicate entries. Cache
semantics by a differential trace of 100800 random operations on all seven cache
classes (default and `len` sizes, `maxsize` 0, 1, 3, 10, 2.5 and infinity, timer
advances) under a fixed `PYTHONHASHSEED`: identical to v7.2.7 (see Code #16 for why
the seed matters). The `__repr__`s are asserted by `test_decorator_repr` in both
decorator test modules. Performance by the benchmarks below; against a v7.2.7 worktree
every measured operation is at least as fast except method access to `@cached`
wrappers (Performance #3).

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Medium | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` (`cond.wait()`, `cond.notify_all()` under `lock`) | With `lock` and `condition` given as two unrelated objects, a `threading.Condition` raises `RuntimeError` ("cannot notify on un-acquired lock") on every miss, single-threaded included, for both decorators; only a condition built on that lock (`Condition(lock)`) works. The docs present the pair as independent (Docs #1) and the tests use fakes without the ownership check (Tests #1). |
| 2 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place desyncs `currsize`. Documented footgun. |
| 3 | Low | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` via `@cachedmethod` | Pending sets are per wrapper, so two instances sharing one cache and condition do not coordinate pending keys. |
| 4 | Low | condition variants of `@cached` / `@cachedmethod` | Same-thread recursion on the same key hangs on its own pending marker, where the `lock` variants raise `RecursionError`. |
| 5 | Low | `_MethodDescriptor.__get__` (instance-dict wrapper) | `mock.patch.object(Cls, "method")` is not seen by instances that already called the method, since the wrapper in `obj.__dict__` shadows the class attribute; the wrapper also references `obj`, so such instances form a reference cycle and are freed by the cyclic collector only. Inherent to per-instance wrappers, undocumented. |
| 6 | Info | `_MethodDescriptor.__get__` (class-access path) | `Cls.method(obj, ...)` builds and discards a wrapper per call before `obj.__dict__.setdefault()` returns the stored one: 2020 ns per hit against 295 through the instance and 571 via `super()`, which reuses its stored wrapper (*Maintainer Decisions*). |
| 7 | Info | `_cachedmethod.py` `_wrapper` | `update_wrapper(descriptor, method)` runs *after* `_MethodDescriptor(wrapper)`, so a stacked `@cachedmethod` copies the inner descriptor's `__dict__` (factory, owner, name) over the outer's and the pair silently acts as the inner decorator alone. Unsupported (*Maintainer Decisions*). |
| 8 | Info | `_cached.py` `_WrapperBase.__reduce__` | Pickling by `__qualname__` means a wrapper rebound under another name, or whose original name was deleted, unpickles to the wrong object or fails; a wrapped callable without `__qualname__` (e.g. a `functools.partial`) fails with `AttributeError` rather than `PicklingError`. |
| 9 | Info | `_MethodDescriptor.__get_unbound` | Lazy creation of the `_Unbound` object is unsynchronized; concurrent first class accesses may briefly see distinct, equivalent objects. Benign. |
| 10 | Info | `_descriptor.py` `_Unbound.__call__` / `_MethodDescriptor.__call__` | By design, autospec'd instances accept any arguments, so autospec no longer checks arity. A wrong receiver (`Cls.method(1)`) raises `TypeError` "No `__dict__` attribute on 'int' instance"; `@staticmethod` or `@property` over `@cachedmethod` report the "class methods" message. |
| 11 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a present-but-expired key removes it and raises `KeyError`, consistent with `key in cache`; `pop(key, default)` and `del` differ around the expiry instant. Intentional. |
| 12 | Info | `CacheInfo._make_info` | A cache without `__len__` is only reported, as `TypeError` from `len()`, when `cache_info()` runs; documented requirement. |
| 13 | Info | `_cachedmethod.py` `_WrapperBase.__reduce__` | Unpickling and deep-copying rebuild wrappers through their descriptor, so `info=True` counters reset (asserted by tests, documented). Acceptable. |
| 14 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | `_lookup` must stay importable and resolves through the owner's *current* class dict, so a pickle loaded while `Cls.method` is patched yields the patched attribute, and after `del Cls.method` instances holding the wrapper still call it but no longer pickle (`KeyError`). A descriptor that never saw `__set_name__` pickles but fails to load with `AttributeError`. |
| 15 | Info | `_MethodDescriptor.__get__` | A descriptor assigned after class creation never receives `__set_name__`, so any access, class access included, raises `TypeError`. Undocumented use, asserted by `test_decorator_no_set_name`. After `del Cls.method` an already obtained class callable keeps working through the `super()` path (`test_class_call_after_delete`). |
| 16 | Info | `LFUCache.popitem` | Among equally used keys the victim is `next(iter(link.keys))`, so with `str` keys it varies between processes under hash randomization. Documented in code as arbitrary. |
| 17 | Info | `_decorator.py` `_LockedMixin` / `_LockedInfoMixin` | The lock variants store through `cache.setdefault()`, so a duck-typed cache that is not a `MutableMapping` needs it; the other variants use item access only. |
| 18 | Info | `keys.py` `_kwmark` | `hashkey(a=1) == hashkey(_HashedTuple, ("a", 1))`; the sentinel is a private class, so a collision needs it passed on purpose. |

No implementation bugs found beyond the items above.

## Performance

Hot-path costs measured on 2026-10-31 at `a1e5f45` on CPython 3.14.4, ns per
operation, best of 7 (`timeit`, one pinned core; repeat runs agree within about 5%).
Caches hold 100 items for reads and updates and are full (`maxsize=100`) for evicting
inserts, with new keys from `itertools.count()` (18 ns included); decorators use
`LRUCache(1024)` and a one-argument function.

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 12 | 26 | 61 | 132 | 167 | 169 |
| contains | 12 | 33 | 34 | 34 | 125 | 125 |
| get miss (`KeyError`) | 63 | 242 | 315 | 313 | 398 | 400 |
| set, existing key | 13 | 61 | 103 | 161 | 379 | 601 |
| set, evicting | 107 | 316 | 474 | 568 | 1029 | 1483 |

`FIFOCache` evicting 376, `RRCache` 506; with a custom `getsizeof` (size-dict path)
`Cache` updates cost 120. The `dict` evicting row includes `del d[next(iter(d))]`.

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 222 | 1310 |
| `@cached(lock=Lock())` | 293 | 1539 |
| `@cached(condition=Condition())` | 385 | 2052 |
| `@cached(info=True)` | 264 | 1368 |
| `@cached` on a method (bound) | 322 | |
| `@cachedmethod` | 295 | 1454 |
| `@cachedmethod(condition=...)` | 572 | 2307 |
| `@cachedmethod(info=True)` | 340 | 1512 |
| `cachetools.func.lru_cache` | 433 | 2067 |
| `functools.lru_cache` (C) | 26 | 76 |

Key functions: `hashkey(1, 2, 3)` 45, `hashkey(1, 2, a=3)` 197, `typedkey(1, 2, 3)`
143, `methodkey(obj, 1, 2, 3)` 46.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `_cached.py` `_WrapperBase.__get__` | A hit through a method costs 322 ns against 222 for a direct call: the Python-level `__get__` building a `types.MethodType` makes each attribute access 68 ns where a plain function binds in 22. The price of wrapper objects over closures, and the one measured operation slower than in the previous release. |
| 2 | Info | `TTLCache.__setitem__` / `popitem` (and `TLRUCache`) | An evicting insert costs 1029 ns against 474 for `LRUCache` (TLRU 1483): `expire()` runs twice, the `_Timer` is entered twice and `del self[key]` re-checks expiry. Skipping `popitem()`'s own `expire()` and bypassing `__delitem__` would save more, but a direct `popitem()` could then return an expired item and subclass `__delitem__` overrides would no longer see evictions. |
| 3 | Info | `_decorator.py` mixin `__call__` | A `@cached` hit costs 222 ns: instance `__call__` dispatch plus the `self.cache` / `self.cache_key` attribute loads that a closure would hold as cell variables; the `info` counters as instance attributes add about 40. Price of the shared mixins. |
| 4 | Info | `_cachedmethod.py` `_WrapperBase` properties | A `@cachedmethod` hit costs 295 ns against 222 for `@cached`: the `cache` (and `cache_lock`) properties call the user's `cache(self)` lambda on every call, and the key goes through `functools.partial`. First access per instance 2652 ns including `M()` at 715; class call 2020 (Code #6). Inherent to the per-instance design. |
| 5 | Info | `cachetools.func` | `lru_cache` hit 433 ns against 26 for `functools.lru_cache`, since every `func` decorator uses `condition=Condition()` and `info=True`. By design. |

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | High | The first `TTLCache.__init__` / `TLRUCache.__init__` overload types `self` as `TTLCache[_KT2, _VT2, float]`, which leaves the key and value types unsolved: the documented form `cache: TTLCache[str, bytes] = TTLCache(maxsize=10, ttl=60)`, and passing such a call to a `TTLCache[str, bytes]` parameter, are rejected (`_KT2@__init__` is not `str`); `TTLCache(10, 60, getsizeof=len)` infers `Sized` values. The explicit-`timer` overload and the other cache classes are fine. Verified in a stub copy that `self: TTLCache[_KT, _VT, float]` (with `_VT` in `getsizeof` and `ttu`) accepts every form. |
| 2 | Low | The comment on `_AbstractCondition` says the implementation uses neither `wait()` nor `notify()`; the mixins call `wait()` and `notify_all()`, and `wait_for()` and `notify()` are the unused ones. The protocol itself stays as decided. |
| 3 | Info | `_cachedmethod_unbound.__call__` takes the receiver positional-only, so `Cls.method(self=obj, ...)` works at runtime but needs `# type: ignore` (`test_class_call_keyword_receiver`). |
| 4 | Info | `@classmethod` over `@cached`/`func.*_cache` reports a false "Argument missing" error; pyright does not bind through the wrapper's `__get__`. Rare. |
| 5 | Info | `_cached_wrapper_info.__get__` needs `# pyright: ignore[reportIncompatibleMethodOverride]`; the override is sound. |
| 6 | Info | `func.pyi`'s wrapper omits `cache`, `cache_key`, `cache_lock` and `cache_condition`, which exist at runtime but are undocumented for `cachetools.func`. Matches `functools.lru_cache`. |

Otherwise fine: `ParamSpec`/`Concatenate[Any, _P]` preserve signatures, the
keyword-only `info: Literal[True]` overload precedes the `Literal[False]` default,
`Cache.setdefault` has the `None`-default overload, `CacheInfo` is exported, the key
functions are typed as returning `tuple[Hashable, ...]`, and `func.pyi` covers both
`@lru_cache` and `@lru_cache(...)`.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Medium | `lock` and `condition` as two real `threading` objects are never exercised: `test_cached.py` and `test_cachedmethod.py` use `CountedCondition` fakes without the ownership check, `test_threading.py` passes `condition` alone, and `Cached.get_lock_cond` (`info=False`) is defined but never called. Code #1 passes the suite. |
| 2 | Medium | The exception path of `_ConditionInfoMixin` is untested: `test_decorator_cond_error` in both modules uses `info=False`. A regression in its pending-set cleanup would only hang a second concurrent caller. |
| 3 | Low | `test_threading.py` `run_cond_test` is never called; the condition tests use two threads through `run_cond_wait_test` only. |
| 4 | Low | `test_func.py` never asserts `ttl_cache` expiry (including `maxsize=None`, promised in the docs) or passes `rr_cache(choice=...)`. |
| 5 | Low | `test_keys.py` asserts type sensitivity for positional arguments only; dropping the kwargs type suffix in `typedkey` / `typedmethodkey` would pass. |
| 6 | Low | `@cached(info=True)` with a mapping lacking `__len__` is tested only through `@cachedmethod` (`NoneMethodTest`). |
| 7 | Info | `currsize` and `__repr__` on timed caches are never asserted to expire on their own; every such assertion follows `len()`, `clear()` or `__setitem__`. |
| 8 | Info | `UnboundMethodTest` exercises class access (`Cls.method(obj, ...)`) only for the plain and `info=True` variants; class access dispatches through the same `_Unbound` object for every variant, so the gap is small. |
| 9 | Info | `test_func.py` calls decorators through `Callable[..., Any]`; `FIFODecoratorTest.test_method_typed` covers the stubs, enough since all five decorators share one wrapper type. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Medium | The `cached` `lock` and `condition` paragraphs say nothing about a `condition` given together with a separate `lock` having to be built on that lock (`threading.Condition(lock)`); with the stdlib classes any other pairing fails on the first miss (Code #1). |
| 2 | Low | Neither `@cached` nor `cachetools.func.*_cache` mention decorating methods, which now bind explicitly through `__get__`; a one-line caveat that cache and counters are then shared across instances would help. |
| 3 | Low | The `cached` section still speaks of a "memoizing wrapper function" whose "wrapped function is instrumented", while the result is a callable object; and `cache_lock` is described as exposing the `lock` parameter, but with `condition` alone it is the condition object (asserted by tests). |
| 4 | Info | The `versionchanged:: 8.0` notes cover `cache=None`, `@classmethod`, immutable `__dict__` and `CacheInfo`; the Python 3.11 floor and the wrapper-object change are not mentioned, which is fine for the reference. The class-access paragraph says the receiver may be passed by keyword, which holds only for a positional-or-keyword first parameter visible in the signature; acceptable. |

## `CHANGELOG.rst`

The 8.0.0 section lists the 3.10 drop, the deprecated `@cachedmethod` features
(`@classmethod`, immutable or missing `__dict__`), `cache=None`, the `__len__`
requirement and public `CacheInfo`. Not mentioned, release-only to add: `@cached`
wrappers are callable objects rather than functions (`inspect.isfunction()` is
`False`, `type()` changed); `info=False` wrappers no longer carry a `cache_info`
attribute set to `None`; a `@cachedmethod` descriptor assigned after class creation
raises `TypeError` (Code #15); and no performance bullet, although key functions return
plain tuples and the decorator hot paths were reworked. `__repr__` on both wrapper kinds
is a non-breaking addition.

## Keys & Func Modules

No issues found. The key functions return plain tuples, and `methodkey` /
`typedmethodkey` repeat the `hashkey` / `typedkey` bodies on purpose (a delegating call
cost more); `_HashedTuple` stays as the `_kwmark` sentinel and keeps 7.x pickles
loadable (verified above). Every `func.py` decorator is built on `cached(...,
condition=Condition(), info=True)`, and `_UnboundTTLCache` handles `maxsize=None`.
