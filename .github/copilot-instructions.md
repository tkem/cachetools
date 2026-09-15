# Copilot Instructions for cachetools

## Architecture Overview
**cachetools** provides extensible memoizing collections and decorators, including variants of Python's `@lru_cache`. Pure Python 3.11+, no external runtime dependencies.

### Core Design Pattern
- All caches inherit from `Cache` (a `MutableMapping` with `maxsize`, `currsize`, and `getsizeof`)
- Subclasses override `__setitem__`, `__getitem__`, `__delitem__`, and `popitem()` to implement eviction policies
- **Critical:** Subclasses use default parameter trick (e.g., `cache_setitem=Cache.__setitem__`) to call parent methods efficiently while avoiding recursion
- `Cache.__init__` rejects negative `maxsize` eagerly (`ValueError`); `maxsize=0` (no-space cache) and `math.inf` (unbounded) remain valid
- `Cache.__setitem__` rejects negative `getsizeof` results and values larger than `maxsize` (`ValueError`); when replacing an existing key it evicts until the *new* size fits, recomputing `diffsize` if the key itself gets evicted
- `Cache` rolls its own `get()`/`pop()`/`setdefault()` instead of inheriting them, because the `MutableMapping` defaults assume `__getitem__` raises `KeyError` — untrue when `__missing__` is implemented
- Every subclass overrides `clear()` so it is O(1) instead of the `MutableMapping` O(n) `popitem()` loop; `_TimedCache.clear()` deliberately skips `expire()` for the same reason
- Caches happen to be picklable (`test_pickle`, `test_pickle_maxsize`; `_Timer.__reduce__` and `TTLCache.__setstate__` rebuild time-tracking state), but **pickling is neither officially supported nor documented**. The pickle format is an implementation detail that even a minor or bugfix release may change, so pickled caches must only be unpickled with the exact same `cachetools` version that created them. Do not document, advertise, or build features on pickle compatibility

### Cache Types
- `FIFOCache`: Evicts oldest inserted (`OrderedDict`)
- `LRUCache`: Evicts least recently used (`OrderedDict.move_to_end()`)
- `LFUCache`: Evicts least frequently used; doubly-linked list of `_Link` frequency buckets (`__slots__`, `keys` set) anchored at a sentinel `__root`, plus a `__links` key→bucket dict
- `RRCache`: Random eviction (`__keys` list with `__index` dict for O(1) removal)
- `TTLCache`/`TLRUCache`: Time-based eviction via `_TimedCache` base; `_Timer` context manager freezes time during operations to prevent TOCTOU bugs (re-entrant via `__nesting`, proxies the wrapped timer through `__getattr__`); `expire()` returns `list[tuple[key, value]]`

