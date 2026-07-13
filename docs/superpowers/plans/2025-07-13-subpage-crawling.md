# Subpage Crawling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add subpage crawling to `web_crawl` tool — crawl a URL plus N of its subpages discovered via sitemap.xml and HTML links, with optional keyword filtering.

**Architecture:** New `SubpageDiscoverer` class finds subpage URLs (sitemap first, HTML links fallback). `WebCrawler.crawl()` gets `subpages` and `subpage_target` params — when subpages > 0, discovers and concurrently crawls subpages. MCP `web_crawl` tool passes new params through.

**Tech Stack:** Python 3.12, httpx, beautifulsoup4, xml.etree.ElementTree (stdlib), asyncio, existing livecrawl cache

---

### Task 1: Create SubpageDiscoverer class

**Files:**
- Create: `mcp/search/subpage.py`
- Test: `mcp/tests/test_search/test_subpage.py`

- [ ] **Step 1: Write the failing test for sitemap discovery**

Create `mcp/tests/test_search/test_subpage.py`:

```python
"""Tests for subpage discovery."""
import pytest
from unittest.mock import patch, MagicMock
from httpx import Response
from search.subpage import SubpageDiscoverer


@pytest.fixture
def discoverer():
    return SubpageDiscoverer()


SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
  <url><loc>https://example.com/page3</loc></url>
</urlset>"""


@patch("search.subpage.httpx.Client")
def test_discover_via_sitemap(mock_client_cls, discoverer):
    """Sitemap.xml returns URLs — verify they are parsed correctly."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    sitemap_response = MagicMock(spec=Response)
    sitemap_response.status_code = 200
    sitemap_response.text = SITEMAP_XML
    sitemap_response.raise_for_status = MagicMock()
    mock_client.get.return_value = sitemap_response

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert "https://example.com/page1" in urls
    assert "https://example.com/page2" in urls
    assert "https://example.com/page3" in urls
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_search/test_subpage.py::test_discover_via_sitemap -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'search.subpage'`

- [ ] **Step 3: Write minimal SubpageDiscoverer with sitemap parsing**

Create `mcp/search/subpage.py`:

```python
"""Subpage discovery via sitemap.xml and HTML links."""
import httpx
from bs4 import BeautifulSoup
from xml.etree import ElementTree
from urllib.parse import urljoin, urlparse


class SubpageDiscoverer:
    """Discover subpages of a domain via sitemap.xml and HTML links."""

    def __init__(self):
        self.client = httpx.Client(
            headers={"User-Agent": "Mozilla/5.0 (compatible; SearchEngine/1.0)"},
            follow_redirects=True,
            timeout=10.0,
        )

    def discover_subpages(
        self,
        url: str,
        max_count: int = 10,
        target_keyword: str = "",
    ) -> list[str]:
        """
        Discover subpage URLs for a domain.

        Flow:
        1. Fetch {url}/sitemap.xml -> parse <loc> tags -> collect URLs
        2. If fewer than max_count URLs found:
           a. Fetch main page HTML
           b. Parse <a href> tags -> filter internal links
           c. Merge with sitemap URLs
        3. If target_keyword provided:
           Filter URLs where keyword appears in URL path
        4. Deduplicate URLs (preserve order)
        5. Return first max_count URLs (excluding the main URL itself)
        """
        sitemap_urls = self._fetch_sitemap(url)

        if len(sitemap_urls) < max_count:
            html_urls = self._fetch_html_links(url)
            merged = sitemap_urls + [u for u in html_urls if u not in sitemap_urls]
        else:
            merged = sitemap_urls

        # Exclude main URL
        merged = [u for u in merged if u.rstrip("/") != url.rstrip("/")]

        # Filter by keyword
        if target_keyword:
            keyword = target_keyword.lower()
            merged = [u for u in merged if keyword in urlparse(u).path.lower()]

        # Deduplicate preserving order
        seen = set()
        deduped = []
        for u in merged:
            if u not in seen:
                seen.add(u)
                deduped.append(u)

        return deduped[:max_count]

    def _fetch_sitemap(self, url: str) -> list[str]:
        """Fetch sitemap.xml and parse URLs."""
        sitemap_url = url.rstrip("/") + "/sitemap.xml"
        try:
            response = self.client.get(sitemap_url)
            response.raise_for_status()

            # Parse XML — handle namespace
            root = ElementTree.fromstring(response.text)
            namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            urls = []
            for loc in root.findall(".//sm:loc", namespace):
                if loc.text:
                    urls.append(loc.text.strip())
            # Also try without namespace
            if not urls:
                for loc in root.findall(".//{*}loc"):
                    if loc.text:
                        urls.append(loc.text.strip())
            return urls
        except Exception:
            return []

    def _fetch_html_links(self, url: str) -> list[str]:
        """Fetch main page HTML and extract internal links."""
        try:
            response = self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            base_domain = urlparse(url).netloc

            urls = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                # Only internal links, same domain
                if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                    urls.append(full_url)
            return urls
        except Exception:
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_search/test_subpage.py::test_discover_via_sitemap -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mcp/search/subpage.py mcp/tests/test_search/test_subpage.py
git commit -m "feat(subpage): add SubpageDiscoverer with sitemap parsing"
```

