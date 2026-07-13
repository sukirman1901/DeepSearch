"""
Wikipedia crawler — uses MediaWiki search API for query-based results.
"""
import httpx
from crawlers.base import BaseCrawler, CrawlResult


class WikipediaCrawler(BaseCrawler):
    def __init__(self):
        self.search_url = "https://en.wikipedia.org/w/api.php"
        self.rest_url = "https://en.wikipedia.org/api/rest_v1"

    async def crawl(self, query: str, max_results: int = 5) -> list[CrawlResult]:
        try:
            # Step 1: Search for pages matching the query
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (compatible; DeepSearch/1.0; +https://github.com/deepsearch)"},
            ) as client:
                search_resp = await client.get(
                    self.search_url,
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "srlimit": max_results,
                        "format": "json",
                    },
                )
                search_resp.raise_for_status()
                search_data = search_resp.json()

            results = []
            for item in search_data.get("query", {}).get("search", []):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                # Strip HTML tags from snippet
                import re
                snippet = re.sub(r"<[^>]+>", "", snippet)

                results.append(CrawlResult(
                    source="wikipedia",
                    title=title,
                    content=snippet,
                    url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    metadata={
                        "pageid": item.get("pageid"),
                        "wordcount": item.get("wordcount", 0),
                    },
                ))

            return results
        except Exception:
            return []
