"""Site mapping via BFS crawl with depth control and natural language instructions."""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from collections import deque


@dataclass
class SiteMapResult:
    """Result from site mapping."""
    url: str
    title: str = ""
    depth: int = 0
    links_found: int = 0


@dataclass
class SiteMapOutput:
    """Output of site mapping."""
    root_url: str
    pages: list[SiteMapResult] = field(default_factory=list)
    total_pages: int = 0
    max_depth_reached: int = 0


class SiteMapper:
    """Map a website structure using BFS crawl."""

    def __init__(self):
        self.client = httpx.Client(
            headers={"User-Agent": "Mozilla/5.0 (compatible; SearchEngine/1.0)"},
            follow_redirects=True,
            timeout=10.0,
        )

    def map_site(
        self,
        url: str,
        max_depth: int = 2,
        instructions: str = "",
        max_pages: int = 50,
    ) -> SiteMapOutput:
        """
        BFS crawl a website to map its structure.

        Args:
            url: Starting URL
            max_depth: How many levels deep to crawl (default 2)
            instructions: Natural language instructions to filter pages
            max_pages: Maximum pages to crawl (default 50)
        """
        base_domain = urlparse(url).netloc
        visited = set()
        queue: deque[tuple[str, int]] = deque([(url, 0)])
        pages = []
        max_depth_reached = 0

        # Parse instructions into keywords for filtering
        instruction_keywords = self._parse_instructions(instructions)

        while queue and len(pages) < max_pages:
            current_url, depth = queue.popleft()

            if current_url in visited or depth > max_depth:
                continue
            visited.add(current_url)

            try:
                response = self.client.get(current_url)
                response.raise_for_status()
            except Exception:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else ""

            # Check instruction filter
            if instruction_keywords and not self._matches_instructions(
                current_url, title, response.text, instruction_keywords
            ):
                continue

            # Extract links
            links = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(current_url, href)
                parsed = urlparse(full_url)
                if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                    links.append(full_url)

            pages.append(SiteMapResult(
                url=current_url,
                title=title,
                depth=depth,
                links_found=len(links),
            ))
            max_depth_reached = max(max_depth_reached, depth)

            # Add unvisited links to queue
            for link in links:
                if link not in visited and depth + 1 <= max_depth:
                    queue.append((link, depth + 1))

        return SiteMapOutput(
            root_url=url,
            pages=pages,
            total_pages=len(pages),
            max_depth_reached=max_depth_reached,
        )

    def _parse_instructions(self, instructions: str) -> list[str]:
        """Parse natural language instructions into keywords."""
        if not instructions:
            return []
        # Simple keyword extraction: split by spaces, filter short words
        words = instructions.lower().split()
        return [w for w in words if len(w) > 2]

    def _matches_instructions(
        self, url: str, title: str, content: str, keywords: list[str]
    ) -> bool:
        """Check if page matches instruction keywords."""
        if not keywords:
            return True  # No filter = match all
        text = f"{url} {title} {content[:2000]}".lower()
        return any(kw in text for kw in keywords)
