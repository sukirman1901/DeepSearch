# Docs Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `mode="docs"` to the DeepSearch `search` tool that fetches programming documentation from official library sites.

**Architecture:** Config-driven generic docs crawler → ChromaDB storage → semantic search → token-budget output. Library definitions in JSON config file, generic crawler with CSS selectors per library.

**Tech Stack:** Python, httpx, BeautifulSoup4, ChromaDB, sentence-transformers, FastMCP

**Spec:** `docs/superpowers/specs/2026-07-17-docs-search-design.md`

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `mcp/search/docs_registry.py` | Library config loader/validator |
| CREATE | `mcp/search/docs_crawler.py` | Generic docs crawler |
| CREATE | `mcp/search/docs_engine.py` | Docs search orchestrator |
| CREATE | `mcp/data/docs_library_registry.json` | Library definitions |
| MODIFY | `mcp/server.py:43-75` | Add `mode="docs"` + params |
| MODIFY | `mcp/search/engine.py` | Import & init DocsSearchEngine |
| MODIFY | `mcp/db/vector_store.py` | Add `docs_search` collection |
| CREATE | `mcp/tests/test_docs_registry.py` | Registry tests |
| CREATE | `mcp/tests/test_docs_crawler.py` | Crawler tests |
| CREATE | `mcp/tests/test_docs_engine.py` | Engine tests |

---

## Task 1: Library Registry

**Files:**
- Create: `mcp/data/docs_library_registry.json`
- Create: `mcp/search/docs_registry.py`
- Create: `mcp/tests/test_docs_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# mcp/tests/test_docs_registry.py
import pytest
import json
import tempfile
import os
from search.docs_registry import LibraryRegistry, LibraryConfig

def test_load_registry_from_file():
    """Test loading registry from JSON file."""
    config = {
        "version": "1.0",
        "libraries": {
            "react": {
                "name": "React",
                "docs_url": "https://react.dev",
                "start_paths": ["/reference", "/learn"],
                "content_selector": "main",
                "nav_selector": "aside a",
                "exclude_paths": ["/blog"],
                "include_paths": [],
                "max_pages": 200,
                "ttl_hours": 168
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        registry = LibraryRegistry(temp_path)
        lib = registry.get_library("react")
        
        assert lib is not None
        assert lib.id == "react"
        assert lib.name == "React"
        assert lib.docs_url == "https://react.dev"
        assert lib.start_paths == ["/reference", "/learn"]
        assert lib.content_selector == "main"
        assert lib.nav_selector == "aside a"
        assert lib.exclude_paths == ["/blog"]
        assert lib.max_pages == 200
        assert lib.ttl_hours == 168
    finally:
        os.unlink(temp_path)

def test_list_libraries():
    """Test listing all available libraries."""
    config = {
        "version": "1.0",
        "libraries": {
            "react": {"name": "React", "docs_url": "https://react.dev", "start_paths": []},
            "nextjs": {"name": "Next.js", "docs_url": "https://nextjs.org/docs", "start_paths": []}
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        registry = LibraryRegistry(temp_path)
        libs = registry.list_libraries()
        
        assert "react" in libs
        assert "nextjs" in libs
        assert len(libs) == 2
    finally:
        os.unlink(temp_path)

def test_get_library_not_found():
    """Test getting non-existent library returns None."""
    config = {"version": "1.0", "libraries": {}}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        registry = LibraryRegistry(temp_path)
        lib = registry.get_library("vue")
        
        assert lib is None
    finally:
        os.unlink(temp_path)

def test_validate_library_config():
    """Test that invalid configs raise errors."""
    config = {
        "version": "1.0",
        "libraries": {
            "bad-lib": {
                "name": "Bad Lib"
                # Missing required fields
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="docs_url"):
            LibraryRegistry(temp_path)
    finally:
        os.unlink(temp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/aaa/Documents/Developer/DeepSearch/mcp && python -m pytest tests/test_docs_registry.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'search.docs_registry'"

- [ ] **Step 3: Write minimal implementation**

```python
# mcp/search/docs_registry.py
"""Library registry for docs search - loads and validates library configs."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LibraryConfig:
    """Configuration for a single library's documentation."""
    id: str
    name: str
    docs_url: str
    start_paths: list[str]
    content_selector: str = "main"
    nav_selector: str = ""
    exclude_paths: list[str] = field(default_factory=list)
    include_paths: list[str] = field(default_factory=list)
    version_url_pattern: str = ""
    max_pages: int = 200
    ttl_hours: int = 168
    language: str = "en"


