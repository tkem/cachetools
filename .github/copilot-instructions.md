# Copilot Instructions for cachetools

**cachetools** provides extensible memoizing collections and decorators, including
variants of Python's `@functools.lru_cache`. Pure Python ≥ 3.10, no runtime
dependencies, inline type stubs (`py.typed`). Single maintainer; `master` is the
release branch.

## Ground Rules

- **Run everything through `tox`**, never bare `pytest`.
- **Do not edit `CHANGELOG.rst` or bump `__version__`** — both are release-only.
- **Pickling caches is unsupported.** It happens to work (`test_pickle*`), but the
  format is an implementation detail that any release may change. Do not document,
  advertise, or build features on it.
- PRs must reference an open issue (except trivial fixes). Prefer separate commits:
  `Fix #123: ...`, `Tests for #123: ...`, `Docs for #123: ...`.
- New behavior needs tests under `tests/`; user-visible features need docs in
  `docs/index.rst` (doctested). Keep `README.rst` examples in sync with it.
- Docs style: two spaces after a sentence; single backticks for parameters and
  `:meth:`/`:func:`/`:exc:` roles in `docs/index.rst`, ``double backticks`` in
  `CHANGELOG.rst`. CHANGELOG entries are imperative one-liners without issue numbers,
  tagged "(breaking change)", "(potentially breaking change)" or "(broken since
  vX.Y.Z)"; docs-only work is one "Various documentation improvements." line;
  releases are separated by two blank lines.
- Prefer clarity and performance over DRY: the decorator modules duplicate one
  wrapper per lock/condition/info combination. Apply changes to **all** variants.

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

### `@cached` (`_cached.py`)
- `_wrapper()` dispatches to one closure per lock/condition/info combination;
  `condition` without `lock` serves as both.
- Attributes: `cache`, `cache_key`, `cache_lock`, `cache_condition`, `cache_clear()`;
  `info=True` adds `cache_info()`, `info=False` sets `cache_info = None`.
- Call `functools.update_wrapper()` *before* setting wrapper attributes, so stacked
  `@cached` decorators keep their own state (`test_stacked_decorators`).
- `cache=None` is deprecated and emits `DeprecationWarning`.
- On methods, the cache and counters are shared by all instances.

### `@cachedmethod` (`_cachedmethod.py`, `_descriptor.py`)
- Each variant defines a `Descriptor` with a nested per-instance `Wrapper`.
  `_MethodDescriptor.__get__` stores the wrapper in `obj.__dict__` via `setdefault`;
  for `super()` calls it stores it under `"__cachetools_cachedmethods"` keyed by
  descriptor. Class access returns a lazily created `_Unbound` callable object,
  deliberately not a function so `create_autospec()` strips the receiver (#443); it
  takes the receiver from `*args`, or by the wrapped method's first parameter name
  when passed as a keyword (`Cls.method(self=obj, ...)`), and dispatches through
  `__get__`.
- `__set_name__` on two names, or instances without a writable `__dict__`, raise
  `TypeError`.
- `@cachedmethod` + `@classmethod` (`_ClassMethodDescriptor`, `info=False` only) and
  instances without `__dict__` are **deprecated** and warn instead of raising.
- Stampede prevention uses a pending set per instance. `_condition`'s inner
  `wrapper(self, pending, /, ...)` takes `pending` positional-only, so a method
  parameter of that name can still be passed by keyword.

### Shared behavior
- `CacheInfo` matches the stdlib namedtuple. Wrappers swallow `ValueError` on store;
  lock-only variants store via `setdefault()` (first result wins).
- Locking tiers: unlocked | locked (released while computing) | condition (pending
  keys + `wait_for`/`notify_all`). Same-key recursion deadlocks in the condition tier.

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
- `_cachedmethod_unbound.__call__` has a receiver-less overload for deprecated
  `@classmethod` use; keep `tests/test_classmethod.py` type-clean.
- All wrapper stubs declare `__name__` and `__qualname__`.

## Development

```bash
tox -p auto                                # all: py, docs, doctest, pyright, ruff, ruff-format
tox -e py -- tests/test_ttl.py -k expire   # posargs go to pytest
```

- CI runs `tox` on CPython 3.10–3.15, free-threaded 3.13t–3.15t and PyPy.
  On 3.13+, two deprecated `@classmethod` lines show as uncovered.
- **ruff** for formatting and linting. **pyright** in `standard` mode; prefer scoped
  suppressions (file-level `# pyright: rule=false`, `# pyright: ignore[rule]`) over
  global ones. `reportUnnecessaryTypeIgnoreComment` flags stale ignores.

## Tests
- `tests/__init__.py`: `CacheTestMixin` (shared by all cache types), `CountedLock`,
  `CountedCondition`. One `TestCase` per cache type; TTL tests use a manual `Timer`.
- `test_cached.py`/`test_cachedmethod.py` cover all lock/condition/info combinations.
  `test_func.py` calls decorators via `Callable[..., Any]`, so stub checks need
  concrete, annotated tests (`test_decorator_method`,
  `test_decorator_method_typed`); avoid `# type: ignore` there.
- `test_threading.py`: guard against hangs with `thread.join(timeout=TIMEOUT)` and
  `assertFalse(t.is_alive())`.

## Code Review
- Reviews **amend `.github/copilot-review.md` in place** (header: date, commit, CI
  status, coverage); never new files or dated sections.
- Findings are tables ordered High, Medium, Low, Info with columns
  `# | Priority | Location | Finding` (`Location` optional); renumber after changes;
  cross-reference as "Code #3", "Docs #2". **Resolved issues are removed**, never
  marked resolved; git history is the record.
- Keep accepted trade-offs as Info rows; record settled matters under *Maintainer
  Decisions*. State what was verified and how. A review changes nothing; fix only
  when asked.

## Maintainer Decisions (do not re-raise)
- Pickling caches stays undocumented and unsupported.
- `copy.copy()` of an instance with an active `@cachedmethod` wrapper shares the
  wrapper; accepted.
- Stacking `@cachedmethod` decorators is unsupported and untested.
- A `condition` must provide the full `threading.Condition` interface; `wait()` and
  `notify()` are reserved for future use. Do not propose relaxing the protocol.

## Key Files
- `src/cachetools/__init__.py` / `__init__.pyi` — caches, decorator entry points
- `_cached.py`, `_cachedmethod.py`, `_descriptor.py` — decorator implementations
- `keys.py`, `func.py` (+ `.pyi`) — key functions, `functools`-style decorators
- `docs/index.rst` — user docs; `.github/copilot-review.md` — latest review findings
