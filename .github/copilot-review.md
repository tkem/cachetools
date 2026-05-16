# Code Review — cachetools 7.1.1

**Date:** 2026-05-16
**CI status:** All green (281 tests, ruff lint/format, pyright, 58 doctests)

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

No issues. `cachedmethod` stubs use `Concatenate[Any, _P]` to strip
`self` from `ParamSpec`, and `_cachedmethod_wrapper` models the
descriptor protocol (`__set_name__`, `__get__`, `__call__`). Overload
ordering is correct (`Literal[True]` before `Literal[False]` default).

## Code — Potential Issues

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__init__` | `maxsize` is not validated. Negative values cause confusing `popitem` errors at insertion time rather than a clear early `ValueError`. |
| 2 | Low | `Cache.__setitem__`/`__delitem__` | Size accounting assumes value size is stable after insert. In-place mutation of cached values can desync `currsize`. By design, but a known footgun. |
| 3 | Low | `_cachedmethod.py` condition variants | Stampede prevention uses per-instance pending sets. Two instances sharing one cache+condition won't coordinate pending keys across instances. |
| 4 | Info | `_cachedmethod.py` / `_cached.py` condition variants | Same-thread recursive re-entry on the same key will deadlock (`wait_for` on own pending marker). |

No implementation bugs found.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Medium | Threading tests join workers without timeout (`test_threading.py`), so a deadlock regression hangs CI instead of failing. |
| 2 | Medium | Lock-only race resolution (`cache.setdefault` in locked wrappers) is not stress-tested under real concurrency — only condition-based wrappers have threading tests. |
| 3 | Low | `@cached` condition wrappers lack an error-path test (pending cleanup on exception). Equivalent coverage exists for `@cachedmethod` in `test_cachedmethod.py` but not for `@cached` in `test_cached.py`. |
| 4 | Low | `CacheTestMixin` assertions are intentionally weak on eviction-order correctness (checks key existence, not specific eviction victim), relying on per-cache test files for policy validation. |

## Keys & Func Modules

No issues found.
