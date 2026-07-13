"""
Context API — Token-budget-aware snippet packing for coding agents.
Searches sources, estimates tokens per snippet, greedily fills budget.
No AI API calls — pure utility logic for host AI consumption.
"""
from dataclasses import dataclass, field
from datetime import datetime

from crawlers.base import CrawlResult


@dataclass
class ContextSnippet:
    """Single snippet with token estimate."""
    title: str
    content: str
    url: str
    source: str
    language: str = ""
    tokens: int = 0


@dataclass
class ContextResult:
    """Result from context_search."""
    query: str
    snippets: list[ContextSnippet] = field(default_factory=list)
    formatted: str = ""
    tokens_used: int = 0
    tokens_budget: int = 8000
    total_snippets_found: int = 0
    search_time_ms: float = 0.0


class ContextEngine:
    """Token-budget-aware context packing for coding agents."""

    def __init__(self, crawler_manager, vector_store):
        self.crawler_manager = crawler_manager
        self.vector_store = vector_store

    def estimate_tokens(self, text: str) -> int:
        """Approximate token count. ~4 chars per token (conservative)."""
        return len(text) // 4

    def pack_snippets(
        self,
        results: list[CrawlResult],
        budget_tokens: int,
    ) -> tuple[list[ContextSnippet], int]:
        """
        Greedy fill: sort by score desc, accumulate until budget exhausted.

        Returns (packed_snippets, tokens_used).
        """
        candidates = []
        for r in results:
            content = r.content[:500] if r.content else ""
            tokens = self.estimate_tokens(content)
            candidates.append(ContextSnippet(
                title=r.title or "",
                content=content,
                url=r.url or "",
                source=r.source or "",
                language=r.metadata.get("language", "") if r.metadata else "",
                tokens=tokens,
            ))

        candidates.sort(key=lambda s: s.tokens, reverse=True)

        packed = []
        used = 0
        for snippet in candidates:
            if snippet.tokens == 0:
                continue
            if used + snippet.tokens > budget_tokens:
                continue
            packed.append(snippet)
            used += snippet.tokens

        return packed, used

    def format_context(self, snippets: list[ContextSnippet], query: str) -> str:
        """Format packed snippets into markdown string for agent injection."""
        if not snippets:
            return "No context found."

        lines = [f'## Context for: "{query}"', ""]
        for i, s in enumerate(snippets, 1):
            lines.append(f"[{i}] {s.title} — {s.source} ({s.tokens} tokens)")
            lines.append(f"    URL: {s.url}")
            if s.language:
                lines.append(f"    Language: {s.language}")
            lines.append(f"```{s.language or ''}")
            lines.append(s.content)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    async def search(
        self,
        query: str,
        budget_tokens: int = 8000,
        language: str = "",
        num_results: int = 20,
    ) -> ContextResult:
        """
        Full pipeline: crawl → dedup → pack → format.

        Flow:
        1. Search all sources concurrently
        2. Search vector store for indexed content
        3. Merge + deduplicate by URL
        4. Filter by language if specified
        5. Greedy pack into token budget
        6. Format output
        """
        start_time = datetime.now()

        # 1. Crawl all sources
        all_crawl = await self.crawler_manager.crawl_all(
            query,
            max_results_per_source=num_results // 2,
            generate_variations=False,
        )

        # 2. Vector store search
        vector_results = self.vector_store.search(query, limit=num_results)

        # 3. Merge + dedup
        all_results = all_crawl + vector_results
        seen = set()
        deduped = []
        for r in all_results:
            if r.url and r.url not in seen:
                seen.add(r.url)
                deduped.append(r)

        # 4. Filter by language
        if language:
            deduped = [
                r for r in deduped
                if (r.metadata or {}).get("language", "").lower() == language.lower()
                or language.lower() in (r.title or "").lower()
            ]

        # 5. Pack
        packed, tokens_used = self.pack_snippets(deduped, budget_tokens)

        # 6. Format
        formatted = self.format_context(packed, query)

        search_time = (datetime.now() - start_time).total_seconds() * 1000

        return ContextResult(
            query=query,
            snippets=packed,
            formatted=formatted,
            tokens_used=tokens_used,
            tokens_budget=budget_tokens,
            total_snippets_found=len(deduped),
            search_time_ms=search_time,
        )
