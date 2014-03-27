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
   LRUCache(OrderedDict([('first', 1), ('second', 2)]), maxsize=2)
   >>> cache['third'] = 3
   >>> cache
   LRUCache(OrderedDict([('second', 2), ('third', 3)]), maxsize=2)
   >>> cache['second']
   2
   >>> cache
   LRUCache(OrderedDict([('third', 3), ('second', 2)]), maxsize=2)
   >>> cache['fourth'] = 4
   >>> cache
   LRUCache(OrderedDict([('second', 2), ('fourth', 4)]), maxsize=2)

For the purpose of this module, a *cache* is a mutable mapping_ of
fixed size, defined by its :attr:`maxsize` attribute.  When the cache
is full, i.e. ``len(cache) == cache.maxsize``, the cache must choose
which item(s) to discard based on a suitable `cache algorithm`_.

This module provides various cache implementations based on different
cache algorithms, as well as decorators for easily memoizing function
calls, and utilities for creating custom cache implementations.


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

In addition to a `maxsize` parameter, all decorators feature two
optional arguments, which should be specified as keyword arguments for
compatibility with future extensions:

If `typed` is set to :const:`True`, function arguments of different
types will be cached separately.

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

.. decorator:: lru_cache(maxsize=128, typed=False, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to the `maxsize` most recent calls based on a Least Recently
   Used (LRU) algorithm.

.. decorator:: lfu_cache(maxsize=128, typed=False, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to the `maxsize` most recent calls based on a Least Frequently
   Used (LFU) algorithm.

.. decorator:: rr_cache(maxsize=128, typed=False, lock=threading.RLock)

   Decorator to wrap a function with a memoizing callable that saves
   up to the `maxsize` most recent calls based on a Random Replacement
   (RR) algorithm.


Class Decorators
------------------------------------------------------------------------

.. decorator:: cache

   Class decorator that wraps any mutable mapping to work as a cache.

   This class decorator may be useful when implementing new cache
   classes.  It converts any mutable mapping into a cache-like class
   with a :attr:`maxsize` attribute.  If :func:`__setitem__` is called
   when the cache is full, i.e. ``len(self) == self.maxsize``,
   :func:`popitem` is invoked to make room for new items::

     @cache
     class DictCache(dict):
         pass

     c = DictCache(maxsize=2)
     c['x'] = 1
     c['y'] = 2
     c['z'] = 3  # calls dict.popitem(c)

   The original underlying class or object is accessible through the
   :attr:`__wrapped__` attribute.  This is useful for subclasses that
   need to access the original mapping object directly, e.g. to
   implement their own version of :func:`popitem`.

   It is also possible, and arguably more comprehensible, to use the
   wrapper class as a base class::

     class OrderedDictCache(cache(collections.OrderedDict)):
         def popitem(self):
             return self.__wrapped__.popitem(last=False)  # pop first item

     c = OrderedDictCache(maxsize=2)
     c['x'] = 1
     c['y'] = 2
     c['z'] = 3  # removes 'x'


.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms
.. _context manager: http://docs.python.org/dev/glossary.html#term-context-manager
