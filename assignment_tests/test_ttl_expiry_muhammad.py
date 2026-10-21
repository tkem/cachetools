"""Unit tests for the expiry-related parts of cachetools.TTLCache (Muhammad Dawood).

Covers: ttl, timer, __contains__, __iter__, expire.
Each test maps to a row in notes/ecp_bva_muhammad.md.

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


# --------------------------------------------------------------------------
# ttl
# --------------------------------------------------------------------------
class TestTtl:
    @pytest.mark.smoke
    @pytest.mark.parametrize("ttl", [10, 0.5, 0], ids=["int", "float", "zero"])
    def test_ttl_property_returns_configured_value(self, clock, ttl):
        assert TTLCache(3, ttl=ttl, timer=clock).ttl == ttl

    @pytest.mark.boundary
    def test_ttl_zero_item_is_expired_immediately(self, clock):
        cache = TTLCache(3, ttl=0, timer=clock)
        cache["a"] = 1
        assert "a" not in cache
        assert len(cache) == 0

    @pytest.mark.boundary
    def test_negative_ttl_item_is_expired_immediately(self, clock):
        cache = TTLCache(3, ttl=-5, timer=clock)
        cache["a"] = 1
        assert "a" not in cache
        assert len(cache) == 0


# --------------------------------------------------------------------------
# timer
# --------------------------------------------------------------------------
class TestTimer:
    @pytest.mark.smoke
    def test_timer_returns_custom_clock_value(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        assert cache.timer() == 0

    def test_timer_follows_the_clock(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        clock.now = 5
        assert cache.timer() == 5

    def test_default_timer_is_callable_and_returns_float(self):
        cache = TTLCache(2, ttl=10)
        assert callable(cache.timer)
        assert isinstance(cache.timer(), float)

    def test_default_timer_keeps_fresh_item(self):
        cache = TTLCache(2, ttl=10)
        cache["x"] = 1
        assert "x" in cache

    def test_timer_drives_expiry_on_insert(self, clock):
        cache = TTLCache(2, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 5
        cache["b"] = 2
        clock.now = 11
        cache["c"] = 3
        assert list(cache) == ["b", "c"]


# --------------------------------------------------------------------------
# __contains__
# --------------------------------------------------------------------------
class TestContains:
    @pytest.mark.boundary
    @pytest.mark.parametrize(
        "now, expected",
        [(0, True), (9, True), (9.99, True), (10, False), (10.01, False), (11, False)],
        ids=["just_set", "well_before", "just_before", "exactly_at", "just_after", "well_after"],
    )
    def test_membership_around_expiry(self, clock, now, expected):
        cache = TTLCache(3, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = now
        assert ("a" in cache) is expected

    def test_missing_key_is_not_contained(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        assert "zzz" not in cache

    def test_overwrite_resets_expiry(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 8
        cache["a"] = 2
        clock.now = 12
        assert "a" in cache
        clock.now = 18
        assert "a" not in cache


# --------------------------------------------------------------------------
# __iter__
# --------------------------------------------------------------------------
class TestIter:
    @pytest.fixture
    def staggered(self, clock):
        """a set at t=0, b at t=3, c at t=6 (ttl=10)."""
        cache = TTLCache(5, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 3
        cache["b"] = 2
        clock.now = 6
        cache["c"] = 3
        return cache

    @pytest.mark.boundary
    @pytest.mark.parametrize(
        "now, expected",
        [
            (9, ["a", "b", "c"]),
            (10, ["b", "c"]),
            (13, ["c"]),
            (16, []),
        ],
        ids=["none_expired", "a_expires_exactly", "two_expired", "all_expired"],
    )
    def test_iteration_skips_expired_items(self, clock, staggered, now, expected):
        clock.now = now
        assert list(staggered) == expected

    @pytest.mark.boundary
    def test_empty_cache_iterates_nothing(self, clock):
        assert list(TTLCache(2, ttl=10, timer=clock)) == []

    def test_all_items_expire_at_once(self, clock):
        cache = TTLCache(3, ttl=10, timer=clock)
        cache["a"] = 1
        cache["b"] = 2
        clock.now = 10
        assert list(cache) == []
        assert len(cache) == 0
        assert cache.currsize == 0


# --------------------------------------------------------------------------
# expire
# --------------------------------------------------------------------------
class TestExpire:
    @pytest.fixture
    def two_items(self, clock):
        """a set at t=0, b at t=5 (ttl=10)."""
        cache = TTLCache(5, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 5
        cache["b"] = 2
        return cache

    @pytest.mark.smoke
    def test_nothing_expired_returns_empty_list(self, clock, two_items):
        clock.now = 9
        assert two_items.expire() == []

    @pytest.mark.boundary
    def test_item_expires_exactly_at_ttl(self, clock, two_items):
        clock.now = 10
        assert two_items.expire() == [("a", 1)]
        assert list(two_items) == ["b"]

    def test_remaining_item_expires_later(self, clock, two_items):
        clock.now = 20
        assert two_items.expire() == [("a", 1), ("b", 2)]
        assert list(two_items) == []

    @pytest.mark.boundary
    def test_expire_on_empty_cache(self, clock):
        assert TTLCache(2, ttl=10, timer=clock).expire() == []

    def test_explicit_time_overrides_the_clock(self, clock):
        cache = TTLCache(5, ttl=10, timer=clock)
        cache["a"] = 1
        cache["b"] = 2
        assert cache.expire(10) == [("a", 1), ("b", 2)]
        assert list(cache) == []
        assert cache.currsize == 0

    @pytest.mark.boundary
    def test_explicit_time_just_before_expiry(self, clock):
        cache = TTLCache(5, ttl=10, timer=clock)
        cache["a"] = 1
        assert cache.expire(9.99) == []
        assert list(cache) == ["a"]

    def test_expired_items_returned_in_the_order_they_were_set(self, clock):
        cache = TTLCache(5, ttl=10, timer=clock)
        cache["a"] = 1
        clock.now = 1
        cache["b"] = 2
        clock.now = 2
        cache["c"] = 3
        clock.now = 20
        assert [key for key, _ in cache.expire()] == ["a", "b", "c"]