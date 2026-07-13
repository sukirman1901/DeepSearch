"""Tests for search filters"""
import pytest
from datetime import datetime, timedelta
from search.filters import SearchFilters, FilterEngine, create_filters
from crawlers.base import CrawlResult


@pytest.fixture
def sample_results():
    now = datetime.now()
    return [
        CrawlResult(
            source="web",
            title="Test Page 1",
            content="This is test content about AI",
            url="https://example.com/page1",
            metadata={"score": 100},
            crawled_at=now,
        ),
        CrawlResult(
            source="reddit",
            title="Test Post",
            content="Discussion about Python programming",
            url="https://reddit.com/r/python/123",
            metadata={"upvotes": 50},
            crawled_at=now - timedelta(days=2),
        ),
        CrawlResult(
            source="github",
            title="Code Repo",
            content="A Python library for ML",
            url="https://github.com/user/repo",
            metadata={"stars": 1000},
            crawled_at=now - timedelta(days=10),
        ),
    ]


def test_no_filters_returns_all(sample_results):
    engine = FilterEngine()
    result = engine.apply_filters(sample_results)
    assert len(result) == 3


def test_include_domains(sample_results):
    filters = create_filters(include_domains=["example.com"])
    engine = FilterEngine()
    engine.set_filters(filters)
    result = engine.apply_filters(sample_results)
    assert len(result) == 1
    assert result[0].url == "https://example.com/page1"


def test_exclude_domains(sample_results):
    filters = create_filters(exclude_domains=["reddit.com"])
    engine = FilterEngine()
    engine.set_filters(filters)
    result = engine.apply_filters(sample_results)
    assert len(result) == 2
    assert all("reddit.com" not in r.url for r in result)


def test_include_sources(sample_results):
    filters = create_filters(include_sources=["web", "github"])
    engine = FilterEngine()
    engine.set_filters(filters)
    result = engine.apply_filters(sample_results)
    assert len(result) == 2


def test_exclude_sources(sample_results):
    filters = create_filters(exclude_sources=["reddit"])
    engine = FilterEngine()
    engine.set_filters(filters)
    result = engine.apply_filters(sample_results)
    assert len(result) == 2
    assert all(r.source != "reddit" for r in result)


def test_include_text(sample_results):
    filters = create_filters(include_text=["AI"])
    engine = FilterEngine()
    engine.set_filters(filters)
    result = engine.apply_filters(sample_results)
    assert len(result) == 1
    assert "AI" in result[0].content


def test_exclude_text(sample_results):
    filters = create_filters(exclude_text=["Python"])
    engine = FilterEngine()
    engine.set_filters(filters)
    result = engine.apply_filters(sample_results)
    # Only web result should remain (Reddit and GitHub both mention Python)
    assert len(result) == 1
    assert result[0].source == "web"


def test_boost_popular(sample_results):
    filters = create_filters(boost_popular=True)
    engine = FilterEngine()
    engine.set_filters(filters)
    result = engine.apply_filters(sample_results)
    # GitHub has 1000 stars, should be first
    assert result[0].source == "github"
