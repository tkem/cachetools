# Copilot Instructions for cachetools

## Architecture Overview
**cachetools** provides extensible memoizing collections and decorators, including variants of Python's `@lru_cache`. Pure Python 3.10+, no external runtime dependencies.

### Core Design Pattern
- All caches inherit from `Cache` (a `MutableMapping` with `maxsize`, `currsize`, and `getsizeof`)
- Subclasses override `__setitem__`, `__getitem__`, `__delitem__`, and `popitem()` to implement eviction policies
- **Critical:** Subclasses use default parameter trick (e.g., `cache_setitem=Cache.__setitem__`) to call parent methods efficiently while avoiding recursion

### Cache Types
- `FIFOCache`: Evicts oldest inserted (`OrderedDict`)
- `LRUCache`: Evicts least recently used (`OrderedDict.move_to_end()`)
- `LFUCache`: Evicts least frequently used (doubly-linked list of frequency buckets)
- `RRCache`: Random eviction (`__keys` list with `__index` dict for O(1) removal)
- `TTLCache`/`TLRUCache`: Time-based eviction via `_TimedCache` base; `_Timer` context manager freezes time during operations to prevent TOCTOU bugs; `expire()` returns `list[tuple[key, value]]`

### Decorators
- `@cached` (`_cached.py`): Function memoization; separate wrappers for each lock/condition/info combination; supports `cache=None` via `_uncached`/`_uncached_info` wrappers (pass-through without caching)
- `@cachedmethod` (`_cachedmethod.py`): Method memoization via descriptor protocol (`__set_name__`/`__get__`); class hierarchy: `_WrapperBase` (per-instance callable) → `_DescriptorBase` (descriptor with `__set_name__`/`__get__`, replaces self in instance `__dict__` via `setdefault` for thread safety) → `_DeprecatedDescriptorBase` (backward-compatible `@classmethod` support with warnings); the backward-compatible `_condition` variant uses `weakref.WeakKeyDictionary` for per-instance pending sets
- Both support `key`, `lock`, `condition`, and `info` parameters; when `condition` is given without `lock`, `condition` serves as both lock and condition
- `info=True` adds `cache_info()`/`cache_clear()`; `info=False` (default) only provides `cache_clear()`
- `func.py`: `functools.lru_cache`-compatible wrappers; all use `threading.Condition()` by default for thread safety + stampede prevention; `_UnboundTTLCache` extends `TTLCache` with `math.inf` maxsize for `maxsize=None`

### Thread Safety
3-tier locking: **Unlocked** | **Locked** (release during compute) | **Condition** (lock + pending set + `wait_for`/`notify_all` to prevent thundering herd)

`_AbstractCondition` protocol in `__init__.pyi`: extends `AbstractContextManager[Any]` + `Protocol` with `wait()`, `wait_for()`, `notify()`, `notify_all()`. Only `wait_for()` and `notify_all()` are used at runtime.

### Key Generation (`keys.py`)
- `hashkey`: Default key function; `_HashedTuple` caches hash values
- `methodkey`: Drops `self` from key; `typedkey`/`typedmethodkey`: Adds `type()` info

## Developer Workflows

### Testing
```bash
pytest                                    # Run all tests
pytest --cov=cachetools --cov-report term-missing  # With coverage
tox -e py                                 # Just tests
tox -e ruff                               # Linting (ruff check)
tox -e ruff-format                        # Format check (ruff format --diff)
tox -e pyright                            # Type checking
tox -e docs                               # Build docs
tox -e doctest                            # Run doctests
```

- `tests/__init__.py`: `CacheTestMixin` (16 standard tests), `_TestCaseProtocol`, `CountedLock`, `CountedCondition` (implements full `_AbstractCondition` protocol)
- Each cache test inherits `unittest.TestCase` + `CacheTestMixin`
- `test_cached.py` / `test_cachedmethod.py` use `DecoratorTestMixin` / `MethodDecoratorTestMixin` for all lock/condition/info combos
- Threading tests (`test_threading.py`) cover both condition-based stampede prevention and lock-only race resolution under real concurrency; `TIMEOUT` class constant + `thread.join(timeout=TIMEOUT)` + `assertFalse(t.is_alive())` guard against deadlock hangs

### Code Style
- **ruff** formatter and linter (`tox -e ruff-format`, `tox -e ruff`)

## Conventions

### Adding New Cache Types
1. Inherit from `Cache` or `_TimedCache`
2. Override `__setitem__`, `__delitem__`, `popitem()` (optionally `__getitem__`)
3. Use default parameters to call parent: `def __setitem__(self, key, value, cache_setitem=Cache.__setitem__)`
4. Handle `__missing__` edge case: check `if key in self` after parent call
5. Add test class inheriting `CacheTestMixin`

### Type Stubs
Inline stubs ship with the package (`py.typed` marker):
- `@overload` distinguishes `info=True` vs `info=False`; `Literal[False]` overload listed last
- `_TimedCache` uses `Generic[_KT, _VT, _TT]` with `_TT` defaulting to `float`
- `_AbstractCondition` is `@type_check_only` `Protocol` for `condition` params and `cache_condition` attributes
- `_cached_wrapper` / `_cachedmethod_wrapper` use `ParamSpec(_P)` to preserve decorated function signatures; `__call__` uses `_P.args`/`_P.kwargs`
- `_cachedmethod_wrapper` models the descriptor protocol: `__set_name__`, `__get__`, `__call__`; uses `Concatenate[Any, _P]` so `_P` excludes `self`
- `_cachedmethod.py` uses `# type: ignore` for `functools.update_wrapper()` (typeshed #9846)
- Validate stubs with `tox -e pyright`

## Key Files
- `src/cachetools/__init__.py` — All cache implementations
- `src/cachetools/__init__.pyi` — Type stubs for caches and decorators
- `src/cachetools/_cached.py` — `@cached` decorator variants
- `src/cachetools/_cachedmethod.py` — `@cachedmethod` descriptor variants
- `src/cachetools/keys.py` / `keys.pyi` — Key functions
- `src/cachetools/func.py` / `func.pyi` — Functools-compatible wrappers (`lru_cache`, `ttl_cache`, etc.)
- `tests/__init__.py` — Test mixin and helpers
- `pyproject.toml` — Build config, version: `{attr = "cachetools.__version__"}`