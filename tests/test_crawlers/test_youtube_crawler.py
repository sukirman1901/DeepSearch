import pytest
from crawlers.youtube_crawler import YouTubeCrawler


@pytest.mark.asyncio
async def test_youtube_crawler_crawl():
    crawler = YouTubeCrawler()
    results = await crawler.crawl("python tutorial", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "youtube"
        assert "youtube.com" in results[0].url