REQUIRED_FIELDS = ["name", "docs_url", "start_paths"]


class LibraryRegistry:
    """Loads and manages library configurations from JSON file."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.libraries: dict[str, LibraryConfig] = {}
        self._load()
    
    def _load(self):
        """Load and validate library configs from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Registry config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        
        libs = data.get("libraries", {})
        
        for lib_id, lib_data in libs.items():
            # Validate required fields
            missing = [field for field in REQUIRED_FIELDS if field not in lib_data]
            if missing:
                raise ValueError(
                    f"Library '{lib_id}' missing required fields: {', '.join(missing)}"
                )
            
            # Parse config
            config = LibraryConfig(
                id=lib_id,
                name=lib_data["name"],
                docs_url=lib_data["docs_url"],
                start_paths=lib_data.get("start_paths", []),
                content_selector=lib_data.get("content_selector", "main"),
                nav_selector=lib_data.get("nav_selector", ""),
                exclude_paths=lib_data.get("exclude_paths", []),
                include_paths=lib_data.get("include_paths", []),
                version_url_pattern=lib_data.get("version_url_pattern", ""),
                max_pages=lib_data.get("max_pages", 200),
                ttl_hours=lib_data.get("ttl_hours", 168),
                language=lib_data.get("language", "en"),
            )
            
            self.libraries[lib_id] = config
    
    def get_library(self, lib_id: str) -> Optional[LibraryConfig]:
        """Get library config by ID. Returns None if not found."""
        return self.libraries.get(lib_id)
    
    def list_libraries(self) -> list[str]:
        """List all available library IDs."""
        return list(self.libraries.keys())
    
    def get_all(self) -> dict[str, LibraryConfig]:
        """Get all library configs."""
        return self.libraries.copy()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/aaa/Documents/Developer/DeepSearch/mcp && python -m pytest tests/test_docs_registry.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Create initial library registry JSON**

```json
// mcp/data/docs_library_registry.json
{
  "version": "1.0",
  "libraries": {
    "react": {
      "name": "React",
      "docs_url": "https://react.dev",
      "start_paths": ["/reference", "/learn"],
      "content_selector": "main",
      "nav_selector": "aside a",
      "exclude_paths": ["/blog", "/community", "/versions", "/style-guide"],
      "include_paths": [],
      "max_pages": 200,
      "ttl_hours": 168
    },
    "nextjs": {
      "name": "Next.js",
      "docs_url": "https://nextjs.org/docs",
      "start_paths": ["/app", "/pages", "/api-reference"],
      "content_selector": "main",
      "nav_selector": "nav a",
      "exclude_paths": ["/blog", "/learn"],
      "include_paths": [],
      "max_pages": 300,
      "ttl_hours": 168
    },
    "vue": {
      "name": "Vue.js",
      "docs_url": "https://vuejs.org",
      "start_paths": ["/guide", "/api"],
      "content_selector": ".content",
      "nav_selector": ".sidebar a",
      "exclude_paths": ["/blog", "/partners", "/ecosystem"],
      "include_paths": [],
      "max_pages": 150,
      "ttl_hours": 168
    },
    "supabase": {
      "name": "Supabase",
      "docs_url": "https://supabase.com/docs",
      "start_paths": ["/guides/getting-started", "/reference"],
      "content_selector": "article",
      "nav_selector": "nav a",
      "exclude_paths": ["/blog", "/pricing"],
      "include_paths": [],
      "max_pages": 250,
      "ttl_hours": 168
    },
    "prisma": {
      "name": "Prisma",
      "docs_url": "https://www.prisma.io/docs",
      "start_paths": ["/orm", "/orm/more"],
      "content_selector": "main",
      "nav_selector": "nav a",
      "exclude_paths": ["/blog", "/community"],
      "include_paths": [],
      "max_pages": 200,
      "ttl_hours": 168
    }
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add mcp/search/docs_registry.py mcp/data/docs_library_registry.json mcp/tests/test_docs_registry.py
git commit -m "feat(docs): add library registry with config loader and 5 initial libraries"
```

---

## Task 2: Docs Crawler

**Files:**
- Create: `mcp/search/docs_crawler.py`
- Create: `mcp/tests/test_docs_crawler.py`