---

### Task 2: Add HTML links fallback test

**Files:**
- Modify: `mcp/tests/test_search/test_subpage.py`

- [ ] **Step 1: Write the failing test for HTML fallback**

Append to `mcp/tests/test_search/test_subpage.py`:

```python
HTML_WITH_LINKS = """<html><body>
<a href="/page4">Page 4</a>
<a href="/page5">Page 5</a>
<a href="https://other.com/external">External</a>
<a href="/page6">Page 6</a>
</body></html>"""


@patch("search.subpage.httpx.Client")
def test_discover_falls_back_to_html(mock_client_cls, discoverer):
    """When sitemap returns 404, use HTML links from main page."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    sitemap_response = MagicMock(spec=Response)
    sitemap_response.status_code = 404
    sitemap_response.raise_for_status = MagicMock(side_effect=Exception("404"))

    html_response = MagicMock(spec=Response)
    html_response.status_code = 200
    html_response.text = HTML_WITH_LINKS
    html_response.raise_for_status = MagicMock()

    mock_client.get.side_effect = [sitemap_response, html_response]

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert "https://example.com/page4" in urls
    assert "https://example.com/page5" in urls
    assert "https://example.com/page6" in urls
    # External link excluded
    assert "https://other.com/external" not in urls
```

- [ ] **Step 2: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_search/test_subpage.py::test_discover_falls_back_to_html -v`
Expected: PASS (implementation already handles this)

- [ ] **Step 3: Commit**

```bash
git add mcp/tests/test_search/test_subpage.py
git commit -m "test(subpage): add HTML links fallback test"
```

---

### Task 3: Add keyword filtering test

**Files:**
- Modify: `mcp/tests/test_search/test_subpage.py`

- [ ] **Step 1: Write the failing test for keyword filtering**

Append to `mcp/tests/test_search/test_subpage.py`:

```python
SITEMAP_MIXED = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/docs/intro</loc></url>
  <url><loc>https://example.com/docs/guide</loc></url>
  <url><loc>https://example.com/blog/post1</loc></url>
  <url><loc>https://example.com/blog/post2</loc></url>
  <url><loc>https://example.com/about</loc></url>
</urlset>"""


@patch("search.subpage.httpx.Client")
def test_discover_filters_by_keyword(mock_client_cls, discoverer):
    """target_keyword filters URLs by path content."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    sitemap_response = MagicMock(spec=Response)
    sitemap_response.status_code = 200
    sitemap_response.text = SITEMAP_MIXED
    sitemap_response.raise_for_status = MagicMock()
    mock_client.get.return_value = sitemap_response

    urls = discoverer.discover_subpages(
        "https://example.com",
        max_count=10,
        target_keyword="docs",
    )

    assert all("docs" in u for u in urls)
    assert "https://example.com/docs/intro" in urls
    assert "https://example.com/docs/guide" in urls
    assert "https://example.com/blog/post1" not in urls
```

- [ ] **Step 2: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_search/test_subpage.py::test_discover_filters_by_keyword -v`
Expected: PASS (implementation already handles this)

- [ ] **Step 3: Commit**

```bash
git add mcp/tests/test_search/test_subpage.py
git commit -m "test(subpage): add keyword filtering test"
```

