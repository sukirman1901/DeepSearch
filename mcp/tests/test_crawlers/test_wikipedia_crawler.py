import pytest
from crawlers.wikipedia_crawler import WikipediaCrawler

@pytest.mark.asyncio
async def test_wikipedia_crawler_crawl():
    crawler = WikipediaCrawler()
    results = await crawler.crawl("artificial intelligence", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "wikipedia"
        assert "wikipedia.org" in results[0].url