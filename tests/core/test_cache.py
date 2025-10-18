"""Tests for simple TTL cache."""

import time

from football_rag.core.cache import SimpleCache


def test_cache_get_empty():
    """Test getting from empty cache."""
    cache = SimpleCache()
    assert cache.get("key") is None


def test_cache_set_and_get():
    """Test setting and getting values."""
    cache = SimpleCache()
    cache.set("key", "value", ttl_seconds=60)
    assert cache.get("key") == "value"


def test_cache_ttl_expiration():
    """Test that cache entries expire after TTL."""
    cache = SimpleCache()
    cache.set("key", "value", ttl_seconds=1)
    assert cache.get("key") == "value"
    time.sleep(1.1)
    assert cache.get("key") is None


def test_cache_no_ttl():
    """Test cache with zero TTL (no expiration)."""
    cache = SimpleCache()
    cache.set("key", "value", ttl_seconds=0)
    time.sleep(0.1)
    assert cache.get("key") == "value"


def test_cache_overwrite():
    """Test overwriting cache entries."""
    cache = SimpleCache()
    cache.set("key", "value1", ttl_seconds=60)
    cache.set("key", "value2", ttl_seconds=60)
    assert cache.get("key") == "value2"
