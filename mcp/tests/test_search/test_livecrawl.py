"""Tests for livecrawling cache layer"""
import pytest
from datetime import datetime, timedelta
from search.livecrawl import LivecrawlCache, LivecrawlManager
from crawlers.base import CrawlResult


@pytest.fixture
def cache():
    return LivecrawlCache(max_size=10)


@pytest.fixture
def sample_result():
    return CrawlResult(
        source="web",
        title="Test Page",
        content="Test content",
        url="https://example.com",
        crawled_at=datetime.now(),
    )


def test_cache_set_and_get(cache, sample_result):
    cache.set("https://example.com", sample_result)
    result = cache.get("https://example.com")
    assert result is not None
    assert result.title == "Test Page"


def test_cache_miss(cache):
    result = cache.get("https://nonexistent.com")
    assert result is None


def test_cache_max_age_24_hours(cache, sample_result):
    cache.set("https://example.com", sample_result)
    # Should hit cache (fresh)
    result = cache.get("https://example.com", max_age_hours=24)
    assert result is not None


def test_cache_max_age_0_always_livecrawl(cache, sample_result):
    cache.set("https://example.com", sample_result)
    # Should miss (always livecrawl)
    result = cache.get("https://example.com", max_age_hours=0)
    assert result is None


def test_cache_max_age_neg1_cache_only(cache, sample_result):
    cache.set("https://example.com", sample_result)
    # Should hit (cache only)
    result = cache.get("https://example.com", max_age_hours=-1)
    assert result is not None


def test_cache_eviction(cache, sample_result):
    # Fill cache
    for i in range(10):
        cache.set(f"https://example{i}.com", sample_result)

    # Should evict LRU
    cache.set("https://new.com", sample_result)
    assert len(cache.cache) == 10


def test_cache_stats(cache, sample_result):
    cache.set("https://example.com", sample_result)
    cache.get("https://example.com")
    cache.get("https://nonexistent.com")

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1


def test_cache_clear(cache, sample_result):
    cache.set("https://example.com", sample_result)
    cache.clear()
    assert len(cache.cache) == 0


def test_livecrawl_manager_should_livecrawl():
    manager = LivecrawlManager()
    # Should livecrawl (no cache)
    assert manager.should_livecrawl("https://example.com") is True


def test_livecrawl_manager_store_and_get():
    manager = LivecrawlManager()
    result = CrawlResult(
        source="web",
        title="Test",
        content="Test",
        url="https://example.com",
    )
    manager.store("https://example.com", result)
    cached = manager.get_cached("https://example.com")
    assert cached is not None
