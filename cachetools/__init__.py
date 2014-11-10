"""Extensible memoizing collections and decorators"""

from .cache import Cache
from .rrcache import RRCache, rr_cache
from .lfucache import LFUCache, lfu_cache
from .lrucache import LRUCache, lru_cache
from .ttlcache import TTLCache, ttl_cache
from .decorators import cachedmethod
from .errors import ExpiredError

__all__ = (
    'Cache',
    'RRCache', 'LFUCache', 'LRUCache', 'TTLCache',
    'rr_cache', 'lfu_cache', 'lru_cache', 'ttl_cache',
    'cachedmethod',
    'ExpiredError'
)

__version__ = '0.7.0'
