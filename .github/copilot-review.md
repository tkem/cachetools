# Code Review — cachetools 8.0.0 (unreleased)

**Date:** 2026-10-23
**Reviewed:** `dev/v8.0.0` at `7f434b8` (`__version__` 8.0.0) against `master`
(`6f23e2a`, v7.2.4). The branch was rebased onto `develop`, which carries the v7.2.5 work: the
`pending` keyword fix (`36d4e87`), documentation corrections (`4af71c4`) and the
class-access receiver fix (`21ebe67`): `_Unbound.__call__` accepts the receiver as a
keyword argument, popping the wrapped method's first parameter by name when no
positional argument is given (resolved lazily via `inspect.signature` on that path
only), pinned by `test_class_call_keyword_receiver`. v8's mixins keep pending keys in
a name-mangled attribute, so they never had the v7 `pending` bug; its test
`test_cond_pending_keyword` passes unmodified (verified for `info=False` and
`info=True`). `CHANGELOG.rst` carries the v7.2.5 section below v8.0.0. The other
sections are carried over from the previous review, with line numbers in *Docs*
updated.

**CI status:** All `tox` environments pass locally at `7f434b8` (`tox -p auto`, local
`py` environment is Python 3.14): `py` (389 passed), `docs` and `doctest` (58 tests,
both with `-W`), `pyright` (0 errors), `ruff`, `ruff-format`. Other versions, the
free-threaded builds and PyPy were not run locally.

**Coverage:** `tox` measures line and branch coverage (`--cov-branch` in `tox.ini`),
which CI uploads to Codecov.  99% locally on 3.14 (974 statements, 168 branches): the
one missed line and partial branch is the pre-3.13 `@classmethod` check
(`_descriptor.py:32`), reached only on 3.11/3.12, so 100% is attained across the CI
matrix as intended.

## Code — Potential Issues

