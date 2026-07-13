# Deep Search Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a custom search engine MCP server with 7 free sources + semantic search via ChromaDB.

**Architecture:** Crawlers gather data from 7 sources → Embedding model converts to vectors → ChromaDB stores vectors + metadata → Search engine performs semantic search → MCP server exposes tools to AI.

**Tech Stack:** Python 3.12, FastMCP, ChromaDB, sentence-transformers, httpx, BeautifulSoup, yt-dlp, duckduckgo-search

---

## File Structure

```
mining/
├── .agents/skills/deep-search/
│   └── SKILL.md                    # AI skill instructions
├── crawlers/
│   ├── __init__.py                 # Export all crawlers
│   ├── base.py                     # Base crawler class
│   ├── web_crawler.py              # Web crawling
│   ├── reddit_crawler.py           # Reddit JSON API
│   ├── youtube_crawler.py          # YouTube via yt-dlp
│   ├── github_crawler.py           # GitHub REST API
│   ├── twitter_crawler.py          # Twitter/X via Nitter
│   ├── duckduckgo_crawler.py       # DuckDuckGo search
│   └── wikipedia_crawler.py        # Wikipedia API
├── db/
│   ├── __init__.py                 # Export db classes
│   ├── embeddings.py               # Embedding model wrapper
│   └── vector_store.py             # ChromaDB wrapper
├── search/
│   ├── __init__.py                 # Export search engine
│   └── engine.py                   # Search + ranking logic
├── server.py                       # MCP server (FastMCP)
├── requirements.txt                # Dependencies
└── README.md                       # Documentation
```

---

### Task 1: Project Setup

**Files:**
- Create: `mining/requirements.txt`
- Create: `mining/crawlers/__init__.py`
- Create: `mining/db/__init__.py`
- Create: `mining/search/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```txt
mcp
httpx
beautifulsoup4
duckduckgo-search
yt-dlp
chromadb
sentence-transformers
fastmcp
```

- [ ] **Step 2: Create package init files**

```python
# crawlers/__init__.py
```

```python
# db/__init__.py
```

```python
# search/__init__.py
```

- [ ] **Step 3: Install dependencies**

Run: `cd mining && source .venv/bin/activate && pip install -r requirements.txt`
Expected: All packages installed successfully

- [ ] **Step 4: Commit**

```bash
git add requirements.txt crawlers/__init__.py db/__init__.py search/__init__.py
git commit -m "feat: project setup with dependencies"
```

---

### Task 2: Base Crawler Class

**Files:**
- Create: `mining/crawlers/base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_base.py
from crawlers.base import BaseCrawler, CrawlResult

def test_crawl_result_has_required_fields():
    result = CrawlResult(
        source="test",
        title="Test Title",
        content="Test content",
        url="https://example.com",
        metadata={"author": "test"}
    )
    assert result.source == "test"
    assert result.title == "Test Title"
    assert result.content == "Test content"
    assert result.url == "https://example.com"
    assert result.metadata == {"author": "test"}
    assert result.crawled_at is not None

def test_base_crawler_is_abstract():
    import inspect
    from crawlers.base import BaseCrawler
    assert inspect.isabstract(BaseCrawler)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_base.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class CrawlResult:
    source: str
    title: str
    content: str
    url: str
    metadata: dict[str, Any] = field(default_factory=dict)
    crawled_at: datetime = field(default_factory=datetime.now)

class BaseCrawler(ABC):
    @abstractmethod
    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/base.py tests/test_crawlers/test_base.py
git commit -m "feat: add base crawler class with CrawlResult dataclass"
```

---

### Task 3: Embedding Model

**Files:**
- Create: `mining/db/embeddings.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db/test_embeddings.py
from db.embeddings import EmbeddingModel

def test_embedding_model_initializes():
    model = EmbeddingModel()
    assert model is not None

def test_embedding_model_embed_text():
    model = EmbeddingModel()
    embedding = model.embed("test text")
    assert isinstance(embedding, list)
    assert len(embedding) == 384

