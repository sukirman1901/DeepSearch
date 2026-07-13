"""
DuckDuckGo crawler — HTML scraping (independent, no library dependency).
Scrapes https://html.duckduckgo.com/html/ directly.
"""
import httpx
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult


class DuckDuckGoCrawler(BaseCrawler):
    SEARCH_URL = "https://html.duckduckgo.com/html/"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/143.0.0.0 Safari/537.36"
    )

    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.post(
                    self.SEARCH_URL,
                    data={"q": query},
                    headers={"User-Agent": self.USER_AGENT},
                )

            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            result_divs = soup.find_all("div", class_="result")

            results = []
            for div in result_divs[:max_results]:
                title_tag = div.find("a", class_="result__a")
                snippet_tag = div.find("a", class_="result__snippet")

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                link = title_tag.get("href", "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                # Skip ads
                if "y.js" in link or "ad_domain" in link or "rut=" in link:
                    continue

                # DDG HTML returns relative or wrapped URLs, extract actual URL
                if "uddg=" in link:
                    from urllib.parse import unquote, urlparse, parse_qs
                    parsed = urlparse(link)
                    qs = parse_qs(parsed.query)
                    link = unquote(qs.get("uddg", [link])[0])

                results.append(CrawlResult(
                    source="duckduckgo",
                    title=title,
                    content=snippet,
                    url=link,
                    metadata={"engine": "ddg_html"},
                ))

            return results
        except Exception:
            return []
