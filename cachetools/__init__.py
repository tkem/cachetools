"""Extensible memoizing collections and decorators"""

from .cache import Cache
from .decorators import cachedmethod, cachedfunc
from .lfu import LFUCache, lfu_cache
from .lru import LRUCache, lru_cache
from .rr import RRCache, rr_cache
from .ttl import TTLCache, ttl_cache

__all__ = (
    'Cache',
    'cachedmethod', 'cachedfunc',
    'LFUCache', 'LRUCache', 'RRCache', 'TTLCache',
    'lfu_cache', 'lru_cache', 'rr_cache', 'ttl_cache',
)

__version__ = '1.0.0'