### Decorators
- `@cached` (`_cached.py`): Function memoization; separate wrappers for each lock/condition/info combination; supports `cache=None` via `_uncached`/`_uncached_info` wrappers (pass-through without caching — note these ignore `lock`/`condition`, which `_wrapper()` nevertheless still publishes as `cache_lock`/`cache_condition`)
- `@cachedmethod` (`_cachedmethod.py`): Method memoization; `_WrapperBase` (per-instance callable, holds `__wrapped__`/cache/key/lock/cond) is subclassed by six explicit wrapper classes — `_UnlockedWrapper`, `_LockedWrapper`, `_ConditionWrapper`, and their `*Info` variants — one per lock/condition/info combination, selected by the `_wrapper()` factory (previously generated dynamically via nested per-combo classes); each `_Condition*Wrapper` keeps a per-instance pending set
- `_MethodDescriptor` (`_descriptor.py`): generic descriptor helper (not `@cachedmethod`-specific, reusable by other decorators) implementing `__set_name__`/`__get__`/`__call__`; wraps a `wrapper(obj, name)` factory passed into its constructor, where `name` is the attribute name recorded by `__set_name__`; replaces itself in the instance `__dict__` via `setdefault` for thread safety; `obj is None` (class access) returns the bare wrapper so `mock.patch(autospec=True)` works
- `_MethodDescriptor` error cases: `__set_name__` raises `TypeError` if the same descriptor is bound to two names; `__get__` raises `TypeError` when the instance has no writable `__dict__` (e.g. `__slots__`) or when `__set_name__` was never called
- `_WrapperBase.__reduce__` makes wrappers (and their owning instances) picklable by rebuilding them via `getattr(obj, name)`, using the attribute name handed down by the descriptor rather than the wrapped function's `__name__`, so aliases (`get_aliased = cachedmethod(...)(__get)`) round-trip correctly; it relies on the `cache`/`lock`/`cond` getters being lazy, since `getattr()` runs while the unpickled instance `__dict__` is still empty. Wrappers obtained through class access (`_obj is None`) have no instance to rebuild from and raise `TypeError` at dump time rather than failing later on load
- Pickling a wrapper does **not** pickle wrapper state: `__wrapped__` and the lock/condition closures are dropped and rebuilt, and `*Info` hit/miss counters reset to zero on load (only the cache itself, pickled as part of the owning instance, survives). This is accepted behavior, not a bug — the counters are debugging/tuning aids. Unlike cache pickling, restoring objects with cached methods *is* a supported, tested feature (re-enabled in 8.0, broken since 7.0)
- Decorating class methods is **not supported** (removed in 8.0): `_MethodDescriptor.__call__` raises a generic `TypeError` ("Decorating class methods is not supported"), which is what Python ≥ 3.13 hits when a `@cachedmethod` descriptor is wrapped in `@classmethod`
- Both support `key`, `lock`, `condition`, and `info` parameters; when `condition` is given without `lock`, `condition` serves as both lock and condition
- `info=True` adds `cache_info()`/`cache_clear()`; `info=False` (default) only provides `cache_clear()`, and accessing `cache_info` raises `AttributeError`.
- `func.py`: `functools.lru_cache`-compatible wrappers; all use `threading.Condition()` by default for thread safety + stampede prevention; `_UnboundTTLCache` extends `TTLCache` with `math.inf` maxsize for `maxsize=None`; each wrapper also gets a `cache_parameters()` function returning `{"maxsize": ..., "typed": ...}`

### Thread Safety
3-tier locking: **Unlocked** | **Locked** (release during compute) | **Condition** (lock + pending set + `wait_for`/`notify_all` to prevent thundering herd)

`_AbstractCondition` protocol in `__init__.pyi`: extends `AbstractContextManager[Any]` + `Protocol` with `wait()`, `wait_for()`, `notify()`, `notify_all()`. Only `wait_for()` and `notify_all()` are used at runtime.

### Key Generation (`keys.py`)
- `hashkey`: Default key function; `_HashedTuple` caches hash values in `__hashvalue`, and its `__getstate__` returns `{}` so the cached hash is never pickled
- `_kwmark = (_HashedTuple,)` separates args from kwargs; using the class itself keeps the sentinel unique and identity-stable across pickling
- `methodkey`: Drops `self` from key; `typedkey`/`typedmethodkey`: Adds `type()` info

## Developer Workflows

### Testing
**Always run tests and checks through `tox`** — never invoke `pytest`, `unittest`, `ruff`, or `pyright` directly.

```bash
tox -e py                                 # Run tests with coverage
tox -e ruff                               # Linting (ruff check)
tox -e ruff-format                        # Format check (ruff format --diff)
tox -e pyright                            # Type checking
tox -e docs                               # Build docs
tox -e doctest                            # Run doctests
```

