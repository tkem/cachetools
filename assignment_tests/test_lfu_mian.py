import pytest

from cachetools import LFUCache


def filled(maxsize, keys, **kwargs):
    """Return an LFUCache(maxsize) with each key set to 1, in order."""
    cache = LFUCache(maxsize, **kwargs)
    for key in keys:
        cache[key] = 1
    return cache


# --------------------------------------------------------------------------
# __setitem__
# --------------------------------------------------------------------------
class TestSetItem:
    @pytest.mark.boundary
    def test_maxsize_zero_rejects_item(self):
        cache = LFUCache(0)
        with pytest.raises(ValueError, match="value too large"):
            cache["a"] = 1
        assert len(cache) == 0

    @pytest.mark.boundary
    def test_exactly_at_capacity_no_eviction(self):
        cache = filled(2, ["a", "b"])
        assert sorted(cache) == ["a", "b"]
        assert cache.currsize == 2

    @pytest.mark.boundary
    def test_maxsize_one_keeps_latest_key(self):
        cache = filled(1, ["a", "b"])
        assert list(cache) == ["b"]

    @pytest.mark.smoke
    def test_lowest_count_is_evicted(self):
        cache = filled(2, ["a", "b"])
        cache["a"]
        cache["c"] = 1
        assert sorted(cache) == ["a", "c"]

    def test_overwrite_counts_as_a_use(self):
        cache = filled(2, ["a", "b"])
        cache["a"] = 5
        cache["c"] = 1
        assert sorted(cache) == ["a", "c"]
        assert cache["a"] == 5

    def test_high_count_key_survives(self):
        cache = filled(2, ["a"])
        cache["a"]
        cache["a"]
        cache["b"] = 1
        cache["c"] = 1
        assert sorted(cache) == ["a", "c"]

    @pytest.mark.boundary
    @pytest.mark.parametrize(
        "value, should_store",
        [("xxx", True), ("xxxx", False)],
        ids=["size_equals_maxsize", "size_above_maxsize"],
    )
    def test_value_size_against_maxsize(self, value, should_store):
        cache = LFUCache(3, getsizeof=len)
        if should_store:
            cache["a"] = value
            assert cache.currsize == 3
        else:
            with pytest.raises(ValueError, match="value too large"):
                cache["a"] = value
            assert len(cache) == 0

    def test_none_is_a_valid_key(self):
        cache = LFUCache(2)
        cache[None] = 1
        assert list(cache) == [None]

    def test_unhashable_key_raises_type_error(self):
        cache = LFUCache(2)
        with pytest.raises(TypeError):
            cache[[1, 2]] = 1
        assert len(cache) == 0


# --------------------------------------------------------------------------
# __getitem__
# --------------------------------------------------------------------------
class TestGetItem:
    @pytest.mark.smoke
    def test_read_raises_the_use_count(self):
        cache = filled(2, ["a", "b"])
        cache["a"]
        cache["c"] = 1
        assert sorted(cache) == ["a", "c"]

    def test_missing_key_raises_key_error_and_changes_nothing(self):
        cache = filled(2, ["a"])
        with pytest.raises(KeyError):
            cache["zzz"]
        assert list(cache) == ["a"]
        assert cache.currsize == 1

    def test_get_counts_as_a_use(self):
        cache = filled(2, ["a", "b"])
        assert cache.get("a") == 1
        cache["c"] = 1
        assert sorted(cache) == ["a", "c"]

    def test_get_missing_key_returns_default(self):
        cache = filled(2, ["a"])
        assert cache.get("zzz", "fallback") == "fallback"

    def test_membership_check_does_not_count_as_a_use(self):
        cache = filled(2, ["a", "b"])
        cache["a"]
        cache["a"]          # a: count 3
        cache["b"]          # b: count 2
        for _ in range(3):
            assert "b" in cache   # if this counted, b would pass a
        cache["c"] = 1
        assert sorted(cache) == ["a", "c"]


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
        cache = filled(2, ["a"])
        with pytest.raises(KeyError):
            del cache["zzz"]
        assert list(cache) == ["a"]
        assert cache.currsize == 1

    def test_delete_frees_capacity_so_nothing_is_evicted(self):
        cache = filled(2, ["a", "b"])
        del cache["a"]
        cache["c"] = 1
        assert sorted(cache) == ["b", "c"]

    def test_deleted_key_starts_again_at_count_one(self):
        cache = filled(2, ["a"])
        for _ in range(3):
            cache["a"]
        del cache["a"]
        cache["a"] = 1
        cache["b"] = 1
        cache["b"]          # b: count 2, a: count 1
        cache["c"] = 1
        assert sorted(cache) == ["b", "c"]


# --------------------------------------------------------------------------
# popitem
# --------------------------------------------------------------------------
class TestPopItem:
    @pytest.mark.smoke
    def test_pops_the_only_key_with_the_lowest_count(self):
        cache = LFUCache(3)
        cache["a"], cache["b"], cache["c"] = 1, 2, 3
        cache["a"]
        cache["a"]
        cache["b"]
        assert cache.popitem() == ("c", 3)
        assert sorted(cache) == ["a", "b"]
        assert cache.currsize == 2

    @pytest.mark.boundary
    def test_empty_cache_raises_key_error(self):
        with pytest.raises(KeyError, match="LFUCache is empty"):
            LFUCache(2).popitem()

    @pytest.mark.boundary
    def test_popping_last_item_then_empty(self):
        cache = filled(1, ["a"])
        assert cache.popitem() == ("a", 1)
        with pytest.raises(KeyError, match="LFUCache is empty"):
            cache.popitem()

    def test_read_protects_a_key_from_popitem(self):
        cache = filled(2, ["a", "b"])
        cache["b"]
        assert cache.popitem() == ("a", 1)


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
        with pytest.raises(KeyError, match="LFUCache is empty"):
            cache.popitem()

    def test_cache_is_reusable_with_fresh_counts(self):
        cache = filled(2, ["a", "b"])
        cache.clear()
        cache["x"] = 1
        cache["x"]          # x: count 2
        cache["y"] = 1      # y: count 1
        cache["z"] = 1      # evicts y
        assert sorted(cache) == ["x", "z"]

    @pytest.mark.boundary
    def test_clear_on_empty_cache(self):
        cache = LFUCache(2)
        cache.clear()
        assert list(cache) == []
        assert cache.currsize == 0


# --------------------------------------------------------------------------
# __init__ / maxsize
# --------------------------------------------------------------------------
class TestInit:
    @pytest.mark.smoke
    def test_maxsize_property(self):
        assert LFUCache(2).maxsize == 2

    @pytest.mark.boundary
    def test_negative_maxsize_is_rejected(self):
        with pytest.raises(ValueError, match="maxsize must be non-negative"):
            LFUCache(-1)["a"] = 1

    def test_new_cache_is_empty(self):
        cache = LFUCache(3)
        assert len(cache) == 0
        assert cache.currsize == 0