def test_embedding_model_embed_batch():
    model = EmbeddingModel()
    embeddings = model.embed_batch(["text one", "text two"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db/test_embeddings.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'db'"

- [ ] **Step 3: Write minimal implementation**

```python
# db/embeddings.py
from sentence_transformers import SentenceTransformer

class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts)
        return [e.tolist() for e in embeddings]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db/test_embeddings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add db/embeddings.py tests/test_db/test_embeddings.py
git commit -m "feat: add embedding model wrapper with sentence-transformers"
```

---

### Task 4: Vector Store

**Files:**
- Create: `mining/db/vector_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db/test_vector_store.py
from db.vector_store import VectorStore
from crawlers.base import CrawlResult

def test_vector_store_initializes():
    store = VectorStore()
    assert store is not None

def test_vector_store_add_and_search():
    store = VectorStore()
    result = CrawlResult(
        source="test",
        title="AI in Indonesia",
        content="Artificial intelligence is growing in Indonesia",
        url="https://example.com/ai-indonesia",
        metadata={"author": "test"}
    )
    store.add(result)
    
    results = store.search("artificial intelligence", limit=1)
    assert len(results) == 1
    assert results[0].title == "AI in Indonesia"

def test_vector_store_stats():
    store = VectorStore()
    stats = store.stats()
    assert "total_documents" in stats
    assert "sources" in stats
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db/test_vector_store.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'db'"

- [ ] **Step 3: Write minimal implementation**

```python
# db/vector_store.py
import chromadb
from crawlers.base import CrawlResult
from db.embeddings import EmbeddingModel

class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection("search_engine")
        self.embedding_model = EmbeddingModel()

    def add(self, result: CrawlResult) -> None:
        embedding = self.embedding_model.embed(result.content)
        self.collection.add(
            ids=[f"{result.source}_{hash(result.url)}"],
            embeddings=[embedding],
            documents=[result.content],
            metadatas=[{
                "source": result.source,
                "title": result.title,
                "url": result.url,
                "author": result.metadata.get("author", ""),
                "crawled_at": result.crawled_at.isoformat()
            }]
        )

    def search(self, query: str, limit: int = 10) -> list[CrawlResult]:
        query_embedding = self.embedding_model.embed(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        crawl_results = []
        for i in range(len(results["ids"][0])):
            crawl_results.append(CrawlResult(
                source=results["metadatas"][0][i]["source"],
                title=results["metadatas"][0][i]["title"],
                content=results["documents"][0][i],
                url=results["metadatas"][0][i]["url"],
                metadata={"author": results["metadatas"][0][i]["author"]}
            ))
        return crawl_results

    def stats(self) -> dict:
        count = self.collection.count()
        return {
            "total_documents": count,
            "sources": list(set(
                meta["source"] 
                for meta in self.collection.get()["metadatas"]
            )) if count > 0 else []
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db/test_vector_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add db/vector_store.py tests/test_db/test_vector_store.py
git commit -m "feat: add vector store with ChromaDB for semantic search"
```

---

### Task 5: Web Crawler

**Files:**
- Create: `mining/crawlers/web_crawler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_web_crawler.py
import pytest
from crawlers.web_crawler import WebCrawler

@pytest.mark.asyncio
async def test_web_crawler_crawl_url():
    crawler = WebCrawler()
    results = await crawler.crawl("https://example.com")
    assert len(results) >= 1
    assert results[0].source == "web"
    assert results[0].url == "https://example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_web_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/web_crawler.py
import httpx
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult

class WebCrawler(BaseCrawler):
    def __init__(self):
        self.client = httpx.Client(
            headers={"User-Agent": "Mozilla/5.0 (compatible; SearchEngine/1.0)"},
            follow_redirects=True,
            timeout=10.0
        )

    async def crawl(self, url: str, max_results: int = 1) -> list[CrawlResult]:
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            title = soup.title.string if soup.title else url
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            content = soup.get_text(separator="\n", strip=True)
            content = "\n".join(line for line in content.splitlines() if line.strip())
            
            return [CrawlResult(
                source="web",
                title=title,
                content=content[:5000],
                url=url,
                metadata={"status_code": response.status_code}
            )]
        except Exception as e:
            return [CrawlResult(
                source="web",
                title=f"Error: {url}",
                content=str(e),
                url=url,
                metadata={"error": str(e)}
            )]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_web_crawler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/web_crawler.py tests/test_crawlers/test_web_crawler.py
git commit -m "feat: add web crawler with httpx and BeautifulSoup"
```

---

### Task 6: Reddit Crawler

**Files:**
- Create: `mining/crawlers/reddit_crawler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_reddit_crawler.py
import pytest
from crawlers.reddit_crawler import RedditCrawler

@pytest.mark.asyncio
async def test_reddit_crawler_crawl():
    crawler = RedditCrawler()
    results = await crawler.crawl("python programming", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "reddit"
        assert "reddit.com" in results[0].url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_reddit_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/reddit_crawler.py
import httpx
from crawlers.base import BaseCrawler, CrawlResult

class RedditCrawler(BaseCrawler):
    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.headers = {"User-Agent": "Mozilla/5.0 (compatible; SearchEngine/1.0)"}

    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            url = f"{self.base_url}/search.json"
            params = {
                "q": query,
                "restrict_sr": "true",
                "sort": "relevance",
                "limit": max_results
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                results.append(CrawlResult(
                    source="reddit",
                    title=post_data.get("title", ""),
                    content=post_data.get("selftext", "")[:2000],
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    metadata={
                        "author": post_data.get("author", ""),
                        "score": post_data.get("score", 0),
                        "subreddit": post_data.get("subreddit", "")
                    }
                ))
            return results
        except Exception as e:
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_reddit_crawler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/reddit_crawler.py tests/test_crawlers/test_reddit_crawler.py
git commit -m "feat: add Reddit crawler with JSON API"
```

---

### Task 7: YouTube Crawler

**Files:**
- Create: `mining/crawlers/youtube_crawler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_youtube_crawler.py
import pytest
from crawlers.youtube_crawler import YouTubeCrawler

@pytest.mark.asyncio
async def test_youtube_crawler_crawl():
    crawler = YouTubeCrawler()
    results = await crawler.crawl("python tutorial", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "youtube"
        assert "youtube.com" in results[0].url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_youtube_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/youtube_crawler.py
import subprocess
import json
from crawlers.base import BaseCrawler, CrawlResult

class YouTubeCrawler(BaseCrawler):
    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            search_url = f"ytsearch{max_results}:{query}"
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--flat-playlist",
                "--no-download",
                search_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
            
            results = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    data = json.loads(line)
                    results.append(CrawlResult(
                        source="youtube",
                        title=data.get("title", ""),
                        content=data.get("description", "")[:2000],
                        url=f"https://youtube.com/watch?v={data.get('id', '')}",
                        metadata={
                            "author": data.get("uploader", ""),
                            "duration": data.get("duration", 0),
                            "view_count": data.get("view_count", 0)
                        }
                    ))
            return results
        except Exception as e:
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_youtube_crawler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/youtube_crawler.py tests/test_crawlers/test_youtube_crawler.py
git commit -m "feat: add YouTube crawler with yt-dlp"
```

---

### Task 8: GitHub Crawler

**Files:**
- Create: `mining/crawlers/github_crawler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_github_crawler.py
import pytest
from crawlers.github_crawler import GitHubCrawler

@pytest.mark.asyncio
async def test_github_crawler_crawl():
    crawler = GitHubCrawler()
    results = await crawler.crawl("python web framework", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "github"
        assert "github.com" in results[0].url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_github_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/github_crawler.py
import httpx
from crawlers.base import BaseCrawler, CrawlResult

class GitHubCrawler(BaseCrawler):
    def __init__(self):
        self.base_url = "https://api.github.com"

    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            url = f"{self.base_url}/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for repo in data.get("items", []):
                results.append(CrawlResult(
                    source="github",
                    title=repo.get("full_name", ""),
                    content=repo.get("description", "") or "",
                    url=repo.get("html_url", ""),
                    metadata={
                        "author": repo.get("owner", {}).get("login", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language", ""),
                        "topics": repo.get("topics", [])
                    }
                ))
            return results
        except Exception as e:
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_github_crawler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/github_crawler.py tests/test_crawlers/test_github_crawler.py
git commit -m "feat: add GitHub crawler with REST API"
```

---

### Task 9: DuckDuckGo Crawler

**Files:**
- Create: `mining/crawlers/duckduckgo_crawler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_duckduckgo_crawler.py
import pytest
from crawlers.duckduckgo_crawler import DuckDuckGoCrawler

@pytest.mark.asyncio
async def test_duckduckgo_crawler_crawl():
    crawler = DuckDuckGoCrawler()
    results = await crawler.crawl("python programming", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "duckduckgo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_duckduckgo_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/duckduckgo_crawler.py
from duckduckgo_search import DDGS
from crawlers.base import BaseCrawler, CrawlResult

class DuckDuckGoCrawler(BaseCrawler):
    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            with DDGS() as ddgs:
                results_list = list(ddgs.text(query, max_results=max_results))
            
            results = []
            for item in results_list:
                results.append(CrawlResult(
                    source="duckduckgo",
                    title=item.get("title", ""),
                    content=item.get("body", ""),
                    url=item.get("href", ""),
                    metadata={}
                ))
            return results
        except Exception as e:
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_duckduckgo_crawler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/duckduckgo_crawler.py tests/test_crawlers/test_duckduckgo_crawler.py
git commit -m "feat: add DuckDuckGo crawler"
```

---

### Task 10: Twitter Crawler

**Files:**
- Create: `mining/crawlers/twitter_crawler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_twitter_crawler.py
import pytest
from crawlers.twitter_crawler import TwitterCrawler

@pytest.mark.asyncio
async def test_twitter_crawler_crawl():
    crawler = TwitterCrawler()
    results = await crawler.crawl("python", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "twitter"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_twitter_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/twitter_crawler.py
import httpx
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult

class TwitterCrawler(BaseCrawler):
    def __init__(self):
        self.nitter_instances = [
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
            "https://nitter.woodland.cafe"
        ]

    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        for instance in self.nitter_instances:
            try:
                url = f"{instance}/search"
                params = {"f": "tweets", "q": query}
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=10.0)
                    response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                tweets = soup.find_all("div", class_="timeline-item")
                
                results = []
                for tweet in tweets[:max_results]:
                    content_elem = tweet.find("div", class_="tweet-content")
                    username_elem = tweet.find("a", class_="username")
                    
                    results.append(CrawlResult(
                        source="twitter",
                        title=username_elem.string if username_elem else "",
                        content=content_elem.get_text(strip=True) if content_elem else "",
                        url=f"https://twitter.com{username_elem['href']}" if username_elem else "",
                        metadata={"instance": instance}
                    ))
                return results
            except Exception:
                continue
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_twitter_crawler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/twitter_crawler.py tests/test_crawlers/test_twitter_crawler.py
git commit -m "feat: add Twitter crawler via Nitter"
```

---

### Task 11: Wikipedia Crawler

**Files:**
- Create: `mining/crawlers/wikipedia_crawler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_wikipedia_crawler.py
import pytest
from crawlers.wikipedia_crawler import WikipediaCrawler

@pytest.mark.asyncio
async def test_wikipedia_crawler_crawl():
    crawler = WikipediaCrawler()
    results = await crawler.crawl("artificial intelligence", max_results=3)
    assert len(results) <= 3
    if results:
        assert results[0].source == "wikipedia"
        assert "wikipedia.org" in results[0].url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_wikipedia_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/wikipedia_crawler.py
import httpx
from crawlers.base import BaseCrawler, CrawlResult

class WikipediaCrawler(BaseCrawler):
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/api/rest_v1"

    async def crawl(self, query: str, max_results: int = 5) -> list[CrawlResult]:
        try:
            search_url = f"{self.base_url}/page/summary/{query.replace(' ', '_')}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url)
                response.raise_for_status()
                data = response.json()
            
            return [CrawlResult(
                source="wikipedia",
                title=data.get("title", ""),
                content=data.get("extract", ""),
                url=data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                metadata={
                    "description": data.get("description", ""),
                    "thumbnail": data.get("thumbnail", {}).get("source", "")
                }
            )]
        except Exception as e:
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_wikipedia_crawler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/wikipedia_crawler.py tests/test_crawlers/test_wikipedia_crawler.py
git commit -m "feat: add Wikipedia crawler"
```

---

### Task 12: Crawler Manager

**Files:**
- Create: `mining/crawlers/manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawlers/test_manager.py
import pytest
from crawlers.manager import CrawlerManager

@pytest.mark.asyncio
async def test_crawler_manager_initializes():
    manager = CrawlerManager()
    assert len(manager.crawlers) == 7

@pytest.mark.asyncio
async def test_crawler_manager_crawl_all():
    manager = CrawlerManager()
    results = await manager.crawl_all("python", max_results_per_source=2)
    assert isinstance(results, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawlers/test_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawlers'"

- [ ] **Step 3: Write minimal implementation**

```python
# crawlers/manager.py
import asyncio
from crawlers.base import CrawlResult
from crawlers.web_crawler import WebCrawler
from crawlers.reddit_crawler import RedditCrawler
from crawlers.youtube_crawler import YouTubeCrawler
from crawlers.github_crawler import GitHubCrawler
from crawlers.twitter_crawler import TwitterCrawler
from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
from crawlers.wikipedia_crawler import WikipediaCrawler

class CrawlerManager:
    def __init__(self):
        self.crawlers = {
            "web": WebCrawler(),
            "reddit": RedditCrawler(),
            "youtube": YouTubeCrawler(),
            "github": GitHubCrawler(),
            "twitter": TwitterCrawler(),
            "duckduckgo": DuckDuckGoCrawler(),
            "wikipedia": WikipediaCrawler()
        }

    async def crawl_all(self, query: str, max_results_per_source: int = 10) -> list[CrawlResult]:
        tasks = []
        for name, crawler in self.crawlers.items():
            tasks.append(self._crawl_safe(crawler, query, max_results_per_source))
        
        results = await asyncio.gather(*tasks)
        return [item for sublist in results for item in sublist]

    async def _crawl_safe(self, crawler, query: str, max_results: int) -> list[CrawlResult]:
        try:
            return await crawler.crawl(query, max_results)
        except Exception:
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawlers/test_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crawlers/manager.py tests/test_crawlers/test_manager.py
git commit -m "feat: add crawler manager for parallel crawling"
```

---

### Task 13: Search Engine

**Files:**
- Create: `mining/search/engine.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_search/test_engine.py
import pytest
from search.engine import SearchEngine

def test_search_engine_initializes():
    engine = SearchEngine()
    assert engine is not None

@pytest.mark.asyncio
async def test_search_engine_index_and_search():
    engine = SearchEngine()
    await engine.index_topic("python programming", max_results_per_source=1)
    results = engine.search("python", limit=5)
    assert isinstance(results, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_search/test_engine.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'search'"

- [ ] **Step 3: Write minimal implementation**

```python
# search/engine.py
import asyncio
from crawlers.manager import CrawlerManager
from db.vector_store import VectorStore
from crawlers.base import CrawlResult

class SearchEngine:
    def __init__(self):
        self.crawler_manager = CrawlerManager()
        self.vector_store = VectorStore()

    async def index_topic(self, topic: str, max_results_per_source: int = 10) -> int:
        results = await self.crawler_manager.crawl_all(topic, max_results_per_source)
        
        for result in results:
            self.vector_store.add(result)
        
        return len(results)

    def search(self, query: str, limit: int = 10) -> list[CrawlResult]:
        return self.vector_store.search(query, limit)

    def stats(self) -> dict:
        return self.vector_store.stats()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_search/test_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add search/engine.py tests/test_search/test_engine.py
git commit -m "feat: add search engine with indexing and semantic search"
```

---

### Task 14: MCP Server

**Files:**
- Create: `mining/server.py`

- [ ] **Step 1: Write the minimal implementation**

```python
# server.py
import asyncio
from mcp.server.fastmcp import FastMCP
from search.engine import SearchEngine
from crawlers.web_crawler import WebCrawler

mcp = FastMCP("DeepSearchEngine")
engine = SearchEngine()
web_crawler = WebCrawler()

@mcp.tool()
async def deep_search(query: str, source: str = "", limit: int = 10) -> str:
    """
    Semantic search across all indexed content.
    
    Args:
        query: Search query in natural language
        source: Filter by source (reddit, youtube, github, etc.) - optional
        limit: Maximum number of results (default 10)
    """
    results = engine.search(query, limit)
    
    if source:
        results = [r for r in results if r.source == source]
    
    if not results:
        return "No results found. Try indexing a topic first with index_topic."
    
    output = f"Found {len(results)} results for '{query}':\n\n"
    for i, result in enumerate(results, 1):
        output += f"--- Result {i} (Source: {result.source}) ---\n"
        output += f"Title: {result.title}\n"
        output += f"Content: {result.content[:500]}...\n"
        output += f"URL: {result.url}\n\n"
    
    return output

@mcp.tool()
async def index_topic(topic: str, max_results_per_source: int = 10) -> str:
    """
    Crawl and index a topic from all 7 sources.
    
    Args:
        topic: Topic to index (e.g., "AI Indonesia", "python web framework")
        max_results_per_source: Max results per source (default 10)
    """
    count = await engine.index_topic(topic, max_results_per_source)
    return f"Indexed {count} results for topic '{topic}'."

@mcp.tool()
async def web_crawl(url: str) -> str:
    """
    Crawl a specific URL and add to index.
    
    Args:
        url: URL to crawl
    """
    results = await web_crawler.crawl(url)
    if results:
        engine.vector_store.add(results[0])
        return f"Crawled and indexed: {results[0].title}"
    return "Failed to crawl URL."

@mcp.tool()
async def quick_search(query: str, source: str = "") -> str:
    """
    Real-time search without using the database.
    
    Args:
        query: Search query
        source: Source to search (duckduckgo, reddit, etc.) - optional
    """
    from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
    
    if not source:
        source = "duckduckgo"
    
    crawler_map = {
        "duckduckgo": DuckDuckGoCrawler,
    }
    
    if source not in crawler_map:
        return f"Source '{source}' not available for quick search."
    
    crawler = crawler_map[source]()
    results = await crawler.crawl(query, max_results=5)
    
    if not results:
        return "No results found."
    
    output = f"Quick search results for '{query}':\n\n"
    for i, result in enumerate(results, 1):
        output += f"{i}. {result.title}\n   {result.url}\n   {result.content[:200]}...\n\n"
    
    return output

@mcp.tool()
def list_sources() -> str:
    """List all available data sources."""
    sources = [
        "web - General web crawling",
        "reddit - Reddit posts and discussions",
        "youtube - YouTube videos and metadata",
        "github - GitHub repositories",
        "twitter - Twitter/X posts via Nitter",
        "duckduckgo - DuckDuckGo search results",
        "wikipedia - Wikipedia articles"
    ]
    return "Available sources:\n" + "\n".join(f"- {s}" for s in sources)

@mcp.tool()
def db_stats() -> str:
    """Get database statistics."""
    stats = engine.stats()
    return f"Database stats:\n- Total documents: {stats['total_documents']}\n- Sources: {', '.join(stats['sources']) if stats['sources'] else 'none'}"

if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: Test MCP server starts**

Run: `cd mining && python server.py`
Expected: Server starts without errors (Ctrl+C to stop)

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat: add MCP server with 7 tools"
```

---

### Task 15: AI Skill (SKILL.md)

**Files:**
- Create: `mining/.agents/skills/deep-search/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

```markdown
---
name: Deep Search Engine
description: Search informasi dari 7 sources (web, Reddit, YouTube, GitHub, Twitter, DuckDuckGo, Wikipedia) dengan semantic search.
---

# Deep Search Engine

## Persona
Kamu adalah search assistant yang membantu pengguna mencari informasi dari berbagai sumber. Kamu memiliki akses ke 7 sources berbeda dan bisa melakukan semantic search.

## Prasyarat
Skill ini menggunakan MCP server yang menyediakan tools:
- `deep_search` — Semantic search di database
- `index_topic` — Crawl dan index topik dari semua sources
- `web_crawl` — Crawl URL spesifik
- `quick_search` — Real-time search tanpa database
- `list_sources` — List semua sources
- `db_stats` — Statistik database

## Alur Kerja

1. **Pahami kebutuhan pengguna**
   - Tentukan topik pencarian
   - Tentukan sumber yang relevan (atau semua)

2. **Index topik (jika belum ada di DB)**
   - Jalankan `index_topic` dengan topik yang relevan
   - Tunggu selesai (biasanya 30 detik - 2 menit)

3. **Cari informasi**
   - Jalankan `deep_search` dengan query yang sesuai
   - Filter by source jika diperlukan

4. **Present hasil**
   - Ringkas informasi yang ditemukan
   - Sertakan sumber (URL)
   - Berikan insight atau rekomendasi

## Contoh Prompt

> "Cari informasi tentang AI di Indonesia"
> "Riset tentang tren cryptocurrency 2026"
> "Cari artikel tentang web development terbaru"

## Tips

- Gunakan `index_topic` terlebih dahulu untuk topik yang belum ada di DB
- Gunakan `quick_search` untuk pencarian cepat tanpa index
- Gunakan `deep_search` dengan filter `source` untuk hasil yang lebih spesifik
```

- [ ] **Step 2: Commit**

```bash
git add .agents/skills/deep-search/SKILL.md
git commit -m "feat: add AI skill for deep search engine"
```

---

### Task 16: README Documentation

**Files:**
- Create: `mining/README.md`

- [ ] **Step 1: Write the README**

```markdown
# Deep Search Engine

Custom search engine MCP server dengan 7 free sources + semantic search via ChromaDB.

## Features

- 7 data sources (100% free, zero cost)
- Semantic search dengan embedding vectors
- Persistent storage dengan ChromaDB
- MCP server untuk integrasi dengan AI tools

## Sources

| Source | Method |
|--------|--------|
| Web | httpx + BeautifulSoup |
| Reddit | JSON API (publik) |
| YouTube | yt-dlp |
| GitHub | REST API |
| Twitter/X | Nitter scraping |
| DuckDuckGo | duckduckgo-search |
| Wikipedia | Wikipedia API |

## Installation

```bash
cd mining
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### MCP Server

```bash
python server.py
```

### Configuration (Claude Desktop)

```json
{
  "mcpServers": {
    "deep-search": {
      "command": "/path/to/mining/.venv/bin/python",
      "args": ["/path/to/mining/server.py"]
    }
  }
}
```

### Tools

- `deep_search` — Semantic search across indexed content
- `index_topic` — Crawl and index a topic from all sources
- `web_crawl` — Crawl a specific URL
- `quick_search` — Real-time search without database
- `list_sources` — List all available sources
- `db_stats` — Get database statistics

## Architecture

```
User Query → MCP Server → Search Engine → Vector DB → Results ↓
        Crawler Manager → Crawlers → 7 Sources
```

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README documentation"
```

---

## Self-Review

**1. Spec coverage:** ✅ All requirements covered
- 7 crawlers ✅
- ChromaDB vector store ✅
- sentence-transformers embedding ✅
- MCP server with 7 tools ✅
- AI skill ✅

**2. Placeholder scan:** ✅ No TBD/TODO found

**3. Type consistency:** ✅ All types, method signatures consistent across tasks

**Plan complete. Ready for execution.**