---

### Task 4: Add remaining discoverer tests (dedup, max_count, exclude main, merge)

**Files:**
- Modify: `mcp/tests/test_search/test_subpage.py`

- [ ] **Step 1: Write remaining tests**

Append to `mcp/tests/test_search/test_subpage.py`:

```python
SITEMAP_DUPS = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>"""


@patch("search.subpage.httpx.Client")
def test_discover_deduplicates(mock_client_cls, discoverer):
    """Duplicate URLs in sitemap are deduplicated."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    sitemap_response = MagicMock(spec=Response)
    sitemap_response.status_code = 200
    sitemap_response.text = SITEMAP_DUPS
    sitemap_response.raise_for_status = MagicMock()
    mock_client.get.return_value = sitemap_response

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert urls.count("https://example.com/page1") == 1
    assert len(urls) == 2


SITEMAP_MANY = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/p1</loc></url>
  <url><loc>https://example.com/p2</loc></url>
  <url><loc>https://example.com/p3</loc></url>
  <url><loc>https://example.com/p4</loc></url>
  <url><loc>https://example.com/p5</loc></url>
</urlset>"""


@patch("search.subpage.httpx.Client")
def test_discover_respects_max_count(mock_client_cls, discoverer):
    """max_count limits the number of returned URLs."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    sitemap_response = MagicMock(spec=Response)
    sitemap_response.status_code = 200
    sitemap_response.text = SITEMAP_MANY
    sitemap_response.raise_for_status = MagicMock()
    mock_client.get.return_value = sitemap_response

    urls = discoverer.discover_subpages("https://example.com", max_count=3)

    assert len(urls) == 3


SITEMAP_WITH_MAIN = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com</loc></url>
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>"""


@patch("search.subpage.httpx.Client")
def test_discover_excludes_main_url(mock_client_cls, discoverer):
    """Main URL itself is not included in subpage list."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    sitemap_response = MagicMock(spec=Response)
    sitemap_response.status_code = 200
    sitemap_response.text = SITEMAP_WITH_MAIN
    sitemap_response.raise_for_status = MagicMock()
    mock_client.get.return_value = sitemap_response

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert "https://example.com" not in urls
    assert "https://example.com/" not in urls
    assert len(urls) == 2


@patch("search.subpage.httpx.Client")
def test_discover_empty_results(mock_client_cls, discoverer):
    """Both sitemap and HTML return nothing -> empty list."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    sitemap_response = MagicMock(spec=Response)
    sitemap_response.status_code = 404
    sitemap_response.raise_for_status = MagicMock(side_effect=Exception("404"))

    html_response = MagicMock(spec=Response)
    html_response.status_code = 200
    html_response.text = "<html><body></body></html>"
    html_response.raise_for_status = MagicMock()

    mock_client.get.side_effect = [sitemap_response, html_response]

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert urls == []


SITEMAP_PARTIAL = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/s1</loc></url>
  <url><loc>https://example.com/s2</loc></url>
  <url><loc>https://example.com/s3</loc></url>
</urlset>"""

HTML_EXTRA_LINKS = """<html><body>
<a href="/h1">H1</a>
<a href="/h2">H2</a>
<a href="/s1">S1 dup</a>
</body></html>"""


@patch("search.subpage.httpx.Client")
def test_discover_merges_sitemap_and_html(mock_client_cls, discoverer):
    """Sitemap has 3 URLs, HTML has 2 new + 1 dup -> merged has 5."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    sitemap_response = MagicMock(spec=Response)
    sitemap_response.status_code = 200
    sitemap_response.text = SITEMAP_PARTIAL
    sitemap_response.raise_for_status = MagicMock()

    html_response = MagicMock(spec=Response)
    html_response.status_code = 200
    html_response.text = HTML_EXTRA_LINKS
    html_response.raise_for_status = MagicMock()

    mock_client.get.side_effect = [sitemap_response, html_response]

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    # s1, s2, s3 from sitemap + h1, h2 from HTML (s1 is dup)
    assert "https://example.com/s1" in urls
    assert "https://example.com/s2" in urls
    assert "https://example.com/s3" in urls
    assert "https://example.com/h1" in urls
    assert "https://example.com/h2" in urls
    assert urls.count("https://example.com/s1") == 1
```

