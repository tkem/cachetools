# Code Review — cachetools 7.2.6

**Date:** 2026-10-26
**Reviewed:** `9f2bc19` on `master` ("Release v7.2.6", `__version__` 7.2.6, changelog
dated 2026-10-26; reviewed as `dev/v7.2.6`), four performance commits after v7.2.5
(`a2d411e`). Changes
since the v7.2.5 performance review, with no API change: `_HashedTuple` drops its
Python-level hash cache in favor of the C tuple hash;
`LRUCache`/`LFUCache`/`TTLCache`/`TLRUCache.__getitem__` inline the `__missing__` guard
and link lookup; every `popitem()` reads through `Cache.__getitem__` and deletes via
`del self[key]` instead of `self.pop(key)`; the condition variants of
`@cached`/`@cachedmethod` replace `cond.wait_for(lambda: ...)` with `while k in pending:
cond.wait()`, so uncontended calls never wait (the `wait_count` assertions now read 0,
and the threading tests force a contended `wait()`). The *Performance* section was
measured on 2026-10-26 at `80907bd` against v7.2.5 with the same harness; `80907bd` is a
local pre-release commit not in the published history, whose code is identical to
`9f2bc19` without the changelog entry and `__version__` bump. Perf #1 was additionally
measured with the `wip/default-size` change (`65c3cd6`, a local branch, not published)
applied; it is not part of v7.2.6. Prototypes for Code #1 (wrapper reuse on
`super()`/class access) and Perf #2 (timed-cache eviction) were measured and not
adopted.

**CI status:** All `tox` environments pass locally on Python 3.14 at `9f2bc19`: `py`
(381 passed), `docs`, `doctest`, `pyright` (0 errors), `ruff`, `ruff-format`. The GitHub
Actions matrix (CPython 3.10–3.15, 3.13t–3.15t, PyPy 3.10/3.11) is green at `e7104dd`,
which has the same code (ruff 0.17.3, pyright 1.1.414). Note that ruff 0.16.x flags
`datetime.max` in `test_ttl.py` as DTZ901; 0.17.x does not.

**Coverage:** 100% except two lines that only run on Python **< 3.13**, where
`@classmethod` over `@cachedmethod` calls `__get__` with the class as `obj` (on 3.13+
the call goes entirely through `_ClassMethodDescriptor.__call__`):
- `_cachedmethod.py:22` — `_WrapperBase.__init__`'s `isinstance(obj, type)` /
  `_warn_classmethod` call
- `_descriptor.py:91` — `_MethodDescriptor.__get__`'s `elif self.__deprecated:` branch

