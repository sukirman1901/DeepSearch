"""Tests for Monitors API."""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime
from search.monitors import MonitorManager
from crawlers.base import CrawlResult


@pytest.fixture
def manager(tmp_path):
    return MonitorManager(data_file=str(tmp_path / "monitors.json"))


@pytest.fixture
def mock_crawler():
    return AsyncMock()


@pytest.fixture
def sample_results():
    return [
        CrawlResult(source="web", title="Result 1", content="content 1",
                    url="https://example.com/1", crawled_at=datetime.now()),
        CrawlResult(source="web", title="Result 2", content="content 2",
                    url="https://example.com/2", crawled_at=datetime.now()),
        CrawlResult(source="reddit", title="Result 3", content="content 3",
                    url="https://reddit.com/r/test/1", crawled_at=datetime.now()),
    ]


def test_create_monitor(manager):
    """Creates monitor, returns ID, monitor exists in list."""
    mid = manager.create_monitor(query="AI security", sources=["web", "reddit"])

    assert mid is not None
    monitors = manager.list_monitors()
    assert len(monitors) == 1
    assert monitors[0]["id"] == mid
    assert monitors[0]["query"] == "AI security"


def test_list_monitors(manager):
    """Multiple monitors created, all listed with correct stats."""
    manager.create_monitor(query="query1")
    manager.create_monitor(query="query2")

    monitors = manager.list_monitors()
    assert len(monitors) == 2
    queries = [m["query"] for m in monitors]
    assert "query1" in queries
    assert "query2" in queries


@pytest.mark.asyncio
async def test_run_monitor_returns_all_on_first_run(manager, mock_crawler, sample_results):
    """First run: all results are new (seen_urls empty)."""
    mock_crawler.crawl_all.return_value = sample_results
    mid = manager.create_monitor(query="test")

    results = await manager.run_monitor(mid, mock_crawler)

    assert len(results) == 3
    assert all(isinstance(r, CrawlResult) for r in results)


@pytest.mark.asyncio
async def test_run_monitor_deduplicates_on_second_run(manager, mock_crawler, sample_results):
    """Second run: only URLs not in first run returned."""
    mock_crawler.crawl_all.return_value = sample_results
    mid = manager.create_monitor(query="test")

    first = await manager.run_monitor(mid, mock_crawler)
    assert len(first) == 3

    new_result = CrawlResult(
        source="web", title="New", content="new content",
        url="https://example.com/new", crawled_at=datetime.now(),
    )
    mock_crawler.crawl_all.return_value = sample_results + [new_result]

    second = await manager.run_monitor(mid, mock_crawler)
    assert len(second) == 1
    assert second[0].url == "https://example.com/new"


@pytest.mark.asyncio
async def test_run_monitor_invalid_id(manager, mock_crawler):
    """Invalid ID returns empty list."""
    results = await manager.run_monitor("nonexistent", mock_crawler)
    assert results == []


def test_delete_monitor(manager):
    """Delete existing monitor, verify removed from list."""
    mid = manager.create_monitor(query="test")

    deleted = manager.delete_monitor(mid)
    assert deleted is True
    assert len(manager.list_monitors()) == 0


def test_delete_monitor_invalid_id(manager):
    """Delete non-existent returns False."""
    deleted = manager.delete_monitor("nonexistent")
    assert deleted is False


def test_persistence(tmp_path):
    """Create monitor, create new MonitorManager with same file, verify loaded."""
    data_file = str(tmp_path / "monitors.json")
    mgr1 = MonitorManager(data_file=data_file)
    mid = mgr1.create_monitor(query="persist test")

    mgr2 = MonitorManager(data_file=data_file)
    monitors = mgr2.list_monitors()
    assert len(monitors) == 1
    assert monitors[0]["id"] == mid
    assert monitors[0]["query"] == "persist test"
