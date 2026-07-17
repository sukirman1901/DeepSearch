"""Generic documentation crawler for library docs sites."""

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from crawlers.base import CrawlResult
from search.docs_registry import LibraryConfig


class DocsCrawler:
    """Generic crawler that fetches documentation from library sites."""

    def __init__(self, config: LibraryConfig):
        self.config = config
        self.visited: set[str] = set()
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        """Crawl docs site and return relevant pages as CrawlResult objects."""
        results = []

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent}
        ) as client:
            for start_path in self.config.start_paths:
                if len(results) >= max_results:
                    break

                start_url = urljoin(self.config.docs_url, start_path)
                pages = await self._crawl_page(client, start_url, query)
                results.extend(pages)

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:max_results]

    async def _crawl_page(self, client, url, query, depth=0):
        """Recursively crawl a page and its links."""
        results = []

        if len(self.visited) >= self.config.max_pages:
            return results
        if url in self.visited:
            return results
        if self._should_exclude(url):
            return results

        self.visited.add(url)

        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return results

        soup = BeautifulSoup(response.text, 'html.parser')
        content, code_examples = self._extract_content(soup)

        if self._is_relevant(content, query):
            results.append(CrawlResult(
                source="docs",
                title=self._extract_title(soup),
                content=content,
                url=url,
                metadata={
                    "library_id": self.config.id,
                    "library_name": self.config.name,
                    "code_examples": code_examples,
                    "section": self._extract_section(url),
                    "crawled_at": datetime.now().isoformat(),
                },
                crawled_at=datetime.now(),
                category="code",
                score=self._calculate_relevance(content, query),
            ))

        if depth < 3:
            links = self._extract_links(soup, url)
            for link in links:
                if len(results) >= self.config.max_pages:
                    break
                sub_results = await self._crawl_page(client, link, query, depth + 1)
                results.extend(sub_results)

        return results

    def _should_exclude(self, url: str) -> bool:
        path = urlparse(url).path
        return any(path.startswith(p) for p in self.config.exclude_paths)

    def _extract_content(self, soup):
        """Extract main content and code examples from page."""
        content_elem = soup.select_one(self.config.content_selector)
        if not content_elem:
            content_elem = soup.find('main') or soup.find('article') or soup.body

        if not content_elem:
            return "", []

        code_examples = []
        for pre in content_elem.find_all('pre'):
            code = pre.get_text(strip=True)
            if code:
                code_examples.append(code)

        for elem in content_elem.find_all(['script', 'style', 'nav', 'footer']):
            elem.decompose()

        content = content_elem.get_text(separator='\n', strip=True)
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content, code_examples

    def _extract_title(self, soup):
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)
        return "Untitled"

    def _extract_section(self, url):
        parts = [p for p in urlparse(url).path.split('/') if p]
        return parts[0] if parts else ""

    def _extract_links(self, soup, base_url):
        links = []
        if self.config.nav_selector:
            for elem in soup.select(self.config.nav_selector):
                href = elem.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if urlparse(full_url).netloc == urlparse(base_url).netloc:
                        links.append(full_url)
        return links

    def _is_relevant(self, content, query):
        if not content:
            return False
        words = query.lower().split()
        content_lower = content.lower()
        matches = sum(1 for w in words if w in content_lower)
        return matches / len(words) >= 0.3

    def _calculate_relevance(self, content, query):
        if not content:
            return 0.0
        words = query.lower().split()
        content_lower = content.lower()
        matches = sum(1 for w in words if w in content_lower)
        return min(1.0, matches / len(words) * 1.5)
