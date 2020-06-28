v4.1.1 (2020-06-28)
===================

- Improve ``popitem()`` exception context handling.

- Replace ``float('inf')`` with ``math.inf``.

- Improve "envkey" documentation example.


v4.1.0 (2020-04-08)
===================

- Support ``user_function`` with ``cachetools.func`` decorators
  (Python 3.8 compatibility).

- Support ``cache_parameters()`` with ``cachetools.func`` decorators
  (Python 3.9 compatibility).


v4.0.0 (2019-12-15)
===================

- Require Python 3.5 or later.


v3.1.1 (2019-05-23)
===================

- Document how to use shared caches with ``@cachedmethod``.

- Fix pickling/unpickling of cache keys


v3.1.0 (2019-01-29)
===================

- Fix Python 3.8 compatibility issue.

- Use ``time.monotonic`` as default timer if available.

- Improve documentation regarding thread safety.


v3.0.0 (2018-11-04)
===================

- Officially support Python 3.7.

- Drop Python 3.3 support (breaking change).

- Remove ``missing`` cache constructor parameter (breaking change).

- Remove ``self`` from ``@cachedmethod`` key arguments (breaking
  change).

- Add support for ``maxsize=None`` in ``cachetools.func`` decorators.


v2.1.0 (2018-05-12)
===================

- Deprecate ``missing`` cache constructor parameter.

- Handle overridden ``getsizeof()`` method in subclasses.

- Fix Python 2.7 ``RRCache`` pickling issues.

- Various documentation improvements.


v2.0.1 (2017-08-11)
===================

- Officially support Python 3.6.

- Move documentation to RTD.

- Documentation: Update import paths for key functions (courtesy of
  slavkoja).


v2.0.0 (2016-10-03)
===================

- Drop Python 3.2 support (breaking change).

- Drop support for deprecated features (breaking change).

- Move key functions to separate package (breaking change).

- Accept non-integer ``maxsize`` in ``Cache.__repr__()``.


v1.1.6 (2016-04-01)
===================

- Reimplement ``LRUCache`` and ``TTLCache`` using
  ``collections.OrderedDict``.  Note that this will break pickle
  compatibility with previous versions.

- Fix ``TTLCache`` not calling ``__missing__()`` of derived classes.

- Handle ``ValueError`` in ``Cache.__missing__()`` for consistency
  with caching decorators.

- Improve how ``TTLCache`` handles expired items.

- Use ``Counter.most_common()`` for ``LFUCache.popitem()``.


v1.1.5 (2015-10-25)
===================

- Refactor ``Cache`` base class.  Note that this will break pickle
  compatibility with previous versions.

- Clean up ``LRUCache`` and ``TTLCache`` implementations.


v1.1.4 (2015-10-24)
===================

- Refactor ``LRUCache`` and ``TTLCache`` implementations.  Note that
  this will break pickle compatibility with previous versions.

- Document pending removal of deprecated features.

- Minor documentation improvements.


v1.1.3 (2015-09-15)
===================

- Fix pickle tests.


v1.1.2 (2015-09-15)
===================

- Fix pickling of large ``LRUCache`` and ``TTLCache`` instances.


v1.1.1 (2015-09-07)
===================

- Improve key functions.

- Improve documentation.

- Improve unit test coverage.


v1.1.0 (2015-08-28)
===================

- Add ``@cached`` function decorator.

- Add ``hashkey`` and ``typedkey`` fuctions.

- Add `key` and `lock` arguments to ``@cachedmethod``.

- Set ``__wrapped__`` attributes for Python versions < 3.2.

- Move ``functools`` compatible decorators to ``cachetools.func``.

- Deprecate ``@cachedmethod`` `typed` argument.

- Deprecate `cache` attribute for ``@cachedmethod`` wrappers.

- Deprecate `getsizeof` and `lock` arguments for `cachetools.func`
  decorator.


v1.0.3 (2015-06-26)
===================

- Clear cache statistics when calling ``clear_cache()``.


v1.0.2 (2015-06-18)
===================

- Allow simple cache instances to be pickled.

- Refactor ``Cache.getsizeof`` and ``Cache.missing`` default
  implementation.


v1.0.1 (2015-06-06)
===================

- Code cleanup for improved PEP 8 conformance.

- Add documentation and unit tests for using ``@cachedmethod`` with
  generic mutable mappings.

- Improve documentation.


v1.0.0 (2014-12-19)
===================

- Provide ``RRCache.choice`` property.

- Improve documentation.


v0.8.2 (2014-12-15)
===================

- Use a ``NestedTimer`` for ``TTLCache``.


v0.8.1 (2014-12-07)
===================

- Deprecate ``Cache.getsize()``.


v0.8.0 (2014-12-03)
===================

- Ignore ``ValueError`` raised on cache insertion in decorators.

- Add ``Cache.getsize()``.

- Add ``Cache.__missing__()``.

- Feature freeze for `v1.0`.


v0.7.1 (2014-11-22)
===================

- Fix `MANIFEST.in`.


v0.7.0 (2014-11-12)
===================

- Deprecate ``TTLCache.ExpiredError``.

- Add `choice` argument to ``RRCache`` constructor.

- Refactor ``LFUCache``, ``LRUCache`` and ``TTLCache``.

- Use custom ``NullContext`` implementation for unsynchronized
  function decorators.


v0.6.0 (2014-10-13)
===================

- Raise ``TTLCache.ExpiredError`` for expired ``TTLCache`` items.

- Support unsynchronized function decorators.

- Allow ``@cachedmethod.cache()`` to return None


v0.5.1 (2014-09-25)
===================

- No formatting of ``KeyError`` arguments.

- Update ``README.rst``.


v0.5.0 (2014-09-23)
===================

- Do not delete expired items in TTLCache.__getitem__().

- Add ``@ttl_cache`` function decorator.

- Fix public ``getsizeof()`` usage.


v0.4.0 (2014-06-16)
===================

- Add ``TTLCache``.

- Add ``Cache`` base class.

- Remove ``@cachedmethod`` `lock` parameter.


v0.3.1 (2014-05-07)
===================

- Add proper locking for ``cache_clear()`` and ``cache_info()``.

- Report `size` in ``cache_info()``.


v0.3.0 (2014-05-06)
===================

- Remove ``@cache`` decorator.

- Add ``size``, ``getsizeof`` members.

- Add ``@cachedmethod`` decorator.


v0.2.0 (2014-04-02)
===================

- Add ``@cache`` decorator.

- Update documentation.


v0.1.0 (2014-03-27)
===================

- Initial release.
