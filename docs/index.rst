:mod:`cachetools` --- Extensible memoizing collections and decorators
=======================================================================

.. module:: cachetools

This module provides various memoizing collections and decorators,
including a variant of the Python 3 Standard Library
:func:`functools.lru_cache` function decorator.

.. code-block:: pycon

   >>> from cachetools import LRUCache
   >>> cache = LRUCache(maxsize=2)
   >>> cache['first'] = 1
   >>> cache['second'] = 2
   >>> cache
   LRUCache(OrderedDict([('first', 1), ('second', 2)]), size=2, maxsize=2)
   >>> cache['third'] = 3
   >>> cache
   LRUCache(OrderedDict([('second', 2), ('third', 3)]), size=2, maxsize=2)
   >>> cache['second']
   2
   >>> cache
   LRUCache(OrderedDict([('third', 3), ('second', 2)]), size=2, maxsize=2)
   >>> cache['fourth'] = 4
   >>> cache
   LRUCache(OrderedDict([('second', 2), ('fourth', 4)]), size=2, maxsize=2)

For the purpose of this module, a *cache* is a mutable_ mapping_ with
additional attributes :attr:`size` and :attr:`maxsize`, which hold the
current and maximum size of the cache, and a (possibly static) method
:meth:`getsizeof`.

The current size of the cache is the sum of the results of
:meth:`getsizeof` applied to each of the cache's values,
i.e. ``cache.size == sum(map(cache.getsizeof, cache.values()), 0)``.
As a special case, if :meth:`getsizeof` returns :const:`1`
irrespective of its argument, ``cache.size == len(cache)``.

When the cache is full, i.e. ``cache.size > cache.maxsize``, the cache
must choose which item(s) to discard based on a suitable `cache
algorithm`_.

This module provides various cache implementations based on different
cache algorithms, as well as decorators for easily memoizing function
and method calls.


Cache Implementations
------------------------------------------------------------------------

.. autoclass:: LRUCache
   :members:

.. autoclass:: LFUCache
   :members:

.. autoclass:: RRCache
   :members:


Function Decorators
------------------------------------------------------------------------

This module provides several memoizing function decorators compatible
with --- though not necessarily as efficient as --- the Python 3
Standard Library :func:`functools.lru_cache` decorator.

In addition to a `maxsize` parameter, all decorators feature optional
arguments, which should be specified as keyword arguments for
compatibility with future extensions:

If `typed` is set to :const:`True`, function arguments of different
types will be cached separately.

`getsizeof` specifies a function of one argument that will be applied
to each cache value to determine its size.  The default value is
:const:`None`, which will assign each element an equal size of
:const:`1`.

`lock` specifies a function of zero arguments that returns a `context
manager`_ to lock the cache when necessary.  If not specified,
:class:`threading.RLock` will be used for synchronizing access from
multiple threads.

The wrapped function is instrumented with :func:`cache_info` and
:func:`cache_clear` functions to provide information about cache
performance and clear the cache.  See the :func:`functools.lru_cache`
documentation for details.

Unlike :func:`functools.lru_cache`, setting `maxsize` to zero or
:const:`None` is not supported.

.. decorator:: lru_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to the `maxsize` most recent calls based on a Least Recently
   Used (LRU) algorithm.

.. decorator:: lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to the `maxsize` most recent calls based on a Least Frequently
   Used (LFU) algorithm.

.. decorator:: rr_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to the `maxsize` most recent calls based on a Random Replacement
   (RR) algorithm.


Method Decorators
------------------------------------------------------------------------

.. decorator:: cachedmethod(getcache, typed=False)

   Decorator to wrap a class or instance method with a memoizing callable.


.. _mutable: http://docs.python.org/dev/glossary.html#term-mutable
.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms
.. _context manager: http://docs.python.org/dev/glossary.html#term-context-manager
