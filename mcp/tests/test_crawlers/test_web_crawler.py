"""Tests for WebCrawler subpage crawling."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from crawlers.web_crawler import WebCrawler
from crawlers.base import CrawlResult
from datetime import datetime


@pytest.fixture
def crawler():
    return WebCrawler()


@pytest.mark.asyncio
async def test_web_crawler_crawl_url():
    crawler = WebCrawler()
    results = await crawler.crawl("https://example.com")
    assert len(results) >= 1
    assert results[0].source == "web"
    assert results[0].url == "https://example.com"


@pytest.mark.asyncio
async def test_crawl_with_zero_subpages_backward_compatible(crawler):
    """subpages=0 returns single result — backward compatible."""
    with patch.object(crawler, "_crawl_single", new_callable=AsyncMock) as mock_crawl:
        mock_crawl.return_value = CrawlResult(
            source="web",
            title="Main Page",
            content="content",
            url="https://example.com",
            crawled_at=datetime.now(),
        )
        results = await crawler.crawl("https://example.com", subpages=0)
        assert len(results) == 1
        assert results[0].title == "Main Page"


@pytest.mark.asyncio
async def test_crawl_with_subpages_returns_multiple(crawler):
    """subpages=3 returns main + up to 3 subpages."""
    main_result = CrawlResult(
        source="web", title="Main", content="main content",
        url="https://example.com", crawled_at=datetime.now(),
    )
    sub_result_1 = CrawlResult(
        source="web", title="Sub1", content="sub content 1",
        url="https://example.com/page1", crawled_at=datetime.now(),
    )
    sub_result_2 = CrawlResult(
        source="web", title="Sub2", content="sub content 2",
        url="https://example.com/page2", crawled_at=datetime.now(),
    )

    with patch.object(crawler, "_crawl_single", new_callable=AsyncMock) as mock_crawl, \
         patch("crawlers.web_crawler.SubpageDiscoverer") as mock_discoverer_cls:
        mock_discoverer = MagicMock()
        mock_discoverer_cls.return_value = mock_discoverer
        mock_discoverer.discover_subpages.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]
        mock_crawl.side_effect = [main_result, sub_result_1, sub_result_2]

        results = await crawler.crawl(
            "https://example.com",
            subpages=3,
        )

        assert len(results) == 3
        assert results[0].title == "Main"
        assert results[1].title == "Sub1"
        assert results[2].title == "Sub2"


@pytest.mark.asyncio
async def test_crawl_subpage_errors_dont_fail_all(crawler):
    """One subpage errors — others still returned."""
    main_result = CrawlResult(
        source="web", title="Main", content="main",
        url="https://example.com", crawled_at=datetime.now(),
    )
    sub_ok = CrawlResult(
        source="web", title="OK", content="ok",
        url="https://example.com/ok", crawled_at=datetime.now(),
    )
    sub_error = CrawlResult(
        source="web", title="Error: https://example.com/bad",
        content="connection error", url="https://example.com/bad",
        metadata={"error": "connection error"}, crawled_at=datetime.now(),
    )

    with patch.object(crawler, "_crawl_single", new_callable=AsyncMock) as mock_crawl, \
         patch("crawlers.web_crawler.SubpageDiscoverer") as mock_discoverer_cls:
        mock_discoverer = MagicMock()
        mock_discoverer_cls.return_value = mock_discoverer
        mock_discoverer.discover_subpages.return_value = [
            "https://example.com/bad",
            "https://example.com/ok",
        ]
        mock_crawl.side_effect = [main_result, sub_error, sub_ok]

        results = await crawler.crawl("https://example.com", subpages=2)

        assert len(results) == 3
        assert results[0].title == "Main"
        assert "Error" in results[1].title
        assert results[2].title == "OK"