import httpx
from crawlers.base import BaseCrawler, CrawlResult


class GitHubCrawler(BaseCrawler):
    def __init__(self):
        self.base_url = "https://api.github.com"

    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            url = f"{self.base_url}/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            results = []
            for repo in data.get("items", []):
                results.append(
                    CrawlResult(
                        source="github",
                        title=repo.get("full_name", ""),
                        content=repo.get("description", "") or "",
                        url=repo.get("html_url", ""),
                        metadata={
                            "author": repo.get("owner", {}).get("login", ""),
                            "stars": repo.get("stargazers_count", 0),
                            "language": repo.get("language", ""),
                            "topics": repo.get("topics", []),
                        },
                    )
                )
            return results
        except Exception as e:
            return []
