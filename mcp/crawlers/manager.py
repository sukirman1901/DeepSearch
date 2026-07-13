import asyncio
from crawlers.base import CrawlResult
from crawlers.web_crawler import WebCrawler
from crawlers.reddit_crawler import RedditCrawler
from crawlers.youtube_crawler import YouTubeCrawler
from crawlers.github_crawler import GitHubCrawler
from crawlers.twitter_crawler import TwitterCrawler
from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
from crawlers.wikipedia_crawler import WikipediaCrawler


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

    async def crawl_all(self, query: str, max_results_per_source: int = 10) -> list[CrawlResult]:
        tasks = []
        for name, crawler in self.crawlers.items():
            tasks.append(self._crawl_safe(crawler, query, max_results_per_source))

        results = await asyncio.gather(*tasks)
        return [item for sublist in results for item in sublist]

    async def _crawl_safe(self, crawler, query: str, max_results: int) -> list[CrawlResult]:
        try:
            return await crawler.crawl(query, max_results)
        except Exception:
            return []
