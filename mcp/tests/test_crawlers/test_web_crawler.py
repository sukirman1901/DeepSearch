import pytest
from crawlers.web_crawler import WebCrawler

@pytest.mark.asyncio
async def test_web_crawler_crawl_url():
    crawler = WebCrawler()
    results = await crawler.crawl("https://example.com")
    assert len(results) >= 1
    assert results[0].source == "web"
    assert results[0].url == "https://example.com"