The CI matrix covers both.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `_MethodDescriptor.__get__` (`super()` and class-access paths) | `super().method` and `Cls.method(obj, ...)` never hit the instance dict, so every call builds a throw-away `Wrapper` (including `functools.update_wrapper`) and rescans the MRO before `setdefault` returns the stored one. Measured on a cache hit: 2328 ns via `super()` and 2612 ns via the class against 566 ns through the instance (v6.1.0: 733 and 706 ns, when class access was a plain function). Correct, but 4–5x slower than the primary path. Looking up a stored wrapper first was prototyped (`super()` 2260 → 855 ns, class call 2520 → 1070, first access +200 ns) and declined (*Maintainer Decisions*). |
| 2 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place can desync `currsize`. By design and documented, but a known footgun. |
| 3 | Low | `_cachedmethod.py` `_condition_info` / `_condition` | Stampede prevention uses per-instance pending sets, so two instances sharing one cache and condition do not coordinate pending keys. |
| 4 | Info | `_cachedmethod.py` / `_cached.py` condition variants | Same-thread recursive re-entry on the same key deadlocks (`wait()` on its own pending marker). |
| 5 | Info | `_MethodDescriptor.__get_unbound` | Lazy creation of the cached `_Unbound` object is unsynchronized. Concurrent first class accesses may briefly see distinct (equivalent) objects; only `Cls.method is Cls.method` identity is affected during that window. Benign. |
| 6 | Info | `_descriptor.py` `_Unbound.__call__` | By design (see its docstring), autospec'd instances accept any arguments: `inspect.signature(mock.method)` is `(*args, **kwargs)`, so autospec no longer checks call arity for `@cachedmethod` methods. Calling a real method through the class with a wrong receiver, e.g. `Cls.method(1)`, takes the first argument as the receiver: with `info=True` this raises `TypeError` "No `__dict__` attribute on 'int' instance"; with `info=False` the deprecated descriptor only emits that text as a `DeprecationWarning` (hidden by default filters) and the call then fails inside `cache(self)`, e.g. `AttributeError: 'int' object has no attribute 'cache'` (both verified). |
| 7 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a key that is present but expired removes it and then raises `KeyError`. This is consistent with `key in cache` being `False`, but `cache.pop(key, default)` and `del` behave differently around the expiry instant. Intentional; listed for awareness. |
| 8 | Info | `__init__.py` `cachedmethod` `make_info` | A `cache(self)` that is not a mapping is only reported, as `TypeError`, when `cache_info()` is called. Calls and `cache_clear()` work as long as the object supports the operations used. Acceptable, since `cache(self)` is resolved per call anyway. |
| 9 | Info | `_cachedmethod.py` `Wrapper.__call__` / `wrapper(self, ...)` | Stacked `@cachedmethod` is broken: the outer wrapper calls `method(obj, ...)` on the inner *descriptor*. With `info=True` this raises `TypeError: 'Descriptor' object is not callable`. With `info=False` it works only through the deprecated `_ClassMethodDescriptor.__call__` shim, which emits a misleading `@classmethod` `DeprecationWarning` and bypasses the per-instance `Wrapper`. A proper fix would bind via `method.__get__(obj, type(obj))` and pass `__set_name__` on to the inner descriptor. Unsupported by maintainer decision. |
| 10 | Info | `_WrapperBase.__reduce__` | Unpickling and deep-copying reset `hits`/`misses` of `info=True` wrappers, since the wrapper is rebuilt through its descriptor rather than serialized (documented in the code, asserted by `test_decorator_pickle_info` and `_test_copy_super`). Acceptable, since counters are a tuning aid. |
| 11 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | Pickles reference `cachetools._descriptor._MethodDescriptor._lookup` by qualified name, so that path must stay importable for pickles to load across releases. `_lookup` resolves through the owner's *current* class dict, so a pickle loaded while `Cls.method` is reassigned (e.g. under `unittest.mock.patch.object`) silently yields whatever the attribute holds then instead of a wrapper. A descriptor that never received `__set_name__` (the deprecated pre-3.13 `@classmethod` path) reduces to `_lookup(None, None)`: `pickle.dumps` succeeds, `pickle.loads` raises `AttributeError`. |

No implementation bugs found beyond the items above.

## Performance

