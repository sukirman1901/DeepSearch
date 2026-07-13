# Subpage Crawling Design Spec

## Overview

Add subpage crawling capability to the DeepSearch MCP server. When a user crawls a URL, they can optionally request that N subpages of that domain also be crawled. Inspired by Exa's Contents API subpage crawling feature.

## Motivation

Current `web_crawl` tool only crawls a single URL. For documentation sites, wikis, and research tasks, users often need to crawl a domain plus its subpages (e.g., crawl `docs.example.com` plus 10 linked doc pages). Today this requires N separate `web_crawl` calls — slow and tedious.

Subpage crawling lets users do this in one call: `web_crawl(url, subpages=10, subpage_target="docs")`.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Subpage discovery | Sitemap-first, HTML links fallback | Sitemaps give comprehensive coverage; HTML links catch missing pages |
| Scope control | Max subpages count | Simple, predictable, user-friendly |
| Tool integration | Extend existing `web_crawl` tool | One tool for all web crawling, clean API |
| Subpage filtering | Keyword filter on URL/title | Lets users target specific sections (docs, blog, etc.) |
| Discovery approach | Sequential (sitemap → HTML fallback) | Only one extra fetch when sitemap missing |

## Architecture

### New Module: `mcp/search/subpage.py`

```python
class SubpageDiscoverer:
    """Discover subpages of a domain via sitemap.xml and HTML links."""

    def __init__(self):
        self.client = httpx.Client(...)

    async def discover_subpages(
        self,
        url: str,
        max_count: int = 10,
        target_keyword: str = "",
    ) -> list[str]:
        """
        Discover subpage URLs for a domain.

        Flow:
        1. Fetch {url}/sitemap.xml → parse <loc> tags → collect URLs
        2. If fewer than max_count URLs found:
           a. Fetch main page HTML
           b. Parse <a href> tags → filter internal links
           c. Merge with sitemap URLs
        3. If target_keyword provided:
           Filter URLs where keyword appears in URL path
        4. Deduplicate URLs (preserve order)
        5. Return first max_count URLs (excluding the main URL itself)

        Args:
            url: Base URL to discover subpages for
            max_count: Maximum number of subpage URLs to return
            target_keyword: Optional keyword to filter subpages
                (matched against URL path, case-insensitive)

        Returns:
            List of subpage URLs (max_count items, excludes main URL)
        """
```

### Modified: `mcp/crawlers/web_crawler.py`

`WebCrawler.crawl()` gets two new parameters:

```python
async def crawl(
    self,
    url: str,
    max_results: int = 1,
    max_age_hours: Optional[int] = None,
    livecrawl_timeout: int = 10000,
    subpages: int = 0,           # NEW: number of subpages to crawl
    subpage_target: str = "",    # NEW: keyword filter for subpages
) -> list[CrawlResult]:
```

**Behavior when `subpages > 0`:**

1. Crawl main URL (existing behavior) → `main_result`
2. Call `SubpageDiscoverer.discover_subpages(url, max_count=subpages, target_keyword=subpage_target)`
3. Crawl each discovered subpage URL concurrently via `asyncio.gather`
   - Each subpage crawl reuses the existing crawl logic (cache check, fetch, parse, store)
   - Errors on individual subpages don't fail the whole operation — return error CrawlResult for that page
4. Return `[main_result, subpage_result_1, subpage_result_2, ...]`

**Backward compatibility:** When `subpages=0` (default), behavior is unchanged — returns single result.

### Modified: `mcp/server.py`

`web_crawl` MCP tool gets two new parameters:

```python
@mcp.tool()
async def web_crawl(
    url: str,
    max_age_hours: int = 24,
    subpages: int = 0,           # NEW
    subpage_target: str = "",    # NEW
) -> str:
    """
    Crawl a URL and extract content.

    Args:
        url: URL to crawl
        max_age_hours: Cache freshness control (default 24)
        subpages: Number of subpages to also crawl (default 0 = none)
        subpage_target: Keyword to filter subpages (e.g., "docs", "blog")
    """
```

## Data Flow

