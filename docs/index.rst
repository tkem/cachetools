:mod:`cachetools` --- Extensible memoizing collections and decorators
=======================================================================

.. module:: cachetools

This module provides various memoizing collections and decorators,
including a variant of the Python 3 Standard Library
:func:`functools.lru_cache` function decorator.

.. code-block:: pycon

   >>> from cachetools import LRUCache
   >>> cache = LRUCache(maxsize=2)
   >>> cache.update([('first', 1), ('second', 2)])
   >>> cache
   LRUCache([('second', 2), ('first', 1)], maxsize=2, currsize=2)
   >>> cache['third'] = 3
   >>> cache
   LRUCache([('second', 2), ('third', 3)], maxsize=2, currsize=2)
   >>> cache['second']
   2
   >>> cache['fourth'] = 4
   LRUCache([('second', 2), ('fourth', 4)], maxsize=2, currsize=2)

For the purpose of this module, a *cache* is a mutable_ mapping_ of a
fixed maximum size.  When the cache is full, i.e. the size of the
cache would exceed its maximum size, the cache must choose which
item(s) to discard based on a suitable `cache algorithm`_.  A cache's
size is the sum of the size of its items, and an item's size in
general is a property or function of its value, e.g. the result of
:func:`sys.getsizeof`, or :func:`len` for string and sequence values.

This module provides multiple cache implementations based on different
cache algorithms, as well as decorators for easily memoizing function
and method calls.


Cache Implementations
------------------------------------------------------------------------

This module provides several classes implementing caches using
different cache algorithms.  All these classes derive from class
:class:`Cache`, which in turn derives from
:class:`collections.MutableMapping`, providing additional properties
:attr:`maxsize` and :attr:`currsize` to retrieve the maximum and
current size of the cache.

:class:`Cache` also features a :meth:`getsizeof` method, which returns
the size of a given item.  The default implementation of
:meth:`getsizeof` returns :const:`1` irrespective of its `value`
argument, making the cache's size equal to the number of its items, or
`len(cache)`.  For convenience, all cache classes accept an optional
named constructor parameter `getsizeof`, which may specify a function
of one argument used to retrieve the size of an item's value.

.. autoclass:: Cache
   :members:

.. autoclass:: LRUCache
   :members:

.. autoclass:: LFUCache
   :members:

.. autoclass:: RRCache
   :members:

.. autoclass:: TTLCache
   :members:
   :exclude-members: ExpiredError

   Note that a cache item may expire at *any* time, so iterating over
   the items of a :class:`TTLCache` may raise :exc:`ExpiredError`
   unexpectedly::

      from cachetools import TTLCache, ExpiredError
      import time

      cache = TTLCache(maxsize=100, ttl=1)
      cache.update({1: 1, 2: 2, 3: 3})
      time.sleep(1)

      for key in cache:
          try:
              print(cache[key])
          except ExpiredError:
              print('Key %r has expired' % key)


Function Decorators
------------------------------------------------------------------------

This module provides several memoizing function decorators compatible
with -- though not necessarily as efficient as -- the Python 3
Standard Library :func:`functools.lru_cache` decorator.

In addition to a `maxsize` parameter, all decorators feature optional
arguments, which should be specified as keyword arguments for
compatibility with future extensions:

- `typed`, if is set to :const:`True`, will cause function arguments
  of different types to be cached separately.

- `getsizeof` specifies a function of one argument that will be
  applied to each cache value to determine its size.  The default
  value is :const:`None`, which will assign each item an equal size of
  :const:`1`.

- `lock` specifies a function of zero arguments that returns a
  `context manager`_ to lock the cache when necessary.  If not
  specified, :class:`threading.RLock` will be used to synchronize
  access from multiple threads.

The wrapped function is instrumented with :func:`cache_info` and
:func:`cache_clear` functions to provide information about cache
performance and clear the cache.  See the :func:`functools.lru_cache`
documentation for details.

Unlike :func:`functools.lru_cache`, setting `maxsize` to zero or
:const:`None` is not supported.

.. decorator:: rr_cache(maxsize=128, choice=random.choice, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Random Replacement (RR)
   algorithm.

.. decorator:: lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Least Frequently Used
   (LFU) algorithm.

.. decorator:: lru_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Least Recently Used (LRU)
   algorithm.

.. decorator:: ttl_cache(maxsize=128, ttl=600, timer=time.time, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to `maxsize` results based on a Least Recently Used (LRU)
   algorithm with a per-item time-to-live (TTL) value.


Method Decorators
------------------------------------------------------------------------

.. decorator:: cachedmethod(cache, typed=False)

   `cache` specifies a function of one argument that, when passed
   :const:`self`, will return a cache object for the respective
   instance or class.  If `cache(self)` returns :const:`None`, the
   original underlying method is called directly and the result is not
   cached.  The `cache` function is also available as the wrapped
   function's :attr:`cache` attribute.

   Multiple methods of an object or class may share the same cache
   object, but it is the user's responsibility to handle concurrent
   cache access in a multi-threaded environment.

   One advantage of this decorator over the similar function
   decorators is that cache properties such as `maxsize` can be set at
   runtime::

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


Exception Classes
------------------------------------------------------------------------

.. autoexception:: ExpiredError


.. _mutable: http://docs.python.org/dev/glossary.html#term-mutable
.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms
.. _context manager: http://docs.python.org/dev/glossary.html#term-context-manager
