"""Extensible memoizing collections and decorators"""

# flake8: noqa

from .cache import Cache
from .rrcache import RRCache
from .lfucache import LFUCache
from .lrucache import LRUCache
from .ttlcache import TTLCache
from .decorators import rr_cache, lfu_cache, lru_cache, cachedmethod

__version__ = '0.5.0'
