import pytest
from crawlers.manager import CrawlerManager

@pytest.mark.asyncio
async def test_crawler_manager_initializes():
    manager = CrawlerManager()
    assert len(manager.crawlers) == 7

@pytest.mark.asyncio
async def test_crawler_manager_crawl_all():
    manager = CrawlerManager()
    results = await manager.crawl_all("python", max_results_per_source=2)
    assert isinstance(results, list)
