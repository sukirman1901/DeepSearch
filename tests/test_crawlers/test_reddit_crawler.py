import pytest
from crawlers.reddit_crawler import RedditCrawler

@pytest.mark.asyncio
async def test_reddit_crawler_crawl():
    crawler = RedditCrawler()
    results = await crawler.crawl("python programming", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "reddit"
        assert "reddit.com" in results[0].url
