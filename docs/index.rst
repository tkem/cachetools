:mod:`cachetools` --- Extensible memoizing collections and decorators
=======================================================================

.. module:: cachetools

This module provides various memoizing collections and function
decorators, including a variant of the Python 3 Standard Library
:func:`functools.lru_cache` decorator.

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
calls.


Cache Classes
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

All decorators feature two optional arguments, which should be
specified as keyword arguments for compatibility with future
extensions:

If `typed` is set to :const:`True`, function arguments of different
types will be cached separately.

`lock` specifies a function of zero arguments that returns a `context
manager`_ to lock the cache when necessary.  If not specified, a
:class:`threading.RLock` will be used for synchronizing access from
multiple threads.

.. autofunction:: lru_cache

.. autofunction:: lfu_cache

.. autofunction:: rr_cache


.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms
.. _context manager: http://docs.python.org/dev/glossary.html#term-context-manager
