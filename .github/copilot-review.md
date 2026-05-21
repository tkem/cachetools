# Code Review — cachetools 7.1.4

**Date:** 2026-05-22
**CI status:** All green (tox: py, ruff, ruff-format, pyright, docs, doctest)

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

No issues. `cached` and `cachedmethod` stubs use `ParamSpec(_P)` to
preserve decorated function signatures (`__call__` uses `_P.args`/`_P.kwargs`).
`cachedmethod` stubs use `Concatenate[Any, _P]` to strip `self` from
`ParamSpec`, and `_cachedmethod_wrapper` models the descriptor protocol
(`__set_name__`, `__get__`, `__call__`). Overload ordering is correct
(`Literal[True]` before `Literal[False]` default).

`func.pyi` deliberately uses `Callable[..., _R]` instead of `ParamSpec`
for `_cachetools_cache_wrapper` since the `func.*_cache` decorators
rewrite signatures (adding `cache_info`, `cache_clear`, `cache_parameters`).

## Code — Potential Issues

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__init__` | `maxsize` is not validated. Negative values cause confusing `popitem` errors at insertion time rather than a clear early `ValueError`. Docs note `maxsize` must be positive, but code does not enforce it. |
| 2 | Low | `Cache.__setitem__`/`__delitem__` | Size accounting assumes value size is stable after insert. In-place mutation of cached values can desync `currsize`. By design (documented), but a known footgun. |
| 3 | Low | `_cachedmethod.py` condition variants | Stampede prevention uses per-instance pending sets. Two instances sharing one cache+condition won't coordinate pending keys across instances. |
| 4 | Info | `_cachedmethod.py` / `_cached.py` condition variants | Same-thread recursive re-entry on the same key will deadlock (`wait_for` on own pending marker). |

No implementation bugs found.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `@cached` condition wrappers lack an error-path test (pending cleanup on exception). Equivalent coverage exists for `@cachedmethod` (`test_decorator_cond_error`) but not for `@cached`. |
| 2 | Low | `CacheTestMixin` assertions are intentionally weak on eviction-order correctness (checks key existence, not specific eviction victim), relying on per-cache test files for policy validation. |
| 3 | Low | `test_cached.py`: zero-size + condition + `info=True` combination is not tested (zero-size only tested for no-lock and lock variants). |
| 4 | Low | `test_lfu.py`: no tie-breaking test for equal-frequency eviction (current code picks an arbitrary element via `next(iter(curr.keys))`). |
| 5 | Low | `test_classmethod.py`: limited coverage — only deprecation warnings + basic functionality. No `info=True`, error-path, or shared-cache tests. |

## Docs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `condition` docs say it must provide `wait()`, `wait_for()`, `notify()` and `notify_all()`, but only `wait_for()` and `notify_all()` are used at runtime. The `_AbstractCondition` protocol in stubs includes all four for compatibility with `threading.Condition`. |
| 2 | Info | PEP URLs in examples use legacy `http://www.python.org/dev/peps/` (moved to `peps.python.org`), but these are mocked in doctests so functionally irrelevant. |

## Keys & Func Modules

No issues found. `func.py` correctly uses `threading.Condition()` for
all decorators, providing stampede prevention by default. `_UnboundTTLCache`
cleanly extends `TTLCache` with `math.inf` maxsize for the
`maxsize=None` case.
