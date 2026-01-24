# Copilot Instructions for cachetools

## Architecture Overview
**cachetools** provides extensible memorizing collections and decorators, including variants of Python's `@lru_cache`. All cache implementations live in a single ~710-line file (`src/cachetools/__init__.py`) with decorator helpers in separate modules.

### Core Design Pattern
- All caches inherit from `Cache` (a `MutableMapping` with `maxsize`, `currsize`, and `getsizeof`)
- Subclasses override `__setitem__`, `__getitem__`, `__delitem__`, and `popitem()` to implement eviction policies
- **Critical:** Subclasses use default parameter trick (e.g., `cache_setitem=Cache.__setitem__`) to call parent methods efficiently while avoiding recursion

### Cache Types & Eviction Policies
- `FIFOCache`: Evicts oldest inserted (uses `OrderedDict`)
- `LRUCache`: Evicts least recently used (uses `OrderedDict.move_to_end()`)
- `LFUCache`: Evicts least frequently used (doubly-linked list of frequency buckets)
- `RRCache`: Random eviction (maintains `__keys` list with `__index` dict for O(1) removal)
- `TTLCache`/`TLRUCache`: Time-based eviction with `_TimedCache` base (uses `_Timer` context manager to freeze time during operations)

### Decorator Architecture
- `@cached`: Function memoization via `src/cachetools/_cached.py` (3 variants: unlocked, locked, condition-based)
- `@cachedmethod`: Method memoization via `src/cachetools/_cachedmethod.py` (uses `weakref.WeakKeyDictionary` for pending sets)
- Both support custom `key` functions, `lock` objects, and `condition` variables for thread safety
- `info=True` adds `cache_info()` and `cache_clear()` methods (see `_CacheInfo` namedtuple)

## Critical Implementation Details

### Key Generation (`src/cachetools/keys.py`)
- `_HashedTuple` caches hash values to avoid recomputation on cache misses
- `methodkey(self, *args, **kwargs)` drops `self` from cache key (instance methods share cache)
- `typedkey` adds type information: `key += tuple(type(v) for v in args)`

### Thread Safety Pattern
Decorators use 3-tier locking strategy:
1. **Unlocked:** No synchronization (fastest, single-threaded)
2. **Locked:** Lock around cache access, compute outside lock to avoid holding during expensive operations
3. **Condition:** Lock + pending set + wait_for/notify_all (prevents thundering herd on cache misses)

### Time-Based Caches (`_TimedCache`)
- `_Timer` wrapper freezes time during multi-operation methods using `__enter__/__exit__`
- Prevents time-of-check-time-of-use bugs during iteration/expiration
- `expire()` method returns list of `(key, value)` pairs (allows logging/cleanup hooks)

## Developer Workflows

### Testing
```bash
pytest                                    # Run all tests
pytest --cov=cachetools --cov-report term-missing  # With coverage
tox                                       # All environments
tox -e py                                 # Just tests
tox -e flake8                             # Linting
tox -e docs                               # Build docs
tox -e doctest                            # Doctest validation
```

### Code Style
- **Black** formatter (max line length: 80 via flake8)
- flake8 with `flake8-black`, `flake8-bugbear`, `flake8-import-order`
- Ignore: F401 (submodule shims), E501 (line length handled by black)

### Test Patterns
- `tests/__init__.py` defines `CacheTestMixin` with standard cache behavior tests
- Each cache type test inherits: `class LRUCacheTest(unittest.TestCase, CacheTestMixin)`
- Mixin provides 13 standard tests; cache-specific tests added per file
- Decorator tests use `CountedLock` and `CountedCondition` helpers to verify synchronization

## Project-Specific Conventions

### Adding New Cache Types
1. Inherit from `Cache` or `_TimedCache`
2. Override `__setitem__`, `__delitem__`, `popitem()` (and optionally `__getitem__`)
3. Use default parameters to call parent: `def __setitem__(self, key, value, cache_setitem=Cache.__setitem__)`
4. Handle `__missing__` edge case: check `if key in self` after parent call (see LRU/LFU `__getitem__`)
5. Add test class inheriting `CacheTestMixin` in `tests/`

### Module Structure
- All cache classes in `src/cachetools/__init__.py` (~710 lines)
- Decorator wrappers split: `_cached.py` (functions), `_cachedmethod.py` (methods)
- Functools-compatible wrappers in `src/cachetools/func.py` (`lru_cache`, `ttl_cache`, etc.)
- No external dependencies at runtime (pure Python 3.9+)

### Version Management
- Version in `src/cachetools/__init__.py` as `__version__`
- Extracted by `setup.cfg`: `version = attr: cachetools.__version__`
- Docs extract version via `docs/conf.py` parsing

## Key Files
- `src/cachetools/__init__.py` - All cache implementations (~710 lines)
- `src/cachetools/keys.py` - Key generation with hash optimization
- `src/cachetools/_cached.py` - Function decorator variants
- `src/cachetools/_cachedmethod.py` - Method decorator variants
- `tests/__init__.py` - `CacheTestMixin` for standard cache tests
- `setup.cfg` - Package metadata and flake8 config