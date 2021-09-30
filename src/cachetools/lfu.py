import warnings

from . import LFUCache

warnings.warn(
    "cachetools.lfu is deprecated, please use cachetools.LFUCache",
    DeprecationWarning,
    stacklevel=2,
)