- [ ] **Step 1: Write the failing test**

```python
# mcp/tests/test_docs_crawler.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from search.docs_crawler import DocsCrawler, DocsPage
from search.docs_registry import LibraryConfig
from crawlers.base import CrawlResult

@pytest.fixture
def react_config():
    return LibraryConfig(
        id="react",
        name="React",
        docs_url="https://react.dev",
        start_paths=["/reference"],
        content_selector="main",
        nav_selector="aside a",
        exclude_paths=["/blog"],
        include_paths=[],
        max_pages=10,
        ttl_hours=168
    )

@pytest.mark.asyncio
async def test_crawl_returns_crawl_results(react_config):
    """Test that crawl returns CrawlResult objects."""
    crawler = DocsCrawler(react_config)
    
    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <body>
        <main>
            <h1>useState</h1>
            <p>The useState Hook lets you add state to functional components.</p>
            <pre><code>const [count, setCount] = useState(0);</code></pre>
        </main>
        <aside>
            <a href="/reference/react/useState">useState</a>
            <a href="/reference/react/useEffect">useEffect</a>
        </aside>
    </body>
    </html>
    """
    mock_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        results = await crawler.crawl("useState", max_results=5)
        
        assert len(results) > 0
        assert isinstance(results[0], CrawlResult)
        assert results[0].source == "docs"
        assert results[0].metadata.get("library_id") == "react"

@pytest.mark.asyncio
async def test_crawl_extracts_code_blocks(react_config):
    """Test that code blocks are extracted."""
    crawler = DocsCrawler(react_config)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <body>
        <main>
            <h1>Example</h1>
            <pre><code>import { useState } from 'react';

function Counter() {
    const [count, setCount] = useState(0);
    return &lt;button onClick={() => setCount(count + 1)}&gt;{count}&lt;/button&gt;;
}</code></pre>
        </main>
    </body>
    </html>
    """
    mock_response.raise_for_status = MagicMock()
    
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        results = await crawler.crawl("counter example", max_results=5)
        
        # Check that code was extracted in metadata
        assert len(results) > 0
        code_examples = results[0].metadata.get("code_examples", [])
        assert len(code_examples) > 0
        assert "useState" in code_examples[0]

def test_should_exclude_path(react_config):
    """Test that excluded paths are filtered out."""
    crawler = DocsCrawler(react_config)
    
    assert crawler._should_exclude("/blog/my-post") == True
    assert crawler._should_exclude("/reference/react/useState") == False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/aaa/Documents/Developer/DeepSearch/mcp && python -m pytest tests/test_docs_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'search.docs_crawler'"

- [ ] **Step 3: Write minimal implementation**

```python
# mcp/search/docs_crawler.py
"""Generic documentation crawler for library docs sites."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from crawlers.base import CrawlResult
from search.docs_registry import LibraryConfig


class DocsPage:
    """Represents a single documentation page."""
    
    def __init__(
        self,
        library_id: str,
        title: str,
        url: str,
        content: str,
        code_examples: list[str] = None,
        section: str = "",
        version: str = "",
    ):
        self.library_id = library_id
        self.title = title
        self.url = url
        self.content = content
        self.code_examples = code_examples or []
        self.section = section
        self.version = version


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
        """
        Crawl docs site and return relevant pages as CrawlResult objects.
        
        Args:
            query: Search query to find relevant pages
            max_results: Maximum number of results to return
            
        Returns:
            list[CrawlResult]: Crawled documentation pages
        """
        results = []
        
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent}
        ) as client:
            # Crawl start paths
            for start_path in self.config.start_paths:
                if len(results) >= max_results:
                    break
                
                start_url = urljoin(self.config.docs_url, start_path)
                pages = await self._crawl_page(client, start_url, query)
                results.extend(pages)
                
                if len(results) >= max_results:
                    break
        
        # Sort by relevance and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:max_results]
    
    async def _crawl_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        query: str,
        depth: int = 0,
    ) -> list[CrawlResult]:
        """Recursively crawl a page and its links."""
        results = []
        
        # Check limits
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
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract content
        content, code_examples = self._extract_content(soup)
        
        # Check if content is relevant to query
        if self._is_relevant(content, query):
            title = self._extract_title(soup)
            section = self._extract_section(url)
            
            results.append(CrawlResult(
                source="docs",
                title=title,
                content=content,
                url=url,
                metadata={
                    "library_id": self.config.id,
                    "library_name": self.config.name,
                    "code_examples": code_examples,
                    "section": section,
                    "crawled_at": datetime.now().isoformat(),
                },
                crawled_at=datetime.now(),
                category="code",
                score=self._calculate_relevance(content, query),
            ))
        
        # Discover and crawl links
        if depth < 3:
            links = self._extract_links(soup, url)
            for link in links:
                if len(results) >= self.config.max_pages:
                    break
                sub_results = await self._crawl_page(client, link, query, depth + 1)
                results.extend(sub_results)
        
        return results
    
    def _should_exclude(self, url: str) -> bool:
        """Check if URL should be excluded based on config."""
        parsed = urlparse(url)
        path = parsed.path
        
        for exclude_pattern in self.config.exclude_paths:
            if path.startswith(exclude_pattern):
                return True
        
        return False
    
    def _extract_content(self, soup: BeautifulSoup) -> tuple[str, list[str]]:
        """Extract main content and code examples from page."""
        # Find content container
        content_elem = soup.select_one(self.config.content_selector)
        if not content_elem:
            content_elem = soup.find('main') or soup.find('article') or soup.body
        
        if not content_elem:
            return "", []
        
        # Extract code examples first
        code_examples = []
        for pre in content_elem.find_all('pre'):
            code = pre.get_text(strip=True)
            if code:
                code_examples.append(code)
        
        # Get clean text
        # Remove script/style elements
        for elem in content_elem.find_all(['script', 'style', 'nav', 'footer']):
            elem.decompose()
        
        content = content_elem.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content, code_examples
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try h1 first
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        # Fallback to title tag
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)
        
        return "Untitled"
    
    def _extract_section(self, url: str) -> str:
        """Extract section from URL path."""
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split('/') if p]
        
        if parts:
            return parts[0]
        return ""
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract navigation links from page."""
        links = []
        
        if self.config.nav_selector:
            nav_elements = soup.select(self.config.nav_selector)
            for elem in nav_elements:
                href = elem.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    # Only follow links within docs domain
                    if urlparse(full_url).netloc == urlparse(base_url).netloc:
                        links.append(full_url)
        
        return links
    
    def _is_relevant(self, content: str, query: str) -> bool:
        """Check if content is relevant to the query."""
        if not content:
            return False
        
        # Simple relevance check - query words in content
        query_words = query.lower().split()
        content_lower = content.lower()
        
        # At least 30% of query words should be present
        matches = sum(1 for word in query_words if word in content_lower)
        return matches / len(query_words) >= 0.3
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score 0-1."""
        if not content:
            return 0.0
        
        query_words = query.lower().split()
        content_lower = content.lower()
        
        matches = sum(1 for word in query_words if word in content_lower)
        return min(1.0, matches / len(query_words) * 1.5)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/aaa/Documents/Developer/DeepSearch/mcp && python -m pytest tests/test_docs_crawler.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add mcp/search/docs_crawler.py mcp/tests/test_docs_crawler.py
git commit -m "feat(docs): add generic docs crawler with content extraction"
```

---

## Task 3: Docs Search Engine

**Files:**
- Create: `mcp/search/docs_engine.py`
- Create: `mcp/tests/test_docs_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# mcp/tests/test_docs_engine.py
import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, patch, MagicMock
from search.docs_engine import DocsSearchEngine
from search.docs_crawler import DocsPage
from crawlers.base import CrawlResult

@pytest.fixture
def engine_with_mock_vectorstore():
    """Create DocsSearchEngine with mocked VectorStore."""
    # Create temp registry
    config = {
        "version": "1.0",
        "libraries": {
            "react": {
                "name": "React",
                "docs_url": "https://react.dev",
                "start_paths": ["/reference"],
                "content_selector": "main",
                "exclude_paths": [],
                "max_pages": 10,
                "ttl_hours": 168
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        engine = DocsSearchEngine(temp_path)
        
        # Mock VectorStore
        mock_vector_store = MagicMock()
        mock_vector_store.search.return_value = []
        engine.vector_store = mock_vector_store
        
        yield engine
    finally:
        os.unlink(temp_path)

@pytest.mark.asyncio
async def test_search_requires_library(engine_with_mock_vectorstore):
    """Test that search raises error when library not specified."""
    engine = engine_with_mock_vectorstore
    
    with pytest.raises(ValueError, match="library"):
        await engine.search(query="test", library="")

@pytest.mark.asyncio
async def test_search_library_not_found(engine_with_mock_vectorstore):
    """Test that search raises error for unknown library."""
    engine = engine_with_mock_vectorstore
    
    with pytest.raises(ValueError, match="not found"):
        await engine.search(query="test", library="unknown")

@pytest.mark.asyncio
async def test_search_returns_formatted_result(engine_with_mock_vectorstore):
    """Test that search returns formatted result."""
    engine = engine_with_mock_vectorstore
    
    # Mock crawler to return results
    mock_crawler = MagicMock()
    mock_crawler.crawl = AsyncMock(return_value=[
        CrawlResult(
            source="docs",
            title="useState",
            content="The useState Hook lets you add state.",
            url="https://react.dev/reference/react/useState",
            metadata={"library_id": "react", "code_examples": ["const [x, setX] = useState(0)"]},
            category="code",
            score=0.9
        )
    ])
    engine.crawler = mock_crawler
    
    # Mock vector store search
    engine.vector_store.search.return_value = []
    
    result = await engine.search(query="useState", library="react")
    
    assert result.library == "react"
    assert result.query == "useState"
    assert len(result.pages) > 0
    assert "useState" in result.formatted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/aaa/Documents/Developer/DeepSearch/mcp && python -m pytest tests/test_docs_engine.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'search.docs_engine'"

- [ ] **Step 3: Write minimal implementation**

```python
# mcp/search/docs_engine.py
"""Docs search engine - orchestrates library docs crawling and search."""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from crawlers.base import CrawlResult
from db.vector_store import VectorStore
from search.docs_crawler import DocsCrawler, DocsPage
from search.docs_registry import LibraryConfig, LibraryRegistry


@dataclass
class DocsSearchResult:
    """Result from docs search."""
    query: str
    library: str
    pages: list[DocsPage]
    formatted: str
    tokens_used: int
    tokens_budget: int
    total_pages_found: int
    search_time_ms: float


class DocsSearchEngine:
    """Orchestrates documentation search across libraries."""
    
    def __init__(self, registry_path: str):
        self.registry = LibraryRegistry(registry_path)
        self.vector_store = VectorStore(collection_name="docs_search")
        self.cache_path = Path(registry_path).parent / "docs_cache.json"
        self._cache = self._load_cache()
    
    def _load_cache(self) -> dict:
        """Load cache metadata from file."""
        if self.cache_path.exists():
            with open(self.cache_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save cache metadata to file."""
        with open(self.cache_path, 'w') as f:
            json.dump(self._cache, f, indent=2)
    
    def _is_cache_valid(self, library_id: str) -> bool:
        """Check if cache is still valid for a library."""
        if library_id not in self._cache:
            return False
        
        cached = self._cache[library_id]
        cached_at = datetime.fromisoformat(cached["crawled_at"])
        ttl_hours = cached.get("ttl_hours", 168)
        
        return datetime.now() < cached_at + timedelta(hours=ttl_hours)
    
    async def search(
        self,
        query: str,
        library: str,
        version: str = "",
        force_refresh: bool = False,
        tokens_target: int = 5000,
    ) -> DocsSearchResult:
        """
        Search documentation for a library.
        
        Args:
            query: Search query
            library: Library ID (e.g., "react", "nextjs")
            version: Specific version (optional)
            force_refresh: Force refresh cache
            tokens_target: Target token count for output
            
        Returns:
            DocsSearchResult with formatted output
            
        Raises:
            ValueError: If library not found or invalid
        """
        start_time = time.time()
        
        # Validate library
        if not library:
            available = ", ".join(self.registry.list_libraries())
            raise ValueError(f"library is required. Available: {available}")
        
        config = self.registry.get_library(library)
        if not config:
            available = ", ".join(self.registry.list_libraries())
            raise ValueError(f"Library '{library}' not found. Available: {available}")
        
        # Check cache or crawl fresh
        if force_refresh or not self._is_cache_valid(library):
            pages = await self._crawl_and_index(config, query)
        else:
            pages = self._search_indexed(library, query)
        
        # Rank pages by relevance
        pages = self._rank_pages(pages, query)
        
        # Token budget limiting
        pages, tokens_used = self._apply_token_budget(pages, tokens_target)
        
        # Format output
        formatted = self._format_output(query, config, pages, tokens_used, tokens_target, len(pages))
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return DocsSearchResult(
            query=query,
            library=library,
            pages=pages,
            formatted=formatted,
            tokens_used=tokens_used,
            tokens_budget=tokens_target,
            total_pages_found=len(pages),
            search_time_ms=elapsed_ms,
        )
    
    async def _crawl_and_index(self, config: LibraryConfig, query: str) -> list[DocsPage]:
        """Crawl docs and index to vector store."""
        crawler = DocsCrawler(config)
        crawl_results = await crawler.crawl(query, max_results=config.max_pages)
        
        # Index to vector store
        for result in crawl_results:
            self.vector_store.add(result)
        
        # Update cache
        self._cache[config.id] = {
            "crawled_at": datetime.now().isoformat(),
            "ttl_hours": config.ttl_hours,
            "page_count": len(crawl_results),
        }
        self._save_cache()
        
        # Convert to DocsPage
        pages = []
        for result in crawl_results:
            pages.append(DocsPage(
                library_id=config.id,
                title=result.title,
                url=result.url,
                content=result.content,
                code_examples=result.metadata.get("code_examples", []),
                section=result.metadata.get("section", ""),
            ))
        
        return pages
    
    def _search_indexed(self, library_id: str, query: str) -> list[DocsPage]:
        """Search already indexed docs."""
        # Search vector store
        results = self.vector_store.search(query, limit=20)
        
        # Filter by library
        pages = []
        for result in results:
            if result.metadata.get("library_id") == library_id:
                pages.append(DocsPage(
                    library_id=library_id,
                    title=result.title,
                    url=result.url,
                    content=result.content,
                    code_examples=result.metadata.get("code_examples", []),
                    section=result.metadata.get("section", ""),
                ))
        
        return pages
    
    def _rank_pages(self, pages: list[DocsPage], query: str) -> list[DocsPage]:
        """Rank pages by relevance to query."""
        query_words = set(query.lower().split())
        
        def relevance_score(page: DocsPage) -> float:
            content_lower = page.content.lower()
            title_lower = page.title.lower()
            
            # Word matches in content
            content_matches = sum(1 for word in query_words if word in content_lower)
            
            # Word matches in title (weighted higher)
            title_matches = sum(1 for word in query_words if word in title_lower)
            
            return content_matches + (title_matches * 2)
        
        pages.sort(key=relevance_score, reverse=True)
        return pages
    
    def _apply_token_budget(
        self, pages: list[DocsPage], budget: int
    ) -> tuple[list[DocsPage], int]:
        """Apply token budget to limit output size."""
        selected = []
        used = 0
        
        for page in pages:
            # Estimate tokens (rough: 4 chars per token)
            page_tokens = len(page.content) // 4
            
            if used + page_tokens <= budget:
                selected.append(page)
                used += page_tokens
            else:
                break
        
        return selected, used
    
    def _format_output(
        self,
        query: str,
        config: LibraryConfig,
        pages: list[DocsPage],
        tokens_used: int,
        tokens_budget: int,
        total_found: int,
    ) -> str:
        """Format search results as markdown."""
        lines = [f"📚 Documentation: {config.name} — \"{query}\""]
        lines.append("")
        
        for i, page in enumerate(pages, 1):
            tokens_est = len(page.content) // 4
            lines.append(f"--- Page {i}: {page.title} — {config.name} ({tokens_est} tokens) ---")
            lines.append(f"URL: {page.url}")
            lines.append("")
            
            # Add content (truncated)
            content = page.content[:1500]
            if len(page.content) > 1500:
                content += "\n\n..."
            lines.append(content)
            
            # Add code examples if present
            if page.code_examples:
                lines.append("")
                lines.append("**Code Examples:**")
                for code in page.code_examples[:3]:
                    lines.append(f"```")
                    lines.append(code[:500])
                    lines.append(f"```")
            
            lines.append("")
            lines.append("")
        
        lines.append(f"📊 Stats: {total_found} pages | ~{tokens_used} tokens | Budget: {tokens_budget}")
        
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/aaa/Documents/Developer/DeepSearch/mcp && python -m pytest tests/test_docs_engine.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add mcp/search/docs_engine.py mcp/tests/test_docs_engine.py
git commit -m "feat(docs): add docs search engine with cache and token budget"
```

---

## Task 4: Integrate with VectorStore

**Files:**
- Modify: `mcp/db/vector_store.py`

- [ ] **Step 1: Read current vector_store.py to find where to add collection**

Read: `mcp/db/vector_store.py` and find the `__init__` method.

- [ ] **Step 2: Add docs_search collection initialization**

Add after existing collection initialization:

```python
# In VectorStore.__init__, add:
self.docs_collection = self.client.get_or_create_collection("docs_search")
```

- [ ] **Step 3: Add docs-specific methods**

```python
def add_docs(self, result: CrawlResult) -> None:
    """Add a documentation result to the docs collection."""
    doc_id = f"docs_{result.metadata.get('library_id', 'unknown')}_{hash(result.url)}"
    
    self.docs_collection.upsert(
        ids=[doc_id],
        documents=[result.content],
        metadatas=[{
            "source": result.source,
            "title": result.title,
            "url": result.url,
            "library_id": result.metadata.get("library_id", ""),
            "section": result.metadata.get("section", ""),
            "crawled_at": result.crawled_at.isoformat() if result.crawled_at else "",
        }]
    )

