# Code Review — cachetools 8.0.0 (in development)

**Date:** 2026-09-17
**Reviewed:** `develop` @ `f87cf42`
**Validation:** `tox -e py` passed (352 tests, 100% coverage); `tox -e pyright` passed (0 errors)
**CI status:** All green (`tox`: py, docs, doctest, pyright, ruff, ruff-format);
351 passed / 1 skipped, coverage 99% on Python 3.11 (100% on ≥ 3.13)

## Code — Potential Issues

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `src/cachetools/_cachedmethod.py` condition variants | Stampede prevention uses per-instance pending sets. Two instances sharing one cache+condition won't coordinate pending keys across instances. |
| 2 | Info | `Cache.__setitem__` / `__delitem__` | Size accounting assumes value size is stable after insert. In-place mutation of cached values can desync `currsize`. By design (documented), but a known footgun. |
| 3 | Info | `cached()` in `src/cachetools/__init__.py` | The guard is `None`-only, and `TypeError("cache must not be None")` says exactly that — no overpromising. The residual asymmetry is that every *other* invalid cache (`cached(42)`, `cached([])`, `cached("str")`) is still accepted at decoration time and fails later with `'int' object is not subscriptable`, `list indices must be integers...`, etc. Tracked by the `# TODO`; fine to leave as-is for 8.0. |
| 4 | Info | `_WrapperBase.__init__` | `self.__wrapped__ = method` is immediately redundant with `functools.update_wrapper(self, method)`; it exists only to silence pyright (`FIXME` comment in place). Worth revisiting if the pyright/typeshed situation improves. |
| 5 | Info | `_WrapperBase.__reduce__` | Correctness depends on the `cache`/`lock`/`cond` getters staying lazy: on unpickling, `getattr()` runs while the instance `__dict__` is still empty, so an eager `cache(obj)` in a wrapper `__init__` would break round-tripping. |
| 6 | Info | `_WrapperBase.__reduce__` | Rebuilding through `getattr()` discards wrapper state: `*Info` hit/miss counters reset to zero, and a `_Condition*Wrapper`'s pending set is recreated empty. Accepted and covered by `test_decorator_pickle_info`; see Docs item 2 for the corresponding documentation gap. |
| 7 | Info | `src/cachetools/_cachedmethod.py` / `src/cachetools/_cached.py` condition variants | Same-thread recursive re-entry on the same key can deadlock (`wait_for` on own pending marker). |
| 8 | Info | `_Timer.__reduce__`, `TTLCache.__setstate__`, `CacheTestMixin.test_pickle*` | Caches are picklable and the behavior is unit-tested, but pickling is **not** an officially supported or documented feature. The pickled state is raw instance `__dict__` content with no version marker, so any release — including a bugfix release — may silently break compatibility. Pickled caches must only be restored with the exact version that produced them. Keep it undocumented; do not build features on it. |
| 9 | Info | `_TimedCache._Timer.__getattr__` | `__getattr__` resolves through `self.__timer`, so an instance whose `__init__` never ran recurses until `RecursionError` instead of raising `AttributeError`. Unreachable today — `__reduce__` rebuilds via `__init__`, covering both `pickle` and `copy` — but a trap for any future change to `_Timer` construction. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_MethodDescriptor.__set_name__` accepts re-binding to the *same* name and only rejects a *different* one; only the rejecting branch is exercised (`test_decorator_different_names`). |
| 2 | Info | `ClassMethodTest` has two tests that now assert the same `TypeError`; only the message differs by Python version. Could be collapsed, but the split documents the pre/post-3.13 behavior. |

## Docs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `docs/index.rst` still has no `.. versionchanged:: 8.0` entry for the removal of the `cache_info` attribute when `info=False`, although `CHANGELOG.rst` flags it as potentially breaking. Now that `cached` finally has an 8.0 block, the omission is conspicuous. |
| 2 | Low | Restored pickling of objects with cached methods (issue #417) is changelog-only. Unlike cache pickling this *is* a supported, tested feature, so the `cachedmethod` 8.0 `versionchanged` block is the natural place to state it — including the caveat that `cache_info()` counters reset on unpickling. |
| 3 | Low | `condition` docs say it must provide `wait()`, `wait_for()`, `notify()` and `notify_all()`, but only `wait_for()` and `notify_all()` are used at runtime. The `_AbstractCondition` protocol could be relaxed. |
| 4 | Info | Neither the `cachedmethod` docs nor the stubs mention that class-level access returns the bare wrapper, even though `AutospecTest` treats it as a contract for `mock.patch(autospec=True)`. |

## Keys & Func Modules

No issues found, and no changes in the 8.0.0 cycle. `func.py` correctly uses
`threading.Condition()` for all decorators, providing stampede prevention by
default. `_UnboundTTLCache` cleanly extends `TTLCache` with `math.inf` maxsize
for the `maxsize=None` case.