- [ ] **Step 2: Run all subpage tests to verify they pass**

Run: `.venv/bin/python3 -m pytest tests/test_search/test_subpage.py -v`
Expected: 8 passed

- [ ] **Step 3: Commit**

```bash
git add mcp/tests/test_search/test_subpage.py
git commit -m "test(subpage): add dedup, max_count, exclude main, merge tests"
```

---

### Task 5: Extend WebCrawler with subpages parameter

**Files:**
- Modify: `mcp/crawlers/web_crawler.py:16-82`
- Test: `mcp/tests/test_crawlers/test_web_crawler.py`

- [ ] **Step 1: Write failing tests for WebCrawler subpage behavior**

Create `mcp/tests/test_crawlers/test_web_crawler.py`:

```python
"""Tests for WebCrawler subpage crawling."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from crawlers.web_crawler import WebCrawler
from crawlers.base import CrawlResult
from datetime import datetime


@pytest.fixture
def crawler():
    return WebCrawler()


def test_crawl_with_zero_subpages_backward_compatible(crawler):
    """subpages=0 returns single result — backward compatible."""
    with patch.object(crawler, "_crawl_single") as mock_crawl:
        mock_crawl.return_value = CrawlResult(
            source="web",
            title="Main Page",
            content="content",
            url="https://example.com",
            crawled_at=datetime.now(),
        )
        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            crawler.crawl("https://example.com", subpages=0)
        )
        assert len(results) == 1
        assert results[0].title == "Main Page"


@pytest.mark.asyncio
async def test_crawl_with_subpages_returns_multiple(crawler):
    """subpages=3 returns main + up to 3 subpages."""
    main_result = CrawlResult(
        source="web", title="Main", content="main content",
        url="https://example.com", crawled_at=datetime.now(),
    )
    sub_result_1 = CrawlResult(
        source="web", title="Sub1", content="sub content 1",
        url="https://example.com/page1", crawled_at=datetime.now(),
    )
    sub_result_2 = CrawlResult(
        source="web", title="Sub2", content="sub content 2",
        url="https://example.com/page2", crawled_at=datetime.now(),
    )

    with patch.object(crawler, "_crawl_single", new_callable=AsyncMock) as mock_crawl, \
         patch("crawlers.web_crawler.SubpageDiscoverer") as mock_discoverer_cls:
        mock_discoverer = MagicMock()
        mock_discoverer_cls.return_value = mock_discoverer
        mock_discoverer.discover_subpages.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]
        mock_crawl.side_effect = [main_result, sub_result_1, sub_result_2]

        results = await crawler.crawl(
            "https://example.com",
            subpages=3,
        )

        assert len(results) == 3
        assert results[0].title == "Main"
        assert results[1].title == "Sub1"
        assert results[2].title == "Sub2"


@pytest.mark.asyncio
async def test_crawl_subpage_errors_dont_fail_all(crawler):
    """One subpage errors — others still returned."""
    main_result = CrawlResult(
        source="web", title="Main", content="main",
        url="https://example.com", crawled_at=datetime.now(),
    )
    sub_ok = CrawlResult(
        source="web", title="OK", content="ok",
        url="https://example.com/ok", crawled_at=datetime.now(),
    )
    sub_error = CrawlResult(
        source="web", title="Error: https://example.com/bad",
        content="connection error", url="https://example.com/bad",
        metadata={"error": "connection error"}, crawled_at=datetime.now(),
    )

    with patch.object(crawler, "_crawl_single", new_callable=AsyncMock) as mock_crawl, \
         patch("crawlers.web_crawler.SubpageDiscoverer") as mock_discoverer_cls:
        mock_discoverer = MagicMock()
        mock_discoverer_cls.return_value = mock_discoverer
        mock_discoverer.discover_subpages.return_value = [
            "https://example.com/bad",
            "https://example.com/ok",
        ]
        mock_crawl.side_effect = [main_result, sub_error, sub_ok]

        results = await crawler.crawl("https://example.com", subpages=2)

        assert len(results) == 3
        assert results[0].title == "Main"
        # Error result is included but doesn't fail everything
        assert "Error" in results[1].title
        assert results[2].title == "OK"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m pytest tests/test_crawlers/test_web_crawler.py -v`
