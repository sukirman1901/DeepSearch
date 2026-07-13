from duckduckgo_search import DDGS
from crawlers.base import BaseCrawler, CrawlResult


class DuckDuckGoCrawler(BaseCrawler):
    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            with DDGS() as ddgs:
                results_list = list(ddgs.text(query, max_results=max_results))

            results = []
            for item in results_list:
                results.append(CrawlResult(
                    source="duckduckgo",
                    title=item.get("title", ""),
                    content=item.get("body", ""),
                    url=item.get("href", ""),
                    metadata={}
                ))
            return results
        except Exception as e:
            return []
