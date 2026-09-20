# Code Review — cachetools 8.0.0 (in development)

**Date:** 2026-10-05
**Reviewed:** `dev/v8.0.0` @ `14d387e` (the only commit since the last review, `0277033`,
is `14d387e` itself — a documentation-only refresh of `copilot-instructions.md`/
`copilot-review.md`; no source changes to re-review)
**Validation:** `tox -e py` passed (353 tests, 100% coverage on Python 3.14);
`tox -e pyright` passed (0 errors)
**CI status:** All green (`tox`: py, docs, doctest, pyright, ruff, ruff-format)

## Changed Since Last Review

No source changes since `0277033`. All findings below were re-verified
line-by-line against the current code and remain accurate.

## Code — Potential Issues

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `src/cachetools/_cachedmethod.py` condition variants | Stampede prevention uses per-instance pending sets. Two instances sharing one cache+condition won't coordinate pending keys across instances. |
| 2 | Info | `Cache.__setitem__` / `__delitem__` | Size accounting assumes value size is stable after insert. In-place mutation of cached values can desync `currsize`. By design (documented), but a known footgun. |
| 3 | Info | `cached()` in `src/cachetools/__init__.py` | The guard is `None`-only, and `TypeError("cache must not be None")` says exactly that — no overpromising. The residual asymmetry is that every *other* invalid cache (`cached(42)`, `cached([])`, `cached("str")`) is still accepted at decoration time and fails later with `'int' object is not subscriptable`, `list indices must be integers...`, etc. Fine to leave as-is for 8.0. |
| 4 | Low | `src/cachetools/_decorator.py`: `_InfoMixin.cache_info()`, `_LockedInfoMixin.cache_info()`, `_ConditionInfoMixin.cache_info()` | Leftover dead code from the `CacheInfo.maker()` removal: each method still carries a commented-out `# return self.__info(self.__hits, self.__misses)` line (the old 2-arg closure call), inconsistently placed before the live `return` in two methods and after it in the third. Harmless but should be deleted as cleanup. |
| 5 | Info | `CacheInfo.make` in `src/cachetools/__init__.py` | Carries the author's own `# TODO: rename make() from_...()?` comment, left in from the refactor. Naming bikeshed, not a defect. |
| 6 | Info | `src/cachetools/_cachedmethod.py`: `_WrapperBase.__init__` | `functools.update_wrapper(self, method)` runs once per per-instance wrapper (built on first attribute access via the descriptor), in addition to the `functools.update_wrapper(descriptor, method)` already done once in `_wrapper()` for the class-level descriptor — both copy the same metadata from `method`, so the per-instance call looks redundant. Marked with the author's own `# FIXME: cannot be moved to _wrapper()?`; not a bug, just an open question about whether it can be hoisted. |
| 7 | Info | `_WrapperBase.__reduce__` | Correctness depends on the `cache`/`lock`/`cond` getters staying lazy: on unpickling, `getattr()` runs while the instance `__dict__` is still empty, so an eager `cache(obj)` in a wrapper `__init__` would break round-tripping. |
| 8 | Info | `_WrapperBase.__reduce__` | Rebuilding through `getattr()` discards wrapper state: `*Info` hit/miss counters reset to zero, and a `_Condition*Wrapper`'s pending set is recreated empty. Accepted and covered by `test_decorator_pickle_info`; see Docs item 2 for the corresponding documentation gap. |
| 9 | Info | `src/cachetools/_decorator.py` condition mixins (shared by `_cached.py` / `_cachedmethod.py`) | Same-thread recursive re-entry on the same key can deadlock (`wait_for` on own pending marker). |
| 10 | Info | `_Timer.__reduce__`, `TTLCache.__setstate__`, `CacheTestMixin.test_pickle*` | Caches are picklable and the behavior is unit-tested, but pickling is **not** an officially supported or documented feature. The pickled state is raw instance `__dict__` content with no version marker, so any release — including a bugfix release — may silently break compatibility. Pickled caches must only be restored with the exact version that produced them. Keep it undocumented; do not build features on it. |
| 11 | Info | `_TimedCache._Timer.__getattr__` | `__getattr__` resolves through `self.__timer`, so an instance whose `__init__` never ran recurses until `RecursionError` instead of raising `AttributeError`. Unreachable today — `__reduce__` rebuilds via `__init__`, covering both `pickle` and `copy` — but a trap for any future change to `_Timer` construction. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_MethodDescriptor.__set_name__` accepts re-binding to the *same* name and only rejects a *different* one; only the rejecting branch is exercised (`test_decorator_different_names`). |
| 2 | Info | `ClassMethodTest` has two tests that now assert the same `TypeError`; only the message differs by Python version. Could be collapsed, but the split documents the pre/post-3.13 behavior. |

## Docs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `docs/index.rst` has no `.. versionchanged:: 8.0` entry documenting that `cache_info` is unavailable when `info=False`, even though `CHANGELOG.rst` flags it as a breaking change. |
| 2 | Low | Pickling objects with cached methods is a supported, tested feature (unlike cache pickling), but this isn't documented anywhere — including the caveat that `cache_info()` counters reset on unpickling. |
| 3 | Low | `condition` docs say it must provide `wait()`, `wait_for()`, `notify()` and `notify_all()`, but only `wait_for()` and `notify_all()` are used at runtime. The `_AbstractCondition` protocol could be relaxed. |
| 4 | Info | Neither the `cachedmethod` docs nor the stubs mention that class-level access returns the bare wrapper, even though `AutospecTest` treats it as a contract for `mock.patch(autospec=True)`. |

## Keys & Func Modules

No issues found. `func.py` correctly uses
`threading.Condition()` for all decorators, providing stampede prevention by
default. `_UnboundTTLCache` cleanly extends `TTLCache` with `math.inf` maxsize
for the `maxsize=None` case.
