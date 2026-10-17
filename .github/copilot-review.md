# Code Review — cachetools 8.0.0 (unreleased)

**Date:** 2026-10-17
**Reviewed:** `develop` at `59090bf` ("Prepare v8.0.0.").

**CI status:** All `tox` environments pass locally on Python 3.14: `py` (376 passed),
`docs`, `doctest`, `pyright` (0 errors), `ruff`, `ruff-format`.

**Coverage:** 100%.

## Code — Potential Issues

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | Low | `_MethodDescriptor.__get__` (`super()` path) | #417 is only partly fixed. After an override calls `super().method()`, `obj.__dict__["__cachetools_cachedmethods"]` holds the base wrapper keyed by the `_MethodDescriptor`, whose wrapper factory is a local lambda, so `pickle.dumps(obj)` fails with `Can't pickle local object <function _wrapper.<locals>.<lambda>>`. `copy.deepcopy(obj)` succeeds but deep-copies the descriptor key, leaving a stale entry that never matches. The base wrapper's `__reduce__` would also rebuild it as `getattr(obj, name)`, i.e. the *override's* wrapper. A fix could drop or rebuild that dict in a `__reduce__`-friendly form, or key it by attribute name plus defining class. |
| 2 | Low | `_MethodDescriptor.__get__` (`super()` path) | `super().method` never hits the instance dict, so every call builds a throw-away wrapper (including `functools.update_wrapper`) and rescans the MRO before `setdefault` returns the stored one. Correct, but noticeably slower than the primary path. |
| 3 | Low | `_descriptor.py` / `_cachedmethod.py` `_wrapper` | Stacked `@cachedmethod` now silently ignores the outer decorator: `functools.update_wrapper(descriptor, method)` copies the inner descriptor's `__dict__`, including its private `_MethodDescriptor__wrapper`, onto the outer one. Only the inner cache is used. Stacking is unsupported, but this is the same class of bug fixed for `@cached` in 7.2.3; calling `update_wrapper` before setting the descriptor's own state would make it fail loudly (or work) instead. |
| 4 | Low | `_MethodDescriptor.__get__` | On Python 3.11/3.12, `@classmethod` over `@cachedmethod` reaches `__get__` with the class as `obj` and fails with the misleading `TypeError: No '__dict__' attribute on 'type' instance ...` (mappingproxy has no `setdefault`). Same for methods defined on a metaclass. Only 3.13+ gets "Decorating class methods is not supported"; `ClassMethodTest.test_classmethod` is skipped below 3.13 for this reason. An `isinstance(obj, type)` check would give one message everywhere. |
| 5 | Low | `Cache.__setitem__` / `__delitem__` | Size accounting assumes a value's size is stable after insertion; mutating cached values in place can desync `currsize`. By design and documented, but a known footgun. |
| 6 | Low | `_decorator.py` `_ConditionMixin` / `_ConditionInfoMixin` | Stampede prevention uses a pending set per wrapper, i.e. per instance for `@cachedmethod`. Two instances sharing one cache and condition do not coordinate pending keys. |
| 7 | Info | `_cachedmethod.py` `_WrapperBase` | Each per-instance wrapper references `obj`, and `obj.__dict__` references the wrapper, so instances with active wrappers are freed only by the cyclic GC, not by reference counting. Expected for this design; worth knowing for large or short-lived instances. |
| 8 | Info | `_decorator.py` condition mixins | Same-thread recursive re-entry on the same key deadlocks (`wait_for` on its own pending marker). |
| 9 | Info | `_MethodDescriptor.__get_unbound` | Lazy creation of the cached `unbound` function is unsynchronized. Concurrent first class accesses may briefly see distinct (equivalent) functions. Benign. |
| 10 | Info | `TTLCache.__delitem__` / `TLRUCache.__delitem__` | Deleting a key that is present but expired removes it and then raises `KeyError`. Consistent with `key in cache` being `False`; intentional. |
| 11 | Info | `_decorator.py`, `__init__.py`, `_cachedmethod.py` | Leftovers from the refactoring: commented-out `# return self.__info(self.__hits, self.__misses)` lines in all three `cache_info()` methods; the locked mixins' comments still say `self.__wrapped__()` although they call `self.__func`; `TODO: rename make() from_...()?` on `CacheInfo.make`; `FIXME` on `update_wrapper` in `_cachedmethod._WrapperBase.__init__`. Resolve before release, since `CacheInfo.make` is now public by name. |

