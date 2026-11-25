# cachetools

Memoizing collections and decorators, including `functools.lru_cache` variants. Pure
Python ≥ 3.11, no runtime dependencies, `src/` layout, inline type stubs (`*.pyi`,
`py.typed`). Single maintainer; `master` is the release branch, `develop` prepares the
next release, rebased onto `master`, and `dev/vX.Y.x` branches maintain older series
with fixes picked from `master`. Code reviews follow `.github/copilot-instructions.md`.

## Commands

Run everything through `tox`, never bare `pytest`, `ruff` or `pyright`:

```bash
tox -p auto                                # all environments, as CI does
tox -e py -- tests/test_ttl.py -k expire   # tests; posargs go to pytest
tox -e pyright,ruff,ruff-format,docs,doctest   # stubs, lint, format, docs
```

CI (GitHub Actions, every push) runs CPython 3.11–3.15, free-threaded 3.13t–3.15t and
the latest PyPy 3.11 (locally `tox -e pypy311`, with that release from
`downloads.python.org/pypy` on `PATH` for that run only, as it shadows `python3.11`);
without `gh`, list runs via `api.github.com/repos/tkem/cachetools/actions/runs` and
read job logs, which need a login there, with the GitHub MCP `get_job_logs`. Branch
coverage is 100 %, except the pre-3.13 `@classmethod` line (`_descriptor.py`) on 3.13+.

## Code Style

- No annotations in `.py` files; types live in the `.pyi` stubs. Decorator `@overload`
  order: keyword-only `info: Literal[True]`, `info: Literal[False] = ...`, positional.
- Prefer clarity and performance over DRY: one wrapper class per lock/condition/info
  combination in `_decorator.py`, `_cached.py` and `_cachedmethod.py`, and the key
  functions in `keys.py` are written out in full. Apply a change to **all** variants.
- Keep hot paths free of avoidable Python-level calls. Look links and items up with
  `.get()` or test `in` first instead of catching `KeyError` per new key (~50 ns each).
- Wrapper `__call__` methods, `_Unbound.__call__`, `_MethodDescriptor.__call__` and
  the key functions take their receiver positional-only (`self, /`), so wrapped
  callables may take a keyword argument named `self`; keep it that way everywhere.
- Stubs: never annotate `self` in an `__init__` overload with class-scoped type
  variables (pyright warns, and `tox` does not fail on warnings, so check for
  `0 warnings`); an overload without `timer` relies on the `_TT` default instead.
- Unsupported use raises `TypeError`, at decoration time where it shows, else before
  anything is cached (`from None`); a store failing with `ValueError` returns the value.
- Docs (`docs/index.rst`, doctested): wrap prose at column 70, two spaces after a
  sentence, single backticks for parameters and `:meth:`/`:func:`/`:exc:` roles. Keep
  `README.rst` examples in sync. Multi-line code comments are full sentences, too.

## Architecture Constraints

- A value's size must not change after insertion. With the default `getsizeof` the
  size dict is `None` and `getsizeof()` is never called: keep that fast path.
- Cache subclasses override `__setitem__`, `__delitem__`, `popitem()`, `clear()` and
  optionally `__getitem__`; after the parent `__getitem__`, check the subclass's own
  bookkeeping, not `key in self`, since `__missing__` may not store the item.
  `popitem()` evicts via `del self[key]`, so `__delitem__` overrides see evictions.
- `items()` and `values()` read through `__getitem__` and count as a use of every item;
  inspect state with `list(cache)`. `LFUCache` ties discard the least recently used key
  in O(1): keep the `OrderedDict` per use count (#461). `LFUCache` and `TTLCache` links
  pickle without `next`/`prev` (recursion limit, #474); `__setstate__` relinks them.
  `__copy__` copies `__dict__` shallowly; each class then copies its own state (#473).
- Timed caches expire lazily (`__len__`, `__repr__` and `currsize` call `expire()`,
  `clear()` does not); every insert and `popitem()` must keep calling that hook.
- Decorator wrappers are objects, not functions (`@cached` ones copy as themselves);
  `_WrapperBase` runs `update_wrapper()` *before* setting its attributes (stacking).
- A separate `lock` must be its `condition`'s own (`Condition(lock)`, not checked);
  `func.py` passes one, as `with cond:` runs Python-level methods (#485). Pending keys
  map to threads, so recursion runs uncached; `threading` is imported lazily there.
- `@cachedmethod` stores per-instance wrappers in `obj.__dict__`; `super()` lookups and
  lookups after `del Cls.method` use `obj.__dict__["__cachetools_cachedmethods"]`.
  `cache_key` is `partial(key, obj)`, not `types.MethodType`, which on PyPy accepts a
  non-callable `key`. Pickling and deep-copying such objects (#417), `create_autospec()`
  on their classes (#443) and importing `_MethodDescriptor._lookup` must keep working.
- Key functions return plain tuples (`hashkey`: `args` itself without kwargs);
  `_HashedTuple` survives only as kwargs separator and to load keys pickled by 7.x.

## Testing

- New behavior needs tests in `tests/`, user-visible features docs in `docs/index.rst`.
  One `TestCase` per cache type on `CacheTestMixin`; TTL tests use a manual `Timer`.
  Objects pickled by name must be module-level. Copy and pickle caches in a used state.
- Stub checks need concrete annotated tests without `# type: ignore`, since
  `test_func.py` calls decorators via `Callable[..., Any]`.
- Threading tests use real `Lock`/`Condition` objects (`WaitCondition(lock)` forces a
  contended `wait()`), join with `TIMEOUT` and assert the thread finished.
- Performance: `.github/copilot-bench.py` (`timeit`, best of 7) on one pinned core
  (`taskset`), never in a VM, against a worktree of the previous release; never trade
  documented hooks or semantics for speed. Scratch files: `.cache/tmp/`; delete after.

## Boundaries

- Never edit `CHANGELOG.rst` or bump `__version__` unless the maintainer asks.
- Never promise or rely on cross-version pickle compatibility; any release may break it.
  Obsolete pickle protocols 0 and 1 are unsupported (`TLRUCache` raises `TypeError`).

## Git

- PRs reference an open issue (except trivial fixes), initially in separate commits to
  reproduce it (may be squash-merged later): `Fix`/`Tests for`/`Docs for #123: ...`.
- Run `tox -p auto` before pushing. Never change this file or the `.github/copilot-*`
  files in a code PR; they get a PR of their own. Keep this file under 100 lines.
