cachetools
========================================================================

This module provides various memoizing collections and decorators,
including a variant of the Python 3 Standard Library
`functools.lru_cache` function decorator.

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
fixed maximum *size*.  When the cache is full, i.e. the current size
of the cache exceeds its maximum size, the cache must choose which
item(s) to discard based on a suitable `cache algorithm`_.

In general, a cache's size is the sum of the size of its items.  If
the size of each items is :const:`1`, a cache's size is equal to the
number of its items, i.e. :func:`len`.  An items's size may also be a
property or function of its value, e.g. the result of
:func:`sys.getsizeof`, or :func:`len` for string and sequence values.

This module provides various cache implementations based on different
cache algorithms, as well as decorators for easily memoizing function
and method calls.


Installation
------------------------------------------------------------------------

Install cachetools using pip::

    pip install cachetools


Project Resources
------------------------------------------------------------------------

.. image:: http://img.shields.io/pypi/v/cachetools.svg
    :target: https://pypi.python.org/pypi/cachetools/
    :alt: Latest PyPI version

.. image:: http://img.shields.io/pypi/dm/cachetools.svg
    :target: https://pypi.python.org/pypi/cachetools/
    :alt: Number of PyPI downloads

- `Documentation`_
- `Issue Tracker`_
- `Source Code`_
- `Change Log`_


License
------------------------------------------------------------------------

Copyright (c) 2014 Thomas Kemmer.

Licensed under the `MIT License`_.


.. _functools.lru_cache: http://docs.python.org/3.4/library/functools.html#functools.lru_cache
.. _mutable: http://docs.python.org/dev/glossary.html#term-mutable
.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms

.. _Documentation: http://pythonhosted.org/cachetools/
.. _Source Code: https://github.com/tkem/cachetools/
.. _Issue Tracker: https://github.com/tkem/cachetools/issues/
.. _Change Log: http://raw.github.com/tkem/cachetools/master/Changes
.. _MIT License: http://raw.github.com/tkem/cachetools/master/LICENSE
