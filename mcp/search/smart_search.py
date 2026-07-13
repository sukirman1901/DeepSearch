"""
Knowledge IR + Context Optimizer — Hybrid token-efficient search.
Compacts raw results into IR, then optimizes context for host AI.
"""
from dataclasses import dataclass, field

from crawlers.base import CrawlResult


@dataclass
class KnowledgeIR:
    """Intermediate Representation — compact single-line summary."""
    n: int
    title: str
    source: str
    url: str
    score: float
    summary: str

    def to_dict(self):
        return {
            "n": self.n,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "score": self.score,
            "summary": self.summary,
        }

    def to_line(self) -> str:
        """One-line IR format (~30 tokens)."""
        return f"[{self.n}] {self.title} | {self.source} | {self.url} | score:{self.score:.1f} | {self.summary}"


@dataclass
class DetailItem:
    """Full content for selected items."""
    n: int
    title: str
    url: str
    source: str
    content: str

    def to_dict(self):
        return {
            "n": self.n,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "content": self.content,
        }


@dataclass
class SmartSearchResult:
    """Hybrid result: compact overview + full details for top N."""
    query: str
    overview: list[KnowledgeIR] = field(default_factory=list)
    details: list[DetailItem] = field(default_factory=list)
    total_results: int = 0
    details_count: int = 0
    tokens_overview: int = 0
    tokens_details: int = 0
    tokens_saved_pct: float = 0.0


class KnowledgeCompiler:
    """Compile raw CrawlResults into compact IR."""

    def compile(self, results: list[CrawlResult]) -> list[KnowledgeIR]:
        """Convert results to IR format."""
        ir_items = []
        for i, r in enumerate(results, 1):
            summary = self._make_summary(r)
            ir_items.append(KnowledgeIR(
                n=i,
                title=r.title or "Untitled",
                source=r.source or "unknown",
                url=r.url or "",
                score=r.score or 0.0,
                summary=summary,
            ))
        return ir_items

    def _make_summary(self, result: CrawlResult) -> str:
        """Generate 1-line summary from content (~15 words)."""
        content = result.content or ""
        if not content:
            return result.description if hasattr(result, "description") else ""

        # Take first sentence or first 100 chars
        first_sentence = content.split(". ")[0] if ". " in content else content[:100]
        # Trim to ~100 chars
        if len(first_sentence) > 100:
            first_sentence = first_sentence[:97] + "..."
        return first_sentence.replace("\n", " ").strip()


class ContextOptimizer:
    """Select top items by score, return overview + full details."""

    def optimize(
        self,
        ir_items: list[KnowledgeIR],
        results: list[CrawlResult],
        top_full: int = 3,
        max_overview_tokens: int = 500,
    ) -> tuple[list[KnowledgeIR], list[DetailItem], int, int]:
        """
        Two-pass optimization:
        1. Overview: all IR items (compact)
        2. Details: full content for top N by score

        Returns (overview, details, tokens_overview, tokens_details).
        """
        # Pass 1: Overview — all IR items, limited by token budget
        overview = []
        tokens_overview = 0
        for ir in ir_items:
            line_tokens = len(ir.to_line()) // 4
            if tokens_overview + line_tokens > max_overview_tokens:
                break
            overview.append(ir)
            tokens_overview += line_tokens

        # Pass 2: Details — top N by score
        scored = sorted(
            zip(ir_items, results),
            key=lambda x: x[0].score,
            reverse=True,
        )
        details = []
        tokens_details = 0
        for ir, r in scored[:top_full]:
            content = (r.content or "")[:500]
            detail_tokens = len(content) // 4
            details.append(DetailItem(
                n=ir.n,
                title=ir.title,
                url=ir.url,
                source=ir.source,
                content=content,
            ))
            tokens_details += detail_tokens

        return overview, details, tokens_overview, tokens_details


class SmartSearchEngine:
    """Hybrid search: compile → optimize → return."""

    def __init__(self, crawler_manager, vector_store):
        self.crawler_manager = crawler_manager
        self.vector_store = vector_store
        self.compiler = KnowledgeCompiler()
        self.optimizer = ContextOptimizer()

    async def search(
        self,
        query: str,
        top_full: int = 3,
        num_results: int = 10,
        max_overview_tokens: int = 500,
    ) -> SmartSearchResult:
        """
        Hybrid search: IR overview + full details for top N.

        Flow:
        1. Crawl all sources
        2. Merge + dedup + rank
        3. Compile to IR (compact)
        4. Optimize: overview all + details top N
        5. Calculate token savings
        """
        # 1. Crawl
        all_crawl = await self.crawler_manager.crawl_all(
            query,
            max_results_per_source=num_results,
            generate_variations=False,
        )

        # 2. Vector store
        vector_results = self.vector_store.search(query, limit=num_results)

        # 3. Merge + dedup
        all_results = all_crawl + vector_results
        seen = set()
        deduped = []
        for r in all_results:
            if r.url and r.url not in seen:
                seen.add(r.url)
                deduped.append(r)

        # 4. Sort by score
        deduped.sort(key=lambda r: r.score or 0, reverse=True)
        deduped = deduped[:num_results]

        # 5. Compile to IR
        ir_items = self.compiler.compile(deduped)

        # 6. Optimize
        overview, details, tokens_overview, tokens_details = self.optimizer.optimize(
            ir_items, deduped, top_full, max_overview_tokens,
        )

        # 7. Calculate savings
        tokens_raw = sum(len((r.content or "")[:500]) // 4 for r in deduped)
        tokens_optimized = tokens_overview + tokens_details
        savings_pct = max(0, (1 - tokens_optimized / max(tokens_raw, 1)) * 100)

        return SmartSearchResult(
            query=query,
            overview=overview,
            details=details,
            total_results=len(deduped),
            details_count=len(details),
            tokens_overview=tokens_overview,
            tokens_details=tokens_details,
            tokens_saved_pct=round(savings_pct, 1),
        )