Expected: FAIL — `WebCrawler.crawl()` doesn't have `subpages` param, `_crawl_single` doesn't exist

- [ ] **Step 3: Refactor WebCrawler to support subpages**

Rewrite `mcp/crawlers/web_crawler.py`:

```python
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
        self.subpage_discoverer = SubpageDiscoverer()

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
        # Crawl main URL
        main_result = await self._crawl_single(
            url, max_age_hours, livecrawl_timeout
        )
        results = [main_result]

        # Crawl subpages if requested
        if subpages > 0:
            subpage_urls = self.subpage_discoverer.discover_subpages(
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
        # Check cache first
        cached = livecrawl_manager.get_cached(url, max_age_hours)
        if cached:
            return cached

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

            return result
        except Exception as e:
            return CrawlResult(
                source="web",
                title=f"Error: {url}",
                content=str(e),
                url=url,
                metadata={"error": str(e)},
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m pytest tests/test_crawlers/test_web_crawler.py -v`
Expected: 3 passed

- [ ] **Step 5: Run full test suite to verify backward compatibility**

Run: `.venv/bin/python3 -m pytest tests/ -q`
Expected: All tests pass (79 original + 8 subpage + 3 webcrawler = 90)

- [ ] **Step 6: Commit**

```bash
git add mcp/crawlers/web_crawler.py mcp/tests/test_crawlers/test_web_crawler.py
git commit -m "feat(web-crawler): add subpage crawling support"
```

---

### Task 6: Update web_crawl MCP tool with new parameters

**Files:**
- Modify: `mcp/server.py:250-272`

- [ ] **Step 1: Update the web_crawl tool**

Edit `mcp/server.py` lines 250-272, replace the `web_crawl` function with:

```python
@mcp.tool()
async def web_crawl(
    url: str,
    max_age_hours: int = -1,
    livecrawl_timeout: int = 10000,
    subpages: int = 0,
    subpage_target: str = "",
) -> str:
    """
    Crawl a URL and extract content, optionally crawling subpages.

    Args:
        url: URL to crawl
        max_age_hours: Cache freshness control
            - 24: Use cache if <24 hours old
            - 1: Use cache if <1 hour old
            - 0: Always livecrawl
            - -1: Cache only (default)
        livecrawl_timeout: Timeout in ms for livecrawl (default 10000)
        subpages: Number of subpages to also crawl (default 0 = none)
        subpage_target: Keyword to filter subpages (e.g., "docs", "blog")
    """
    results = await web_crawler.crawl(
        url,
        max_age_hours=max_age_hours,
        livecrawl_timeout=livecrawl_timeout,
        subpages=subpages,
        subpage_target=subpage_target,
    )
    if results:
        for result in results:
            engine.vector_store.add(result)
        if len(results) == 1:
            return f"Crawled and indexed: {results[0].title}"
        titles = [r.title for r in results]
        return f"Crawled and indexed {len(results)} pages:\n" + "\n".join(
            f"  - {t}" for t in titles
        )
    return "Failed to crawl URL."
```

- [ ] **Step 2: Verify server imports and tool registered**

Run: `.venv/bin/python3 -c "from server import mcp; print('OK'); print('web_crawl' in mcp._tool_manager._tools)"`
Expected: `OK` then `True`

- [ ] **Step 3: Run full test suite**

Run: `.venv/bin/python3 -m pytest tests/ -q`
Expected: 90 passed

- [ ] **Step 4: Commit**

```bash
git add mcp/server.py
git commit -m "feat(server): add subpages and subpage_target params to web_crawl tool"
```

---

### Task 7: Final verification and push

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite one final time**

Run: `.venv/bin/python3 -m pytest tests/ -v`
Expected: 90 passed

- [ ] **Step 2: Verify all 13 MCP tools registered**

Run:
```python
.venv/bin/python3 -c "
from server import mcp
tools = sorted(mcp._tool_manager._tools.keys())
print(f'{len(tools)} tools:')
for t in tools:
    print(f'  - {t}')
"
```
Expected: 13 tools including `web_crawl`

- [ ] **Step 3: Push to GitHub**

```bash
git push origin main
```
