import asyncio
from crawlers.base import CrawlResult
from crawlers.web_crawler import WebCrawler
from crawlers.reddit_crawler import RedditCrawler
from crawlers.youtube_crawler import YouTubeCrawler
from crawlers.github_crawler import GitHubCrawler
from crawlers.twitter_crawler import TwitterCrawler
from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
from crawlers.wikipedia_crawler import WikipediaCrawler
from search.categories import detect_category, get_sources_for_category, Category
from search.query_variation import QueryVariationGenerator


class CrawlerManager:
    def __init__(self):
        self.crawlers = {
            "web": WebCrawler(),
            "reddit": RedditCrawler(),
            "youtube": YouTubeCrawler(),
            "github": GitHubCrawler(),
            "twitter": TwitterCrawler(),
            "duckduckgo": DuckDuckGoCrawler(),
            "wikipedia": WikipediaCrawler(),
        }
        self.query_generator = QueryVariationGenerator()

    async def crawl_all(
        self,
        query: str,
        max_results_per_source: int = 10,
        category: str = "auto",
        sources: list[str] = None,
        generate_variations: bool = True,
    ) -> list[CrawlResult]:
        # Auto-detect category
        if category == "auto":
            detected = detect_category(query)
            category = detected.value
        
        # Select sources based on category
        if not sources:
            cat_enum = Category(category) if category in [c.value for c in Category] else Category.GENERAL
            sources = get_sources_for_category(cat_enum)
        
        # Generate query variations
        queries = [query]
        if generate_variations:
            variations = self.query_generator.generate_variations(query, category, max_variations=2)
            queries = variations
        
        # Crawl with variations
        tasks = []
        for source_name in sources:
            if source_name in self.crawlers:
                crawler = self.crawlers[source_name]
                for q in queries:
                    tasks.append(self._crawl_safe(crawler, q, max(1, max_results_per_source // len(queries))))

        results = await asyncio.gather(*tasks)
        all_results = [item for sublist in results for item in sublist]
        
        # Tag results with category
        for result in all_results:
            if result.category == "general":
                result.category = category
        
        return all_results

    async def crawl_sources(
        self,
        query: str,
        sources: list[str],
        max_results_per_source: int = 10,
    ) -> list[CrawlResult]:
        """Crawl specific sources only"""
        tasks = []
        for source_name in sources:
            if source_name in self.crawlers:
                tasks.append(self._crawl_safe(self.crawlers[source_name], query, max_results_per_source))
        
        results = await asyncio.gather(*tasks)
        return [item for sublist in results for item in sublist]

    async def _crawl_safe(self, crawler, query: str, max_results: int) -> list[CrawlResult]:
        try:
            return await crawler.crawl(query, max_results)
        except Exception:
            return []

    async def crawl_all_streaming(
        self,
        query: str,
        max_results_per_source: int = 10,
        category: str = "auto",
        sources: list[str] = None,
        generate_variations: bool = True,
    ):
        """Yield (source_name, results) as each source completes."""
        if category == "auto":
            detected = detect_category(query)
            category = detected.value

        if not sources:
            cat_enum = Category(category) if category in [c.value for c in Category] else Category.GENERAL
            sources = get_sources_for_category(cat_enum)

        queries = [query]
        if generate_variations:
            variations = self.query_generator.generate_variations(query, category, max_variations=2)
            queries = variations

        tasks = {}
        for source_name in sources:
            if source_name in self.crawlers:
                crawler = self.crawlers[source_name]
                for q in queries:
                    task = asyncio.create_task(
                        self._crawl_safe(crawler, q, max(1, max_results_per_source // len(queries)))
                    )
                    tasks[task] = source_name

        # Wrap each task to carry source_name through as_completed
        async def _tagged(coro, name):
            return name, await coro

        tagged = [_tagged(t, tasks[t]) for t in tasks]
        for completed in asyncio.as_completed(tagged):
            try:
                source_name, results = await completed
            except Exception:
                continue

            for result in results:
                if result.category == "general":
                    result.category = category

            yield source_name, results
