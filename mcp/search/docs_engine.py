"""Docs search engine - orchestrates library docs crawling and search."""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from crawlers.base import CrawlResult
from db.vector_store import VectorStore
from search.docs_crawler import DocsCrawler
from search.docs_registry import LibraryConfig, LibraryRegistry


@dataclass
class DocsPage:
    """A single documentation page."""
    library_id: str
    title: str
    url: str
    content: str
    code_examples: list[str] = field(default_factory=list)
    section: str = ""


@dataclass
class DocsSearchResult:
    """Result from docs search."""
    query: str
    library: str
    pages: list
    formatted: str
    tokens_used: int
    tokens_budget: int
    total_pages_found: int
    search_time_ms: float


class DocsSearchEngine:
    """Orchestrates documentation search across libraries."""

    def __init__(self, registry_path: str):
        self.registry = LibraryRegistry(registry_path)
        self.vector_store = VectorStore()
        self.cache_path = Path(registry_path).parent / "docs_cache.json"
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        if self.cache_path.exists():
            with open(self.cache_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        with open(self.cache_path, 'w') as f:
            json.dump(self._cache, f, indent=2)

    def _is_cache_valid(self, library_id: str) -> bool:
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
        start_time = time.time()

        if not library:
            available = ", ".join(self.registry.list_libraries())
            raise ValueError(f"library is required. Available: {available}")

        config = self.registry.get_library(library)
        if not config:
            available = ", ".join(self.registry.list_libraries())
            raise ValueError(f"Library '{library}' not found. Available: {available}")

        if force_refresh or not self._is_cache_valid(library):
            pages = await self._crawl_and_index(config, query)
        else:
            pages = self._search_indexed(library, query)

        pages = self._rank_pages(pages, query)
        pages, tokens_used = self._apply_token_budget(pages, tokens_target)
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

    async def _crawl_and_index(self, config: LibraryConfig, query: str) -> list:
        crawler = DocsCrawler(config)
        crawl_results = await crawler.crawl(query, max_results=config.max_pages)

        for result in crawl_results:
            self.vector_store.add_docs(result)

        self._cache[config.id] = {
            "crawled_at": datetime.now().isoformat(),
            "ttl_hours": config.ttl_hours,
            "page_count": len(crawl_results),
        }
        self._save_cache()

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

    def _search_indexed(self, library_id: str, query: str) -> list:
        results = self.vector_store.search_docs(query, library_id=library_id, limit=20)
        pages = []
        for result in results:
            pages.append(DocsPage(
                library_id=library_id,
                title=result.title,
                url=result.url,
                content=result.content,
                code_examples=result.metadata.get("code_examples", []),
                section=result.metadata.get("section", ""),
            ))
        return pages

    def _rank_pages(self, pages: list, query: str) -> list:
        query_words = set(query.lower().split())

        def relevance_score(page):
            content_lower = page.content.lower()
            title_lower = page.title.lower()
            content_matches = sum(1 for word in query_words if word in content_lower)
            title_matches = sum(1 for word in query_words if word in title_lower)
            return content_matches + (title_matches * 2)

        pages.sort(key=relevance_score, reverse=True)
        return pages

    def _apply_token_budget(self, pages: list, budget: int) -> tuple:
        selected = []
        used = 0
        for page in pages:
            page_tokens = len(page.content) // 4
            if used + page_tokens <= budget:
                selected.append(page)
                used += page_tokens
            else:
                break
        return selected, used

    def _format_output(self, query, config, pages, tokens_used, tokens_budget, total_found) -> str:
        lines = [f"Documentation: {config.name} - \"{query}\""]
        lines.append("")

        for i, page in enumerate(pages, 1):
            tokens_est = len(page.content) // 4
            lines.append(f"--- Page {i}: {page.title} - {config.name} ({tokens_est} tokens) ---")
            lines.append(f"URL: {page.url}")
            lines.append("")

            content = page.content[:1500]
            if len(page.content) > 1500:
                content += "\n\n..."
            lines.append(content)

            if page.code_examples:
                lines.append("")
                lines.append("**Code Examples:**")
                for code in page.code_examples[:3]:
                    lines.append("```")
                    lines.append(code[:500])
                    lines.append("```")

            lines.append("")
            lines.append("")

        lines.append(f"Stats: {total_found} pages | ~{tokens_used} tokens | Budget: {tokens_budget}")
        return "\n".join(lines)
