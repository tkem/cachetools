# Copilot Instructions for cachetools

**cachetools** provides memoizing collections and decorators, including variants of
`functools.lru_cache`. Pure Python ≥ 3.11, no runtime dependencies, inline type stubs
(`py.typed`). Single maintainer; `master` is the release branch, `develop` the
integration branch.

## Ground Rules

- **Run everything through `tox`**: `pytest`, `ruff`, `pyright` and `sphinx` only via
  `tox -e <env> -- <posargs>`, never directly or via `.tox/<env>/bin/<tool>`. A
  throw-away probe script may run with `.tox/py/bin/python probe.py`.
- **Do not edit `CHANGELOG.rst` or bump `__version__`**; both are release-only.
- PRs reference an open issue (except trivial fixes), in separate commits:
  `Fix #123: ...`, `Tests for #123: ...`, `Docs for #123: ...`.
- New behavior needs tests under `tests/`; user-visible changes need docs in
  `docs/index.rst` (doctested) with a `.. versionchanged::` note.
- Docs style: two spaces after a sentence; single backticks for parameter names and
  `:meth:`/`:func:`/`:exc:` roles in `docs/index.rst`; ``double backticks`` in
  `CHANGELOG.rst`. CHANGELOG entries are imperative one-liners, one change each, no
  issue numbers, tagged "(breaking change)" or "(potentially breaking change)"; a
  regression fix adds "(broken since v7.0.0)", docs-only work is one "Various
  documentation improvements." line; releases are separated by two blank lines.
  Keep `README.rst` examples in sync with `docs/index.rst`.
- Prefer clarity and performance over DRY: there is one mixin/wrapper class per
  lock/condition/info combination. Apply changes to **all** variants.

## Architecture

**Caches** (`__init__.py`): `Cache` is a `MutableMapping` with `maxsize`, `currsize`
and `getsizeof`; `maxsize=0` and `math.inf` are valid, negative values raise
`ValueError`, and a value's size must not change after insertion. Subclasses override
`__setitem__`, `__delitem__`, `popitem()`, `clear()` and optionally `__getitem__`,
binding parent methods via default parameters (`cache_setitem=Cache.__setitem__`).
`FIFOCache`/`LRUCache` use `OrderedDict`, `LFUCache` a linked list of frequency
buckets, `RRCache` a key list plus index dict. `_TimedCache` (`TTLCache`, `TLRUCache`)
wraps the timer in a re-entrant `_Timer` that freezes time per operation; `__setitem__`,
`popitem()`, `__len__`, `__repr__` and `currsize` call `expire()` first, while
`__delitem__`, `__getitem__`, `__contains__`, `__iter__` and `clear()` do not. Since
`list()`/`set()` ask for a length hint, only a bare `for` loop sees expired items that
have not been removed yet. `TLRUCache` uses a min-heap with lazy deletion and iterates
in heap order. `CacheInfo` is a public namedtuple; the private `CacheInfo._make_info()`
uses `maxsize`/`currsize` for `Cache` instances and `len()` otherwise, so custom caches
need `__len__` with `info=True`.

**Decorator mixins** (`_decorator.py`): `_BasicMixin`, `_LockedMixin`,
`_ConditionMixin` and their `*InfoMixin` counterparts implement `__call__`,
`cache_clear()` and `cache_info()` on top of the wrapper's `cache`, `cache_key`,
`cache_lock` and `cache_condition`. Wrappers swallow `ValueError` on store; locked
variants release the lock while computing and store via `setdefault()`; the condition
tier adds a pending-key set with `wait_for`/`notify_all` (same-key recursion deadlocks
there). `condition` without `lock` serves as both.

**`@cached`** (`_cached.py`): one `_WrapperBase` + mixin class per combination; the
wrapper is a callable object with `cache`, `cache_key`, `cache_lock`,
`cache_condition`, `cache_clear()` and, with `info=True`, `cache_info()`. Call
`functools.update_wrapper()` *before* setting attributes so stacked decorators keep
their state. `__get__` binds via `types.MethodType`, so `@cached` works on methods with
one shared cache. `__reduce__` returns `__qualname__` (as the C `lru_cache` does), so
pickling resolves by name and `copy`/`deepcopy` return the wrapper unchanged; there
are deliberately no `__copy__`/`__deepcopy__` methods.

