import pytest
from crawlers.duckduckgo_crawler import DuckDuckGoCrawler


@pytest.mark.asyncio
async def test_duckduckgo_crawler_crawl():
    crawler = DuckDuckGoCrawler()
    results = await crawler.crawl("python programming", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "duckduckgo"
