# cachetools

Memoizing collections and decorators, including `functools.lru_cache` variants. Pure
Python ≥ 3.11, no runtime dependencies, `src/` layout, inline type stubs (`*.pyi`,
`py.typed`). Single maintainer; `master` is the release branch, `develop` the 8.0 line.
Code reviews follow `.github/copilot-instructions.md`.

## Commands

Run everything through `tox`, never bare `pytest`, `ruff` or `pyright`:

```bash
tox -p auto                                # all environments, as CI does
tox -e py -- tests/test_ttl.py -k expire   # tests; posargs go to pytest
tox -e pyright,ruff,ruff-format            # type stubs, lint, formatting
tox -e docs,doctest                        # docs build and doctests
```

CI (GitHub Actions on `tkem/cachetools`, every push) runs CPython 3.11–3.15,
free-threaded 3.13t–3.15t and PyPy 3.11; without `gh`, check runs via
`https://api.github.com/repos/tkem/cachetools/actions/runs?branch=<branch>`. Branch
coverage is 100 %; on 3.13+ only the pre-3.13 `@classmethod` line in
`_MethodDescriptor.__get__` is uncovered.

## Code Style

- No annotations in `.py` files; types live in the `.pyi` stubs. Decorator
  `@overload`s come in the order keyword-only `info: Literal[True]`,
  `info: Literal[False] = ...` (default), positional `Literal[True]`.
- Prefer clarity and performance over DRY: one wrapper class per lock/condition/info
  combination in `_decorator.py`, `_cached.py` and `_cachedmethod.py`, and the key
  functions in `keys.py` are written out in full. Apply a change to **all** variants.
- Keep hot paths free of avoidable Python-level calls. Look links and items up with
  `.get()` instead of catching `KeyError` per new key (~200 ns each):

  ```python
  link = links.get(key)
  if link is None:
      ...  # new key
  ```

- Unsupported use raises `TypeError` before anything is cached, chained `from None`;
  a store that fails with `ValueError` (value too large) is swallowed and the
  computed value returned.
- Docs (`docs/index.rst`, doctested): wrap prose at column 70, two spaces after a
  sentence, single backticks for parameters and `:meth:`/`:func:`/`:exc:` roles. Keep
  `README.rst` examples in sync with it.

## Architecture Constraints

- A value's size must not change after insertion. With the default `getsizeof` the
  size dict is `None` and `getsizeof()` is never called: keep that fast path.
- Cache subclasses override `__setitem__`, `__delitem__`, `popitem()`, `clear()` and
  optionally `__getitem__`; after the parent `__getitem__`, check the subclass's own
  bookkeeping, not `key in self`, since `__missing__` may not store the item.
  `popitem()` evicts via `del self[key]`, so `__delitem__` overrides see evictions.
- Timed caches expire lazily (`__len__`, `__repr__` and `currsize` call `expire()`,
  `clear()` does not); `expire()` is a documented override hook, so every insert and
  `popitem()` must keep calling it.
- Decorator wrappers are objects, not functions; `_WrapperBase` runs
  `update_wrapper()` *before* setting its public attributes (stacked decorators).
- `@cachedmethod` stores per-instance wrappers in `obj.__dict__`; `super()` lookups and
  lookups after `del Cls.method` use `obj.__dict__["__cachetools_cachedmethods"]`.
  `cache_key` is `partial(key, obj)`, not `types.MethodType`, which on PyPy accepts a
  non-callable `key`. Pickling and deep-copying such objects (#417) and
  `create_autospec()` on their classes (#443) must keep working;
  `_MethodDescriptor._lookup` must stay importable.
- Key functions return plain tuples, `args` itself without kwargs; `_HashedTuple`
  survives only as the kwargs separator and to load keys pickled by 7.x.

## Testing

- New behavior needs tests under `tests/`; user-visible features need docs in
  `docs/index.rst`. One `TestCase` per cache type on `CacheTestMixin`; TTL tests use a
  manual `Timer`. Objects pickled by name must be reachable from module level.
- Stub checks need concrete annotated tests without `# type: ignore`, since
  `test_func.py` calls decorators via `Callable[..., Any]`.
- Threading tests join with `TIMEOUT` and assert the thread finished.
- Performance: `timeit`, best of 7, on a pinned core (`taskset`), never in a VM,
  against a git worktree of the previous release. Never trade documented subclass
  hooks or semantics for speed.

## Boundaries

- Never edit `CHANGELOG.rst` or bump `__version__`; both are release-only.
- Never promise cross-version pickle compatibility or build on the byte format; any
  release, even a bugfix, may change it.
- Do not re-raise the *Maintainer Decisions* in `.github/copilot-instructions.md`.

## Git

- PRs reference an open issue (except trivial fixes), in separate commits:
  `Fix #123: ...`, `Tests for #123: ...`, `Docs for #123: ...`.
- Run `tox -p auto` before pushing. Update this file in the same PR that changes a
  convention, and keep it under 100 lines.
