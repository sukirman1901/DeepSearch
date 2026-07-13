"""Content extraction from URLs with batch processing and instruction filtering."""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dataclasses import dataclass, field


@dataclass
class ExtractedContent:
    """Extracted content from a single URL."""
    url: str
    title: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: str = ""
    error: str = ""  # Error message if extraction failed


@dataclass
class ExtractOutput:
    """Output of content extraction."""
    urls_processed: int = 0
    contents: list[ExtractedContent] = field(default_factory=list)
    extract_depth: str = "basic"
    instructions: str = ""


class ContentExtractor:
    """Extract structured content from URLs."""

    def __init__(self):
        self.client = httpx.Client(
            headers={"User-Agent": "Mozilla/5.0 (compatible; SearchEngine/1.0)"},
            follow_redirects=True,
            timeout=15.0,
        )

    def extract(
        self,
        urls: list[str],
        extract_depth: str = "basic",
        instructions: str = "",
    ) -> ExtractOutput:
        """
        Extract content from a list of URLs.

        Args:
            urls: List of URLs to extract from
            extract_depth: "basic" (text only) or "advanced" (text + metadata + links)
            instructions: What to extract (e.g., "product prices", "contact info")
        """
        contents = []
        instruction_keywords = self._parse_instructions(instructions)
        successful = 0

        for url in urls:
            try:
                content = self._extract_single(url, extract_depth, instruction_keywords)
                if content:
                    contents.append(content)
                    successful += 1
                else:
                    contents.append(ExtractedContent(url=url, error="No content extracted"))
            except Exception as e:
                contents.append(ExtractedContent(url=url, error=str(e)[:200]))

        return ExtractOutput(
            urls_processed=successful,
            contents=contents,
            extract_depth=extract_depth,
            instructions=instructions,
        )

    def _extract_single(
        self,
        url: str,
        extract_depth: str,
        instruction_keywords: list[str],
    ) -> ExtractedContent | None:
        """Extract content from a single URL."""
        response = self.client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Extract main text
        text = soup.get_text(separator="\n", strip=True)

        # Apply instruction filter
        if instruction_keywords:
            text = self._filter_by_instructions(text, instruction_keywords)
            if not text:
                return None

        result = ExtractedContent(url=url, title=title, text=text)

        # Advanced depth: extract links and metadata
        if extract_depth == "advanced":
            # Extract links
            for a_tag in soup.find_all("a", href=True):
                result.links.append(a_tag["href"])

            # Extract metadata
            for meta in soup.find_all("meta"):
                name = meta.get("name", meta.get("property", ""))
                content = meta.get("content", "")
                if name and content:
                    result.metadata[name] = content

        return result

    def _parse_instructions(self, instructions: str) -> list[str]:
        """Parse natural language instructions into keywords."""
        if not instructions:
            return []
        words = instructions.lower().split()
        return [w for w in words if len(w) > 2]

    def _filter_by_instructions(self, text: str, keywords: list[str]) -> str:
        """Filter text to only include paragraphs matching instruction keywords."""
        paragraphs = text.split("\n\n")
        matching = []
        for para in paragraphs:
            para_lower = para.lower()
            if any(kw in para_lower for kw in keywords):
                matching.append(para.strip())
        return "\n\n".join(matching) if matching else ""
