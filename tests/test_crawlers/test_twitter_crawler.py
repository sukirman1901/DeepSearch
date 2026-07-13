import pytest
from crawlers.twitter_crawler import TwitterCrawler

@pytest.mark.asyncio
async def test_twitter_crawler_crawl():
    crawler = TwitterCrawler()
    results = await crawler.crawl("python", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "twitter"
