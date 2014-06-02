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
   LRUCache(maxsize=2, currsize=2, items=[('first', 1)])
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

For the purpose of this module, a *cache* is a mutable_ mapping_ of a
fixed maximum *size*.  When the cache is full, i.e. the current size
of the cache exceeds its maximum size, the cache must choose which
item(s) to discard based on a suitable `cache algorithm`_.

In general, a cache's size is the sum of its element's sizes.  For the
trivial case, if the size of each element is :const:`1`, a cache's
size is equal to the number of its entries, i.e. :func:`len`.  An
element's size may also be a property or function of its value,
e.g. the result of :func:`sys.getsizeof`, or :func:`len` for string
and sequence elements.

This module provides various cache implementations based on different
cache algorithms, as well as decorators for easily memoizing function
and method calls.


Cache Base Class
------------------------------------------------------------------------

.. autoclass:: Cache
   :members:


Cache Implementations
------------------------------------------------------------------------

.. autoclass:: LRUCache
   :members:

.. autoclass:: LFUCache
   :members:

.. autoclass:: RRCache
   :members:

.. autoclass:: TTLCache
   :members:

   Note that a cache element may expire at *any* time, so the
   following *may* raise an exception::

     cache = TTLCache(100, 1)
     ...
     for k in cache:
       print(cache[k])



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
   up to `maxsize` results based on a Least Recently Used (LRU)
   algorithm.

.. decorator:: lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to `maxsize` results based on a Least Frequently Used (LFU)
   algorithm.

.. decorator:: rr_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to `maxsize` results based on a Random Replacement (RR)
   algorithm.


Method Decorators
------------------------------------------------------------------------

.. decorator:: cachedmethod(getcache, typed=False, lock=threading.RLock)

   Decorator to wrap a class or instance method with a memoizing
   callable that saves results in a (possibly shared) cache.

   `getcache` specifies a function of one argument that, when passed
   :const:`self`, will return the cache object for the instance or
   class.  See the `Function Decorators`_ section for details on the
   other arguments.

   Python 3 example of a shared (class) LRU cache for static web
   content::

     class CachedPEPs(object):

        cache = LRUCache(maxsize=32)

        @cachedmethod(operator.attrgetter('cache'))
        def get_pep(self, num):
            """Retrieve text of a Python Enhancement Proposal"""
            resource = 'http://www.python.org/dev/peps/pep-%04d/' % num
            try:
                with urllib.request.urlopen(resource) as s:
                    return s.read()
            except urllib.error.HTTPError:
                return 'Not Found'


.. _mutable: http://docs.python.org/dev/glossary.html#term-mutable
.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms
.. _context manager: http://docs.python.org/dev/glossary.html#term-context-manager
