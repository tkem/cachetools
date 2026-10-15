# Copilot Instructions for cachetools

**cachetools** provides extensible memoizing collections and decorators, including
variants of Python's `@functools.lru_cache`. Pure Python ≥ 3.10, no runtime
dependencies, inline type stubs (`py.typed`). Maintained by a single maintainer;
`develop` is the working branch, `master` the release branch.

## Ground Rules

- **Run everything through `tox`**, never bare `pytest`/`python -m pytest` — tox pins
  the environment CI relies on (see [Developer Workflows](#developer-workflows)).
- **Do not edit `CHANGELOG.rst`.** The maintainer writes it immediately before a
  release. Never add, amend, or reorder entries as part of a regular change.
- **Do not bump `__version__`** (`src/cachetools/__init__.py`) — release-only.
- **Pickling caches is unsupported.** Caches happen to be picklable (and
  `test_pickle*` exercise it), but the format is an implementation detail that any
  release — even a bugfix release — may change. Do not document, advertise, or build
  features on it.
- Pull requests must reference an open issue (except trivial fixes such as typos).
  Prefer separate commits for code, tests and docs: `Fix #123: ...`,
  `Tests for #123: ...`, `Docs for #123: ...` (see `.github/PULL_REQUEST_TEMPLATE.md`).
- New behavior needs unit tests under `tests/` and, for user-visible features, docs in
  `docs/index.rst` (Sphinx; code examples there are run by `tox -e doctest`).
- Prefer clarity and performance over DRY: the decorator modules intentionally
  duplicate one wrapper per lock/condition/info combination. Keep that structure
  when changing one variant — apply the change to **all** variants.

## Architecture

### `Cache` base class (`src/cachetools/__init__.py`)
- `Cache` is a `MutableMapping` with `maxsize`, `currsize` and `getsizeof`.
- `__init__` rejects negative `maxsize` (`ValueError`); `maxsize=0` (no-space cache)
  and `math.inf` (unbounded) are valid.
- `__init__` checks `getsizeof is not None` (not truthiness), so falsey-but-callable
  `getsizeof` objects are honored (#430).
- Unless `getsizeof` is overridden (parameter or subclass), the per-key size store
  `Cache.__size` is a shared `_DefaultSize` fake dict that always reports 1, so no
  per-key size dict is kept.
- `__setitem__` rejects negative sizes and values larger than `maxsize`
  (`ValueError`). When replacing an existing key it evicts until the *new* size fits,
  recomputing `diffsize` if the key itself gets evicted.
- `get()`/`pop()`/`setdefault()` are implemented directly because the
  `MutableMapping` defaults assume `__getitem__` raises `KeyError`, which is untrue
  when a subclass implements `__missing__`.
- Every subclass overrides `clear()` to be O(1) instead of the `MutableMapping`
  `popitem()` loop.
- Size accounting assumes a value's size does not change after insertion (documented).

### Subclass pattern
- Subclasses override `__setitem__`, `__delitem__`, `popitem()` and optionally
  `__getitem__` to implement eviction policies.
- **Critical:** parent methods are bound via default parameters
  (`def __setitem__(self, key, value, cache_setitem=Cache.__setitem__)`) for speed and
  to avoid recursion through overridden methods.
- After calling the parent `__getitem__`, check `key in self` (or equivalent) to handle
  values produced by `__missing__`.

### Cache types
- `FIFOCache`: evicts oldest inserted (`OrderedDict`).
- `LRUCache`: evicts least recently used (`OrderedDict.move_to_end()`).
- `LFUCache`: evicts least frequently used; doubly-linked list of `_Link` frequency
  buckets (`__slots__`, `keys` set) anchored at a sentinel `__root`, plus a
  `__links` key→bucket dict.
- `RRCache`: random eviction (`__keys` list + `__index` dict for O(1) removal).
  `popitem()` checks for emptiness itself before calling `choice`, since a custom
  `choice` only has to handle non-empty sequences.
- `_TimedCache` (base of `TTLCache`/`TLRUCache`):
  - `_Timer` wraps the user timer as a re-entrant context manager (`__nesting`) that
    freezes time for the duration of an operation, preventing TOCTOU bugs; it proxies
    other attributes to the wrapped timer via `__getattr__`.
  - `__len__`, `__repr__` and `currsize` call `expire()` first; `get`/`pop`/
    `setdefault` run under a frozen timer. `clear()` deliberately skips `expire()`.
  - `expire(time=None)` returns `list[tuple[key, value]]` of removed items.
  - `__delitem__` on a present-but-expired key removes it and then raises `KeyError`,
    consistent with `key in cache` being `False`.
- `TTLCache`: LRU order in `__links` (`OrderedDict`) plus an expiry-ordered
  doubly-linked `_Link` list at sentinel `__root`. `__setitem__` computes
  `expires = time + ttl` *before* mutating any state, so a failing `+` leaves the cache
  consistent. `_Timer.__reduce__`/`TTLCache.__setstate__` rebuild time-tracking state
  on unpickling.
- `TLRUCache`: per-item expiry from `ttu(key, value, time)`; min-heap `__order` of
  `_Item`s with lazy deletion (`removed` flag), compacted in `expire()` once the heap
  exceeds `__HEAP_CLEANUP_FACTOR` × live items. Setting an already-expired item removes
  any existing entry instead of storing it.

### `@cached` (`_cached.py`)
- `_wrapper()` dispatches to one closure per lock/condition/info combination; when
  `condition` is given without `lock`, `condition` serves as both.
- Wrapper attributes: `cache`, `cache_key`, `cache_lock` (`lock` or `condition`),
  `cache_condition`, `cache_clear()`; `info=True` adds `cache_info()`, `info=False`
  sets `cache_info = None` at runtime.
- `cache=None` (pass-through via `_uncached`/`_uncached_info`) is **deprecated since
  7.2** and emits `DeprecationWarning`.
- `@cached` may decorate methods (not encouraged, like `functools.lru_cache`), but the
  cache and hit/miss counters are then shared by *every* instance
  (`test_decorator_method` in `test_cached.py`/`test_func.py`).

### `@cachedmethod` (`_cachedmethod.py`, `_descriptor.py`)
- Each variant defines a local `Descriptor` class with a nested
  `Wrapper(_WrapperBase)` — the per-instance callable. `_WrapperBase` exposes `cache`,
  `cache_key`, `cache_lock`, `cache_condition` as properties resolved against the
  instance. The `info=False` variants delegate to a module-level `wrapper(self, ...)`
  function that is shared with the deprecated `@classmethod` path.
- The descriptor object itself also carries `cache`/`cache_key`/`cache_lock`/
  `cache_condition` (the raw callables) for backward-compatible `@classmethod` use.
- `_descriptor.py`:
  - `_MethodDescriptor` implements `__set_name__`/`__get__` and takes a `deprecated`
    flag.
  - `_ClassMethodDescriptor` (`deprecated=True`) adds `__call__` and
    `cache_clear(objtype)` for backward-compatible `@classmethod` on Python ≥ 3.13,
    with `DeprecationWarning`. Only `info=False` variants use it; `info=True` never
    supported `@classmethod`. The `_condition` variant keeps per-class pending sets in
    a `weakref.WeakKeyDictionary` for that path.
- `__get__` on an instance resolves the attribute name along `type(obj).__mro__`:
  - finds itself → the wrapper replaces the descriptor in `obj.__dict__` via
    `setdefault` (thread-safe, first wins);
  - finds another descriptor (a `super()` call from an override) → the wrapper is
    stored in `obj.__dict__["__cachetools_cachedmethods"]` keyed by descriptor, so base
    and override keep separate state and the override is never shadowed (#437).
- `__get__` with `obj is None` (class access) returns a plain
  `unbound(self, *args, **kwargs)` function (`functools.wraps` of the method) that
  dispatches through `__get__`, so `Cls.method(obj, ...)` shares the instance's
  wrapper/statistics and `mock.create_autospec` works (#435). It is created lazily once
  per descriptor (`Cls.method is Cls.method`, shared with subclasses) and has no
  `cache_clear`/`cache_info`/`cache` attributes.
- Errors: `__set_name__` raises `TypeError` if the same descriptor is bound to two
  names; `__get__` raises `TypeError` when the instance has no `__dict__`
  (`__slots__`), a non-assignable one, or `__set_name__` was never called. The
  deprecated (`info=False`) variants warn instead of raising.
- Per-instance stampede prevention: `_condition_info` keeps a pending set per wrapper,
  i.e. per instance.

### Shared decorator behavior
- `_CacheInfo` is a namedtuple whose runtime name is `CacheInfo` (matches stdlib).
  `@cached(info=True)` reports `maxsize=None` for plain mappings and `(0, 0)` for
  non-mappings; `@cachedmethod(info=True)` raises `TypeError` from `cache_info()` if
  `cache(self)` is not a mapping.
- All wrappers swallow `ValueError` (value too large) on store and return the computed
  value. Lock-only variants store via `cache.setdefault()` so the first concurrent
  result wins.
- Locking tiers: **unlocked** | **locked** (lock released while computing) |
  **condition** (lock + pending-key set + `wait_for`/`notify_all` to prevent cache
  stampedes). Same-thread recursion on the same key deadlocks in the condition tier.
- `_AbstractCondition` (`__init__.pyi`) is a `Protocol` over
  `AbstractContextManager[Any]` with `wait()`, `wait_for()`, `notify()`,
  `notify_all()`; only `wait_for()` and `notify_all()` are used at runtime.

### `cachetools.func`
- `functools.lru_cache`-compatible `fifo_cache`, `lfu_cache`, `lru_cache`, `rr_cache`,
  `ttl_cache`, built on `cached(..., condition=Condition(), info=True)` for thread
  safety and stampede prevention; they add `cache_parameters()`.
- Bare `@lru_cache` is accepted (callable `maxsize` → 128).
- `maxsize=None` uses a plain `dict`, except `ttl_cache`, which uses
  `_UnboundTTLCache` (`TTLCache` with `math.inf` maxsize, reports `maxsize=None`).

### Keys (`keys.py`)
- `hashkey` (default): returns a `_HashedTuple`, which caches its hash and drops it on
  pickling (`__getstate__`). Keyword arguments are sorted and separated by the `_kwmark`
  sentinel.
- `methodkey` drops `self`; `typedkey`/`typedmethodkey` append argument types.

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)
- `@overload` distinguishes `info=True` vs `info=False`: `Literal[False]` (default)
  first, then keyword-only and fully positional `Literal[True]` overloads.
- `_cached_wrapper` / `_cachedmethod_wrapper` use `ParamSpec(_P)` to preserve
  decorated signatures; `_cachedmethod_wrapper` uses `Concatenate[Any, _P]` so `_P`
  excludes `self`, and models `__set_name__`, `__get__`, `__call__`.
- `__get__` overloads: `obj: None` (class access) returns `_cachedmethod_unbound`
  (`__wrapped__` + `__call__(obj, *args)`, plus a receiver-less `__call__` overload for
  deprecated `@classmethod` use); any other `obj` returns the bound wrapper.
- Pyright resolves `@classmethod`-wrapped `@cachedmethod` attributes through the
  `obj: None` overload, so `__get__`/`_cachedmethod_unbound` changes must keep
  `tests/test_classmethod.py` type-clean. Drop the receiver-less `__call__` overload
  together with `@classmethod` support.
- `func.pyi`: `ParamSpec`-based `_cachetools_cache_wrapper`, with one overload per
  decorator for the factory form (`maxsize: int | None`) and one for the bare-decorator
  form (`maxsize: Callable[_P, _R]`).
- `_TimedCache` is `Generic[_KT, _VT, _TT]` with `_TT` defaulting to `float`;
  `TTLCache`/`TLRUCache` `__init__` overloads bind `_TT=float` without `timer` and
  infer it from `timer` otherwise.
- `_AbstractCondition` and the wrapper classes are `@type_check_only`.
- `_cachedmethod.py` uses `# type: ignore` for `functools.update_wrapper()` on a
  descriptor (typeshed #9846).

## Developer Workflows

```bash
tox                       # all envs: py, docs, doctest, pyright, ruff, ruff-format
tox -p auto               # same, in parallel
tox -e py                 # tests + coverage (term-missing)
tox -e py -- tests/test_ttl.py -k expire   # posargs go to pytest
tox -e ruff               # ruff check
tox -e ruff-format        # ruff format --diff
tox -e pyright            # type checking (stubs + tests)
tox -e docs               # sphinx-build -W (warnings are errors)
tox -e doctest            # run examples in docs/index.rst
```

- CI (`.github/workflows/ci.yml`) runs `tox` on CPython 3.10–3.15, free-threaded
  3.13t–3.15t and PyPy 3.10/3.11, then uploads coverage to Codecov.
- A single local interpreter cannot reach 100% coverage: Python < 3.13-only
  `@classmethod` paths (`_cachedmethod.py` `_WrapperBase.__init__` warning,
  `_descriptor.py` deprecated `__get__` branch) show as uncovered on 3.13+.

### Code style
- **ruff** formatter and linter; lint ignores `DTZ005` and `UP031` (`pyproject.toml`).
- **pyright** runs in `typeCheckingMode = "standard"` project-wide with no global rule
  downgrades. `_cached.py` and `_cachedmethod.py` carry file-level
  `# pyright: rule=false` comments for known-safe patterns (dynamic attributes on plain
  functions; lock/condition never `None` at their call sites). Prefer such scoped
  suppressions over relaxing rules globally.
- No type annotations in `.py` files; types live in the `.pyi` stubs.

## Tests (`tests/`)
- `tests/__init__.py`: `CacheTestMixin` (23 tests shared by every cache type),
  `SimplifiedTestCaseProtocol` (typing aid for mixins), `CountedLock`,
  `CountedCondition` (full `_AbstractCondition` implementation).
- One `unittest.TestCase` + `CacheTestMixin` class per cache type; policy-specific
  eviction checks live in the per-cache files. `test_ttl.py`/`test_tlru.py` use a
  manual `Timer` for deterministic time.
- `test_cached.py` (`DecoratorTestMixin`) and `test_cachedmethod.py`
  (`MethodDecoratorTestMixin`) cover all lock/condition/info combinations against both
  `Cache` and plain `dict`. `test_cachedmethod.py` also covers inheritance and `super()`
  overrides, weakrefs, and class access (`UnboundMethodTest`: class calls, identity,
  `__wrapped__`, `create_autospec`). `test_func.py` has its own `DecoratorTestMixin`
  per `func.*_cache`.
- `test_classmethod.py`: deprecated `@cachedmethod` + `@classmethod` combinations and
  their `DeprecationWarning`s.
- `test_threading.py`: real-concurrency tests for condition-based stampede prevention
  and lock-only races; guard against hangs with the `TIMEOUT` class constant,
  `thread.join(timeout=TIMEOUT)` and `assertFalse(t.is_alive())`.

### Adding a new cache type
1. Inherit from `Cache` (or `_TimedCache` for time-based eviction).
2. Override `__setitem__`, `__delitem__`, `popitem()` (optionally `__getitem__`),
   binding parent methods via default parameters.
3. Handle the `__missing__` case after calling the parent `__getitem__`.
4. Override `clear()` to reset subclass bookkeeping in O(1).
5. Add stubs to `__init__.pyi`, an entry to `__all__`, docs to `docs/index.rst`, and a
   test class inheriting `CacheTestMixin`.

## Maintainer Decisions (do not re-raise)
- Pickling caches stays undocumented and unsupported (see Ground Rules).
- `copy.copy()` of an instance with an active `@cachedmethod` wrapper shares the
  wrapper with the original; accepted, no docs note or code change.
- `@cachedmethod` + `@classmethod` and instances without a mutable `__dict__` are
  deprecated since 7.0 and will be removed in the next major version.

## Key Files
- `src/cachetools/__init__.py` — `Cache` and all cache types, `cached`/`cachedmethod`
  entry points, `_CacheInfo`, `__version__`
- `src/cachetools/__init__.pyi` — stubs for caches and decorators
- `src/cachetools/_cached.py` — `@cached` wrapper variants
- `src/cachetools/_cachedmethod.py` — `@cachedmethod` descriptor/wrapper variants
- `src/cachetools/_descriptor.py` — `_MethodDescriptor`/`_ClassMethodDescriptor` and
  deprecation warning helpers
- `src/cachetools/keys.py` / `keys.pyi` — key functions
- `src/cachetools/func.py` / `func.pyi` — `functools`-compatible decorators
- `tests/__init__.py` — test mixins and helpers
- `docs/index.rst` — user documentation (single page, doctested)
- `pyproject.toml` — build config, `ruff`/`pyright` settings; version read from
  `cachetools.__version__`
- `tox.ini` — test environments
- `.github/workflows/ci.yml` — CI matrix
- `.github/copilot-review.md` — latest code review findings; refresh alongside these
  instructions
- `CHANGELOG.rst` — maintainer-only, written at release time