def search_docs(self, query: str, library_id: str = "", limit: int = 10) -> list[CrawlResult]:
    """Search the docs collection."""
    where_filter = {"library_id": library_id} if library_id else None
    
    results = self.docs_collection.query(
        query_texts=[query],
        n_results=limit,
        where=where_filter,
    )
    
    if not results or not results.get("documents"):
        return []
    
    crawl_results = []
    for i, doc in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
        
        crawl_results.append(CrawlResult(
            source=metadata.get("source", "docs"),
            title=metadata.get("title", ""),
            content=doc,
            url=metadata.get("url", ""),
            metadata=metadata,
            crawled_at=datetime.fromisoformat(metadata.get("crawled_at", datetime.now().isoformat())),
            category="code",
        ))
    
    return crawl_results
```

- [ ] **Step 4: Update DocsSearchEngine to use new methods**

In `mcp/search/docs_engine.py`, update `_crawl_and_index` and `_search_indexed` to use `add_docs` and `search_docs`.

- [ ] **Step 5: Commit**

```bash
git add mcp/db/vector_store.py
git commit -m "feat(docs): add docs_search collection to VectorStore"
```

---

## Task 5: Integrate with Search Tool

**Files:**
- Modify: `mcp/server.py`

- [ ] **Step 1: Add docs imports at top of server.py**

```python
# Add after existing imports
from search.docs_engine import DocsSearchEngine
```

- [ ] **Step 2: Initialize DocsSearchEngine**

```python
# Add after other engine initializations
docs_engine = DocsSearchEngine(
    str(Path(__file__).parent / "data" / "docs_library_registry.json")
)
```

- [ ] **Step 3: Add new params to search tool function signature**

```python
@mcp.tool()
async def search(
    query: str,
    mode: str = "basic",
    source: str = "",
    limit: int = 10,
    category: str = "",
    format_type: str = "text",
    search_depth: str = "basic",
    topic: str = "general",
    max_age_hours: int = -1,
    # ... existing params ...
    # NEW docs params
    library: str = "",
    version: str = "",
    docs_refresh: bool = False,
) -> str:
```

- [ ] **Step 4: Add docs mode handler**

Add before the `# --- BASIC MODE (default) ---` section:

