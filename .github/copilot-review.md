# Code Review — cachetools 8.0.0 (in development)

**Date:** 2026-09-15
**Reviewed:** `develop` @ a987dee (plus uncommitted docs/changelog edits)
**CI status:** All green (`tox`: py, docs, doctest, pyright, ruff, ruff-format)

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

No issues. `cached` and `cachedmethod` stubs use `ParamSpec(_P)` to
preserve decorated function signatures (`__call__` uses `_P.args`/`_P.kwargs`).
`cachedmethod` stubs use `Concatenate[Any, _P]` to strip `self` from
`ParamSpec`, and `_cachedmethod_wrapper` models the descriptor protocol
(`__set_name__`, `__get__`, `__call__`).
Overload order is `Literal[False]` (the default) first, then the two
`Literal[True]` variants. Order is not load-bearing here since the
literal types are disjoint, but note it is the *opposite* of the usual
"most specific first" convention.

`func.pyi` deliberately uses `Callable[..., _R]` instead of `ParamSpec`
for `_cachetools_cache_wrapper` since the `func.*_cache` decorators
rewrite signatures (adding `cache_info`, `cache_clear`, `cache_parameters`).

## Code — Potential Issues

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes value size is stable after insert. In-place mutation of cached values can desync `currsize`. By design (documented), but a known footgun. |
| 2 | Low | `src/cachetools/_cachedmethod.py` condition variants | Stampede prevention uses per-instance pending sets. Two instances sharing one cache+condition won't coordinate pending keys across instances. |
| 3 | Info | `src/cachetools/_cachedmethod.py` / `src/cachetools/_cached.py` condition variants | Same-thread recursive re-entry on the same key can deadlock (`wait_for` on own pending marker). |
| 4 | Info | `_cached._wrapper` | With `cache=None` the `_uncached`/`_uncached_info` wrappers ignore `lock` and `condition` entirely, yet `_wrapper()` still publishes them as `cache_lock`/`cache_condition`. Harmless, but the attributes advertise synchronization that never happens. |
| 5 | Info | `_Timer.__reduce__`, `TTLCache.__setstate__`, `CacheTestMixin.test_pickle*` | Caches are picklable and the behavior is unit-tested, but pickling is **not** an officially supported or documented feature. The pickled state is raw instance `__dict__` content with no version marker, so any release — including a bugfix release — may silently break compatibility. Pickled caches must only be restored with the exact version that produced them. Keep it undocumented; do not build features on it. |
| 6 | Info | `_TimedCache._Timer.__getattr__` | `__getattr__` resolves through `self.__timer`, so an instance whose `__init__` never ran recurses until `RecursionError` instead of raising `AttributeError`. Unreachable today — `__reduce__` rebuilds via `__init__`, covering both `pickle` and `copy` — but a trap for any future change to `_Timer` construction. |
| 7 | Info | `_WrapperBase.__reduce__` | Correctness depends on the `cache`/`lock`/`cond` getters staying lazy: on unpickling, `getattr()` runs while the instance `__dict__` is still empty, so an eager `cache(obj)` in a wrapper `__init__` would break round-tripping. |
| 8 | Info | `_WrapperBase.__reduce__` | Rebuilding through `getattr()` discards wrapper state: `*Info` hit/miss counters reset to zero, and a `_Condition*Wrapper`'s pending set is recreated empty. Accepted and covered by `test_decorator_pickle_info`; worth a docs note if pickling of cached methods ever gets documented beyond the changelog entry. |

No implementation bugs found beyond the items above.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | The 8.0 removal of `wrapper.cache_info = None` is unasserted. No test checks that `cache_info` is absent when `info=False` — for either decorator — so a re-added assignment would pass CI. A `hasattr` / `assertRaises(AttributeError)` check in `DecoratorTestMixin` and `MethodDecoratorTestMixin` would lock in the new contract. |
| 2 | Low | `NoneWrapperTest` (`cache=None`) only covers the bare and `info=True` wrappers. `cache_condition` is never asserted, and `cached(None, lock=...)` / `cached(None, condition=...)` are untested — exactly the combinations behind Code item 4. |
| 3 | Info | `ClassMethodTest` has two tests that now assert the same `TypeError`; only the message differs by Python version. Could be collapsed, but the split documents the pre/post-3.13 behavior. |

## Docs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `condition` docs say it must provide `wait()`, `wait_for()`, `notify()` and `notify_all()`, but only `wait_for()` and `notify_all()` are used at runtime. The `_AbstractCondition` protocol could be relaxed. |
| 2 | Low | `cached(cache=None)` is supported at runtime (`_uncached`/`_uncached_info`), typed in `__init__.pyi` and unit-tested, but `docs/index.rst` never mentions it. The `cached` reference describes `cache` only as a cache object, so the documented way to disable caching does not exist. |
| 3 | Info | `docs/index.rst` has no `.. versionchanged:: 8.0` under `cached`, although `CHANGELOG.rst` flags the removal of the `cache_info` attribute as potentially breaking. `cachedmethod` has an 8.0 note for the `classmethod` change; `cached` has none, and the re-enabled pickling of cached methods is changelog-only too. |

## Keys & Func Modules

No issues found. `func.py` correctly uses `threading.Condition()` for
all decorators, providing stampede prevention by default. `_UnboundTTLCache`
cleanly extends `TTLCache` with `math.inf` maxsize for the
`maxsize=None` case.
