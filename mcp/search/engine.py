import asyncio
from crawlers.manager import CrawlerManager
from db.vector_store import VectorStore
from crawlers.base import CrawlResult

class SearchEngine:
    def __init__(self):
        self.crawler_manager = CrawlerManager()
        self.vector_store = VectorStore()

    async def index_topic(self, topic: str, max_results_per_source: int = 10) -> int:
        results = await self.crawler_manager.crawl_all(topic, max_results_per_source)
        
        for result in results:
            self.vector_store.add(result)
        
        return len(results)

    def search(self, query: str, limit: int = 10) -> list[CrawlResult]:
        return self.vector_store.search(query, limit)

    def stats(self) -> dict:
        return self.vector_store.stats()
