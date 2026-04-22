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
- `@cached` (`_cached.py`): Function memoization; separate wrappers for each lock/condition/info combination
- `@cachedmethod` (`_cachedmethod.py`): Method memoization via descriptor protocol (`__set_name__`/`__get__`)
- Both support `key`, `lock`, `condition`, and `info` parameters
- `info=True` adds `cache_info()`/`cache_clear()`; `info=False` (default) only provides `cache_clear()`

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
tox -e flake8                             # Linting
tox -e docs                              # Build docs
```

- `tests/__init__.py`: `CacheTestMixin` (13+ standard tests), `_TestCaseProtocol`, `CountedLock`, `CountedCondition` (implements full `_AbstractCondition` protocol)
- Each cache test inherits `unittest.TestCase` + `CacheTestMixin`
- Threading stampede tests gated by `THREADING_TESTS` env var

### Code Style
- **Black** formatter; flake8 with `flake8-black`, `flake8-bugbear`, `flake8-import-order`

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
- `_cachedmethod.py` uses `# type: ignore` for `functools.update_wrapper()` (typeshed #9846)

## Key Files
- `src/cachetools/__init__.py` — All cache implementations
- `src/cachetools/__init__.pyi` — Type stubs for caches and decorators
- `src/cachetools/_cached.py` — `@cached` decorator variants
- `src/cachetools/_cachedmethod.py` — `@cachedmethod` descriptor variants
- `src/cachetools/keys.py` / `keys.pyi` — Key functions
- `src/cachetools/func.py` / `func.pyi` — Functools-compatible wrappers (`lru_cache`, `ttl_cache`, etc.)
- `tests/__init__.py` — Test mixin and helpers
- `pyproject.toml` — Build config, version: `{attr = "cachetools.__version__"}`