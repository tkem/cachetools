:mod:`cachetools` --- Extensible memoizing collections and decorators
=======================================================================

.. module:: cachetools

This module provides various memoizing collections and decorators,
including a variant of the Python 3 Standard Library `@lru_cache`_
function decorator.

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
   >>> cache
   LRUCache([('second', 2), ('fourth', 4)], maxsize=2, currsize=2)

For the purpose of this module, a *cache* is a mutable_ mapping_ of a
fixed maximum size.  When the cache is full, i.e. by adding another
item the cache would exceed its maximum size, the cache must choose
which item(s) to discard based on a suitable `cache algorithm`_.  In
general, a cache's size is the total size of its items, and an item's
size is a property or function of its value, e.g. the result of
``sys.getsizeof(value)``.  For the trivial but common case that each
item counts as :const:`1`, irrespective of its value, a cache's size
is equal to the number of its items, or ``len(cache)``.

This module provides multiple cache implementations based on different
cache algorithms, as well as decorators for easily memoizing function
and method calls.


Cache Implementations
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


Function Decorators
------------------------------------------------------------------------

This module provides several memoizing function decorators similar to
the Python 3 Standard Library :func:`functools.lru_cache` decorator::

    import cachetools
    import urllib.request

    @cachetools.lru_cache(maxsize=4)
    def get_pep(num):
        """Retrieve text of a Python Enhancement Proposal"""
        url = 'http://www.python.org/dev/peps/pep-%04d/' % num
        with urllib.request.urlopen(url) as s:
            return s.read()

    for n in 8, 290, 308, 320, 8, 218, 320, 279, 289, 320, 9991:
        try:
            print(n, len(get_pep(n)))
        except urllib.error.HTTPError:
            print(n, 'Not Found')
    print(get_pep.cache_info())

In addition to a `maxsize` parameter, all decorators provide the
following optional keyword arguments:

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

Like with :func:`functools.lru_cache`, the positional and keyword
arguments to the underlying function must be hashable.  Note that
unlike :func:`functools.lru_cache`, setting `maxsize` to :const:`None`
is not supported.

.. decorator:: lfu_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Least Frequently Used
   (LFU) algorithm.

.. decorator:: lru_cache(maxsize=128, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Least Recently Used (LRU)
   algorithm.

.. decorator:: rr_cache(maxsize=128, choice=random.choice, typed=False, getsizeof=None, lock=threading.RLock)

   Decorator that wraps a function with a memoizing callable that
   saves up to `maxsize` results based on a Random Replacement (RR)
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
   function's :attr:`cache` attribute.  Multiple methods of an object
   or class may share the same cache object, but it is the user's
   responsibility to handle concurrent cache access in a
   multi-threaded environment.

   Note that the objects returned from `cache` are not required to be
   instances of the cache implementations provided by this module.
   :func:`cachedmethod` should work with any mutable mapping type, be
   it plain :class:`dict` or :class:`weakref.WeakValueDictionary`.

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


.. _@lru_cache: http://docs.python.org/3/library/functools.html#functools.lru_cache
.. _mutable: http://docs.python.org/dev/glossary.html#term-mutable
.. _mapping: http://docs.python.org/dev/glossary.html#term-mapping
.. _cache algorithm: http://en.wikipedia.org/wiki/Cache_algorithms
.. _context manager: http://docs.python.org/dev/glossary.html#term-context-manager
