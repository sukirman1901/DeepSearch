"""
Streaming Search — Results grouped by completion order with timing metadata.
Uses asyncio.as_completed to yield results as each source finishes.
"""
from dataclasses import dataclass, field
from datetime import datetime

from crawlers.base import CrawlResult


@dataclass
class StreamBatch:
    """Results from one source, with timing."""
    batch_number: int
    source: str
    time_ms: float
    result_count: int
    results: list[dict] = field(default_factory=list)


@dataclass
class StreamSearchResult:
    """Complete streaming search result."""
    query: str
    total_results: int = 0
    total_time_ms: float = 0.0
    batches: list[StreamBatch] = field(default_factory=list)
    sources_searched: list[str] = field(default_factory=list)


class StreamSearchManager:
    """Streaming search using as_completed for concurrent source yielding."""

    def __init__(self, crawler_manager, vector_store):
        self.crawler_manager = crawler_manager
        self.vector_store = vector_store

    def _serialize_result(self, result: CrawlResult) -> dict:
        """Convert CrawlResult to dict for JSON output."""
        return {
            "title": result.title or "",
            "url": result.url or "",
            "content": (result.content or "")[:500],
            "source": result.source or "",
            "score": result.score or 0.0,
            "metadata": result.metadata or {},
        }

    async def search(
        self,
        query: str,
        num_results: int = 10,
        sources: list[str] = None,
    ) -> StreamSearchResult:
        """
        Run streaming search, collect all batches.

        Yields (source_name, results) as each source completes,
        then returns aggregated StreamSearchResult.
        """
        start = datetime.now()
        batches = []
        all_results = []
        batch_num = 0

        async for source_name, results in self.crawler_manager.crawl_all_streaming(
            query=query,
            max_results_per_source=num_results,
            sources=sources,
            generate_variations=False,
        ):
            batch_num += 1
            elapsed = (datetime.now() - start).total_seconds() * 1000
            batches.append(StreamBatch(
                batch_number=batch_num,
                source=source_name,
                time_ms=round(elapsed, 1),
                result_count=len(results),
                results=[self._serialize_result(r) for r in results[:num_results]],
            ))
            all_results.extend(results)

        total_time = (datetime.now() - start).total_seconds() * 1000

        return StreamSearchResult(
            query=query,
            total_results=len(all_results),
            total_time_ms=round(total_time, 1),
            batches=batches,
            sources_searched=[b.source for b in batches],
        )
