:mod:`cachetools` --- Extensible memoizing collections and decorators
=======================================================================

.. module:: cachetools

This module provides various memoizing collections and decorators,
including variants of the Python 3 Standard Library `@lru_cache`_
function decorator.

For the purpose of this module, a *cache* is a mutable_ mapping_ of a
fixed maximum size.  When the cache is full, i.e. by adding another
item the cache would exceed its maximum size, the cache must choose
which item(s) to discard based on a suitable `cache algorithm`_.  In
general, a cache's size is the total size of its items, and an item's
size is a property or function of its value, e.g. the result of
``sys.getsizeof(value)``.  For the trivial but common case that each
item counts as :const:`1`, a cache's size is equal to the number of
its items, or ``len(cache)``.

Multiple cache classes based on different caching algorithms are
implemented, and decorators for easily memoizing function and method
calls are provided, too.

.. note::

   Several features are now marked as deprecated and will be removed
   in the next major release, :mod:`cachetools` version 2.0.  If you
   happen to rely on any of these features, it is highly recommended
   to specify your module dependencies accordingly, for example
   ``cachetools ~= 1.1`` when using :mod:`setuptools`.

.. versionchanged:: 1.1

   Moved :func:`functools.lru_cache` compatible decorators to the
   :mod:`cachetools.func` module.  For backwards compatibility, they
   continue to be visible in this module as well.


Cache implementations
------------------------------------------------------------------------

This module provides several classes implementing caches using
different cache algorithms.  All these classes derive from class
:class:`Cache`, which in turn derives from
:class:`collections.MutableMapping`, and provide :attr:`maxsize` and
:attr:`currsize` properties to retrieve the maximum and current size
of the cache.  When a cache is full, :meth:`setitem` calls
:meth:`popitem` repeatedly until there is enough room for the item to
be added.

All cache classes accept an optional `missing` keyword argument in
their constructor, which can be used to provide a default *factory
function*.  If the key `key` is not present, the ``cache[key]``
operation calls :meth:`Cache.__missing__`, which in turn calls
`missing` with `key` as its sole argument.  The cache will then store
the object returned from ``missing(key)`` as the new cache value for
`key`, possibly discarding other items if the cache is full.  This may
be used to provide memoization for existing single-argument functions::

    from cachetools import LRUCache
    import urllib.request

    def get_pep(num):
        """Retrieve text of a Python Enhancement Proposal"""
        url = 'http://www.python.org/dev/peps/pep-%04d/' % num
        with urllib.request.urlopen(url) as s:
            return s.read()

    cache = LRUCache(maxsize=4, missing=get_pep)

    for n in 8, 9, 290, 308, 320, 8, 218, 320, 279, 289, 320, 9991:
        try:
            print(n, len(cache[n]))
        except urllib.error.HTTPError:
            print(n, 'Not Found')
    print(sorted(cache.keys()))


:class:`Cache` also features a :meth:`getsizeof` method, which returns
the size of a given `value`.  The default implementation of
:meth:`getsizeof` returns :const:`1` irrespective of its argument,
making the cache's size equal to the number of its items, or
``len(cache)``.  For convenience, all cache classes accept an optional
named constructor parameter `getsizeof`, which may specify a function
of one argument used to retrieve the size of an item's value.

.. autoclass:: Cache
   :members:

   This class discards arbitrary items using :meth:`popitem` to make
   space when necessary.  Derived classes may override :meth:`popitem`
   to implement specific caching strategies.  If a subclass has to
   keep track of item access, insertion or deletion, it may
   additionally need to override :meth:`__getitem__`,
   :meth:`__setitem__` and :meth:`__delitem__`.  If a subclass wants
   to store meta data with its values, i.e. the `value` argument
   passed to :meth:`Cache.__setitem__` is different from what the
   derived class's :meth:`__setitem__` received, it will probably need
   to override :meth:`getsizeof`, too.

.. autoclass:: LFUCache
   :members:

   This class counts how often an item is retrieved, and discards the
   items used least often to make space when necessary.

.. autoclass:: LRUCache
   :members:

   This class discards the least recently used items first to make
   space when necessary.

.. autoclass:: RRCache(maxsize, choice=random.choice, missing=None, getsizeof=None)
   :members:

   This class randomly selects candidate items and discards them to
   make space when necessary.

   By default, items are selected from the list of cache keys using
   :func:`random.choice`.  The optional argument `choice` may specify
   an alternative function that returns an arbitrary element from a
   non-empty sequence.

