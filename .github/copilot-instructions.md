# Copilot Instructions for cachetools

**cachetools** provides extensible memoizing collections and decorators, including
variants of Python's `@functools.lru_cache`. Pure Python ≥ 3.11, no runtime
dependencies, inline type stubs (`py.typed`). Single maintainer; `master` is the
release branch, `develop` the integration branch.

## Ground Rules

- **Run everything through `tox`**, never bare `pytest`.
- **Do not edit `CHANGELOG.rst` or bump `__version__`** — both are release-only.
- **Pickling caches is unsupported.** It happens to work (`test_pickle*`), but the
  format is an implementation detail that any release may change. Do not document,
  advertise, or build features on it.
- PRs must reference an open issue (except trivial fixes). Prefer separate commits:
  `Fix #123: ...`, `Tests for #123: ...`, `Docs for #123: ...`.
- New behavior needs tests under `tests/`; user-visible features need docs in
  `docs/index.rst` (doctested).
- Prefer clarity and performance over DRY: the decorators use one mixin/wrapper
  class per lock/condition/info combination. Apply changes to **all** variants.

## Architecture

### Caches (`src/cachetools/__init__.py`)
- `Cache` is a `MutableMapping` with `maxsize`, `currsize`, `getsizeof`. `maxsize=0`
  and `math.inf` are valid; negative values raise `ValueError`. Without a custom
  `getsizeof`, no per-key size dict is kept (`_DefaultSize`). A value's size must not
  change after insertion.
- `get()`/`pop()`/`setdefault()` are implemented directly to work with `__missing__`.
- Subclasses override `__setitem__`, `__delitem__`, `popitem()` (optionally
  `__getitem__`) and `clear()` (O(1)). **Bind parent methods via default parameters**
  (`cache_setitem=Cache.__setitem__`) for speed and to avoid recursion. After calling
  the parent `__getitem__`, check `key in self` to handle `__missing__` values.
- `FIFOCache`/`LRUCache` use `OrderedDict`; `LFUCache` a linked list of frequency
  buckets; `RRCache` a key list plus index dict and checks for emptiness before
  calling `choice`.
- `_TimedCache` (base of `TTLCache`/`TLRUCache`) wraps the timer in a re-entrant
  `_Timer` that freezes time per operation. `__len__`, `__repr__`, `currsize` expire
  first; `clear()` does not. `expire()` returns the removed `(key, value)` pairs.
  Deleting a present-but-expired key removes it and raises `KeyError`.
- `TTLCache`: LRU `OrderedDict` plus an expiry-ordered linked list; computes
  `expires` before mutating state. `TLRUCache`: per-item `ttu()`, min-heap with lazy
  deletion, compacted in `expire()`.
- `CacheInfo` is a public namedtuple matching the stdlib one. `CacheInfo.make(cache,
  hits, misses)` uses `maxsize`/`currsize` for `Cache` instances, otherwise
  `maxsize=None` and `len(cache)`, so custom caches need `__len__` with `info=True`.

### Decorator mixins (`_decorator.py`)
- `_BasicMixin`, `_LockedMixin`, `_ConditionMixin` and their `*InfoMixin`
  counterparts implement `__call__`, `cache_clear()` and `cache_info()`. They read
  `self.cache`, `self.cache_key`, `self.cache_lock`, `self.cache_condition` from the
  concrete wrapper class.
- Wrappers swallow `ValueError` on store; locked variants store via `setdefault()`
  (first result wins). Locking tiers: unlocked | locked (released while computing) |
  condition (pending-key set + `wait_for`/`notify_all`). Same-key recursion
  deadlocks in the condition tier. `condition` without `lock` serves as both.

### `@cached` (`_cached.py`)
- `_wrapper()` instantiates one `_WrapperBase` + mixin class per combination; the
  wrapper is a callable object, not a function.
- Attributes: `cache`, `cache_key`, `cache_lock`, `cache_condition`, `cache_clear()`;
  `info=True` adds `cache_info()`. With `info=False` there is no `cache_info`.
- Call `functools.update_wrapper()` *before* setting wrapper attributes, so stacked
  `@cached` decorators keep their own state (`test_stacked_decorators`).
- `__get__` binds via `types.MethodType`, so `@cached` works on methods; the cache
  and counters are then shared by all instances.
