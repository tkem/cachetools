"""Extensible memoizing collections and decorators"""

from .cache import Cache
from .decorators import cache, cachedmethod, cachekey
from .func import lfu_cache, lru_cache, rr_cache, ttl_cache
from .lfu import LFUCache
from .lru import LRUCache
from .rr import RRCache
from .ttl import TTLCache

__all__ = (
    'Cache', 'LFUCache', 'LRUCache', 'RRCache', 'TTLCache',
    'cache', 'cachedmethod', 'cachekey',
    # make cachetools.func.* available for backwards compatibility
    'lfu_cache', 'lru_cache', 'rr_cache', 'ttl_cache',
)

__version__ = '1.0.3'