## Type Stubs (`__init__.pyi`, `keys.pyi`, `func.pyi`)

| # | Severity | Finding |
|---|----------|---------|
| 1 | Info | `CacheInfo` is public, but the stub does not declare `CacheInfo.make`. Fine if `make` stays an implementation detail; then consider renaming it `_make_info` or similar (see Code #11). Note that `namedtuple` already defines `_make`, so avoid that name. |
| 2 | Info | `@classmethod` stacked over `@cached`/`func.*_cache` still reports a false "Argument missing" error. Python passes `cls` correctly at runtime, but pyright does not bind through the wrapper's `__get__` there. Rare and not encouraged. |
| 3 | Info | `_cached_wrapper_info.__get__` carries `# pyright: ignore[reportIncompatibleMethodOverride]`. Pyright cannot match the subclass overloads against the base's self-typed `Concatenate` overload. The override is sound. |

Resolved since 7.2.3: the receiver-less `_cachedmethod_unbound.__call__` overload
and the `cache: MutableMapping | None` typing were removed together with
`@classmethod` and `cache=None` support, and the runtime no longer sets
`cache_info = None`, matching the stubs.

## Tests — Gaps

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | No test pickles or deep-copies an instance after a `super()` call to a cached base method (Code #1). |
| 2 | Low | `UnboundMethodTest` does not assert that class access exposes no `cache_clear`/`cache_info`, and does not exercise class access for the lock/condition variants. |
| 3 | Low | `ClassMethodTest.test_classmethod_basic` only checks for `TypeError` on 3.11/3.12, which hides the misleading message (Code #4). |
| 4 | Info | `CacheTestMixin` deliberately checks key existence rather than the specific eviction victim; policy-specific checks live in the per-cache test files. No action needed. |
| 5 | Info | `test_func.py` calls decorators through `Callable[..., Any]`; one concrete test (`FIFODecoratorTest.test_decorator_method_typed`) covers the shared `_cachetools_cache_wrapper` stub. Enough. |

## Docs (`docs/index.rst`)

| # | Priority | Finding |
|---|----------|---------|
| 1 | Low | `CacheInfo` is now public and referenced as `:class:`CacheInfo``, but has no `.. class::` entry, so the reference does not resolve. Document its fields and the `maxsize=None` / `len(cache)` behavior for non-`Cache` mappings. |
| 2 | Low | The `@cachedmethod` docs do not mention that class access (`Cls.method`) yields a plain function without `cache_clear()`/`cache_info()`, or that pickling an instance resets `cache_info()` counters. |
| 3 | Low | The `condition` docs require `wait()`, `wait_for()`, `notify()` and `notify_all()`, but only `wait_for()` and `notify_all()` are used at runtime (the stub's `_AbstractCondition` notes this too). Docs and protocol could be relaxed. |
| 4 | Info | Neither the `@cached` nor the `cachetools.func.*_cache` docs mention that they may decorate methods. Worth a one-line caveat that the cache and counters are then shared across all instances, unlike `@cachedmethod`. |

## Keys & Func Modules

No issues found. `hashkey`/`typedkey` sort keyword arguments and cache the hash in
`_HashedTuple`, which is not pickled. Every `func.py` decorator is built on
`cached(..., condition=Condition(), info=True)`, so stampede prevention is on by
default. `_UnboundTTLCache` extends `TTLCache` with `math.inf` maxsize for
`maxsize=None`.