```python
# --- DOCS MODE ---
if mode == "docs":
    if not library:
        available = ", ".join(docs_engine.registry.list_libraries())
        return f"Error: 'library' required for docs mode. Available: {available}"
    
    try:
        result = await docs_engine.search(
            query=query,
            library=library,
            version=version,
            force_refresh=docs_refresh,
            tokens_target=tokens_target,
        )
        return result.formatted
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error searching docs: {str(e)}"
```

- [ ] **Step 5: Update docstring**

Add docs mode to the search tool's docstring:

```python
"""
Unified search tool — all search modes in one.

Modes:
  ...existing modes...
  - "docs": Search programming documentation from official library docs sites

Args:
  ...existing args...
  
  # Docs mode:
  library: Library/framework name (required for docs mode)
  version: Specific version (optional, default: latest)
  docs_refresh: Force refresh docs cache (default: False)
"""
```

- [ ] **Step 6: Commit**

```bash
git add mcp/server.py
git commit -m "feat(docs): integrate docs mode into search tool"
```

---

## Task 6: Integration Test

**Files:**
- Create: `mcp/tests/test_docs_integration.py`

- [ ] **Step 1: Write integration test**

```python
# mcp/tests/test_docs_integration.py
"""Integration test for docs search feature."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from crawlers.base import CrawlResult

# This test requires the full stack to be working
# Skip if running in CI without network access

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_docs_search_flow():
    """Test complete docs search flow from query to output."""
    from search.docs_engine import DocsSearchEngine
    
    # Use real registry path
    registry_path = "/Users/aaa/Documents/Developer/DeepSearch/mcp/data/docs_library_registry.json"
    
    engine = DocsSearchEngine(registry_path)
    
    # Mock the crawler to avoid actual HTTP calls in test
    mock_crawler = MagicMock()
    mock_crawler.crawl = AsyncMock(return_value=[
        CrawlResult(
            source="docs",
            title="useState – React",
            content="The useState Hook lets you add state to functional components.\n\n```jsx\nconst [count, setCount] = useState(0);\n```",
            url="https://react.dev/reference/react/useState",
            metadata={
                "library_id": "react",
                "code_examples": ["const [count, setCount] = useState(0);"],
                "section": "reference",
            },
            category="code",
            score=0.95
        )
    ])
    engine.crawler = mock_crawler
    
    # Mock vector store
    engine.vector_store.search.return_value = []
    
    # Execute search
    result = await engine.search(
        query="useState hook",
        library="react",
        tokens_target=3000,
    )
    
    # Verify result structure
    assert result.library == "react"
    assert result.query == "useState hook"
    assert len(result.pages) > 0
    assert result.tokens_used > 0
    assert result.tokens_budget == 3000
    assert "useState" in result.formatted
    assert "📚 Documentation" in result.formatted
```