No functional regressions found. All items are design trade-offs or edge cases;
none blocks the release.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `_MethodDescriptor.__get__` (`super()` path) | `super().method` never hits the instance dict, so every call builds a throw-away wrapper (including `functools.update_wrapper`) and rescans the MRO before `setdefault` returns the stored one. Correct, but noticeably slower than the primary path. |
| 2 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place can desync `currsize`. By design and documented, but a known footgun. |
| 3 | Low | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` | Stampede prevention uses a pending set per wrapper, i.e. per instance for `@cachedmethod`. Two instances sharing one cache and condition do not coordinate pending keys. |
| 4 | Info | `_MethodDescriptor.__get__` | `copy.copy(obj)` shallow-copies `obj.__dict__`, so the copy shares the original's wrapper, still bound to the original `obj` (`a2.get is a.get`).  `copy.deepcopy` and `pickle` are fine.  Accepted, `functools.cached_property` semantics; the data-descriptor fix was rejected for its per-call cost (*Maintainer Decisions* in `copilot-instructions.md`). |
| 5 | Info | `_descriptor.py` / `_cachedmethod.py` `_wrapper` | Stacked `@cachedmethod` silently uses the inner cache only, because `functools.update_wrapper(descriptor, method)` copies the inner descriptor's private state onto the outer one.  Stacking is unsupported and untested (*Maintainer Decisions* in `copilot-instructions.md`). |
| 6 | Info | `_descriptor.py` `_Unbound.__call__` | By design (see its docstring), autospec'd instances accept any arguments: `inspect.signature(mock.method)` is `(*args, **kwargs)` and `mock.method(1, 2)` does not raise for a one-parameter method (verified).  Autospec no longer checks call arity for `@cachedmethod` methods. |
| 7 | Info | `_cachedmethod.py` `_WrapperBase` | `inspect.signature(obj.method)` reports `(self, value)` for a `@cachedmethod` wrapper, because `__wrapped__` is the unbound function and the wrapper is a callable object rather than a `MethodType`. `@cached` on a method yields `(value)` since `__get__` returns a real bound method. Frameworks that `bind()` call arguments against the signature will see a spurious `self` parameter. Setting `__wrapped__` to the bound partial would fix introspection but break the documented `wrapper.__wrapped__(self, ...)` contract; a per-instance `__signature__` costs time on every first access. Document rather than fix. |
| 8 | Info | `_WrapperBase.__reduce__` | Unpickling resets `hits`/`misses` of `info=True` wrappers (documented in the code and asserted by `test_decorator_pickle_info`). Acceptable, since counters are a tuning aid. |
| 9 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | Pickles reference `cachetools._descriptor._MethodDescriptor._lookup` by qualified name, so that path must stay importable for pickles to load across releases (same constraint as `@cached` pickling by `__qualname__`). `_lookup` also resolves through the owner's *current* class dict: a pickle loaded while `Cls.method` is reassigned (verified with `unittest.mock.patch.object`) silently yields a bound method of the replacement instead of a wrapper. |
| 10 | Info | `_MethodDescriptor.__reduce__` | A descriptor that never received `__set_name__` reduces to `_lookup(None, None)`: `pickle.dumps` succeeds, `pickle.loads` raises `AttributeError`. Such a descriptor is unusable anyway. |
| 11 | Info | `_MethodDescriptor.__set_name__` | Assigning one descriptor to the same attribute name in two classes keeps the first owner silently (verified: the second owner's instances work and store the wrapper under the same name; `_lookup` resolves through the first owner). Harmless as long as the first class keeps the attribute; the accepted case is pinned by `test_decorator_same_name`. |
| 12 | Info | `_cachedmethod.py` `_WrapperBase` | Each per-instance wrapper references `obj`, and `obj.__dict__` references the wrapper, so instances with active wrappers are freed only by the cyclic GC, not by reference counting (verified with `gc.disable()` and a weakref). Expected for this design; worth knowing for large or short-lived instances. |
| 13 | Info | `_decorator.py` condition mixins | Same-thread recursive re-entry on the same key deadlocks (`wait_for` on its own pending marker). |
| 14 | Info | `_MethodDescriptor.__get_unbound` / `__call__` | Lazy creation of the cached `_Unbound` object is unsynchronized; concurrent first class accesses may briefly see distinct (equivalent) objects. Benign. Two error messages are misleading at the margins: `Cls.method(None, 1)` reports "No `__dict__` attribute on 'int' instance" (the `None` receiver makes `__get__` return the `_Unbound` object, which then takes `1` as its receiver), and calling the raw descriptor from `Cls.__dict__` reports "Decorating class methods is not supported". |
| 15 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a key that is present but expired removes it and then raises `KeyError`. Consistent with `key in cache` being `False`; intentional. Neither `__delitem__` calls `expire()` (verified), unlike `__setitem__`, `__len__`, `__repr__`, `currsize` and `popitem`. |
| 16 | Info | `Cache.__setitem__` | With `maxsize=math.inf` and a `getsizeof` returning `math.inf`, the value is accepted (`inf > inf` is false), `currsize` becomes `inf`, and deleting the item leaves `currsize = nan`. Only non-negative sizes are validated. Pathological input; not worth a check on the hot path. |
| 17 | Info | `TLRUCache.__iter__` | Iterates the expiry heap, so `list(cache)` is in heap order (verified: inserting 1, 2, 3 with ttu 30/10/20 yields `[2, 1, 3]`), while `TTLCache` iterates in expiry (= insertion) order and `popitem()` uses LRU order. No ordering is documented; fine, but surprising next to `TTLCache`. |

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `@classmethod` stacked over `@cached`/`func.*_cache` still reports a false "Argument missing" error. Python passes `cls` correctly at runtime, but pyright does not bind through the wrapper's `__get__` there. Rare and not encouraged. |
| 2 | Info | `_cached_wrapper_info.__get__` carries `# pyright: ignore[reportIncompatibleMethodOverride]`. Pyright cannot match the subclass overloads against the base's self-typed `Concatenate` overload. The override is sound. |
| 3 | Info | `func.pyi` `_cachetools_cache_wrapper` exposes only the `functools.lru_cache`-compatible API (`cache_info`, `cache_clear`, `cache_parameters`), while the runtime wrapper, being built on `cached(...)`, also has `cache`, `cache_key`, `cache_lock` and `cache_condition`. Those are undocumented for `cachetools.func`, so hiding them is defensible; just be aware that user code touching `lru_cache(...)(f).cache` type-checks only with a cast. |
| 4 | Info | `TTLCache.__init__`'s second overload types `ttl: Any` with the comment `must be "addable" to _TT`. It documents a real limitation of the type system (no "addable to `_TT`" constraint), so `Any` is deliberate. |
| 5 | Info | `info: bool` (non-literal) arguments to `cached`/`cachedmethod`, as in `test_threading.py`, type-check only because pyright expands `bool` into `Literal[True] | Literal[False]` when matching overloads. mypy does not, so mypy users passing a `bool` variable will see "no overload matches". The project targets pyright only. |
| 6 | Info | `_cachedmethod_unbound.__call__` takes the receiver positional-only, so `Cls.method(self=obj, value=1)`, which the runtime accepts, is a pyright error; the receiver's name is not expressible in the stub (`Concatenate[Any, _P]` erases it), so `test_class_call_keyword_receiver` carries `# type: ignore` on those calls. |

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | No test checks that `copy.copy(obj)` gets its own wrapper, or pins the current sharing behavior (Code #4). |
| 2 | Low | `UnboundMethodTest` does not assert that class access exposes no `cache_clear`/`cache_info` (verified: both `hasattr` checks are `False`), and does not exercise class access for the lock/condition variants. |
| 3 | Low | The pickle tests use the default protocol only. Protocols 0–5 were verified by hand; a `subTest` loop over `range(pickle.HIGHEST_PROTOCOL + 1)` would pin this, as `tests/__init__.py` does for caches. |
| 4 | Info | `test_threading.py` `run_cond_test` asserts `misses == 1`, but nothing forces the threads to overlap (the lock tests use a `Barrier` inside the function; a condition-guarded function cannot, since only one thread enters). `misses == 1` would also hold if the threads happened to run sequentially, so the test demonstrates correctness but cannot detect a broken stampede guard. Hard to fix deterministically; note only. |
| 5 | Info | `CacheTestMixin` deliberately checks key existence rather than the specific eviction victim; policy-specific checks live in the per-cache test files. No action needed. |
| 6 | Info | `test_func.py` calls decorators through `Callable[..., Any]`; one concrete test (`FIFODecoratorTest.test_method_typed`) covers the shared `_cachetools_cache_wrapper` stub. Enough. |

## Docs — `docs/index.rst`

`tox -e docs` and `tox -e doctest` pass with `-W` at `7f434b8`. The text is clear and
consistent (two spaces after sentences, single backticks for parameters and
expressions, `versionchanged` entries for 7.0 and 8.0, `:meth:`/`:func:`/`:exc:`
roles by kind). Every doctest expectation was re-derived by hand (LRU eviction order
in `PepStore`, both `CacheInfo` values, the Fibonacci/Lucas sums) and matches.
Behavioral claims were checked against the source: `FIFOCache.__setitem__` re-inserts
(`move_to_end`), `LFUCache.__setitem__` touches an existing key, `__missing__` is
called from `Cache.__getitem__`, `expire()` returns a list, `cache_parameters()`
reports only `maxsize` and `typed`, and the Python 3.11/3.13 dates for descriptor
chaining in `classmethod` are right. Link resolution was verified by scanning the
built HTML for `xref` nodes that are not wrapped in a link.

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `cachedmethod` section | The docs do not mention that class access (`Cls.method`) yields a plain callable without `cache_clear()`/`cache_info()`, that `copy.copy()` of an instance shares its wrappers (Code #4), that pickling an instance resets its `cache_info()` counters, or that `inspect.signature()` of a bound wrapper still shows `self` (Code #7). |
| 2 | Low | `Cache` pickling note (lines 81–88) | Says the cache classes "can generally be pickled" without saying what the exception is. Verified with a probe: pickling fails with `PicklingError` for a `getsizeof`, `timer` or `ttu` callable that is itself unpicklable, e.g. a lambda; the defaults and module-level functions such as `len` work. Suggest "can be pickled, provided that any `getsizeof`, `timer` or `ttu` callable is picklable". |
| 3 | Low | lines 561–567 | The `info` parameter of `cachedmethod` is never explained; "an optional :meth:`cache_info()` function" leaves the reader to infer it from the example. Suggest "and, if `info` is :const:`True`, a :meth:`cache_info()` function reporting per-instance cache statistics". "Similarly to the :func:`cached` function decorator" reads better as "As with the :func:`cached` function decorator". |
| 4 | Info | lines 43, 74–75, 226, 245–248 | References without a documented target, rendered as plain code (cosmetic): `:meth:`self.popitem()`` shows literally as "self.popitem()"; `popitem` and `expire` in "Extending cache classes" are outside any class; `Cache` has no `popitem` of its own (it inherits `MutableMapping.popitem`), so it is not in `:members:` and `Cache.popitem` is not a target either. |
| 5 | Info | lines 752, 759, 768 | The `env={}` mutable default argument is a well-known trap (ruff `B006` flags it in user code). It is harmless in these examples, but examples get copied. |
| 6 | Info | line 837 | `rr_cache` shows a `choice` parameter in its signature that the text never describes (it is the `RRCache` `choice` function; ignored for `maxsize=None`). |
| 7 | Info | `cached` section, `cachetools.func` section | Neither mentions that these decorators may decorate methods. Worth a one-line caveat that the cache and counters are then shared across all instances, unlike `@cachedmethod` (verified: two instances share one `CacheInfo`). |
| 8 | Info | line 264 | The `ExpCache` doctest calls `time.sleep(1.5)`, which accounts for most of the `doctest` environment's runtime. A `Timer` object as in `tests/test_ttl.py` would make the example deterministic and instant, at the cost of a few more lines. |

## Keys & Func Modules

No issues found. `hashkey`/`typedkey` sort keyword arguments and cache the hash in
`_HashedTuple`, which is not pickled. Every `func.py` decorator is built on
`cached(..., condition=Condition(), info=True)`, so stampede prevention is on by
default, and `Condition()`'s default `RLock` keeps `test_decorator_needs_rlock`
passing. `_UnboundTTLCache` extends `TTLCache` with `math.inf` maxsize for
`maxsize=None`; `rr_cache(maxsize=None)` ignores `choice`, which is correct since an
unbounded `dict` never evicts.

## Packaging, CI and Tooling

No issues found. `pyproject.toml` requires `setuptools-scm` only for git-based sdist
file discovery (the version comes from `cachetools.__version__`), and `MANIFEST.in`
prunes `.github/`. The `ruff` rule set is the ruff default (currently a broad
preset including `UP`, `PYI`, `RUF`, `PL*`, `B`, `SIM`, `DTZ`, …); the two entries in
`[tool.ruff.lint] ignore` (`DTZ005`, `UP031`) are therefore effective. CI pins
actions by SHA with Dependabot grouping monthly updates against `develop`; the
matrix matches the classifiers (3.11–3.15, 3.13t–3.15t, PyPy 3.11). Codecov needs
the explicitly installed `coverage` package to convert `.coverage` to XML.
