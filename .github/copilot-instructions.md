# Copilot Instructions for cachetools

**cachetools** provides memoizing collections and decorators, including variants of
`functools.lru_cache`. Pure Python ≥ 3.10, no runtime dependencies, inline type stubs
(`py.typed`). Single maintainer; `master` is the release branch.

## Ground Rules

- **Run everything through `tox`** (`tox -e <env> -- <posargs>`), never bare `pytest`,
  `ruff` or `pyright`.
- **Do not edit `CHANGELOG.rst` or bump `__version__`**; both are release-only.
- **Pickling caches is unsupported.** It happens to work (`test_pickle*`), but the
  format may change in any release. Do not document, advertise or build on it.
- PRs reference an open issue (except trivial fixes), in separate commits:
  `Fix #123: ...`, `Tests for #123: ...`, `Docs for #123: ...`.
- New behavior needs tests under `tests/`; user-visible features need docs in
  `docs/index.rst` (doctested). Keep `README.rst` examples in sync with it.
- Docs style: two spaces after a sentence; single backticks for parameters and
  `:meth:`/`:func:`/`:exc:` roles in `docs/index.rst`, ``double backticks`` in
  `CHANGELOG.rst`, whose entries are imperative one-liners without issue numbers,
  tagged "(breaking change)", "(potentially breaking change)" or "(broken since
  vX.Y.Z)"; docs-only work is one "Various documentation improvements." line, speed-ups
  one "Various performance improvements." line; two blank lines between releases.
- Prefer clarity and performance over DRY: the decorator modules duplicate one wrapper
  per lock/condition/info combination. Apply changes to **all** variants.

## Architecture

**Caches** (`__init__.py`): `Cache` is a `MutableMapping`; a value's size must not
change after insertion. With the default `getsizeof` the private size dict is `None`,
each item counts 1 and `getsizeof()` is never called. Subclasses override
`__setitem__`, `__delitem__`, `popitem()`, `clear()` and optionally `__getitem__`;
after the parent `__getitem__`, check the subclass's own bookkeeping (not
`key in self`), since `__missing__` may not store the item. `popitem()` evicts via `del self[key]`, so subclass `__delitem__` overrides
see evictions. `_TimedCache` (`TTLCache`, `TLRUCache`) wraps the timer in a re-entrant
`_Timer` that freezes time per operation. Expiry is lazy: `__len__`, `__repr__` and
`currsize` call `expire()` first, `clear()` does not, and deleting a present-but-expired
key removes it and raises `KeyError`. `expire()` returns early when nothing has expired
and is a documented override hook, so every insert and `popitem()` must keep calling
it. Look links/items up with `.get()`; raising `KeyError` per new key cost ~200 ns.

**`@cached`** (`_cached.py`): one closure per lock/condition/info combination;
`condition` without `lock` serves as both. Call `functools.update_wrapper()` *before*
setting wrapper attributes so stacked decorators keep their state. `info=False` sets
`cache_info = None`; `cache=None` is deprecated. On methods, cache and counters are
shared by all instances.

**`@cachedmethod`** (`_cachedmethod.py`, `_descriptor.py`): each variant defines a
`Descriptor` with a nested per-instance `Wrapper(obj, descriptor)`, stored in
`obj.__dict__` via `setdefault`; `super()` lookups use
`obj.__dict__["__cachetools_cachedmethods"]` keyed by descriptor. A missing or
read-only `__dict__` raises `TypeError` from `info=True` descriptors; `info=False` ones
(`_ClassMethodDescriptor`) warn (`stacklevel=4`, at the caller) and run a throwaway
`Wrapper`, as does their **deprecated** `@classmethod` use. Class access returns a lazy
`_Unbound` callable object, deliberately not a function so `create_autospec()` strips
the receiver (#443); it takes the receiver positionally or by the wrapped method's first
parameter name. Pickle/deepcopy (#417) rebuild wrappers through their descriptor, so
counters reset and nothing unpicklable is serialized; `_MethodDescriptor._lookup` must
stay importable. Stampede prevention uses a pending set per instance, passed
positional-only so a method parameter named `pending` still works.

**Shared**: wrappers swallow `ValueError` on store; locked variants release the lock
while computing and store via `setdefault()`; the condition tier uses
`while k in pending: cond.wait()` and `notify_all()`, so uncontended calls never wait
(same-key recursion deadlocks there).

**`func.py`, `keys.py`**: `*_cache` decorators use `cached(..., condition=Condition(),
info=True)`; `maxsize=None` uses a `dict` (`ttl_cache`: `_UnboundTTLCache`). `hashkey`
returns a `_HashedTuple` using the C tuple hash (a Python-level hash cache was slower),
`methodkey` drops `self`, `typed*` variants append argument types.

## Type Stubs (`*.pyi`)

No annotations in `.py` files. `@overload`s split `info=False` (default, first) and
`info=True`; wrappers use `ParamSpec`, `_cachedmethod_wrapper` uses
`Concatenate[Any, _P]`. `@cached` wrapper stubs have three `__get__` overloads (class
access, instance binding, `obj: object` catch-all for `@staticmethod`).
`_cachedmethod_unbound.__call__` keeps a receiver-less overload for deprecated
`@classmethod` use; `tests/test_classmethod.py` must stay type-clean. pyright runs in
`standard` mode with `reportUnnecessaryTypeIgnoreComment`; prefer scoped suppressions.

## Development and Tests

```bash
tox -p auto                                # all environments
tox -e py -- tests/test_ttl.py -k expire   # posargs go to pytest
```

- CI runs CPython 3.10–3.15, free-threaded 3.13t–3.15t and PyPy. On 3.13+ two
  deprecated `@classmethod` lines show as uncovered; the matrix covers them.
- `tests/__init__.py` has `CacheTestMixin`, `CountedLock`, `CountedCondition`; one
  `TestCase` per cache type; TTL tests use a manual `Timer`. Objects pickled by name
  must be module-level, not locals.
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
  something. Keep accepted trade-offs as Info rows; record settled matters under
  *Maintainer Decisions*. A review changes nothing; fix only when asked.

## Maintainer Decisions (do not re-raise)

- Pickling caches stays undocumented and unsupported. Pickling and deep-copying
  objects that use `@cachedmethod` is supported (#417) and must keep working.
- `copy.copy()` of an instance with an active `@cachedmethod` wrapper shares the
  wrapper; accepted.
- Stacking `@cachedmethod` decorators is unsupported and untested.
- Class access to `@cachedmethod` (`Cls.method(obj, ...)`) builds and discards a
  `Wrapper` per call; accepted.
- A `condition` must provide the full `threading.Condition` interface; `notify()` is
  reserved for future use. Do not propose relaxing the protocol.
