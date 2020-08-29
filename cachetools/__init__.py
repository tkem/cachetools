"""Extensible memoizing collections and decorators."""

from .cache import Cache
from .decorators import cached, cachedmethod
from .lfu import LFUCache
from .lru import LRUCache
from .rr import RRCache
from .ttl import FlexTTLCache, TTLCache, TTLCacheBase

__all__ = (
    'Cache',
    'FlexTTLCache',
    'LFUCache',
    'LRUCache',
    'RRCache',
    'TTLCache',
    'TTLCacheBase',
    'cached',
    'cachedmethod'
)

__version__ = '4.1.1'