```
web_crawl(url="https://docs.example.com", subpages=10, subpage_target="api")
  ↓
WebCrawler.crawl(url, subpages=10, subpage_target="api")
  ↓
1. Crawl main URL → main_result (with cache check)
  ↓
2. SubpageDiscoverer.discover_subpages(url, max_count=10, target="api")
   ├─ GET https://docs.example.com/sitemap.xml
   ├─ Parse XML <loc> tags → [url1, url2, url3, ...]
   ├─ If < 10 URLs found:
   │   └─ GET main page HTML → parse <a href> → merge internal links
   ├─ Filter URLs containing "api" in path
   ├─ Deduplicate, exclude main URL
   └─ Return top 10 subpage URLs
  ↓
3. asyncio.gather(*[crawl_subpage(u) for u in subpage_urls])
   ├─ Each crawl_subpage checks livecrawl cache
   ├─ Fetches if cache miss
   └─ Stores in cache
  ↓
4. Return [main_result, sub1, sub2, ...] (up to 11 results)
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Sitemap.xml returns 404 | Skip sitemap, use HTML links only |
| Sitemap.xml malformed XML | Skip sitemap, use HTML links only |
| Main page fetch fails | Return error CrawlResult, skip subpage discovery |
| Individual subpage fetch fails | Return error CrawlResult for that page, continue others |
| No subpages discovered | Return just `[main_result]` |
| subpages=0 | Existing behavior, return `[main_result]` |

## Subpage Filtering Logic

When `subpage_target` is provided:
- Convert both URL path and target to lowercase
- Match if `target_keyword` appears anywhere in the URL path
- Example: `target="docs"` matches `docs.example.com/guide` and `example.com/docs/intro` but not `example.com/blog/post`

When `subpage_target` is empty:
- No filtering, return all discovered subpage URLs up to `max_count`

## Testing Strategy

### Unit Tests: `SubpageDiscoverer` (`tests/test_search/test_subpage.py`)

1. `test_discover_via_sitemap` — Mock sitemap.xml response, verify URLs parsed correctly
2. `test_discover_falls_back_to_html` — Mock 404 on sitemap, verify HTML links used
3. `test_discover_filters_by_keyword` — Mock sitemap with mixed URLs, verify keyword filter works
4. `test_discover_deduplicates` — Mock sitemap with duplicate URLs, verify dedup
5. `test_discover_excludes_main_url` — Verify main URL not in subpage list
6. `test_discover_respects_max_count` — Mock 20 URLs, max_count=5, verify only 5 returned
7. `test_discover_empty_sitemap_and_no_links` — Both sources empty, return empty list
8. `test_discover_merges_sitemap_and_html` — Sitemap has 3 URLs, HTML has 5 more, verify all 8 merged

### Unit Tests: `WebCrawler` with subpages (`tests/test_crawlers/test_web_crawler.py`)

9. `test_crawl_with_zero_subpages_backward_compatible` — subpages=0 returns single result
10. `test_crawl_with_subpages_returns_multiple` — subpages=3 returns main + up to 3 subpages
11. `test_crawl_subpage_errors_dont_fail_all` — One subpage errors, others still returned

### Test mocks
- Mock `httpx.Client.get` for sitemap.xml and HTML responses
- Mock `SubpageDiscoverer` in WebCrawler tests to isolate crawl logic
- Use sample HTML and sitemap XML as test fixtures

## Dependencies

No new packages required. Uses:
- `httpx` (already installed) — for fetching sitemap.xml and HTML
- `beautifulsoup4` (already installed) — for parsing HTML links
- `xml.etree.ElementTree` (stdlib) — for parsing sitemap XML
- `asyncio` (stdlib) — for concurrent subpage crawling
- `livecrawl_manager` (existing) — for caching subpage results

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `mcp/search/subpage.py` | CREATE | SubpageDiscoverer class |
| `mcp/crawlers/web_crawler.py` | MODIFY | Add subpages + subpage_target params |
| `mcp/server.py` | MODIFY | Add subpages + subpage_target params to web_crawl tool |
| `mcp/tests/test_search/test_subpage.py` | CREATE | 8 unit tests for SubpageDiscoverer |
| `mcp/tests/test_crawlers/test_web_crawler.py` | MODIFY/CREATE | 3 tests for WebCrawler subpage behavior |

## Success Criteria

- `web_crawl(url, subpages=10)` crawls main URL + up to 10 subpages in one call
- `web_crawl(url, subpages=10, subpage_target="docs")` only crawls subpages with "docs" in URL
- `web_crawl(url)` (no subpages param) behaves exactly as before — backward compatible
- All existing 79 tests still pass
- 11 new tests pass
- Total: 90 tests passing
