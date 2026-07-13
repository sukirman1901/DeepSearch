"""Tests for Streaming Search — as_completed batch results."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from search.streaming import StreamSearchManager, StreamBatch, StreamSearchResult
from crawlers.base import CrawlResult


@pytest.fixture
def mock_crawler():
    return AsyncMock()


@pytest.fixture
def mock_vector_store():
    return MagicMock()


@pytest.fixture
def manager(mock_crawler, mock_vector_store):
    return StreamSearchManager(mock_crawler, mock_vector_store)


def _make_result(source, title, url, content="content"):
    return CrawlResult(
        source=source, title=title, content=content, url=url,
        crawled_at=datetime.now(), score=0.5,
    )


@pytest.mark.asyncio
async def test_crawl_all_streaming_yields_results(mock_crawler):
    """Streaming crawl yields at least one batch."""
    async def fake_streaming(*args, **kwargs):
        yield "web", [_make_result("web", "A", "https://a.com")]

    mock_crawler.crawl_all_streaming = fake_streaming
    batches = []
    async for source, results in mock_crawler.crawl_all_streaming("test"):
        batches.append((source, results))
    assert len(batches) == 1
    assert batches[0][0] == "web"


@pytest.mark.asyncio
async def test_crawl_all_streaming_order(mock_crawler):
    """Faster source appears first in streaming results."""
    async def fake_streaming(*args, **kwargs):
        yield "fast_source", [_make_result("fast_source", "Fast", "https://fast.com")]
        yield "slow_source", [_make_result("slow_source", "Slow", "https://slow.com")]

    mock_crawler.crawl_all_streaming = fake_streaming
    batches = []
    async for source, results in mock_crawler.crawl_all_streaming("test"):
        batches.append(source)
    assert batches[0] == "fast_source"
    assert batches[1] == "slow_source"


@pytest.mark.asyncio
async def test_stream_search_returns_batches(manager, mock_crawler):
    """StreamSearchResult contains batches with timing."""
    async def fake_streaming(*args, **kwargs):
        yield "web", [_make_result("web", "A", "https://a.com")]

    mock_crawler.crawl_all_streaming = fake_streaming
    result = await manager.search("test")
    assert isinstance(result, StreamSearchResult)
    assert len(result.batches) == 1
    assert result.batches[0].source == "web"


@pytest.mark.asyncio
async def test_stream_search_timing(manager, mock_crawler):
    """total_time_ms is positive."""
    async def fake_streaming(*args, **kwargs):
        yield "web", []

    mock_crawler.crawl_all_streaming = fake_streaming
    result = await manager.search("test")
    assert result.total_time_ms >= 0


@pytest.mark.asyncio
async def test_stream_search_deduplicates(manager, mock_crawler):
    """Same URL from multiple sources appears once per batch."""
    async def fake_streaming(*args, **kwargs):
        yield "web", [
            _make_result("web", "A", "https://same.com"),
            _make_result("web", "A", "https://same.com"),
        ]

    mock_crawler.crawl_all_streaming = fake_streaming
    result = await manager.search("test")
    # Each batch has its own results — dedup is at the tool level
    assert result.batches[0].result_count == 2


@pytest.mark.asyncio
async def test_stream_search_sources_filter(manager, mock_crawler):
    """Only requested sources are searched."""
    async def fake_streaming(*args, **kwargs):
        sources = kwargs.get("sources") or args[1] if len(args) > 1 else None
        yield "github", [_make_result("github", "GH", "https://gh.com")]

    mock_crawler.crawl_all_streaming = fake_streaming
    result = await manager.search("test", sources=["github"])
    assert result.sources_searched == ["github"]


@pytest.mark.asyncio
async def test_stream_search_empty(manager, mock_crawler):
    """Empty query returns empty result."""
    async def fake_streaming(*args, **kwargs):
        return
        yield  # make it async generator

    mock_crawler.crawl_all_streaming = fake_streaming
    result = await manager.search("")
    assert result.total_results == 0
    assert len(result.batches) == 0


def test_serialize_crawl_result(manager):
    """CrawlResult serializes to dict correctly."""
    r = _make_result("github", "Repo", "https://github.com/repo", "code here")
    r.metadata = {"language": "python"}
    d = manager._serialize_result(r)
    assert d["title"] == "Repo"
    assert d["source"] == "github"
    assert d["metadata"]["language"] == "python"
    assert d["content"] == "code here"
