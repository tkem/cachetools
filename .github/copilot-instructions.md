# Copilot Instructions for cachetools

**cachetools** provides memoizing collections and decorators, including variants of
`functools.lru_cache`. Pure Python ≥ 3.11, no runtime dependencies, inline type stubs
(`py.typed`). Single maintainer; `master` is the release branch, `develop` the 8.0 line.

## Ground Rules

- **Run everything through `tox`** (`tox -e <env> -- <posargs>`), never bare `pytest`,
  `ruff` or `pyright`.
- **Do not edit `CHANGELOG.rst` or bump `__version__`**; both are release-only.
- **Pickling caches works with limitations** (`test_pickle*`, documented in the `Cache`
  note): the byte stream format is an implementation detail that any release, even a
  bugfix, may change. Never promise cross-version compatibility or build on the format.
- PRs reference an open issue (except trivial fixes), in separate commits:
  `Fix #123: ...`, `Tests for #123: ...`, `Docs for #123: ...`.
- New behavior needs tests under `tests/`; user-visible features need docs in
  `docs/index.rst` (doctested). Keep `README.rst` examples in sync with it.
- Docs style: wrap prose paragraphs in `docs/index.rst` at column 70 (code examples,
  directive signatures, titles and link targets excepted); two spaces after a
  sentence; single backticks for parameters and
  `:meth:`/`:func:`/`:exc:` roles in `docs/index.rst`, ``double backticks`` in
  `CHANGELOG.rst`, whose entries are imperative one-liners without issue numbers,
  tagged "(breaking change)", "(potentially breaking change)" or "(broken since
  vX.Y.Z)"; docs-only work is one "Various documentation improvements." line, speed-ups
  one "Various performance improvements." line; two blank lines between releases.
- Prefer clarity and performance over DRY: there is one wrapper class per
  lock/condition/info combination. Apply changes to **all** variants.
- This file stays at most 150 lines; when adding, drop details the code already shows.

## Architecture

**Caches** (`__init__.py`): `Cache` is a `MutableMapping`; a value's size must not
change after insertion. With the default `getsizeof` the private size dict is `None`,
each item counts 1 and `getsizeof()` is never called. Subclasses override
`__setitem__`, `__delitem__`, `popitem()`, `clear()` and optionally `__getitem__`;
after the parent `__getitem__`, check the subclass's own bookkeeping (not
`key in self`), since `__missing__` may not store the item. `popitem()` evicts via
`del self[key]`, so subclass `__delitem__` overrides see evictions. `_TimedCache`
(`TTLCache`, `TLRUCache`) wraps the timer in a re-entrant `_Timer` that freezes time per
operation. Expiry is lazy: `__len__`, `__repr__` and `currsize` call `expire()` first,
`clear()` does not, and deleting a present-but-expired key removes it and raises
`KeyError`. `expire()` returns early when nothing has expired and is a documented
override hook, so every insert and `popitem()` must keep calling it. Look links/items
up with `.get()`; raising `KeyError` per new key cost ~200 ns. `CacheInfo` is public;
`CacheInfo._make_info(cache, hits, misses)` reports `maxsize`/`currsize` for a `Cache`,
else `None` and `len(cache)`, so other caches used with `info=True` need `len()`.

**Decorator mixins** (`_decorator.py`): `_BasicMixin`, `_LockedMixin`,
`_ConditionMixin` and their `*Info*` twins implement `__call__`, `cache_clear()` and
`cache_info()` against `self.cache`, `self.cache_key`, `self.cache_lock` and
`self.cache_condition`; the wrapped callable, counters and pending set live in
name-mangled attributes. `condition` without `lock` serves as both. Wrappers swallow
`ValueError` on store; locked variants release the lock while computing and store via
`setdefault()`; the condition tier uses `while key in pending: cond.wait()` and
`notify_all()`, so uncontended calls never wait (same-key recursion deadlocks there).

**`@cached`** (`_cached.py`): `_WrapperBase` calls `functools.update_wrapper()`
*before* setting the four public attributes, so stacked decorators keep their state.
Wrappers are objects, not functions: `__get__` binds via `types.MethodType` (cache and
counters shared by all instances) and `__reduce__` returns `__qualname__`, so they
pickle by name like `functools.lru_cache` (wrappers on local functions raise
`AttributeError`); `__repr__` is `<cached f>`. `info=False` wrappers have no
`cache_info`; `cached(None)` raises `TypeError` before decorating.

