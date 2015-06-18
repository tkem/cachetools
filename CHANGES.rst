1.0.2 2015-06-18
----------------

- Allow simple cache instances to be pickled.

- Refactor ``Cache.getsizeof`` and ``Cache.missing`` default
  implementation.


1.0.1 2015-06-06
----------------

- Code cleanup for improved PEP 8 conformance.

- Add documentation and unit tests for using ``@cachedmethod`` with
  generic mutable mappings.

- Improve documentation.


1.0.0 2014-12-19
----------------

- Provide ``RRCache.choice`` property.

- Improve documentation.


0.8.2 2014-12-15
----------------

- Use a ``NestedTimer`` for ``TTLCache``.


0.8.1 2014-12-07
----------------

- Deprecate ``Cache.getsize()``.


0.8.0 2014-12-03
----------------

- Ignore ``ValueError`` raised on cache insertion in decorators.

- Add ``Cache.getsize()``.

- Add ``Cache.__missing__()``.

- Feature freeze for `v1.0`.


0.7.1 2014-11-22
----------------

- Fix `MANIFEST.in`.


0.7.0 2014-11-12
----------------

- Deprecate ``TTLCache.ExpiredError``.

- Add `choice` argument to ``RRCache`` constructor.

- Refactor ``LFUCache``, ``LRUCache`` and ``TTLCache``.

- Use custom ``NullContext`` implementation for unsynchronized
  function decorators.


0.6.0 2014-10-13
----------------

- Raise ``TTLCache.ExpiredError`` for expired ``TTLCache`` items.

- Support unsynchronized function decorators.

- Allow ``@cachedmethod.cache()`` to return None


0.5.1 2014-09-25
----------------

- No formatting of ``KeyError`` arguments.

- Update ``README.rst``.


0.5.0 2014-09-23
----------------

- Do not delete expired items in TTLCache.__getitem__().

- Add ``@ttl_cache`` function decorator.

- Fix public ``getsizeof()`` usage.


0.4.0 2014-06-16
----------------

- Add ``TTLCache``.

- Add ``Cache`` base class.

- Remove ``@cachedmethod`` `lock` parameter.


0.3.1 2014-05-07
----------------

- Add proper locking for ``cache_clear()`` and ``cache_info()``.

- Report `size` in ``cache_info()``.


0.3.0 2014-05-06
----------------

- Remove ``@cache`` decorator.

- Add ``size``, ``getsizeof`` members.

- Add ``@cachedmethod`` decorator.


0.2.0 2014-04-02
----------------

- Add ``@cache`` decorator.

- Update documentation.


0.1.0 2014-03-27
----------------

- Initial release.