**`@cachedmethod`** (`_cachedmethod.py`, `_descriptor.py`): `_MethodDescriptor` builds
one per-instance wrapper (bound via `functools.partial`; `__wrapped__` is the unbound
method, so `inspect.signature()` keeps `self`) and stores it in `obj.__dict__`;
wrappers reached through `super()` go to `obj.__dict__["__cachetools_cachedmethods"]`,
keyed by descriptor. Class access returns a lazily created `_Unbound` callable object,
deliberately not a function so `create_autospec()` strips the receiver (#443); it takes
the receiver from `*args`, binds via `__get__` when aliased in another class body, and
pickles/copies by reference through its descriptor.
`update_wrapper()` runs *after* the descriptor's state is set, so stacked
`@cachedmethod` silently uses the inner cache. Pickle/deepcopy (#417):
`_WrapperBase.__reduce__` returns `(descriptor.__get__, (obj,))` and
`_MethodDescriptor.__reduce__` returns `(_lookup, (owner, attrname))`, so wrappers are
rebuilt through their descriptor, counters reset, and lock, condition and
`__wrapped__` are never serialized. `_lookup` must stay importable and reads the
owner's *current* class dict. `copy.copy(obj)` shares the wrappers, still bound to the
original. `TypeError` is raised for `@classmethod` (via `__call__` on 3.13+, via
`__get__` before), for a second `__set_name__`, for class-access calls without an
instance and for instances without a writable `__dict__`.

**`func.py`, `keys.py`**: `*_cache` decorators use `cached(..., condition=Condition(),
info=True)` plus `cache_parameters()`; `maxsize=None` uses a `dict` (`ttl_cache`:
`_UnboundTTLCache`). `hashkey` returns a `_HashedTuple` with a cached hash, `methodkey`
drops `self`, `typed*` variants append argument types.

## Type Stubs (`*.pyi`)

No annotations in `.py` files. `@overload`s split `info=False` (default, first) and
`info=True`; wrappers use `ParamSpec`, `_cachedmethod_wrapper` uses
`Concatenate[Any, _P]`. `@cached` wrapper stubs have three `__get__` overloads (class
access, instance binding, `obj: object` catch-all for `@staticmethod`) and declare
`__name__`/`__qualname__`. pyright runs in `standard` mode; prefer scoped
suppressions, and note that `reportUnnecessaryTypeIgnoreComment` flags stale ignores.
mypy is not a target.

## Development and Tests

```bash
tox -p auto                                # all environments
tox -e py -- tests/test_ttl.py -k expire   # posargs go to pytest
```

- CI covers CPython 3.11–3.15, free-threaded builds and PyPy; 100% line and branch
  coverage is reached only across the matrix (e.g. the pre-3.13 `@classmethod` check).
  Do not add tests that emulate older Pythons for local coverage.
- ruff uses its default rule set, so the `ignore` entries in `pyproject.toml` matter.
- `tests/__init__.py` has `CacheTestMixin`, `CountedLock`, `CountedCondition`; one
  `TestCase` per cache type; TTL tests use a manual `Timer`.
- `test_cached.py`/`test_cachedmethod.py` cover all lock/condition/info combinations.
  Objects pickled by name must be reachable from module level (`PickleTest`, `Cached`,
  `CachedChild`), not locals.
- `test_func.py` calls decorators via `Callable[..., Any]`; stub checks need concrete
  annotated tests (`test_decorator_method*`) without `# type: ignore`.
- `test_threading.py`: join with `TIMEOUT` and assert threads finished. Lock tests force
  overlap with a `Barrier`; condition tests cannot, so they do not prove the stampede
  guard engaged.
- `list()`, `set()` and `len()` run `expire()`; use a `for` loop to observe expired
  items.

## Code Review

- Reviews **amend `.github/copilot-review.md` in place** (header: date, commit, CI
  status, coverage), never new files or dated sections.
- Findings are tables ordered High, Medium, Low, Info with columns
  `# | Priority | Location | Finding` (or without `Location`); renumber after changes;
  cross-reference as "Code #3", "Docs #2".
- **Resolved issues are removed**, never marked resolved; git history is the record.
- Keep accepted trade-offs as Info rows; record settled matters under *Maintainer
  Decisions*. State what was verified and how. A review changes nothing; fix only
  when asked.

## Maintainer Decisions (do not re-raise)

- Pickling caches works and is documented only with the caveat that the format may
  change in any release; no stable format, cross-version compatibility or
  pickle-based features. Pickling and deep-copying objects that use `@cachedmethod`
  is supported (#417) and must keep working.
- Stacking `@cachedmethod` decorators is unsupported and untested.
- `copy.copy()` sharing `@cachedmethod` wrappers is accepted (`cached_property`
  semantics); the data-descriptor fix costs ~30% per call and was rejected.
- `cachetools.func` stubs expose only the `lru_cache`-compatible API.
- A `condition` must provide the full `threading.Condition` interface; `wait()` and
  `notify()` are reserved for future use. Do not propose relaxing the protocol.
- `README.rst` does not state Python versions; `pyproject.toml` is the source of truth.
