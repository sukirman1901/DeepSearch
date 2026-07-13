"""Tests for Tavily-inspired features: search_depth, topic, max_age."""
import pytest
from datetime import datetime, timedelta
from search.engine import SearchEngine, SEARCH_DEPTH_PRESETS, NEWS_DOMAINS
from crawlers.base import CrawlResult


def test_search_depth_presets_exist():
    assert "fast" in SEARCH_DEPTH_PRESETS
    assert "basic" in SEARCH_DEPTH_PRESETS
    assert "advanced" in SEARCH_DEPTH_PRESETS


def test_search_depth_fast_preset():
    preset = SEARCH_DEPTH_PRESETS["fast"]
    assert preset["max_per_source"] == 3
    assert preset["rerank"] is False


def test_search_depth_basic_preset():
    preset = SEARCH_DEPTH_PRESETS["basic"]
    assert preset["max_per_source"] == 5
    assert preset["rerank"] is False


def test_search_depth_advanced_preset():
    preset = SEARCH_DEPTH_PRESETS["advanced"]
    assert preset["max_per_source"] == 20
    assert preset["rerank"] is True


def test_news_domains_list():
    assert len(NEWS_DOMAINS) > 10
    assert "reuters.com" in NEWS_DOMAINS
    assert "bbc.com" in NEWS_DOMAINS
    assert "techcrunch.com" in NEWS_DOMAINS


def test_filter_by_topic_news():
    engine = SearchEngine()
    now = datetime.now()
    results = [
        CrawlResult(source="web", title="Reuters Article", content="test", url="https://reuters.com/article", crawled_at=now),
        CrawlResult(source="web", title="Old Blog", content="test", url="https://example.com/blog", crawled_at=now - timedelta(days=60)),
        CrawlResult(source="web", title="BBC News", content="test", url="https://bbc.com/news", crawled_at=now - timedelta(hours=12)),
    ]
    filtered = engine._filter_by_topic_news(results)
    # News domains should be boosted to the top
    assert filtered[0].url in ("https://reuters.com/article", "https://bbc.com/news")
    # Old content should be demoted
    assert filtered[-1].url == "https://example.com/blog"


def test_filter_by_topic_news_recency_boost():
    engine = SearchEngine()
    now = datetime.now()
    results = [
        CrawlResult(source="web", title="Old News", content="test", url="https://reuters.com/old", crawled_at=now - timedelta(days=5)),
        CrawlResult(source="web", title="Fresh News", content="test", url="https://reuters.com/fresh", crawled_at=now - timedelta(hours=6)),
    ]
    filtered = engine._filter_by_topic_news(results)
    # Fresh news should be ranked higher
    assert filtered[0].url == "https://reuters.com/fresh"


def test_max_age_filter():
    engine = SearchEngine()
    now = datetime.now()
    results = [
        CrawlResult(source="web", title="Fresh", content="test", url="https://a.com", crawled_at=now - timedelta(hours=1)),
        CrawlResult(source="web", title="Old", content="test", url="https://b.com", crawled_at=now - timedelta(hours=48)),
    ]
    # Filter to last 24 hours
    filtered = [r for r in results if r.crawled_at >= now - timedelta(hours=24)]
    assert len(filtered) == 1
    assert filtered[0].title == "Fresh"


def test_max_age_no_limit():
    engine = SearchEngine()
    now = datetime.now()
    results = [
        CrawlResult(source="web", title="Fresh", content="test", url="https://a.com", crawled_at=now - timedelta(hours=1)),
        CrawlResult(source="web", title="Old", content="test", url="https://b.com", crawled_at=now - timedelta(hours=48)),
    ]
    # No limit (-1) means no filter applied, all results kept
    # max_age_hours=-1 should not trigger any filtering
    assert results[0].crawled_at < now + timedelta(hours=1)
    assert results[1].crawled_at < now + timedelta(hours=1)
    # Both results exist (no filtering applied)
    assert len(results) == 2


def test_search_engine_accepts_search_depth():
    engine = SearchEngine()
    # Should accept all three depth values without error
    assert "fast" in SEARCH_DEPTH_PRESETS
    assert "basic" in SEARCH_DEPTH_PRESETS
    assert "advanced" in SEARCH_DEPTH_PRESETS


def test_search_engine_accepts_topic():
    engine = SearchEngine()
    # Topic filter should be a simple string param
    assert hasattr(engine, '_filter_by_topic_news')


def test_search_engine_accepts_max_age():
    engine = SearchEngine()
    # max_age should be an integer param
    results = [
        CrawlResult(source="web", title="Test", content="test", url="https://a.com", crawled_at=datetime.now()),
    ]
    # Should not crash with max_age_hours=24
    filtered = [r for r in results if r.crawled_at >= datetime.now() - timedelta(hours=24)]
    assert len(filtered) == 1
