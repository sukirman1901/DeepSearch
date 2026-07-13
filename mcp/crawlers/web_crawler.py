import httpx
import asyncio
import html2text
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult
from search.livecrawl import livecrawl_manager
from search.subpage import SubpageDiscoverer
from typing import Optional


# --- Constants (inspired by webfetch.ts) ---
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5MB
DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 120
MAX_CONTENT_LENGTH = 5000

BROWSER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
]

# Cloudflare bypass UA (from webfetch.ts)
CLOUDFLARE_BYPASS_UA = "opencode"

# Skip tags for text extraction (from webfetch.ts)
SKIP_TAGS = {"script", "style", "noscript", "iframe", "object", "embed"}


def _get_user_agent(index: int = 0) -> str:
    """Rotate user agents."""
    return BROWSER_USER_AGENTS[index % len(BROWSER_USER_AGENTS)]


def _is_cloudflare_challenge(response: httpx.Response) -> bool:
    """Detect Cloudflare challenge (from webfetch.ts pattern)."""
    return (
        response.status_code == 403
        and response.headers.get("cf-mitigated", "").lower() == "challenge"
    )


def _is_textual_content(content_type: str) -> bool:
    """Check if content type is textual (from webfetch.ts pattern)."""
    if not content_type:
        return True
    mime = content_type.split(";", 1)[0].strip().lower()
    return (
        mime.startswith("text/")
        or mime == "application/json"
        or mime.endswith("+json")
        or mime == "application/xml"
        or mime.endswith("+xml")
        or mime == "application/javascript"
    )


def _html_to_markdown(html: str) -> str:
    """Convert HTML to markdown using html2text (from webfetch.ts TurndownService pattern)."""
    h = html2text.HTML2Text()
    h.body_width = 0  # Don't wrap lines
    h.protect_links = True
    h.unicode_snob = True
    h.images_to_alt = True
    h.single_line_break = False
    return h.handle(html).strip()


def _extract_text(html: str) -> str:
    """Extract text from HTML, skipping script/style/etc (from webfetch.ts extractTextFromHTML pattern)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(SKIP_TAGS):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(line for line in text.splitlines() if line.strip())


class WebCrawler(BaseCrawler):
    def __init__(self):
        self.client = httpx.Client(
            headers={"User-Agent": _get_user_agent(0)},
            follow_redirects=True,
            timeout=DEFAULT_TIMEOUT,
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
        main_result = await self._crawl_single(url, max_age_hours, livecrawl_timeout)
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
        cached = livecrawl_manager.get_cached(url, max_age_hours)
        if cached:
            return cached

        timeout_seconds = min(livecrawl_timeout / 1000, MAX_TIMEOUT)

        # --- First attempt (from webfetch.ts pattern) ---
        result = await self._fetch_with_retry(url, timeout_seconds, attempt=0)

        livecrawl_manager.store(url, result)
        return result

    async def _fetch_with_retry(
        self, url: str, timeout_seconds: float, attempt: int, max_retries: int = 2
    ) -> CrawlResult:
        """Fetch URL with Cloudflare bypass retry (from webfetch.ts pattern)."""
        ua = _get_user_agent(attempt)

        try:
            response = httpx.get(
                url,
                headers={
                    "User-Agent": ua,
                    "Accept": "text/markdown;q=1.0, text/plain;q=0.8, text/html;q=0.7, */*;q=0.1",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
                timeout=timeout_seconds,
            )

            # --- Cloudflare bypass (from webfetch.ts isCloudflareChallenge pattern) ---
            if _is_cloudflare_challenge(response) and attempt < max_retries:
                return await self._fetch_with_retry(
                    url, timeout_seconds, attempt + 1, max_retries
                )

            response.raise_for_status()

            # --- Content-type validation (from webfetch.ts isTextualMime pattern) ---
            content_type = response.headers.get("content-type", "")
            if not _is_textual_content(content_type):
                return CrawlResult(
                    source="web",
                    title=url,
                    content=f"Unsupported content type: {content_type}",
                    url=url,
                    metadata={"status_code": response.status_code, "content_type": content_type},
                )

            # --- Response size limit (from webfetch.ts MAX_RESPONSE_BYTES) ---
            content_bytes = response.content[:MAX_RESPONSE_BYTES]
            html = content_bytes.decode("utf-8", errors="ignore")

            # --- Parse title ---
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else url

            # --- Convert to markdown (from webfetch.ts convertHTMLToMarkdown pattern) ---
            markdown = _html_to_markdown(html)

            # --- Fallback: plain text extraction if markdown is poor ---
            if len(markdown.strip()) < 50:
                markdown = _extract_text(html)

            result = CrawlResult(
                source="web",
                title=title,
                content=markdown[:MAX_CONTENT_LENGTH],
                url=url,
                metadata={
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "format": "markdown",
                    "user_agent": ua,
                },
            )
            return result

        except Exception as e:
            return CrawlResult(
                source="web",
                title=f"Error: {url}",
                content=str(e)[:500],
                url=url,
                metadata={"error": str(e)},
            )
