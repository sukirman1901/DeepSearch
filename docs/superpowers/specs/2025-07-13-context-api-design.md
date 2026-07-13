# Context API Design Spec

**Date:** 2025-07-13
**Status:** Draft
**Author:** Superpowers

## Problem

Code agents (OpenCode, Cursor, Codex) need to inject search results into their context, but have limited token budgets. Current `code_search` tool returns all results regardless of token cost. Agents waste tokens or truncate arbitrarily.

## Solution

Context API — token-budget-aware snippet packing. Searches sources, estimates tokens per snippet, greedily fills budget, returns structured result with token usage stats. No AI API calls — pure utility logic for host AI consumption.

## Data Flow

```
Agent → context_search(query, budget_tokens=8000)
  → SearchEngine crawls all sources
  → Merge + deduplicate results
  → Estimate tokens per snippet (len(text) // 4)
  → Sort by score desc
  → Greedy fill: accumulate snippets until budget full
  → Return ContextResult with formatted string + stats
```

## New Module: `mcp/search/context.py`

### Dataclasses

```python
@dataclass
class ContextSnippet:
    """Single code/doc snippet with token estimate."""
    title: str
    content: str
    url: str
    source: str          # github, stackoverflow, web, etc.
    language: str = ""
    tokens: int = 0      # estimated tokens for this snippet

@dataclass
class ContextResult:
    """Result from context_search."""
    query: str
    snippets: list[ContextSnippet]   # budget-fitted subset
    formatted: str                    # ready-to-inject markdown string
    tokens_used: int                  # total tokens in fitted snippets
    tokens_budget: int                # requested budget
    total_snippets_found: int         # before budget filtering
    search_time_ms: float = 0.0
```

### ContextEngine Class

```python
class ContextEngine:
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
    ) -> list[ContextSnippet]:
        """Greedy fill: sort by score, accumulate until budget exhausted."""
        # Convert CrawlResult → ContextSnippet with token estimates
        # Sort by score desc
        # Accumulate tokens, stop when next snippet would exceed budget
        pass

    def format_context(self, snippets: list[ContextSnippet], query: str) -> str:
        """Format packed snippets into markdown string for agent injection."""
        # Returns structured markdown with source URLs
        pass

    async def search(
        self,
        query: str,
        budget_tokens: int = 8000,
        num_results: int = 20,
    ) -> ContextResult:
        """Full pipeline: crawl → dedup → pack → format."""
        pass
```

### Token Estimation

`len(text) // 4` — conservative approximation. Real tokenizers vary (1.3–4 chars/token depending on content), but `// 4` provides ~25% headroom. Agents can adjust `budget_tokens` based on their actual limits.

### Greedy Fill Algorithm

1. Convert all `CrawlResult` → `ContextSnippet` (with `tokens = estimate_tokens(content[:500])`)
2. Sort by `score` descending (highest relevance first)
3. Accumulate `tokens_used += snippet.tokens`
4. If `tokens_used + next_token_estimate > budget_tokens`, stop
5. Return fitted subset

## MCP Tool: `context_search`

```python
@mcp.tool()
async def context_search(
    query: str,
    budget_tokens: int = 8000,
    language: str = "",
    num_results: int = 20,
) -> str:
    """
    Search code and docs with token budget limit.

    Returns snippets that fit within the token budget,
    ready to inject into your context window.

    Args:
        query: What to search for
        budget_tokens: Max tokens for returned context (default 8000)
        language: Filter by programming language
        num_results: Max results to consider before budget packing
    """
```

### Tool Output Format

```
Context search results (6,240 / 8,000 tokens):

[1] FastAPI WebSocket Tutorial — web
    Tokens: 1,400
    URL: https://example.com/fastapi-ws
    ```python
    from fastapi import FastAPI, WebSocket
    app = FastAPI()
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        ...
    ```

[2] React Hook Patterns — github
    Tokens: 1,200
    URL: https://github.com/example/react-hooks
    ```javascript
    const useDebounce = (value, delay) => {
      ...
    };
    ```

...

Budget: 8,000 tokens | Used: 6,240 | Snippets: 6 of 15 considered
```

## Tests: `mcp/tests/test_search/test_context.py`

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_estimate_tokens` | `estimate_tokens("a" * 100)` == 25 |
| 2 | `test_pack_snippets_fits_budget` | 3 snippets under 500 tokens all included |
| 3 | `test_pack_snippets_respects_budget` | Large snippet skipped when budget full |
| 4 | `test_format_context_markdown` | Output contains titles, URLs, code blocks |
| 5 | `test_format_empty` | Empty snippets returns "No context found" |
| 6 | `test_search_returns_result` | Returns ContextResult with tokens_used <= budget |
| 7 | `test_search_deduplicates` | Same URL appears once |
| 8 | `test_token_usage_stats` | tokens_used reflects actual packed tokens |

## Dependencies

- `crawlers.base.CrawlResult` — input type
- `search.engine.SearchEngine` — crawl + vector search
- No new packages

## File Changes

| File | Change |
|------|--------|
| `mcp/search/context.py` | NEW — ContextEngine, ContextSnippet, ContextResult |
| `mcp/tests/test_search/test_context.py` | NEW — 8 tests |
| `mcp/server.py` | Add `context_search` tool |

## Scope

- Token estimation only (no external tokenizer)
- Greedy fill (no knapsack optimization)
- Single budget parameter (no min/max range)
- No streaming — returns complete result

## Verification

```bash
cd mcp && .venv/bin/python3 -m pytest tests/ -q
# Target: 114 tests (106 existing + 8 new)
```
