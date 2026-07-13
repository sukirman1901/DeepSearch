import httpx
import asyncio
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult
from search.livecrawl import livecrawl_manager
from search.subpage import SubpageDiscoverer
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
        subpages: int = 0,
        subpage_target: str = "",
    ) -> list[CrawlResult]:
        """
        Crawl a URL with optional caching and subpage crawling.

        Args:
            url: URL to crawl
            max_results: Max results to return
            max_age_hours: Cache freshness control
            livecrawl_timeout: Timeout in ms for livecrawl
            subpages: Number of subpages to also crawl (0 = none)
            subpage_target: Keyword to filter subpages (e.g., "docs", "blog")
        """
        main_result = await self._crawl_single(
            url, max_age_hours, livecrawl_timeout
        )
        results = [main_result]

        if subpages > 0:
            discoverer = SubpageDiscoverer()
            subpage_urls = discoverer.discover_subpages(
                url, max_count=subpages, target_keyword=subpage_target
            )
            subpage_tasks = [
                self._crawl_single(u, max_age_hours, livecrawl_timeout)
                for u in subpage_urls
            ]
            subpage_results = await asyncio.gather(*subpage_tasks)
            results.extend(subpage_results)

        return results

    async def _crawl_single(
        self,
        url: str,
        max_age_hours: Optional[int] = None,
        livecrawl_timeout: int = 10000,
    ) -> CrawlResult:
        """Crawl a single URL with cache support."""
        cached = livecrawl_manager.get_cached(url, max_age_hours)
        if cached:
            return cached

        try:
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

            livecrawl_manager.store(url, result)

            return result
        except Exception as e:
            return CrawlResult(
                source="web",
                title=f"Error: {url}",
                content=str(e),
                url=url,
                metadata={"error": str(e)},
            )