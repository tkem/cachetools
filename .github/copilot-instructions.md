# Copilot Instructions for cachetools

**cachetools** provides memoizing collections and decorators, including variants of
`functools.lru_cache`. Pure Python ≥ 3.10, no runtime dependencies, inline type stubs
(`py.typed`). Single maintainer; `master` is the release branch.

## Ground Rules

- **Run everything through `tox`** (`tox -e <env> -- <posargs>`), never bare `pytest`,
  `ruff` or `pyright`.
- **Do not edit `CHANGELOG.rst` or bump `__version__`**; both are release-only.
- **Pickling caches is unsupported.** It happens to work (`test_pickle*`), but the
  format is an implementation detail that any release may change. Do not document,
  advertise, or build features on it.
- PRs reference an open issue (except trivial fixes), in separate commits:
  `Fix #123: ...`, `Tests for #123: ...`, `Docs for #123: ...`.
- New behavior needs tests under `tests/`; user-visible features need docs in
  `docs/index.rst` (doctested). Keep `README.rst` examples in sync with it.
- Docs style: two spaces after a sentence; single backticks for parameters and
  `:meth:`/`:func:`/`:exc:` roles in `docs/index.rst`, ``double backticks`` in
  `CHANGELOG.rst`. CHANGELOG entries are imperative one-liners without issue numbers,
  tagged "(breaking change)", "(potentially breaking change)" or "(broken since
  vX.Y.Z)"; docs-only work is one "Various documentation improvements." line,
  internal speed-ups without behavior change one "Various performance
  improvements." line; releases are separated by two blank lines.
- Prefer clarity and performance over DRY: the decorator modules duplicate one
  wrapper per lock/condition/info combination. Apply changes to **all** variants.

## Architecture

**Caches** (`__init__.py`): `Cache` is a `MutableMapping` with `maxsize`, `currsize`
and `getsizeof`; `maxsize=0` and `math.inf` are valid, negative values raise
`ValueError`, and a value's size must not change after insertion. Subclasses override
`__setitem__`, `__delitem__`, `popitem()`, `clear()` and optionally `__getitem__`,
binding parent methods via default parameters (`cache_setitem=Cache.__setitem__`); after
the parent `__getitem__`, check the subclass's own bookkeeping (not `key in self`) to
handle a `__missing__` that does not store the item. `popitem()` reads via
`Cache.__getitem__` and evicts via `del self[key]`, so subclass `__delitem__` overrides
see evictions. `_TimedCache`
(`TTLCache`, `TLRUCache`) wraps the timer in a re-entrant `_Timer` that freezes time
per operation; expiry is lazy: `__len__`, `__repr__` and `currsize` call `expire()`
first, `clear()` does not, and deleting a present-but-expired key removes it and
raises `KeyError`. `expire()` returns the removed `(key, value)` pairs.

**`@cached`** (`_cached.py`): one closure per lock/condition/info combination;
`condition` without `lock` serves as both. Call `functools.update_wrapper()` *before*
setting wrapper attributes so stacked decorators keep their state. `info=False` sets
`cache_info = None`; `cache=None` is deprecated. On methods, cache and counters are
shared by all instances.

**`@cachedmethod`** (`_cachedmethod.py`, `_descriptor.py`): each variant defines a
`Descriptor` with a nested per-instance `Wrapper`, constructed as
`Wrapper(obj, descriptor)`. `_MethodDescriptor.__get__` stores it in `obj.__dict__` via
`setdefault`; wrappers reached through `super()` go to
`obj.__dict__["__cachetools_cachedmethods"]` keyed by descriptor. Class access returns
a lazily created `_Unbound` callable object, deliberately not a function so
`create_autospec()` strips the receiver (#443); it takes the receiver from `*args` or by
the wrapped method's first parameter name when passed as a keyword, binds via `__get__`
when aliased in another class body, and pickles/copies by reference. Pickle/deepcopy
(#417): `_WrapperBase.__reduce__` returns `(descriptor.__get__, (obj,))` and
`_MethodDescriptor.__reduce__` returns `(_lookup, (owner, attrname))`, so wrappers are
rebuilt through their descriptor, counters reset, and lock, condition, `__wrapped__`
and the nested `Wrapper` class are never serialized; `_lookup` must stay importable and
reads the owner's *current* class dict. `__set_name__` on two names, or instances
without a writable `__dict__`, raise `TypeError`; `@classmethod` use
(`_ClassMethodDescriptor`, `info=False` only) and instances without `__dict__` are
**deprecated** and warn instead. Stampede prevention uses a pending set per instance;
`_condition`'s inner `wrapper(self, pending, /, ...)` takes `pending` positional-only
so a method parameter of that name can be passed by keyword.

**Shared**: wrappers swallow `ValueError` on store; locked variants release the lock
while computing and store via `setdefault()`; the condition tier adds pending keys with
`while k in pending: cond.wait()` and `notify_all()`, so uncontended calls never wait
(same-key recursion deadlocks there).

**`func.py`, `keys.py`**: `*_cache` decorators use `cached(..., condition=Condition(),
info=True)` plus `cache_parameters()`; `maxsize=None` uses a `dict` (`ttl_cache`:
`_UnboundTTLCache`). `hashkey` returns a `_HashedTuple` using the C tuple hash (a
Python-level hash cache was slower; kept commented out with its rationale),
`methodkey` drops `self`, `typed*` variants append argument types.

## Type Stubs (`*.pyi`)

No annotations in `.py` files. `@overload`s split `info=False` (default, first) and
`info=True`; wrappers use `ParamSpec`, `_cachedmethod_wrapper` uses
`Concatenate[Any, _P]`. `@cached` wrapper stubs have three `__get__` overloads (class
access, instance binding, `obj: object` catch-all for `@staticmethod`);
`_cached_wrapper_info` needs a scoped `# pyright: ignore[reportIncompatibleMethodOverride]`.
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
  `TestCase` per cache type; TTL tests use a manual `Timer`.
- `test_cached.py`/`test_cachedmethod.py` cover all lock/condition/info combinations.
  Objects pickled by name must be module-level (`Cached`, `CachedChild`), not locals.
- `test_func.py` calls decorators via `Callable[..., Any]`; stub checks need concrete
  annotated tests (`test_decorator_method*`) without `# type: ignore`.
- `test_threading.py`: join with `TIMEOUT` and assert threads finished; the condition
  tests force a contended `wait()`, since `CountedCondition.wait_count` stays 0 for
  single-threaded calls.
- Performance work: measure with `timeit` (best of 7) against a git worktree of the
  previous release, before and after; keep hot paths free of avoidable Python-level
  calls, and do not trade documented subclass hooks or semantics for speed.

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

- Pickling caches stays undocumented and unsupported. Pickling and deep-copying
  objects that use `@cachedmethod` is supported (#417) and must keep working.
- `copy.copy()` of an instance with an active `@cachedmethod` wrapper shares the
  wrapper; accepted.
- Stacking `@cachedmethod` decorators is unsupported and untested.
- `super()` and class access to `@cachedmethod` build and discard a `Wrapper` per call;
  accepted (looking up the stored wrapper first was prototyped and declined).
- A `condition` must provide the full `threading.Condition` interface; `notify()` is
  reserved for future use. Do not propose relaxing the protocol.
- `TTLCache`/`TLRUCache` read the timer through the `timer` property, not a cached
  private attribute (~28 ns per hit); evicting-insert overhead in the timed caches is
  accepted as inherent.