- [ ] **Step 2: Run integration test**

Run: `cd /Users/aaa/Documents/Developer/DeepSearch/mcp && python -m pytest tests/test_docs_integration.py -v -m integration`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add mcp/tests/test_docs_integration.py
git commit -m "test(docs): add integration test for docs search"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `mcp/AGENTS.md`

- [ ] **Step 1: Add docs mode to AGENTS.md**

Add a new section after the existing search tool documentation:

```markdown
### `search` — Unified Search (8 modes)
The main search tool. Use `mode` parameter to switch behavior:

| Mode | Description | Key Params |
|------|-------------|------------|
| `basic` (default) | Semantic search across indexed content | source, limit, category, search_depth, topic, max_age_hours |
| `advanced` | Search with domain/date/text/source filters | include_domains, exclude_domains, start_date, end_date, include_text, exclude_text |
| `quick` | Real-time search without database (DuckDuckGo) | source |
| `stream` | Search with streaming batches + timing | sources |
| `smart` | Compact IR overview + full details (saves 50-70% tokens) | top_full, max_overview_tokens |
| `code` | Search GitHub + Stack Overflow for code snippets | language, tokens_target |
| `context` | Token-budget-aware snippet packing | budget_tokens, language, num_results |
| `docs` | Search programming documentation from official library sites | library, version, docs_refresh |
```

- [ ] **Step 2: Add docs library list**

```markdown
#### Supported Libraries
- `react` — React (https://react.dev)
- `nextjs` — Next.js (https://nextjs.org/docs)
- `vue` — Vue.js (https://vuejs.org)
- `supabase` — Supabase (https://supabase.com/docs)
- `prisma` — Prisma (https://www.prisma.io/docs)

To add a new library, edit `mcp/data/docs_library_registry.json`.
```

- [ ] **Step 3: Commit**

```bash
git add mcp/AGENTS.md
git commit -m "docs: update AGENTS.md with docs mode documentation"
```

---

## Summary

**Tasks:** 7
**New files:** 6 (3 Python modules, 2 test files, 1 JSON config)
**Modified files:** 3 (server.py, vector_store.py, AGENTS.md)
**Estimated LOC:** ~500 new, ~50 modified

**Implementation order:**
1. Task 1: Library Registry (foundation)
2. Task 2: Docs Crawler (core crawling)
3. Task 3: Docs Search Engine (orchestration)
4. Task 4: VectorStore integration (storage)
5. Task 5: Search tool integration (user-facing)
6. Task 6: Integration test (verification)
7. Task 7: Documentation (usability)

**Testing strategy:** TDD with unit tests per module, integration test at the end.