.. autoclass:: TTLCache(maxsize, ttl, timer=time.time, missing=None, getsizeof=None)
   :members:
   :exclude-members: expire

   This class associates a time-to-live value with each item.  Items
   that expire because they have exceeded their time-to-live will be
   removed automatically.  If no expired items are there to remove,
   the least recently used items will be discarded first to make space
   when necessary.  Trying to access an expired item will raise a
   :exc:`KeyError`.

   By default, the time-to-live is specified in seconds, and the
   :func:`time.time` function is used to retrieve the current time.  A
   custom `timer` function can be supplied if needed.

   .. automethod:: expire(self, time=None)

      Since expired items will be "physically" removed from a cache
      only at the next mutating operation, e.g. :meth:`__setitem__` or
      :meth:`__delitem__`, to avoid changing the underlying dictionary
      while iterating over it, expired items may still claim memory
      although they are no longer accessible.  Calling this method
      removes all items whose time-to-live would have expired by
      `time`, so garbage collection is free to reuse their memory.  If
      `time` is :const:`None`, this removes all items that have
      expired by the current value returned by :attr:`timer`.


Decorators
------------------------------------------------------------------------

The :mod:`cachetools` module provides decorators for memoizing
function and method calls.  This can save time when a function is
often called with the same arguments::

  from cachetools import cached

  @cached(cache={})
  def fib(n):
      return n if n < 2 else fib(n - 1) + fib(n - 2)

  for i in range(100):
      print('fib(%d) = %d' % (i, fib(i)))

.. decorator:: cached(cache, key=hashkey, lock=None)

   Decorator to wrap a function with a memoizing callable that saves
   results in a cache.

   The `cache` argument specifies a cache object to store previous
   function arguments and return values.  Note that `cache` need not
   be an instance of the cache implementations provided by the
   :mod:`cachetools` module.  :func:`cached` will work with any
   mutable mapping type, including plain :class:`dict` and
   :class:`weakref.WeakValueDictionary`.

   `key` specifies a function that will be called with the same
   positional and keyword arguments as the wrapped function itself,
   and which has to return a suitable cache key.  Since caches are
   mappings, the object returned by `key` must be hashable.  The
   default is to call :func:`hashkey`.

   If `lock` is not :const:`None`, it must specify an object
   implementing the `context manager`_ protocol.  Any access to the
   cache will then be nested in a ``with lock:`` statement.  This can
   be used for synchronizing thread access to the cache by providing a
   :class:`threading.RLock` instance, for example.

   .. note::

      The `lock` context manager is used only to guard access to the
      cache object.  The underlying wrapped function will be called
      outside the `with` statement, and must be thread-safe by itself.

   The original underlying function is accessible through the
   :attr:`__wrapped__` attribute of the memoizing wrapper function.
   This can be used for introspection or for bypassing the cache.

   To perform operations on the cache object, for example to clear the
   cache during runtime, the cache should be assigned to a variable.
   When a `lock` object is used, any access to the cache from outside
   the function wrapper should also be performed within an appropriate
   `with` statement::

     from threading import RLock
     from cachetools import cached, LRUCache

     cache = LRUCache(maxsize=100)
     lock = RLock()

     @cached(cache, lock=lock)
     def fib(n):
         return n if n < 2 else fib(n - 1) + fib(n - 2)

     # make sure access to cache is synchronized
     with lock:
         cache.clear()

   It is also possible to use a single shared cache object with
   multiple functions.  However, care must be taken that different
   cache keys are generated for each function, even for identical
   function arguments::

     from functools import partial
     from cachetools import cached, hashkey, LRUCache

     cache = LRUCache(maxsize=100)

     @cached(cache, key=partial(hashkey, 'fib'))
     def fib(n):
         return n if n < 2 else fib(n - 1) + fib(n - 2)

     @cached(cache, key=partial(hashkey, 'fac'))
     def fac(n):
         return 1 if n == 0 else n * fac(n - 1)

     print(fib(42))
     print(fac(42))
     print(cache)

   .. versionadded:: 1.1

.. decorator:: cachedmethod(cache, key=hashkey, lock=None, typed=False)

   Decorator to wrap a class or instance method with a memoizing
   callable that saves results in a (possibly shared) cache.

   The main difference between this and the :func:`cached` function
   decorator is that `cache` and `lock` are not passed objects, but
   functions.  Both will be called with :const:`self` (or :const:`cls`
   for class methods) as their sole argument to retrieve the cache or
   lock object for the method's respective instance or class.

   .. note::

      As with :func:`cached`, the context manager obtained by calling
      ``lock(self)`` will only guard access to the cache itself.  It
      is the user's responsibility to handle concurrent calls to the
      underlying wrapped method in a multithreaded environment.

   If `key` or the optional `typed` keyword argument are set to
   :const:`True`, the :func:`typedkey` function is used for generating
   hash keys.  This has been deprecated in favor of specifying
   ``key=typedkey`` explicitly.

   One advantage of :func:`cachedmethod` over the :func:`cached`
   function decorator is that cache properties such as `maxsize` can
   be set at runtime::

     import operator
     import urllib.request

     from cachetools import LRUCache, cachedmethod

     class CachedPEPs(object):

         def __init__(self, cachesize):
             self.cache = LRUCache(maxsize=cachesize)

         @cachedmethod(operator.attrgetter('cache'))
         def get(self, num):
             """Retrieve text of a Python Enhancement Proposal"""
             url = 'http://www.python.org/dev/peps/pep-%04d/' % num
             with urllib.request.urlopen(url) as s:
                 return s.read()

     peps = CachedPEPs(cachesize=10)
     print("PEP #1: %s" % peps.get(1))

   For backwards compatibility, the default key function used by
   :func:`cachedmethod` will generate distinct keys for different
   methods to ease using a shared cache with multiple methods.  This
   has been deprecated, and relying on this feature is strongly
   discouraged.  When using a shared cache, distinct key functions
   should be used, as with the :func:`cached` decorator.

   .. versionadded:: 1.1

      The optional `key` and `lock` parameters.

   .. versionchanged:: 1.1

      The :attr:`__wrapped__` attribute is now set when running Python
      2.7, too.

   .. deprecated:: 1.1

      The `typed` argument.  Use ``key=typedkey`` instead.

   .. deprecated:: 1.1

      When using a shared cached for multiple methods, distinct key
      function should be used.

   .. deprecated:: 1.1

      The wrapper function's :attr:`cache` attribute.  Use the
      original function passed as the decorator's `cache` argument to
      access the cache object.


