import pytest
from crawlers.github_crawler import GitHubCrawler


@pytest.mark.asyncio
async def test_github_crawler_crawl():
    crawler = GitHubCrawler()
    results = await crawler.crawl("python web framework", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "github"
        assert "github.com" in results[0].url
