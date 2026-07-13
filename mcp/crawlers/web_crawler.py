import httpx
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult
from search.livecrawl import livecrawl_manager
from typing import Optional


class WebCrawler(BaseCrawler):
    def __init__(self):
        self.client = httpx.Client(
            headers={"User-Agent": "Mozilla/5.0 (compatible; SearchEngine/1.0)"},
            follow_redirects=True,
            timeout=10.0,
        )

    async def crawl(
        self,
        url: str,
        max_results: int = 1,
        max_age_hours: Optional[int] = None,
        livecrawl_timeout: int = 10000,
    ) -> list[CrawlResult]:
        """
        Crawl a URL with optional caching.

        Args:
            url: URL to crawl
            max_results: Max results to return
            max_age_hours: Cache freshness control
                - 24: Use cache if <24 hours old
                - 1: Use cache if <1 hour old
                - 0: Always livecrawl
                - -1: Cache only
                - None: Default behavior
            livecrawl_timeout: Timeout in ms for livecrawl
        """
        # Check cache first
        cached = livecrawl_manager.get_cached(url, max_age_hours)
        if cached:
            return [cached]

        try:
            # Livecrawl with timeout
            timeout_seconds = livecrawl_timeout / 1000
            client = httpx.Client(
                headers={"User-Agent": "Mozilla/5.0 (compatible; SearchEngine/1.0)"},
                follow_redirects=True,
                timeout=min(timeout_seconds, 30),
            )
            response = client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.title.string if soup.title else url

            for script in soup(["script", "style"]):
                script.decompose()

            content = soup.get_text(separator="\n", strip=True)
            content = "\n".join(line for line in content.splitlines() if line.strip())

            result = CrawlResult(
                source="web",
                title=title,
                content=content[:5000],
                url=url,
                metadata={"status_code": response.status_code},
            )

            # Store in cache
            livecrawl_manager.store(url, result)

            return [result]
        except Exception as e:
            return [CrawlResult(
                source="web",
                title=f"Error: {url}",
                content=str(e),
                url=url,
                metadata={"error": str(e)},
            )]