Key functions
------------------------------------------------------------------------

The following functions can be used as key functions with the
:func:`cached` and :func:`cachedmethod` decorators:

.. autofunction:: hashkey

   This function returns a :class:`tuple` instance suitable as a cache
   key, provided the positional and keywords arguments are hashable.

   .. versionadded:: 1.1

.. autofunction:: typedkey

   This function is similar to :func:`hashkey`, but arguments of
   different types will yield distinct cache keys.  For example,
   ``typedkey(3)`` and ``typedkey(3.0)`` will return different
   results.

   .. versionadded:: 1.1

These functions can also be helpful when implementing custom key
functions for handling some non-hashable arguments.  For example,
calling the following function with a dictionary as its `env` argument
will raise a :class:`TypeError`, since :class:`dict` is not hashable::

  @cached(LRUCache(maxsize=128))
  def foo(x, y, z, env={}):
      pass

However, if `env` always holds only hashable values itself, a custom
key function can be written that handles the `env` keyword argument
specially::

  def envkey(*args, env={}, **kwargs):
      key = hashkey(*args, **kwargs)
      key += tuple(env.items())
      return key

The :func:`envkey` function can then be used in decorator declarations
like this::

  @cached(LRUCache(maxsize=128), key=envkey)


:mod:`cachetools.func` --- :func:`functools.lru_cache` compatible decorators
============================================================================

.. module:: cachetools.func

To ease migration from (or to) Python 3's :func:`functools.lru_cache`,
this module provides several memoizing function decorators with a
similar API.  All these decorators wrap a function with a memoizing
callable that saves up to the `maxsize` most recent calls, using
different caching strategies.  Note that unlike
:func:`functools.lru_cache`, setting `maxsize` to :const:`None` is not
supported.

The wrapped function is instrumented with :func:`cache_info` and
:func:`cache_clear` functions to provide information about cache
performance and clear the cache.  See the :func:`functools.lru_cache`
documentation for details.

In addition to `maxsize`, all decorators accept the following
optional keyword arguments:

- `typed`, if is set to :const:`True`, will cause function arguments
  of different types to be cached separately.  For example, ``f(3)``
  and ``f(3.0)`` will be treated as distinct calls with distinct
  results.

- `getsizeof` specifies a function of one argument that will be
  applied to each cache value to determine its size.  The default
  value is :const:`None`, which will assign each item an equal size of
  :const:`1`.  This has been deprecated in favor of the new
  :func:`cachetools.cached` decorator, which allows passing fully
  customized cache objects.

- `lock` specifies a function of zero arguments that returns a
  `context manager`_ to lock the cache when necessary.  If not
  specified, :class:`threading.RLock` will be used to synchronize
  access from multiple threads.  The use of `lock` is discouraged, and
  the `lock` argument has been deprecated.

.. versionadded:: 1.1

   Formerly, the decorators provided by :mod:`cachetools.func` were
   part of the :mod:`cachetools` module.

.. decorator:: lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Least Frequently Used
   (LFU) algorithm.

   .. deprecated:: 1.1

      The `getsizeof` and `lock` arguments.

.. decorator:: lru_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Least Recently Used (LRU)
   algorithm.

   .. deprecated:: 1.1

      The `getsizeof` and `lock` arguments.

.. decorator:: rr_cache(maxsize=128, choice=random.choice, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Random Replacement (RR)
   algorithm.

   .. deprecated:: 1.1

      The `getsizeof` and `lock` arguments.

.. decorator:: ttl_cache(maxsize=128, ttl=600, timer=time.time, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to `maxsize` results based on a Least Recently Used (LRU)
   algorithm with a per-item time-to-live (TTL) value.

   .. deprecated:: 1.1

      The `getsizeof` and `lock` arguments.


.. _@lru_cache: http://docs.python.org/3/library/functools.html#functools.lru_cache
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms
.. _context manager: http://docs.python.org/dev/glossary.html#term-context-manager
.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _mutable: http://docs.python.org/dev/glossary.html#term-mutable
