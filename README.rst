cachetools
========================================================================

This module provides various memoizing collections and function
decorators, including a variant of the Python 3 Standard Library
`functools.lru_cache`_ decorator.

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
fixed size, defined by its ``maxsize`` attribute.  When the cache is
full, i.e. ``len(cache) == cache.maxsize``, the cache must choose
which item(s) to discard based on a suitable `cache algorithm`_.

This module provides various cache implementations based on different
cache algorithms, as well as decorators for easily memoizing function
calls.


Installation
------------------------------------------------------------------------

Install cachetools using pip::

    pip install cachetools


Project Resources
------------------------------------------------------------------------

- `Documentation`_
- `Issue Tracker`_
- `Source Code`_
- `Change Log`_

.. image:: https://pypip.in/v/cachetools/badge.png
    :target: https://pypi.python.org/pypi/cachetools/
    :alt: Latest PyPI version

.. image:: https://pypip.in/d/cachetools/badge.png
    :target: https://pypi.python.org/pypi/cachetools/
    :alt: Number of PyPI downloads


License
------------------------------------------------------------------------

Copyright 2014 Thomas Kemmer.

Licensed under the `MIT License`_.


.. _functools.lru_cache: http://docs.python.org/3.4/library/functools.html#functools.lru_cache
.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms

.. _Documentation: http://pythonhosted.org/cachetools/
.. _Source Code: https://github.com/tkem/cachetools/
.. _Issue Tracker: https://github.com/tkem/cachetools/issues/
.. _Change Log: http://raw.github.com/tkem/cachetools/master/Changes
.. _MIT License: http://raw.github.com/tkem/cachetools/master/MIT-LICENSE
