# Code Review — cachetools 7.2.5

**Date:** 2026-10-25
**Reviewed:** `dev/v7.2.5` at `5120324`, one commit after "Release v7.2.5" (`a2d411e`,
`__version__` 7.2.5, changelog dated 2026-10-25). Changes since the 7.2.3
review: class access returns the `_Unbound` callable object (#443), which takes the
receiver from `*args` or by the wrapped method's first parameter name when passed as
a keyword (broken in 7.2.4 only), binds like a method when aliased in another class
body, and pickles/copies by reference; `_condition`'s wrapper takes `pending`
positional-only, so a method parameter of that name can be passed by keyword again
(broken since 7.0.0); instances with populated `@cachedmethod` wrappers pickle and
deep-copy again (#417, broken since 7.0.0): wrappers reduce to
`descriptor.__get__(obj)` and descriptors to `_MethodDescriptor._lookup(owner,
attrname)`, with the matching `__get__` overloads on the `_cachedmethod_unbound` stub.

**CI status:** All `tox` environments pass locally on Python 3.14 at `5120324`: `py`
(381 passed), `docs`, `doctest`, `pyright` (0 errors), `ruff`, `ruff-format`.

**Coverage:** 100% except two lines that only run on Python **< 3.13**, where
`@classmethod` over `@cachedmethod` calls `__get__` with the class as `obj` (on 3.13+
the call goes entirely through `_ClassMethodDescriptor.__call__`):
- `_cachedmethod.py:22` — `_WrapperBase.__init__`'s `isinstance(obj, type)` /
  `_warn_classmethod` call
- `_descriptor.py:91` — `_MethodDescriptor.__get__`'s `elif self.__deprecated:` branch

The CI matrix covers both.

## Code — Potential Issues

| # | Priority | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `_MethodDescriptor.__get__` (`super()` path) | `super().method` never hits the instance dict, so every call builds a throw-away `Wrapper` (including `functools.update_wrapper`) and rescans the MRO before `setdefault` returns the stored one. Correct, but noticeably slower than the primary path. |
| 2 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place can desync `currsize`. By design and documented, but a known footgun. |
| 3 | Low | `_cachedmethod.py` `_condition_info` / `_condition` | Stampede prevention uses per-instance pending sets, so two instances sharing one cache and condition do not coordinate pending keys. |
| 4 | Info | `_cachedmethod.py` / `_cached.py` condition variants | Same-thread recursive re-entry on the same key deadlocks (`wait_for` on its own pending marker). |
| 5 | Info | `_MethodDescriptor.__get_unbound` | Lazy creation of the cached `_Unbound` object is unsynchronized. Concurrent first class accesses may briefly see distinct (equivalent) objects; only `Cls.method is Cls.method` identity is affected during that window. Benign. |
| 6 | Info | `_descriptor.py` `_Unbound.__call__` | By design (see its docstring), autospec'd instances accept any arguments: `inspect.signature(mock.method)` is `(*args, **kwargs)`, so autospec no longer checks call arity for `@cachedmethod` methods. Calling a real method through the class with a wrong receiver, e.g. `Cls.method(None, 1)` or `Cls.method(1)`, reports "No `__dict__` attribute on 'int' instance" (verified), since the first argument is taken as the receiver. |
| 7 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a key that is present but expired removes it and then raises `KeyError`. This is consistent with `key in cache` being `False`, but `cache.pop(key, default)` and `del` behave differently around the expiry instant. Intentional; listed for awareness. |
| 8 | Info | `__init__.py` `cachedmethod` `make_info` | A `cache(self)` that is not a mapping is only reported, as `TypeError`, when `cache_info()` is called. Calls and `cache_clear()` work as long as the object supports the operations used. Acceptable, since `cache(self)` is resolved per call anyway. |
| 9 | Info | `_cachedmethod.py` `Wrapper.__call__` / `wrapper(self, ...)` | Stacked `@cachedmethod` is broken: the outer wrapper calls `method(obj, ...)` on the inner *descriptor*. With `info=True` this raises `TypeError: 'Descriptor' object is not callable`. With `info=False` it works only through the deprecated `_ClassMethodDescriptor.__call__` shim, which emits a misleading `@classmethod` `DeprecationWarning` and bypasses the per-instance `Wrapper`. A proper fix would bind via `method.__get__(obj, type(obj))` and pass `__set_name__` on to the inner descriptor. Unsupported by maintainer decision. |
| 10 | Info | `_WrapperBase.__reduce__` | Unpickling and deep-copying reset `hits`/`misses` of `info=True` wrappers, since the wrapper is rebuilt through its descriptor rather than serialized (documented in the code, asserted by `test_decorator_pickle_info` and `_test_copy_super`). Acceptable, since counters are a tuning aid. |
| 11 | Info | `_MethodDescriptor.__reduce__` / `_lookup` | Pickles reference `cachetools._descriptor._MethodDescriptor._lookup` by qualified name, so that path must stay importable for pickles to load across releases. `_lookup` resolves through the owner's *current* class dict, so a pickle loaded while `Cls.method` is reassigned (e.g. under `unittest.mock.patch.object`) silently yields whatever the attribute holds then instead of a wrapper. A descriptor that never received `__set_name__` (the deprecated pre-3.13 `@classmethod` path) reduces to `_lookup(None, None)`: `pickle.dumps` succeeds, `pickle.loads` raises `AttributeError`. |

No implementation bugs found beyond the items above.

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Info | `_cachedmethod_unbound.__call__` has a second, receiver-less overload so that deprecated `@classmethod` + `@cachedmethod` calls (`Cls.method(arg)`) still type-check. Trade-off: a missing instance on a regular method (`Cls.method(arg)`) is not reported. Drop that overload when `@classmethod` support is removed. The receiver is positional-only in both overloads, so `Cls.method(self=obj, value=1)`, which the runtime now accepts, is a pyright error; the receiver's name is not expressible in the stub (`Concatenate[Any, _P]` erases it), so `test_class_call_keyword_receiver` carries `# type: ignore` on those calls. |
| 2 | Info | At runtime, `@cached(info=False)` wrappers have `cache_info = None`, but `_cached_wrapper` does not declare it, so `wrapper.cache_info` is a type error. The stub is arguably right (the attribute is meaningless), but the stub and runtime differ. `_cached_wrapper.cache` is typed `MutableMapping \| None` and `cached()` still accepts `None` for the deprecated pass-through; tighten both when that support is removed. |
| 3 | Info | `@classmethod` stacked over `@cached`/`func.*_cache` still reports a false "Argument missing" error. Python passes `cls` correctly at runtime, but pyright does not bind through the wrapper's `__get__` there. Rare and not encouraged. |
| 4 | Info | `_cached_wrapper_info.__get__` carries `# pyright: ignore[reportIncompatibleMethodOverride]`. Pyright cannot match the subclass overloads against the base's self-typed `Concatenate` overload. The override is sound, since each return type is the `_cached_wrapper_info` subtype of the base's. |

Otherwise fine: `ParamSpec(_P)` and `Concatenate[Any, _P]` preserve signatures. The
overload order is the `Literal[False]` default first, then keyword-only and positional
`Literal[True]`. `func.pyi` overloads cover both `@lru_cache` and `@lru_cache(...)`.
The `__get__` overloads bind `self` correctly for instance and class calls on
`@cached` and `func.*_cache` methods.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `test_classmethod.py` covers only deprecation warnings and basic behavior: no error-path or shared-cache tests. (`info=True` never supported `@classmethod`.) |
| 2 | Low | `UnboundMethodTest` does not assert that class access exposes no `cache_clear`/`cache_info`, and does not exercise class access for the lock/condition variants. |
| 3 | Info | `CacheTestMixin` deliberately checks key existence rather than the specific eviction victim, since it is shared across all cache types. Policy-specific checks live in the per-cache test files. No action needed. |
| 4 | Info | The `test_func.py` `DecoratorTestMixin` calls decorators through `Callable[..., Any]`, so pyright does not check the `func.pyi` stubs there. One concrete test (`FIFODecoratorTest.test_decorator_method_typed`) covers them; that is enough, since all five decorators share `_cachetools_cache_wrapper`. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | The `@cachedmethod` docs do not mention that class access (`Cls.method`) yields a callable without `cache_clear()`/`cache_info()` that takes the receiver positionally or by its parameter name, or that pickling an instance resets its `cache_info()` counters (Code #10). |
| 2 | Info | Neither the `@cached` nor the `cachetools.func.*_cache` docs mention that they may decorate methods (covered by `test_decorator_method`). Worth a one-line caveat that the cache and counters are then shared across all instances, unlike `@cachedmethod`. |

## `CHANGELOG.rst`

No issues found. The 7.2.5 section (dated 2026-10-25) has four imperative one-liners,
the three fixes tagged "(broken since v7.0.0)" or "(broken since v7.2.4)" (origins
verified against the tagged history), docs-only work as the standard line, and two
blank lines before 7.2.4. The file parses cleanly with docutils.

## Keys & Func Modules

No issues found. `hashkey`/`typedkey` sort keyword arguments and cache the hash in
`_HashedTuple`, which is not pickled. Every `func.py` decorator is built on
`cached(..., condition=Condition(), info=True)`, so stampede prevention is on by default.
`_UnboundTTLCache` extends `TTLCache` with `math.inf` maxsize for `maxsize=None`.