- `__reduce__` returns `__qualname__` (as for the C `functools.lru_cache`), so
  pickling resolves the wrapper by name and `copy`/`deepcopy` return it unchanged.
  There are deliberately no `__copy__`/`__deepcopy__` methods.
- `cache=None` raises `TypeError` (dropped in v8.0.0).

### `@cachedmethod` (`_cachedmethod.py`, `_descriptor.py`)
- `_wrapper()` returns a `_MethodDescriptor` holding a factory that builds one
  per-instance `_WrapperBase` + mixin object, bound via `functools.partial`.
- `_MethodDescriptor.__get__` stores the wrapper in `obj.__dict__` via `setdefault`;
  for `super()` lookups it stores it in `obj.__dict__["__cachetools_cachedmethods"]`
  keyed by descriptor. Class access returns a plain, lazily created `unbound`
  function that dispatches through `__get__`.
- `_WrapperBase.__reduce__` rebuilds the wrapper as `getattr(obj, name)`, so objects
  with active wrappers can be pickled (#417); `*Info` counters are reset.
- Raise `TypeError` for: `__set_name__` on two names, instances without a writable
  `__dict__`, and `@classmethod` (via `_MethodDescriptor.__call__` on 3.13+).
- Stampede prevention uses a pending set per instance wrapper.

### `cachetools.func` and `keys.py`
- `*_cache` decorators use `cached(..., condition=Condition(), info=True)` and add
  `cache_parameters()`. Bare `@lru_cache` works; `maxsize=None` uses a `dict`
  (`ttl_cache`: `_UnboundTTLCache`).
- `hashkey` returns a `_HashedTuple` (cached hash, not pickled); `methodkey` drops
  `self`; `typed*` variants append argument types.

## Type Stubs (`*.pyi`)
- No annotations in `.py` files; types live in the stubs.
- `@overload`s split `info=False` (default, first) and `info=True`. Wrappers use
  `ParamSpec`; `_cachedmethod_wrapper` uses `Concatenate[Any, _P]`.
- `_cached_wrapper`, `_cached_wrapper_info`, `_cachetools_cache_wrapper` have three
  `__get__` overloads: class access, instance binding via `Concatenate`, and a
  required `obj: object` catch-all for `@staticmethod`. `_cached_wrapper_info` needs
  a scoped `# pyright: ignore[reportIncompatibleMethodOverride]`.
- All wrapper stubs declare `__name__` and `__qualname__`.

## Development

```bash
tox -p auto                                # all: py, docs, doctest, pyright, ruff, ruff-format
tox -e py -- tests/test_ttl.py -k expire   # posargs go to pytest
```

- CI runs `tox` on CPython 3.11–3.15, free-threaded 3.13t–3.15t and PyPy 3.11.
  Coverage is 100%.
- **ruff** for formatting and linting. **pyright** in `standard` mode; prefer scoped
  suppressions (file-level `# pyright: rule=false`, `# pyright: ignore[rule]`) over
  global ones. `reportUnnecessaryTypeIgnoreComment` flags stale ignores.

## Tests
- `tests/__init__.py`: `CacheTestMixin` (shared by all cache types), `CountedLock`,
  `CountedCondition`. One `TestCase` per cache type; TTL tests use a manual `Timer`.
- `test_cached.py`/`test_cachedmethod.py` cover all lock/condition/info combinations.
  Objects pickled by name (`PickleTest`) must be reachable from module level, e.g.
  as class attributes or `@staticmethod`s, not locals.
- `test_func.py` calls decorators via `Callable[..., Any]`, so stub checks need
  concrete, annotated tests (`test_decorator_method`, `test_decorator_method_typed`);
  avoid `# type: ignore` there.
- `test_threading.py`: guard against hangs with `thread.join(timeout=TIMEOUT)` and
  `assertFalse(t.is_alive())`.

## Maintainer Decisions (do not re-raise)
- Pickling caches stays undocumented and unsupported.
- Stacking `@cachedmethod` decorators is unsupported and untested.

## Key Files
- `src/cachetools/__init__.py` / `__init__.pyi` — caches, `CacheInfo`, decorator
  entry points
- `_decorator.py` — call/clear/info mixins; `_cached.py`, `_cachedmethod.py`,
  `_descriptor.py` — decorator wrappers and descriptor
- `keys.py`, `func.py` (+ `.pyi`) — key functions, `functools`-style decorators
- `docs/index.rst` — user docs; `.github/copilot-review.md` — latest review findings
