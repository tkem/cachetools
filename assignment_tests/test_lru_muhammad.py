import pytest

from cachetools import LRUCache


def filled(maxsize, keys, **kwargs):
    """Return an LRUCache(maxsize) with each key set to 1, in order."""
    cache = LRUCache(maxsize, **kwargs)
    for key in keys:
        cache[key] = 1
    return cache


# --------------------------------------------------------------------------
# __setitem__
# --------------------------------------------------------------------------
class TestSetItem:
    @pytest.mark.boundary
    def test_maxsize_zero_rejects_item(self):
        cache = LRUCache(0)
        with pytest.raises(ValueError, match="value too large"):
            cache["a"] = 1
        assert len(cache) == 0

    @pytest.mark.boundary
    def test_value_size_equals_maxsize_is_stored(self):
        cache = filled(1, ["a"])
        assert list(cache) == ["a"]
        assert cache.currsize == 1

    @pytest.mark.smoke
    def test_item_over_capacity_evicts_least_recently_used(self):
        cache = filled(2, ["a", "b", "c"])
        assert list(cache) == ["b", "c"]
        assert cache.currsize == 2

    def test_overwrite_refreshes_recency(self):
        cache = filled(2, ["a", "b"])
        cache["a"] = 1
        cache["c"] = 1
        assert list(cache) == ["a", "c"]

    @pytest.mark.boundary
    def test_overwrite_with_larger_value_can_evict_the_key_itself(self):
        cache = LRUCache(3, getsizeof=len)
        cache["a"] = "x"
        cache["b"] = "yy"
        cache["a"] = "zz"
        assert list(cache) == ["a"]
        assert cache.currsize == 2

    @pytest.mark.boundary
    @pytest.mark.parametrize(
        "value, should_store",
        [("xxx", True), ("xxxx", False)],
        ids=["size_equals_maxsize", "size_above_maxsize"],
    )
    def test_value_size_against_maxsize(self, value, should_store):
        cache = LRUCache(3, getsizeof=len)
        if should_store:
            cache["a"] = value
            assert cache.currsize == 3
        else:
            with pytest.raises(ValueError, match="value too large"):
                cache["a"] = value

    def test_failed_insert_leaves_cache_unchanged(self):
        cache = LRUCache(3, getsizeof=len)
        cache["a"] = "xxx"
        with pytest.raises(ValueError):
            cache["b"] = "xxxx"
        assert list(cache) == ["a"]
        assert cache.currsize == 3

    def test_none_is_a_valid_key(self):
        cache = LRUCache(2)
        cache[None] = 1
        assert list(cache) == [None]

    def test_unhashable_key_raises_type_error(self):
        cache = LRUCache(2)
        with pytest.raises(TypeError):
            cache[[1, 2]] = 1
        assert len(cache) == 0

    @pytest.mark.boundary
    @pytest.mark.parametrize(
        "size, valid",
        [(-1, False), (0, True)],
        ids=["negative_size", "zero_size"],
    )
    def test_value_size_zero_and_below(self, size, valid):
        cache = LRUCache(2, getsizeof=lambda v: v)
        if valid:
            cache["a"] = size
            assert cache.currsize == 0
            assert list(cache) == ["a"]
        else:
            with pytest.raises(ValueError, match="non-negative"):
                cache["a"] = size
            assert len(cache) == 0


# --------------------------------------------------------------------------
# __getitem__
# --------------------------------------------------------------------------
class TestGetItem:
    @pytest.mark.smoke
    def test_read_refreshes_recency(self):
        cache = filled(2, ["a", "b"])
        cache["a"]
        cache["c"] = 1
        assert list(cache) == ["a", "c"]

    def test_missing_key_raises_key_error_and_changes_nothing(self):
        cache = filled(2, ["a"])
        with pytest.raises(KeyError):
            cache["zzz"]
        assert list(cache) == ["a"]
        assert cache.currsize == 1

    def test_get_on_existing_key_refreshes_recency(self):
        cache = filled(2, ["a", "b"])
        assert cache.get("a") == 1
        cache["c"] = 1
        assert list(cache) == ["a", "c"]

    def test_membership_check_does_not_refresh_recency(self):
        cache = filled(2, ["a", "b"])
        assert "a" in cache
        cache["c"] = 1
        assert list(cache) == ["b", "c"]

    def test_get_missing_key_returns_default(self):
        cache = filled(2, ["a"])
        assert cache.get("zzz", "fallback") == "fallback"