**`@cachedmethod`** (`_cachedmethod.py`, `_descriptor.py`): `_wrapper()` picks a
factory `wrapper(obj, descriptor)` and returns `_MethodDescriptor(wrapper)`. Per-instance
wrappers expose `cache`, `cache_lock` and `cache_condition` as properties calling the
user's `cache(self)` etc. on every access; `cache_key` is a plain attribute holding
`partial(key, obj)`, the mixin gets `types.MethodType(method, obj)`. The descriptor
stores the wrapper in `obj.__dict__` via `setdefault`; `super()` lookups, and lookups
after `del Cls.method`, use `obj.__dict__["__cachetools_cachedmethods"]` keyed by
descriptor; a missing or read-only `__dict__` raises `TypeError`, as does any access to
a descriptor that never received `__set_name__` (assigned after class creation).
`@classmethod` over `@cachedmethod` raises `TypeError`: on 3.13+ through `__call__`,
before through `__get__(cls, ...)` on such a descriptor. Class access returns a lazy
`_Unbound` callable object, deliberately not a function so `create_autospec()` strips
the receiver (#443); it takes the receiver positionally or by the wrapped method's
first parameter name. Pickle/deepcopy (#417) rebuild wrappers through their descriptor,
so counters reset and nothing unpicklable is serialized; `_MethodDescriptor._lookup`
must stay importable. `__repr__` is `<cachedmethod f of obj>` with
`object.__repr__(obj)`, so a user `__repr__` cannot recurse into the cache; `_Unbound`
prints `<cachedmethod f>`.

**`func.py`, `keys.py`**: `*_cache` decorators use `cached(..., condition=Condition(),
info=True)`; `maxsize=None` uses a `dict` (`ttl_cache`: `_UnboundTTLCache`). Key
functions return plain tuples (`args` itself without kwargs: a tuple subclass or a
Python-level hash cache cost more) and are written out in full, not delegating;
`_HashedTuple` survives only as the kwargs separator and to load keys pickled by 7.x.

## Type Stubs (`*.pyi`)

No annotations in `.py` files; the wrapper and descriptor modules silence pyright with
module-level `# pyright: report...=false` pragmas, the rest uses scoped suppressions.
Decorator `@overload`s come in the order keyword-only `info: Literal[True]`,
`info: Literal[False] = ...` (default), positional `Literal[True]`; wrappers use
`ParamSpec`, `_cachedmethod_wrapper` uses `Concatenate[Any, _P]`. `@cached` wrapper
stubs have three `__get__` overloads (class access, instance binding, `obj: object`
catch-all); `_cachedmethod_unbound.__call__` takes the receiver positional-only.
pyright runs in `standard` mode with `reportUnnecessaryTypeIgnoreComment`.

## Development and Tests

```bash
tox -p auto                                # all environments
tox -e py -- tests/test_ttl.py -k expire   # posargs go to pytest
```

- CI (GitHub Actions on `tkem/cachetools`, every push) runs CPython 3.11–3.15,
  free-threaded 3.13t–3.15t and PyPy 3.11; without `gh`, check runs via
  `https://api.github.com/repos/tkem/cachetools/actions/runs?branch=<branch>`. On 3.13+
  the pre-3.13 `@classmethod` line in `_MethodDescriptor.__get__` is uncovered; CI
  covers it.
- `tests/__init__.py` has `CacheTestMixin`, `CountedLock`, `CountedCondition`; one
  `TestCase` per cache type; TTL tests use a manual `Timer`. Objects pickled by name
  must be reachable from module level by their `__qualname__`. `test_cached.py` keeps a
  duck-typed non-`Mapping` cache (`CustomCacheTest`); `@classmethod` tests live in
  `test_cachedmethod.py`.
- `test_func.py` calls decorators via `Callable[..., Any]`, so stub checks need concrete
  annotated tests without `# type: ignore` (`test_decorator_method`, `test_method_typed`).
- `test_threading.py`: join with `TIMEOUT` and assert threads finished; its
  `WaitCondition` forces a contended `wait()`; single-threaded `wait_count` stays 0.
- Performance work: `timeit`, best of 7, on a pinned core (`taskset`), never in a VM,
  against a git worktree of the previous release; keep hot paths free of avoidable
  Python-level calls; never trade documented subclass hooks or semantics for speed.

## Code Review

- Reviews **amend `.github/copilot-review.md` in place** (header: date, commit, CI
  status, coverage, one *Verified* paragraph); never new files, dated sections or a
  per-commit change summary (git history is the record).
- Findings are tables ordered High, Medium, Low, Info with columns
  `# | Priority | Location | Finding`; renumber after changes; cross-reference as
  "Code #3". **Resolved issues are removed**, never marked resolved.
- Keep it brief: one or two sentences per row, numbers only where they decide
  something, current snapshot only (no comparisons with earlier releases). Record settled
  matters under *Maintainer Decisions*. A review changes nothing; fix only when asked.

## Maintainer Decisions (do not re-raise)

- Pickling caches is documented only as working within one release; the format stays
  unstable. Pickling and deep-copying objects that use `@cachedmethod` is supported
  (#417) and must keep working.
- `copy.copy()` of an instance with an active `@cachedmethod` wrapper shares the
  wrapper; accepted.
- Stacking `@cachedmethod` decorators is unsupported and untested.
- Class access to `@cachedmethod` (`Cls.method(obj, ...)`) builds and discards a
  wrapper per call; accepted.
- A `condition` must provide the full `threading.Condition` interface; `notify()` is
  reserved for future use. Do not propose relaxing the protocol.
