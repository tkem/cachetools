:mod:`cachetools` --- Python 2.7 memoizing collections and decorators
=======================================================================

.. module:: cachetools

This module provides various memoizing collections and function
decorators, including a variant of the Python 3 Standard Library
lru_cache_ decorator.

.. note::

    This module is in early pre-alpha, and not fit for *any* purpose
    (yet).

.. code-block:: pycon

    >>> from cachetools import LRUCache
    >>> cache = LRUCache(maxsize=16)
    >>> cache['test'] = 1
    >>> cache.info()
    CacheInfo(hits=0, misses=0, maxsize=16, currsize=1)
    >>> cache['test']
    1
    >>> cache.info()
    CacheInfo(hits=1, misses=0, maxsize=16, currsize=1)


.. autoclass:: LRUCache
   :members:

.. autoclass:: LFUCache
   :members:


.. autofunction:: lru_cache

.. autofunction:: lfu_cache

.. _lru_cache: http://docs.python.org/3/library/functools.html#functools.lru_cache
