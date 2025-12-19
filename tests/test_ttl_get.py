"""Tests for TTLCache.get_ttl() method."""
import unittest

from cachetools import TTLCache


class Timer:
    """Mock timer for deterministic testing."""
    def __init__(self):
        self.time = 0

    def __call__(self):
        return self.time

    def tick(self, amount=1):
        self.time += amount


class TestTTLCacheGetTTL(unittest.TestCase):
    """Test cases for TTLCache.get_ttl() method."""

    def test_get_ttl_returns_remaining_time(self):
        """get_ttl should return remaining time until expiration."""
        timer = Timer()
        cache = TTLCache(maxsize=2, ttl=10, timer=timer)
        cache["key"] = "value"
        self.assertEqual(cache.get_ttl("key"), 10)
        timer.tick(3)
        self.assertEqual(cache.get_ttl("key"), 7)
        timer.tick(5)
        self.assertEqual(cache.get_ttl("key"), 2)

    def test_get_ttl_nonexistent_key_raises_keyerror(self):
        """get_ttl should raise KeyError for keys that don't exist."""
        timer = Timer()
        cache = TTLCache(maxsize=2, ttl=10, timer=timer)
        with self.assertRaises(KeyError):
            cache.get_ttl("nonexistent")

    def test_get_ttl_expired_key_raises_keyerror(self):
        """get_ttl should raise KeyError for keys that have expired."""
        timer = Timer()
        cache = TTLCache(maxsize=2, ttl=5, timer=timer)
        cache["key"] = "value"
        timer.tick(5)
        with self.assertRaises(KeyError):
            cache.get_ttl("key")

    def test_get_ttl_updated_key_resets_ttl(self):
        """Updating a key should reset its TTL."""
        timer = Timer()
        cache = TTLCache(maxsize=2, ttl=10, timer=timer)
        cache["key"] = "value1"
        timer.tick(5)
        self.assertEqual(cache.get_ttl("key"), 5)
        cache["key"] = "value2"
        self.assertEqual(cache.get_ttl("key"), 10)

    def test_get_ttl_with_custom_timer(self):
        """get_ttl should work correctly with custom timer functions."""
        from datetime import datetime, timedelta
        start_time = datetime(2025, 1, 1, 12, 0, 0)
        current_time = [start_time]
        def custom_timer():
            return current_time[0]
        cache = TTLCache(maxsize=2, ttl=timedelta(hours=1), timer=custom_timer)
        cache["key"] = "value"
        remaining = cache.get_ttl("key")
        self.assertEqual(remaining, timedelta(hours=1))
        current_time[0] = start_time + timedelta(minutes=30)
        remaining = cache.get_ttl("key")
        self.assertEqual(remaining, timedelta(minutes=30))

    def test_get_ttl_at_exact_boundary(self):
        """get_ttl at exact expiration boundary should raise KeyError."""
        timer = Timer()
        cache = TTLCache(maxsize=2, ttl=5, timer=timer)
        cache["key"] = "value"
        timer.tick(4)
        self.assertEqual(cache.get_ttl("key"), 1)
        timer.tick(1)
        with self.assertRaises(KeyError):
            cache.get_ttl("key")

    def test_get_ttl_does_not_affect_lru_order(self):
        """CRITICAL: get_ttl must NOT affect LRU eviction order."""
        timer = Timer()
        cache = TTLCache(maxsize=3, ttl=100, timer=timer)
        cache["a"] = 1
        timer.tick(1)
        cache["b"] = 2
        timer.tick(1)
        cache["c"] = 3
        timer.tick(1)
        cache.get_ttl("a")
        cache.get_ttl("a")
        cache.get_ttl("a")
        cache["d"] = 4
        self.assertNotIn("a", cache)
        self.assertIn("b", cache)
        self.assertIn("c", cache)
        self.assertIn("d", cache)

    def test_get_ttl_preserves_iteration_order(self):
        """TRAP: get_ttl must not affect iteration order."""
        timer = Timer()
        cache = TTLCache(maxsize=10, ttl=100, timer=timer)
        cache["first"] = 1
        timer.tick(1)
        cache["second"] = 2
        timer.tick(1)
        cache["third"] = 3
        order_before = list(cache.keys())
        for _ in range(5):
            cache.get_ttl("first")
        order_after = list(cache.keys())
        self.assertEqual(order_before, order_after)

    def test_get_ttl_with_float_timer_precision(self):
        """TRAP: Handle floating point timer correctly."""
        timer = Timer()
        timer.time = 0.0
        cache = TTLCache(maxsize=2, ttl=10.5, timer=timer)
        cache["key"] = "value"
        timer.time = 3.7
        remaining = cache.get_ttl("key")
        self.assertAlmostEqual(remaining, 6.8, places=5)

    def test_get_ttl_immediately_before_expiry(self):
        """TRAP: Test behavior at very close to expiry."""
        timer = Timer()
        timer.time = 0.0
        cache = TTLCache(maxsize=2, ttl=10.0, timer=timer)
        cache["key"] = "value"
        timer.time = 9.999999
        remaining = cache.get_ttl("key")
        self.assertGreater(remaining, 0)
        self.assertLess(remaining, 0.001)
        timer.time = 10.0
        with self.assertRaises(KeyError):
            cache.get_ttl("key")

    def test_get_ttl_after_reading_key(self):
        """TRAP: get_ttl after reading a key should return same TTL."""
        timer = Timer()
        cache = TTLCache(maxsize=3, ttl=100, timer=timer)
        cache["key"] = "value"
        timer.tick(30)
        _ = cache["key"]
        remaining = cache.get_ttl("key")
        self.assertEqual(remaining, 70)

    def test_get_ttl_consistent_with_contains(self):
        """TRAP: get_ttl must be consistent with 'in' operator."""
        timer = Timer()
        cache = TTLCache(maxsize=2, ttl=10, timer=timer)
        cache["key"] = "value"
        timer.tick(5)
        self.assertIn("key", cache)
        remaining = cache.get_ttl("key")
        self.assertEqual(remaining, 5)
        timer.tick(5)
        self.assertNotIn("key", cache)
        with self.assertRaises(KeyError):
            cache.get_ttl("key")

    def test_get_ttl_with_cache_miss_handler(self):
        """TRAP: get_ttl should NOT trigger __missing__ handler."""
        timer = Timer()

        class CustomTTLCache(TTLCache):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.missing_called = False

            def __missing__(self, key):
                self.missing_called = True
                return "default"

        cache = CustomTTLCache(maxsize=2, ttl=10, timer=timer)
        with self.assertRaises(KeyError):
            cache.get_ttl("nonexistent")
        self.assertFalse(cache.missing_called)

    def test_get_ttl_multiple_sequential_calls(self):
        """TRAP: Multiple get_ttl calls should return decreasing values."""
        timer = Timer()
        cache = TTLCache(maxsize=2, ttl=100, timer=timer)
        cache["key"] = "value"
        results = []
        for i in range(5):
            results.append(cache.get_ttl("key"))
            timer.tick(10)
        self.assertEqual(results, [100, 90, 80, 70, 60])

    def test_get_ttl_does_not_extend_lifetime(self):
        """CRITICAL: get_ttl must NOT extend item lifetime."""
        timer = Timer()
        cache = TTLCache(maxsize=2, ttl=10, timer=timer)
        cache["key"] = "value"
        timer.tick(5)
        cache.get_ttl("key")
        cache.get_ttl("key")
        cache.get_ttl("key")
        timer.tick(5)
        with self.assertRaises(KeyError):
            cache.get_ttl("key")
        self.assertNotIn("key", cache)