Hot-path costs on CPython 3.14.4, ns per operation, best of 7, v7.2.5 → `80907bd`
(`timeit`, same harness run from git worktrees). Caches hold 100 items for reads and
updates and are full (`maxsize=100`) for evicting inserts; decorators use
`LRUCache(1024)` and a one-argument function. Unchanged paths moved by up to ±5%,
which is noise. `@cached` hits are 53% faster and evicting misses 39%, mostly from the
C tuple hash; condition-variant hits (all of `cachetools.func`) are 44–55% faster.
The `@cachedmethod` paths are still slower than v6.1.0 by design of the 7.0
per-instance wrappers (Code #1, Perf #3).

| Operation | `dict` | `Cache` | `LRU` | `LFU` | `TTL` | `TLRU` |
|---|---|---|---|---|---|---|
| get hit | 14 | 28 | 113 → 69 | 168 → 146 | 204 → 187 | 206 → 188 |
| contains | 14 | 38 | 38 | 37 | 137 | 139 |
| get miss (`KeyError`) | 71 | 275 | 361 | 353 | 507 → 453 | 488 → 455 |
| set, existing key | 15 | 182 | 230 | 300 | 581 | 857 |
| set, evicting | 120 | 422 | 788 → 643 | 1169 → 730 | 2213 → 1551 | 2741 → 2021 |

`FIFOCache` evicting 571 → 514, `RRCache` 718 → 671. The `dict` evicting row includes
`del d[next(iter(d))]`.

| Decorator call | hit | evicting miss |
|---|---|---|
| `@cached` | 566 → 264 | 2663 → 1636 |
| `@cached(lock=Lock())` | 649 → 338 | 2931 → 1875 |
| `@cached(condition=Condition())` | 974 → 437 | 3767 → 2399 |
| `@cached(info=True)` | 598 → 288 | 2681 → 1696 |
| `@cachedmethod` | 916 → 566 | 3183 → 2123 |
| `@cachedmethod(condition=...)` | 1423 → 800 | 4470 → 3008 |
| `cachetools.func.lru_cache` | 1002 → 451 | 3823 → 2391 |
| `functools.lru_cache` (C) | 28 | 83 |

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__setitem__` / `_DefaultSize` | With the default `getsizeof`, the `_DefaultSize` stand-in dict is read and written through Python-level `__getitem__`/`__setitem__` on every store, so a `Cache` update costs 167 ns with the default but 138 ns with `getsizeof=len` and a real size dict. Treating the default as `None` and skipping the size bookkeeping (local branch `wip/default-size`, `65c3cd6`, not published; applied to `dev/v7.2.6`, all `tox` environments pass, 100% coverage of `__init__.py`) makes updates 167 → 106 ns for `Cache`, 222 → 154 for `LRUCache`, 290 → 215 for `LFUCache`, 538 → 465 for `TTLCache`, and evicting inserts 7–15% faster (`LRUCache` 646 → 552, `FIFOCache` 493 → 433); `getsizeof=len` updates also drop 138 → 125. Caches pickled by v7.2.5 still load (verified). |
| 2 | Info | `TTLCache.__setitem__` / `TTLCache.popitem` (and `TLRUCache`) | An evicting insert costs 1551 ns against 643 for `LRUCache` (TLRU 2021), although the timer is frozen. By cProfile per insert: `expire()` runs twice (once in `__setitem__`, again inside `popitem`), the `_Timer` is entered twice and the `timer` property read three times, and `del self[key]` in `popitem` re-checks expiry in `__delitem__`. Prototyped: inlining the link lookup in `__setitem__` saves ~20 ns (noise); skipping `popitem`'s own `expire()` ~40 ns, but a direct `popitem()` could then return an expired item; deleting via `Cache.__delitem__` plus own bookkeeping ~120 ns, but a subclass `__delitem__` would no longer see evictions; both together 1474 → 1285 ns (−13%). The remaining gap is the re-entrant timer, the linked list and the second links dict. Accepted as inherent (*Maintainer Decisions*). |
| 3 | Info | `_cachedmethod.py` `Wrapper.__call__` | A `@cachedmethod` hit costs 566 ns against 264 for `@cached`: `__call__` dispatch on the wrapper object, the module-level `wrapper(self._obj, ...)` hop, the `cache(self)` lambda and the `partial(methodkey, obj)` → `hashkey` chain. First access per instance builds the `Wrapper` and runs `update_wrapper` (4174 ns including object creation, was 4687); `super()` 2747 → 2328 ns and class calls 3032 → 2612 (Code #1). Inherent to the per-instance design. |
| 4 | Info | `_TimedCache._Timer` / `timer` property | `timer()` through the re-entrant wrapper costs 66 ns against 30 for `time.monotonic()`, and `with timer as t` 117 ns; this is most of the gap between `TTLCache` and `LRUCache` reads (187 vs 69) and `contains` (137 vs 38). Reading the wrapper from a plain attribute instead of the `timer` property would save ~28 ns per `TTLCache`/`TLRUCache` hit; prototyped and declined (*Maintainer Decisions*). Inherent to freezing time per operation. |
| 5 | Info | `cachetools.func` | `lru_cache` hit 451 ns against 28 ns for `functools.lru_cache`, 16x (was 36x), because every `func` decorator uses `condition=Condition()` and `info=True`. By design (stampede protection). |
| 6 | Info | `keys.typedkey` | 449 ns against 96 for `hashkey(1, 2, 3)`: two `_HashedTuple` allocations (`__add__`) and a generator for `tuple(type(v) for v in args)`; `tuple(map(type, args))` and a single concatenation would trim it. Rarely on a hot path (`typed=True`). |

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` has a second, receiver-less overload so that deprecated `@classmethod` + `@cachedmethod` calls (`Cls.method(arg)`) still type-check. Trade-off: a missing instance on a regular method (`Cls.method(arg)`) is not reported. Drop that overload when `@classmethod` support is removed. The receiver is positional-only in both overloads, so `Cls.method(self=obj, value=1)`, which the runtime now accepts, is a pyright error; the receiver's name is not expressible in the stub (`Concatenate[Any, _P]` erases it), so `test_class_call_keyword_receiver` carries `# type: ignore` on those calls. |
| 2 | Info | At runtime, `@cached(info=False)` wrappers have `cache_info = None`, but `_cached_wrapper` does not declare it, so `wrapper.cache_info` is a type error. The stub is arguably right (the attribute is meaningless), but the stub and runtime differ. `_cached_wrapper.cache` is typed `MutableMapping \| None` and `cached()` still accepts `None` for the deprecated pass-through; tighten both when that support is removed. |
| 3 | Info | `@classmethod` stacked over `@cached`/`func.*_cache` still reports a false "Argument missing" error. Python passes `cls` correctly at runtime, but pyright does not bind through the wrapper's `__get__` there. Rare and not encouraged. |
| 4 | Info | `_cached_wrapper_info.__get__` carries `# pyright: ignore[reportIncompatibleMethodOverride]`. Pyright cannot match the subclass overloads against the base's self-typed `Concatenate` overload. The override is sound, since each return type is the `_cached_wrapper_info` subtype of the base's. |

Otherwise fine: `ParamSpec(_P)` and `Concatenate[Any, _P]` preserve signatures. The
overload order is the `Literal[False]` default first, then keyword-only and positional
`Literal[True]`. `func.pyi` overloads cover both `@lru_cache` and `@lru_cache(...)`.
The `__get__` overloads bind `self` correctly for instance and class calls on
`@cached` and `func.*_cache` methods.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `test_classmethod.py` covers only deprecation warnings and basic behavior: no error-path or shared-cache tests. (`info=True` never supported `@classmethod`.) |
| 2 | Low | `UnboundMethodTest` does not assert that class access exposes no `cache_clear`/`cache_info`, and does not exercise class access for the lock/condition variants. |
| 3 | Info | `CacheTestMixin` deliberately checks key existence rather than the specific eviction victim, since it is shared across all cache types. Policy-specific checks live in the per-cache test files. No action needed. |
| 4 | Info | The `test_func.py` `DecoratorTestMixin` calls decorators through `Callable[..., Any]`, so pyright does not check the `func.pyi` stubs there. One concrete test (`FIFODecoratorTest.test_method_typed`) covers them; that is enough, since all five decorators share `_cachetools_cache_wrapper`. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | The `@cachedmethod` docs do not mention that class access (`Cls.method`) yields a callable without `cache_clear()`/`cache_info()` that takes the receiver positionally or by its parameter name, or that pickling an instance resets its `cache_info()` counters (Code #10). |
| 2 | Info | Neither the `@cached` nor the `cachetools.func.*_cache` docs mention that they may decorate methods (covered by `test_decorator_method`). Worth a one-line caveat that the cache and counters are then shared across all instances, unlike `@cachedmethod`. |

## `CHANGELOG.rst`

No issues found. The 7.2.6 section (dated 2026-10-26) has a single "Various
performance improvements." line, consistent with the four performance-only commits
since v7.2.5 (no API or behavior change, so no tags), and two blank lines before
7.2.5. The file parses cleanly with docutils.

## Keys & Func Modules

No issues found. `hashkey`/`typedkey` sort keyword arguments and return a
`_HashedTuple`, which uses the C tuple hash (the former Python-level hash cache is
kept commented out with its rationale) and pickles with empty state. Every `func.py` decorator is built on
`cached(..., condition=Condition(), info=True)`, so stampede prevention is on by default.
`_UnboundTTLCache` extends `TTLCache` with `math.inf` maxsize for `maxsize=None`.