# --------------------------------------------------------------------------
# __delitem__
# --------------------------------------------------------------------------
class TestDelItem:
    @pytest.mark.smoke
    def test_delete_existing_key(self):
        cache = filled(2, ["a", "b"])
        del cache["a"]
        assert list(cache) == ["b"]
        assert cache.currsize == 1

    def test_delete_missing_key_raises_and_changes_nothing(self):
        cache = filled(2, ["b"])
        with pytest.raises(KeyError):
            del cache["zzz"]
        assert list(cache) == ["b"]
        assert cache.currsize == 1

    def test_reinserted_key_counts_as_most_recent(self):
        cache = filled(2, ["a", "b"])
        del cache["a"]
        cache["a"] = 1
        cache["c"] = 1
        assert list(cache) == ["a", "c"]

    def test_deleted_key_is_no_longer_present(self):
        cache = filled(2, ["a"])
        del cache["a"]
        assert "a" not in cache
        assert len(cache) == 0

    def test_delete_frees_capacity_so_nothing_is_evicted(self):
        cache = filled(2, ["a", "b"])
        del cache["a"]
        cache["c"] = 1
        assert sorted(cache) == ["b", "c"]


# --------------------------------------------------------------------------
# popitem
# --------------------------------------------------------------------------
class TestPopItem:
    @pytest.mark.smoke
    def test_pops_least_recently_used(self):
        cache = LRUCache(3)
        cache["a"], cache["b"], cache["c"] = 1, 2, 3
        assert cache.popitem() == ("a", 1)
        assert list(cache) == ["b", "c"]
        assert cache.currsize == 2

    def test_read_changes_which_item_is_popped(self):
        cache = LRUCache(3)
        cache["a"], cache["b"], cache["c"] = 1, 2, 3
        cache["a"]
        assert cache.popitem() == ("b", 2)

    def test_overwrite_changes_which_item_is_popped(self):
        cache = LRUCache(3)
        cache["a"], cache["b"] = 1, 2
        cache["a"] = 9
        assert cache.popitem() == ("b", 2)

    @pytest.mark.boundary
    def test_empty_cache_raises_key_error(self):
        with pytest.raises(KeyError, match="LRUCache is empty"):
            LRUCache(2).popitem()

    @pytest.mark.boundary
    def test_popping_last_item_then_empty(self):
        cache = filled(1, ["a"])
        assert cache.popitem() == ("a", 1)
        with pytest.raises(KeyError, match="LRUCache is empty"):
            cache.popitem()


# --------------------------------------------------------------------------
# clear
# --------------------------------------------------------------------------
class TestClear:
    @pytest.mark.smoke
    def test_clear_full_cache(self):
        cache = filled(2, ["a", "b"])
        cache.clear()
        assert list(cache) == []
        assert cache.currsize == 0
        assert len(cache) == 0

    def test_popitem_after_clear_raises(self):
        cache = filled(2, ["a", "b"])
        cache.clear()
        with pytest.raises(KeyError, match="LRUCache is empty"):
            cache.popitem()

    def test_cache_is_reusable_after_clear(self):
        cache = filled(2, ["a", "b"])
        cache.clear()
        for key in ("x", "y", "z"):
            cache[key] = 1
        assert list(cache) == ["y", "z"]

    @pytest.mark.boundary
    def test_clear_on_empty_cache(self):
        cache = LRUCache(2)
        cache.clear()
        assert list(cache) == []
        assert cache.currsize == 0


# --------------------------------------------------------------------------
# __init__ / maxsize
# --------------------------------------------------------------------------
class TestInit:
    @pytest.mark.smoke
    def test_maxsize_property(self):
        assert LRUCache(2).maxsize == 2

    @pytest.mark.boundary
    def test_negative_maxsize_is_rejected(self):
        with pytest.raises(ValueError, match="maxsize must be non-negative"):
            LRUCache(-1)["a"] = 1

    def test_new_cache_is_empty(self):
        cache = LRUCache(3)
        assert len(cache) == 0
        assert cache.currsize == 0

    @pytest.mark.boundary
    def test_default_value_size_is_one(self):
        cache = filled(3, ["a", "b"])
        assert cache.currsize == 2