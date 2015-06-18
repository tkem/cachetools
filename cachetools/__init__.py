"""Extensible memoizing collections and decorators"""

from .cache import Cache
from .func import lfu_cache, lru_cache, rr_cache, ttl_cache
from .lfu import LFUCache
from .lru import LRUCache
from .method import cachedmethod
from .rr import RRCache
from .ttl import TTLCache

__all__ = (
    'Cache',
    'cachedmethod',
    'LFUCache', 'LRUCache', 'RRCache', 'TTLCache',
    'lfu_cache', 'lru_cache', 'rr_cache', 'ttl_cache',
)

__version__ = '1.0.2'
