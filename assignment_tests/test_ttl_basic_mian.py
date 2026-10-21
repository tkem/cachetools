"""Unit tests for the basic parts of cachetools.TTLCache (Mian Dawood).

Covers: __init__, __setitem__, __getitem__, __delitem__, popitem, clear,
__len__ and currsize. The expiry-specific methods (ttl, timer, __contains__,
__iter__, expire) are covered in test_ttl_expiry_muhammad.py.
Each test maps to a row in notes/ecp_bva_mian.md.

Rule under test: an item is valid while  now < time_set + ttl.
A fake clock is used instead of sleep(), so the tests are instant and exact.
"""
import pytest

from cachetools import TTLCache


class Clock:
    """Fake timer: a callable whose value is set by hand."""

    def __init__(self, now=0):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


def filled(clock, maxsize, keys, ttl=10, **kwargs):
    """Return a TTLCache with each key set to 1 at the clock's current time."""
    cache = TTLCache(maxsize, ttl=ttl, timer=clock, **kwargs)
    for key in keys:
        cache[key] = 1
    return cache


# --------------------------------------------------------------------------
# __init__
# --------------------------------------------------------------------------
class TestInit:
    @pytest.mark.smoke
    def test_new_cache_is_empty(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        assert len(cache) == 0
        assert cache.currsize == 0
        assert cache.maxsize == 3

    @pytest.mark.boundary
    def test_negative_maxsize_is_rejected(self, clock):
        with pytest.raises(ValueError, match="maxsize must be non-negative"):
            TTLCache(-1, ttl=10, timer=clock)["a"] = 1


# --------------------------------------------------------------------------
# __setitem__
# --------------------------------------------------------------------------
class TestSetItem:
    @pytest.mark.smoke
    def test_store_and_read_back(self, clock):
        cache = TTLCache(2, ttl=10, timer=clock)
        cache["a"] = 1
        cache["b"] = 2
        assert cache["a"] == 1
        assert cache["b"] == 2
        assert len(cache) == 2
        assert cache.currsize == 2

    @pytest.mark.boundary
    def test_over_capacity_evicts_least_recently_used(self, clock):
        cache = filled(clock, 2, ["a", "b", "c"])
        assert list(cache) == ["b", "c"]

    @pytest.mark.boundary
    def test_maxsize_zero_rejects_item(self, clock):
        cache = TTLCache(0, ttl=10, timer=clock)
        with pytest.raises(ValueError, match="value too large"):
            cache["a"] = 1

    def test_overwrite_resets_the_expiry(self, clock):
        cache = TTLCache(2, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 8
        cache["a"] = 2
        clock.now = 12
        assert cache["a"] == 2

    def test_unhashable_key_raises_type_error(self, clock):
        cache = TTLCache(2, ttl=10, timer=clock)
        with pytest.raises(TypeError):
            cache[[1, 2]] = 1
        assert len(cache) == 0


# --------------------------------------------------------------------------
# __getitem__
# --------------------------------------------------------------------------
class TestGetItem:
    @pytest.mark.boundary
    def test_read_just_before_expiry(self, clock):
        cache = filled(clock, 2, ["a"])
        clock.now = 9.99
        assert cache["a"] == 1

    @pytest.mark.boundary
    def test_read_exactly_at_expiry_raises(self, clock):
        cache = filled(clock, 2, ["a"])
        clock.now = 10
        with pytest.raises(KeyError):
            cache["a"]

    def test_missing_key_raises_key_error(self, clock):
        cache = filled(clock, 2, ["a"])
        with pytest.raises(KeyError):
            cache["zzz"]

    def test_read_refreshes_recency(self, clock):
        cache = filled(clock, 2, ["a", "b"])
        cache["a"]
        cache["c"] = 1
        assert list(cache) == ["a", "c"]

    def test_read_long_after_expiry_raises(self, clock):
        cache = filled(clock, 2, ["a"])
        clock.now = 50
        with pytest.raises(KeyError):
            cache["a"]


# --------------------------------------------------------------------------
# __delitem__
# --------------------------------------------------------------------------
class TestDelItem:
    @pytest.mark.smoke
    def test_delete_existing_key(self, clock):
        cache = filled(clock, 3, ["a", "b"])
        del cache["a"]
        assert list(cache) == ["b"]
        assert len(cache) == 1

    def test_delete_missing_key_raises(self, clock):
        cache = filled(clock, 3, ["a"])
        with pytest.raises(KeyError):
            del cache["zzz"]
        assert list(cache) == ["a"]

    @pytest.mark.boundary
    def test_delete_expired_key_raises_and_key_is_gone(self, clock):
        cache = filled(clock, 3, ["a"])
        clock.now = 10
        with pytest.raises(KeyError):
            del cache["a"]
        assert len(cache) == 0

    def test_delete_frees_capacity_so_nothing_is_evicted(self, clock):
        cache = filled(clock, 2, ["a", "b"])
        del cache["a"]
        cache["c"] = 1
        assert sorted(cache) == ["b", "c"]


# --------------------------------------------------------------------------
# popitem
# --------------------------------------------------------------------------
class TestPopItem:
    @pytest.mark.smoke
    def test_pops_least_recently_used(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 5
        cache["b"] = 2
        assert cache.popitem() == ("a", 1)
        assert list(cache) == ["b"]

    @pytest.mark.boundary
    def test_expired_item_is_skipped(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 5
        cache["b"] = 2
        clock.now = 11
        assert cache.popitem() == ("b", 2)

    @pytest.mark.boundary
    def test_everything_expired_raises(self, clock):
        cache = filled(clock, 3, ["a"])
        clock.now = 11
        with pytest.raises(KeyError, match="TTLCache is empty"):
            cache.popitem()

    @pytest.mark.boundary
    def test_empty_cache_raises(self, clock):
        with pytest.raises(KeyError, match="TTLCache is empty"):
            TTLCache(2, ttl=10, timer=clock).popitem()

    def test_read_changes_which_item_is_popped(self, clock):
        cache = filled(clock, 2, ["a", "b"])
        cache["a"]
        assert cache.popitem() == ("b", 1)


# --------------------------------------------------------------------------
# clear
# --------------------------------------------------------------------------
class TestClear:
    @pytest.mark.smoke
    def test_clear_full_cache(self, clock):
        cache = filled(clock, 3, ["a", "b"])
        cache.clear()
        assert list(cache) == []
        assert cache.currsize == 0
        assert len(cache) == 0

    def test_popitem_after_clear_raises(self, clock):
        cache = filled(clock, 3, ["a", "b"])
        cache.clear()
        with pytest.raises(KeyError, match="TTLCache is empty"):
            cache.popitem()

    def test_cache_is_reusable_after_clear(self, clock):
        cache = filled(clock, 2, ["a", "b"])
        cache.clear()
        for key in ("x", "y", "z"):
            cache[key] = 1
        assert list(cache) == ["y", "z"]

    @pytest.mark.boundary
    def test_clear_on_empty_cache(self, clock):
        cache = TTLCache(2, ttl=10, timer=clock)
        cache.clear()
        assert list(cache) == []
        assert cache.currsize == 0


# --------------------------------------------------------------------------
# __len__ / currsize
# --------------------------------------------------------------------------
class TestLenAndCurrsize:
    @pytest.mark.boundary
    def test_empty_cache(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        assert len(cache) == 0
        assert cache.currsize == 0

    @pytest.mark.smoke
    def test_two_items_of_size_one(self, clock):
        cache = filled(clock, 3, ["a", "b"])
        assert len(cache) == 2
        assert cache.currsize == 2

    @pytest.mark.boundary
    def test_all_items_expired(self, clock):
        cache = filled(clock, 3, ["a", "b"])
        clock.now = 10
        assert len(cache) == 0
        assert cache.currsize == 0

    def test_partial_expiry(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 5
        cache["b"] = 1
        clock.now = 10
        assert len(cache) == 1
        assert cache.currsize == 1

    def test_currsize_sums_value_sizes(self, clock):
        cache = TTLCache(10, ttl=10, timer=clock, getsizeof=len)
        cache["a"] = "xx"
        cache["b"] = "yyy"
        assert len(cache) == 2
        assert cache.currsize == 5
