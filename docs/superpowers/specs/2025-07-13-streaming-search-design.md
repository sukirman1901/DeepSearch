# Streaming Search Design Spec

**Date:** 2025-07-13
**Status:** Draft
**Author:** Superpowers

## Problem

Current `deep_search` uses `asyncio.gather` — waits for all 7 sources to complete before returning. Fast sources (DuckDuckGo, Wikipedia) finish in <1s, but slow sources (Twitter/Nitter, Reddit) can take 3-5s. Agent waits for the slowest source even if fast results are sufficient.

## Solution

Stream search — use `asyncio.as_completed` to yield results as each source finishes. Return JSON with batches grouped by completion order + timing metadata. Agent sees fast results first, can start synthesizing immediately.

## Data Flow

```
Agent → stream_search(query)
  → CrawlerManager.crawl_all_streaming(query)
    → asyncio.as_completed (not gather)
    → DuckDuckGo finishes first (0.3s) → batch 1
    → GitHub finishes (0.8s) → batch 2
    → Reddit finishes (3.2s) → batch 3
  → Return StreamSearchResult (JSON with batches + timing)
```

## Changes to CrawlerManager

New method `crawl_all_streaming` — same logic as `crawl_all` but uses `as_completed`:

```python
async def crawl_all_streaming(self, query, ...) -> AsyncGenerator[tuple[str, list[CrawlResult]], None]:
    """Yield (source_name, results) as each source completes."""
    tasks = {}
    for source_name in sources:
        if source_name in self.crawlers:
            task = asyncio.create_task(self._crawl_safe(...))
            tasks[task] = source_name

    for completed in asyncio.as_completed(list(tasks.keys())):
        source_name = tasks[completed]
        results = await completed
        yield source_name, results
```

## New Module: `mcp/search/streaming.py`

```python
@dataclass
class StreamBatch:
    """Results from one source, with timing."""
    batch_number: int
    source: str
    time_ms: float
    result_count: int
    results: list[dict]  # serialized CrawlResult

@dataclass
class StreamSearchResult:
    """Complete streaming search result."""
    query: str
    total_results: int
    total_time_ms: float
    batches: list[StreamBatch]
    sources_searched: list[str]
```

### StreamSearchManager

```python
class StreamSearchManager:
    def __init__(self, crawler_manager, vector_store):
        self.crawler_manager = crawler_manager
        self.vector_store = vector_store

    async def search(self, query, num_results=10, sources=None) -> StreamSearchResult:
        """Run streaming search, collect all batches."""
        start = datetime.now()
        batches = []
        all_results = []

        batch_num = 0
        async for source_name, results in self.crawler_manager.crawl_all_streaming(query, sources=sources):
            batch_num += 1
            elapsed = (datetime.now() - start).total_seconds() * 1000
            batches.append(StreamBatch(
                batch_number=batch_num,
                source=source_name,
                time_ms=elapsed,
                result_count=len(results),
                results=[self._serialize(r) for r in results[:num_results]],
            ))
            all_results.extend(results)

        total_time = (datetime.now() - start).total_seconds() * 1000

        return StreamSearchResult(
            query=query,
            total_results=len(all_results),
            total_time_ms=total_time,
            batches=batches,
            sources_searched=[b.source for b in batches],
        )
```

## MCP Tool: `stream_search`

```python
@mcp.tool()
async def stream_search(
    query: str,
    num_results: int = 10,
    sources: str = "",
) -> str:
    """
    Search with streaming — results grouped by completion order.

    Returns JSON with batches showing which source finished first
    and timing metadata. Faster sources appear earlier.

    Args:
        query: Search query
        num_results: Max results per source
        sources: Comma-separated sources (empty = all)
    """
```

### Output Format

```json
{
  "query": "fastapi websocket",
  "total_results": 12,
  "total_time_ms": 1200,
  "batches": [
    {
      "batch": 1,
      "source": "duckduckgo",
      "time_ms": 300,
      "result_count": 3,
      "results": [{"title": "...", "url": "...", "content": "..."}]
    },
    {
      "batch": 2,
      "source": "github",
      "time_ms": 800,
      "result_count": 4,
      "results": [...]
    }
  ]
}
```

## Tests

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_crawl_all_streaming_yields_results` | Yields at least one batch |
| 2 | `test_crawl_all_streaming_order` | Faster source appears first |
| 3 | `test_stream_search_returns_batches` | StreamSearchResult has batches |
| 4 | `test_stream_search_timing` | total_time_ms > 0 |
| 5 | `test_stream_search_deduplicates` | Same URL appears once |
| 6 | `test_stream_search_sources_filter` | Only requested sources searched |
| 7 | `test_stream_search_empty` | Empty query returns empty result |
| 8 | `test_serialize_crawl_result` | CrawlResult → dict correctly |

## File Changes

| File | Change |
|------|--------|
| `mcp/crawlers/manager.py` | Add `crawl_all_streaming` method |
| `mcp/search/streaming.py` | NEW — StreamSearchManager, StreamBatch, StreamSearchResult |
| `mcp/tests/test_search/test_streaming.py` | NEW — 8 tests |
| `mcp/tests/test_crawlers/test_manager_streaming.py` | NEW — 2 streaming-specific tests |
| `mcp/server.py` | Add `stream_search` tool |

## Scope

- `as_completed` for concurrency (not true SSE/WebSocket streaming)
- JSON output (not SSE events)
- Batches grouped by completion order
- No incremental agent notification (agent receives complete JSON)

## Verification

```bash
cd mcp && .venv/bin/python3 -m pytest tests/ -q
# Target: 127 tests (117 existing + 10 new)
```
