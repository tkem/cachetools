# Code Review — cachetools 8.0.0 (in development)

**Date:** 2026-09-21
**Reviewed:** `wip/aio` @ `dfc4c8b`
**Validation:** full `tox` green (py, docs, doctest, pyright, ruff, ruff-format)
**Tests:** 412 collected, 409 passed / 3 skipped on Python 3.11; coverage 99%
(`_descriptor.py` 93%, everything else 100%) — 100% on Python ≥ 3.13
**Type checking:** `pyright` 0 errors, 20 warnings, 18 informations (all
`reportOptionalContextManager`/`reportOptionalMemberAccess` in
`_cached.py`/`_cachedmethod.py`, downgraded by design)

## Code — Potential Issues

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `src/cachetools/_cachedmethod.py` condition variants | Stampede prevention uses per-instance pending sets. Two instances sharing one cache+condition won't coordinate pending keys across instances. |
| 2 | Info | `Cache.__setitem__` / `__delitem__` | Size accounting assumes value size is stable after insert. In-place mutation of cached values can desync `currsize`. By design (documented), but a known footgun. |
| 3 | Info | `cached()` in `src/cachetools/__init__.py` | The guard is `None`-only, and `TypeError("cache must not be None")` says exactly that — no overpromising. The residual asymmetry is that every *other* invalid cache (`cached(42)`, `cached([])`, `cached("str")`) is still accepted at decoration time and fails later with `'int' object is not subscriptable`, `list indices must be integers...`, etc. Fine to leave as-is for 8.0. |
| 4 | Info | `_WrapperBase.__init__`, `_AsyncWrapperBase.__init__` | `self.__wrapped__ = method` is immediately redundant with `functools.update_wrapper(self, method)`; it exists only to silence pyright (`FIXME` comment in place). Worth revisiting if the pyright/typeshed situation improves. |
| 5 | Info | `_WrapperBase.__reduce__`, `_AsyncWrapperBase.__reduce__` | Correctness depends on the `cache`/`lock`/`cond` getters staying lazy: on unpickling, `getattr()` runs while the instance `__dict__` is still empty, so an eager `cache(obj)` in a wrapper `__init__` would break round-tripping. |
| 6 | Info | `_WrapperBase.__reduce__`, `_AsyncWrapperBase.__reduce__` | Rebuilding through `getattr()` discards wrapper state: `*Info` hit/miss counters reset to zero, and a `_Condition*Wrapper`'s pending set is recreated empty. Accepted and covered by `test_decorator_pickle_info` (sync and async); see Docs item 2 for the corresponding documentation gap. |
| 7 | Info | `src/cachetools/_cachedmethod.py` / `src/cachetools/_cached.py` condition variants | Same-thread recursive re-entry on the same key can deadlock (`wait_for` on own pending marker). |
| 8 | Info | `_Timer.__reduce__`, `TTLCache.__setstate__`, `CacheTestMixin.test_pickle*` | Caches are picklable and the behavior is unit-tested, but pickling is **not** an officially supported or documented feature. The pickled state is raw instance `__dict__` content with no version marker, so any release — including a bugfix release — may silently break compatibility. Pickled caches must only be restored with the exact version that produced them. Keep it undocumented; do not build features on it. |
| 9 | Info | `_TimedCache._Timer.__getattr__` | `__getattr__` resolves through `self.__timer`, so an instance whose `__init__` never ran recurses until `RecursionError` instead of raising `AttributeError`. Unreachable today — `__reduce__` rebuilds via `__init__`, covering both `pickle` and `copy` — but a trap for any future change to `_Timer` construction. |

## Async (aio)

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `src/cachetools/_acachedmethod.py` `_AsyncWrapperBase` | Near-verbatim copy of `_WrapperBase` (`__init__`, `__reduce__`, `cache`, `cache_key`, the `__wrapped__` FIXME) minus the lock/condition properties. Private name mangling (`__name`, `__cache`, `__key`) blocks a trivial subclassing fix, so the duplication is contained — but the two `__reduce__` implementations must now be kept in sync by hand. |
| 2 | Info | `src/cachetools/_acached.py`, `src/cachetools/_acachedmethod.py` | Neither `acached()` nor `acachedmethod()` has `lock`/`condition` parameters, so concurrent tasks awaiting the same uncached key both call the wrapped coroutine and race to store the result — a cache stampede. Acknowledged by a `# TODO` in `_acached.py` (referenced from `_acachedmethod.py`); acceptable for an initial async implementation but worth tracking as a known gap versus the sync decorators. |
| 3 | Info | `src/cachetools/aio.py` | `info` is keyword-only (`*, info=False`) on both async decorators, unlike the positional-or-keyword `info` on `cached()`/`cachedmethod()`. Intentional per an in-code comment ("require to pass `info` as kwargs for now for future extensions") to leave room for new parameters; a deliberate, documented API inconsistency rather than an oversight. |
| 4 | Info | `src/cachetools/aio.py` `acachedmethod()` | No eager `cache is None` check, unlike `acached()`, which raises `TypeError("cache must not be None")` at decoration time. This matches sync `cachedmethod()` (the `cache` argument is a callable, so it can only be validated per instance) and fails late instead — covered by `NoneMethodTest`. Consistent with the sync API, inconsistent within `aio`. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `AutospecTest` in `test_acachedmethod.py` is `@unittest.skip`-ped (`create_autospec` returns an `AsyncMock` for async functions), so the class-level-access contract that `_MethodDescriptor.__get__` exists to support is unverified for `@acachedmethod`. The sync test still covers the descriptor itself, so this is a coverage gap rather than a correctness risk. |
| 2 | Info | `_MethodDescriptor.__set_name__` accepts re-binding to the *same* name and only rejects a *different* one; only the rejecting branch is exercised (`test_decorator_different_names`). |
| 3 | Info | `ClassMethodTest` (in both `test_cachedmethod.py` and `test_acachedmethod.py`) has two tests that now assert the same `TypeError`; only the message differs by Python version. Could be collapsed, but the split documents the pre/post-3.13 behavior. |
| 4 | Info | There is no async counterpart to `test_threading.py`. Reasonable while the async decorators have no lock/condition support, but the stampede behavior in Async item 2 is therefore unasserted — a regression test would pin down the current semantics before they change. |

## Docs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `docs/index.rst` has no `.. versionchanged:: 8.0` entry documenting that `cache_info` is unavailable when `info=False`, even though `CHANGELOG.rst` flags it as a breaking change. |
| 2 | Low | Pickling objects with cached methods is a supported, tested feature (unlike cache pickling), but this isn't documented anywhere — including the caveat that `cache_info()` counters reset on unpickling. |
| 3 | Low | `condition` docs say it must provide `wait()`, `wait_for()`, `notify()` and `notify_all()`, but only `wait_for()` and `notify_all()` are used at runtime. The `_AbstractCondition` protocol could be relaxed. |
| 4 | Low | `docs/index.rst` does not mention the `cachetools.aio` module at all — `acached` and `acachedmethod` are undocumented, so the async API ships without reference docs. |
| 5 | Info | Neither the `cachedmethod` docs nor the stubs mention that class-level access returns the bare wrapper, even though `AutospecTest` treats it as a contract for `mock.patch(autospec=True)`. |

## Keys & Func Modules

No issues found. `func.py` correctly uses
`threading.Condition()` for all decorators, providing stampede prevention by
default. `_UnboundTTLCache` cleanly extends `TTLCache` with `math.inf` maxsize
for the `maxsize=None` case.
