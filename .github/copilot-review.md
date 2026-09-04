# Code Review — cachetools 8.0.0 (in development)

**Date:** 2026-09-05
**Reviewed:** `dev/v8.0.0` @ 54a5e48 (drops Python 3.10 and `@cachedmethod` + `@classmethod` support)
**CI status:** All green (tox: py, docs, doctest, pyright, ruff, ruff-format)

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

## Code — Potential Issues (checked against dev/v8.0.0)

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes value size is stable after insert. In-place mutation of cached values can desync `currsize`. By design (documented), but a known footgun. |
| 2 | Low | `src/cachetools/_cachedmethod.py` condition variants | Stampede prevention uses per-instance pending sets. Two instances sharing one cache+condition won't coordinate pending keys across instances. |
| 3 | Info | `src/cachetools/_cachedmethod.py` / `src/cachetools/_cached.py` condition variants | Same-thread recursive re-entry on the same key can deadlock (`wait_for` on own pending marker). |
| 4 | Info | `_Timer.__reduce__`, `TTLCache.__setstate__`, `CacheTestMixin.test_pickle*` | Caches are picklable and the behavior is unit-tested, but pickling is **not** an officially supported or documented feature. The pickled state is raw instance `__dict__` content with no version marker, so any release — including a bugfix release — may silently break compatibility. Pickled caches must only be restored with the exact version that produced them. Keep it undocumented; do not build features on it. |
| 5 | Info | `_DescriptorBase.__call__` | The `TypeError` is only reachable on Python ≥ 3.13 via `@classmethod`; on earlier versions the descriptor is simply never invoked that way. The comment above it explains this, but the message ("Decorating class methods with @cachedmethod is not supported") also surfaces for any other accidental direct call of a descriptor instance. Acceptable, but slightly over-specific. |

No implementation bugs found beyond the items above.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `@cached` condition wrappers lack an error-path test (pending cleanup on exception). Equivalent coverage exists for `@cachedmethod` (`test_decorator_cond_error`) but not for `@cached`. |
| 2 | Low | `test_cached.py`: zero-size + condition + `info=True` combination is not tested (zero-size only tested for no-lock and lock variants). |
| 3 | Low | `test_lfu.py`: no tie-breaking test for equal-frequency eviction (current code picks an arbitrary element via `next(iter(curr.keys))`). |
| 4 | Resolved | `test_cachedmethod.py::test_decorator_no_set_name` no longer justifies itself with the removed `@classmethod` path, and now covers both the plain and the `info=True` variant. |
| 5 | Info | `ClassMethodTest` has two tests that now assert the same `TypeError`; only the message differs by Python version. Could be collapsed, but the split documents the pre/post-3.13 behavior. |
| 6 | Info | `CacheTestMixin` assertions are intentionally weak on eviction-order correctness (checks key existence, not specific eviction victim). This is by design — the mixin is shared across all cache types, and policy-specific validation lives in the per-cache test files. No action needed. |

## Docs

| # | Priority | Finding |
|---|----------|---------|
| 1 | Resolved | The `.. deprecated:: 7.0` block in `docs/index.rst` was replaced by a `.. versionchanged:: 8.0` note documenting that both `@cachedmethod` + `@classmethod` and instances without a mutable `__dict__` now raise `TypeError`. |
| 2 | Low | `condition` docs say it must provide `wait()`, `wait_for()`, `notify()` and `notify_all()`, but only `wait_for()` and `notify_all()` are used at runtime. The `_AbstractCondition` protocol could be relaxed. |
| 3 | Info | Pickling is correctly absent from the docs and should stay that way — see code finding #4. |

## Packaging / CI

`pyproject.toml` (`requires-python`, classifiers) and
`.github/workflows/ci.yml` (matrix: 3.11, 3.12, 3.13, 3.13t, 3.14, 3.14t,
pypy3.11) agree on the 3.11 floor. `src/cachetools.egg-info/SOURCES.txt`
still lists the deleted `tests/test_classmethod.py`, but that file is
generated build metadata and regenerates on the next build — no action needed.

`CHANGELOG.rst` is intentionally untouched; both breaking changes must be
recorded by the maintainer at release time.

## Keys & Func Modules

No issues found. `func.py` correctly uses `threading.Condition()` for
all decorators, providing stampede prevention by default. `_UnboundTTLCache`
cleanly extends `TTLCache` with `math.inf` maxsize for the
`maxsize=None` case.
