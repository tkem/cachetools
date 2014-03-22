cachetools
========================================================================

This module provides various memoizing collections and function
decorators, including a variant of the Python 3 Standard Library
lru_cache_ decorator.

    Important Note: This module is in early pre-alpha, and not fit for
    *any* purpose (yet).

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

cachetools is Copyright 2014 Thomas Kemmer.

Licensed under the `MIT License`_.


.. _lru_cache: http://docs.python.org/3.4/library/functools.html#functools.lru_cache

.. _Documentation: http://pythonhosted.org/cachetools/
.. _Source Code: https://github.com/tkem/cachetools/
.. _Issue Tracker: https://github.com/tkem/cachetools/issues/
.. _Change Log: https://raw.github.com/tkem/cachetools/master/Changes
.. _MIT License: http://opensource.org/licenses/MIT
