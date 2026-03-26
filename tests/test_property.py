"""Tests for cachetools.property.cached_property."""

import threading
import time

import pytest

from cachetools.property import cached_property


# ── Fixtures ──────────────────────────────────────────────────────────────────

class _Counter:
    """Helper: counts how many times the property function is called."""

    def __init__(self):
        self._count = 0

    @cached_property(ttl=0.2)
    def value(self):
        self._count += 1
        return self._count


class _Named:
    def __init__(self, name: str):
        self.name = name

    @cached_property(ttl=0.1)
    def info(self):
        return {"name": self.name, "ts": time.monotonic()}


# ── Basic caching ─────────────────────────────────────────────────────────────

def test_cached_on_first_access():
    obj = _Counter()
    v = obj.value
    assert v == 1
    assert obj._count == 1


def test_cache_hit_on_second_access():
    obj = _Counter()
    v1 = obj.value
    v2 = obj.value
    assert v1 == v2
    assert obj._count == 1


def test_instance_isolation():
    """Each instance must have its own cache — no cross-instance collision."""
    a = _Named("A")
    b = _Named("B")
    assert a.info["name"] == "A"
    assert b.info["name"] == "B"
    # Accessing b should not affect a's cache
    assert a.info["name"] == "A"


# ── TTL expiry ────────────────────────────────────────────────────────────────

def test_ttl_expiry_triggers_recompute():
    obj = _Counter()
    v1 = obj.value
    time.sleep(0.25)  # wait for TTL to expire
    v2 = obj.value
    assert v2 == 2, "should recompute after TTL"
    assert obj._count == 2


def test_value_stable_within_ttl():
    obj = _Counter()
    v1 = obj.value
    time.sleep(0.05)  # within TTL
    v2 = obj.value
    assert v1 == v2
    assert obj._count == 1


# ── Manual invalidation ───────────────────────────────────────────────────────

def test_delete_forces_recompute():
    obj = _Counter()
    _ = obj.value
    del obj.value
    v2 = obj.value
    assert v2 == 2
    assert obj._count == 2


def test_delete_before_access_is_safe():
    obj = _Counter()
    del obj.value  # no-op — nothing cached yet
    v = obj.value
    assert v == 1


# ── Class-level access ────────────────────────────────────────────────────────

def test_class_access_returns_descriptor():
    desc = _Counter.value
    assert isinstance(desc, cached_property)


# ── cache_info ────────────────────────────────────────────────────────────────

def test_cache_info_uncached():
    obj = _Counter()
    info = _Counter.value.cache_info(obj)
    assert info["cached"] is False
    assert info["expires_at"] is None
    assert info["ttl"] == pytest.approx(0.2)


def test_cache_info_cached():
    obj = _Counter()
    _ = obj.value
    info = _Counter.value.cache_info(obj)
    assert info["cached"] is True
    assert info["expires_at"] > time.monotonic()


def test_cache_info_expired():
    obj = _Counter()
    _ = obj.value
    time.sleep(0.25)
    info = _Counter.value.cache_info(obj)
    assert info["cached"] is False


# ── Argument validation ───────────────────────────────────────────────────────

def test_zero_ttl_raises():
    with pytest.raises(ValueError, match="ttl must be a positive number"):
        cached_property(ttl=0)


def test_negative_ttl_raises():
    with pytest.raises(ValueError, match="ttl must be a positive number"):
        cached_property(ttl=-5)


def test_non_callable_raises():
    with pytest.raises(TypeError, match="cached_property requires a callable"):
        cached_property("not-callable", ttl=1)


# ── Double-name assignment ────────────────────────────────────────────────────

def test_cannot_assign_to_two_names():
    prop = cached_property(ttl=1)

    with pytest.raises(TypeError, match="Cannot assign the same @cached_property"):
        class _Bad:
            x = prop
            y = prop


# ── Thread safety ─────────────────────────────────────────────────────────────

def test_thread_safe_single_compute():
    """Under concurrent access the wrapped function must be called exactly once."""
    class _Shared:
        _calls = 0

        @cached_property(ttl=10)
        def data(self):
            _Shared._calls += 1
            time.sleep(0.02)  # simulate latency
            return _Shared._calls

    obj = _Shared()
    results = []

    def access():
        results.append(obj.data)

    threads = [threading.Thread(target=access) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert _Shared._calls == 1, f"Expected 1 call, got {_Shared._calls}"
    assert all(r == 1 for r in results)


# ── Slots compatibility ───────────────────────────────────────────────────────

def test_slots_raises_attribute_error():
    with pytest.raises(AttributeError, match="No '__dict__'"):
        class _Slotted:
            __slots__ = ()

            @cached_property(ttl=1)
            def val(self):
                return 42

        _Slotted().val


# ── Decorator syntax variants ─────────────────────────────────────────────────

def test_decorator_with_arguments():
    """@cached_property(ttl=N) — standard usage."""
    class _A:
        @cached_property(ttl=1)
        def v(self):
            return 99

    assert _A().v == 99


def test_repr():
    class _A:
        @cached_property(ttl=5)
        def compute(self):
            return 1

    r = repr(_A.compute)
    assert "cached_property" in r
    assert "5" in r
