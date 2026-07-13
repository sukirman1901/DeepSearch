import httpx
from crawlers.base import BaseCrawler, CrawlResult

class WikipediaCrawler(BaseCrawler):
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/api/rest_v1"

    async def crawl(self, query: str, max_results: int = 5) -> list[CrawlResult]:
        try:
            search_url = f"{self.base_url}/page/summary/{query.replace(' ', '_')}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url)
                response.raise_for_status()
                data = response.json()
            
            return [CrawlResult(
                source="wikipedia",
                title=data.get("title", ""),
                content=data.get("extract", ""),
                url=data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                metadata={
                    "description": data.get("description", ""),
                    "thumbnail": data.get("thumbnail", {}).get("source", "")
                }
            )]
        except Exception as e:
            return []