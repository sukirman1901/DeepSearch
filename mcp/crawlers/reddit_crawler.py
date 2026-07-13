import httpx
from crawlers.base import BaseCrawler, CrawlResult


class RedditCrawler(BaseCrawler):
    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.headers = {"User-Agent": "Mozilla/5.0 (compatible; DeepSearch/1.0; +https://github.com/deepsearch)"}

    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            url = f"{self.base_url}/search.json"
            params = {
                "q": query,
                "restrict_sr": "true",
                "sort": "relevance",
                "limit": max_results
            }

            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()

            results = []
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                results.append(CrawlResult(
                    source="reddit",
                    title=post_data.get("title", ""),
                    content=post_data.get("selftext", "")[:2000],
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    metadata={
                        "author": post_data.get("author", ""),
                        "score": post_data.get("score", 0),
                        "subreddit": post_data.get("subreddit", "")
                    }
                ))
            return results
        except Exception:
            return []
