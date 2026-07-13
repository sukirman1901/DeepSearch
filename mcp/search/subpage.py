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

            root = ElementTree.fromstring(response.text)
            namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            urls = []
            for loc in root.findall(".//sm:loc", namespace):
                if loc.text:
                    urls.append(loc.text.strip())
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
                if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                    urls.append(full_url)
            return urls
        except Exception:
            return []