- `tests/__init__.py`: `CacheTestMixin` (23 standard tests), `_TestCaseProtocol`, `CountedLock`, `CountedCondition` (implements full `_AbstractCondition` protocol)
- Each cache test inherits `unittest.TestCase` + `CacheTestMixin`
- `test_cached.py` / `test_cachedmethod.py` use `DecoratorTestMixin` / `MethodDecoratorTestMixin` for all lock/condition/info combos
- `DecoratorTestMixin` provides `error_func` (always raises `ValueError`) alongside `func`; `test_decorator_cond_error` uses it to verify the pending set is cleaned up when the wrapped function raises, mirroring the method-level `test_decorator_cond_error` in `test_cachedmethod.py`
- The `Cached` fixture in `test_cachedmethod.py` provides one method per wrapper combination plus `get_cond_error` (raises, for pending-set cleanup) and `get_aliased` (descriptor bound to a name other than the function's `__name__`)
- `ClassMethodTest` in `test_cachedmethod.py` asserts that `@cachedmethod` + `@classmethod` raises `TypeError`
- Threading tests (`test_threading.py`) cover both condition-based stampede prevention and lock-only race resolution under real concurrency; `TIMEOUT` class constant + `thread.join(timeout=TIMEOUT)` + `assertFalse(t.is_alive())` guard against deadlock hangs
- CI (`.github/workflows/ci.yml`) runs `tox` on 3.11–3.15 including the free-threaded builds (`3.13t`/`3.14t`/`3.15t`) and `pypy3.11`; coverage is uploaded to Codecov per interpreter
- Coverage is 100% only on Python ≥ 3.13. On older interpreters `test_classmethod` is skipped, leaving `_MethodDescriptor.__call__` (2 lines) uncovered — expected, not a gap to "fix"

### Code Style
- **ruff** formatter and linter (`tox -e ruff-format`, `tox -e ruff`); lint ignores `DTZ005` and `UP031` in `pyproject.toml`
- **pyright** runs in `typeCheckingMode = "standard"`, with `reportFunctionMemberAccess` downgraded to `information` and `reportOptionalContextManager`/`reportOptionalMemberAccess` downgraded to `warning`

## Conventions

### Adding New Cache Types
1. Inherit from `Cache` or `_TimedCache`
2. Override `__setitem__`, `__delitem__`, `popitem()` (optionally `__getitem__`)
3. Use default parameters to call parent: `def __setitem__(self, key, value, cache_setitem=Cache.__setitem__)`
4. Handle `__missing__` edge case: check `if key in self` after parent call
5. Override `clear()` to reset the subclass bookkeeping in O(1)
6. Add test class inheriting `CacheTestMixin`

### Changelog
**Do not edit `CHANGELOG.rst`.** It is updated by the maintainer only, immediately before a release is published. Never add, amend, or reorder entries as part of a regular code change.

### Type Stubs
Inline stubs ship with the package (`py.typed` marker):
- `@overload` distinguishes `info=True` vs `info=False`; the `Literal[False]` default overload is listed **first**, followed by the two `Literal[True]` variants (order is not load-bearing — the literal types are disjoint)
- `_TimedCache` uses `Generic[_KT, _VT, _TT]` with `_TT` defaulting to `float`
- `_AbstractCondition` is `@type_check_only` `Protocol` for `condition` params and `cache_condition` attributes
- `_cached_wrapper` / `_cachedmethod_wrapper` use `ParamSpec(_P)` to preserve decorated function signatures; `__call__` uses `_P.args`/`_P.kwargs`
- `cache_info` is declared only on the `*_info` wrapper classes, matching the runtime (no `cache_info` attribute at all when `info=False`)
- `_cachedmethod_wrapper` models the descriptor protocol: `__set_name__`, `__get__`, `__call__`; uses `Concatenate[Any, _P]` so `_P` excludes `self`
- `_cachedmethod.py` uses `# type: ignore` for `functools.update_wrapper()` (typeshed #9846)
- Validate stubs with `tox -e pyright`

## Key Files
- `src/cachetools/__init__.py` — All cache implementations
- `src/cachetools/__init__.pyi` — Type stubs for caches and decorators
- `src/cachetools/_cached.py` — `@cached` decorator variants
- `src/cachetools/_cachedmethod.py` — `@cachedmethod` wrapper classes and `_wrapper()` factory
- `src/cachetools/_descriptor.py` — Generic `_MethodDescriptor` descriptor helper, shared by `@cachedmethod`
- `src/cachetools/keys.py` / `keys.pyi` — Key functions
- `src/cachetools/func.py` / `func.pyi` — Functools-compatible wrappers (`lru_cache`, `ttl_cache`, etc.)
- `tests/__init__.py` — Test mixin and helpers
- `tox.ini` — Test/lint/docs environments; `envlist = py,docs,doctest,pyright,ruff,ruff-format`
- `pyproject.toml` — Build config plus `ruff`/`pyright` settings; version: `{attr = "cachetools.__version__"}` (`__version__` lives in `src/cachetools/__init__.py`)
- `CHANGELOG.rst` — Maintainer-only, written at release time; do not modify