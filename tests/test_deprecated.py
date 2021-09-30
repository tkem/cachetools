import unittest
import warnings


class DeprecatedTest(unittest.TestCase):
    def test_cache(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from cachetools.cache import Cache

            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "cachetools.cache" in str(w[-1].message)

    def test_fifo(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from cachetools.fifo import FIFOCache

            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "cachetools.fifo" in str(w[-1].message)

    def test_lfu(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from cachetools.lfu import LFUCache

            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "cachetools.lfu" in str(w[-1].message)

    def test_lru(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from cachetools.lru import LRUCache

            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "cachetools.lru" in str(w[-1].message)

    def test_mru(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from cachetools.mru import MRUCache

            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "cachetools.mru" in str(w[-1].message)

    def test_rr(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from cachetools.rr import RRCache

            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "cachetools.rr" in str(w[-1].message)

    def test_ttl(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from cachetools.ttl import TTLCache

            assert len(w) == 1
            assert issubclass(w[-1].category, DeprecationWarning)
            assert "cachetools.ttl" in str(w[-1].message)
