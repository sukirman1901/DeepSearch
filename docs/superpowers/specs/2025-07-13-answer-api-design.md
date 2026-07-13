# Design Spec: DeepSearch Answer API

## Overview

Add an `answer` MCP tool that searches all 7 sources, formats results with numbered citations, and returns a synthesis prompt for the host AI to generate answers. Zero additional cost — leverages the AI host's LLM.

## Motivation

Exa's Answer API provides direct LLM answers with citations in one call. DeepSearch can match this by using the host AI (OpenCode/Cursor/Claude) as the synthesis engine, avoiding any additional LLM dependency.

## Architecture

```
User: "Berapa valuasi SpaceX?"
    ↓
answer(query="Berapa valuasi SpaceX?")
    ↓
AnswerEngine
  ├─ Search all 7 sources concurrently (asyncio.gather)
  ├─ Deduplicate by URL
  ├─ Rank by relevance score
  ├─ Select top N results
  └─ Format context with numbered citations
    ↓
Return AnswerResult
  ├─ context: Numbered sources with excerpts
  ├─ synthesis_prompt: Instructions for AI
  └─ sources: List of source metadata
    ↓
AI Host synthesizes answer with inline citations [1][2]
```

## Components

### 1. `mcp/search/answer.py` (NEW)

```python
from dataclasses import dataclass, field

@dataclass
class AnswerResult:
    """Result from AnswerEngine."""
    query: str
    context: str              # Formatted sources with numbers
    synthesis_prompt: str      # Instructions for AI host
    sources: list[dict] = field(default_factory=list)  # [{title, url, source, excerpt}]


class AnswerEngine:
    """Search all sources and format for AI synthesis."""
    
    def __init__(self, crawler_manager, vector_store):
        self.crawler_manager = crawler_manager
        self.vector_store = vector_store
    
    async def answer(
        self,
        query: str,
        num_results: int = 10,
        output_schema: dict = None,
        system_prompt: str = "",
    ) -> AnswerResult:
        """
        Search all sources and return context + synthesis prompt.
        
        Flow:
        1. Search all 7 sources concurrently
        2. Also search vector store for indexed content
        3. Merge + deduplicate by URL
        4. Rank by relevance score
        5. Select top num_results
        6. Format context block
        7. Generate synthesis prompt
        """
        ...
    
    def _format_context(self, results: list, query: str) -> tuple[str, list[dict]]:
        """Format results into numbered context block."""
        ...
    
    def _build_synthesis_prompt(
        self, 
        query: str, 
        output_schema: dict = None,
        system_prompt: str = "",
    ) -> str:
        """Build instructions for AI host synthesis."""
        ...
```

### 2. MCP Tool: `answer`

```python
@mcp.tool()
async def answer(
    query: str,
    num_results: int = 10,
    output_schema: str = "",
    system_prompt: str = "",
) -> str:
    """
    Search all sources and return context for AI-powered answer with citations.
    
    Args:
        query: The question to answer
        num_results: Maximum sources to include (default 10)
        output_schema: Optional JSON schema string for structured output
        system_prompt: Optional custom instructions for the answer
    
    Returns:
        Formatted context with numbered sources and synthesis instructions.
        The AI host will use this to generate the final answer.
    """
    ...
```

### 3. Integration with `server.py`

```python
from search.answer import AnswerEngine

# Access internal components from SearchEngine
crawler_manager = engine.crawler_manager
vector_store = engine.vector_store

answer_engine = AnswerEngine(crawler_manager, vector_store)
```

- Add `from search.answer import AnswerEngine` import
- Extract `crawler_manager` and `vector_store` from existing `SearchEngine`
- Instantiate `AnswerEngine` with those components
- Add `answer` tool to MCP server

**Note:** `SearchEngine` is NOT modified. `AnswerEngine` is a standalone module that takes the same dependencies.

## Output Format

### Default (plain text)
```
## Sources for: "Berapa valuasi SpaceX?"

[1] SpaceX valued at $350bn — The Guardian
    URL: https://www.theguardian.com/...
    Excerpt: SpaceX valued at $350 billion as company agrees...

[2] SpaceX latest valuation — Reuters
    URL: https://www.reuters.com/...
    Excerpt: The company was valued at...

## Instructions
Answer the question: "Berapa valuasi SpaceX terakhir?"
Use inline citations [1][2] to reference sources.
If information is insufficient, state what's missing.
Base your answer ONLY on the sources provided.
```

### With output_schema
```
[... same sources ...]

## Instructions
Answer the question: "Berapa valuasi SpaceX terakhir?"
Use inline citations [1][2] to reference sources.

## Output Format
Return a JSON object matching this schema:
{
  "type": "object",
  "properties": {
    "valuation": {"type": "string"},
    "source_count": {"type": "number"}
  },
  "required": ["valuation"]
}
```

### With system_prompt
```
[... same sources ...]

## Instructions
You are a financial analyst. Answer concisely.
Use inline citations [1][2].
```

## Search Strategy

1. **Concurrent crawl**: `asyncio.gather()` all 7 crawlers
2. **Vector search**: Search ChromaDB for indexed content
3. **Merge**: Combine crawl + vector results
4. **Deduplicate**: By URL (same URL = same source)
5. **Rank**: By relevance score (vector similarity + crawl score)
6. **Select**: Top N results by score

## Deduplication Logic

```python
seen_urls = set()
deduped = []
for result in sorted_results:
    if result.url not in seen_urls:
        seen_urls.add(result.url)
        deduped.append(result)
```

## Testing

### Unit Tests: `mcp/tests/test_search/test_answer.py`

| Test | Description |
|------|-------------|
| `test_answer_searches_all_sources` | Verify all 7 crawlers are called |
| `test_answer_deduplicates_by_url` | Same URL from multiple sources = 1 result |
| `test_answer_formats_citations` | Output has [1], [2] format |
| `test_answer_with_output_schema` | Schema included in synthesis prompt |
| `test_answer_empty_results` | Graceful handling when no results |
| `test_answer_with_custom_prompt` | system_prompt included in output |
| `test_answer_respects_num_results` | Limit is respected |
| `test_answer_includes_metadata` | Source name, URL, excerpt present |

### Integration Test

```python
async def test_answer_integration():
    engine = SearchEngine()
    result = await engine.answer("What is Python?")
    assert "[1]" in result.context
    assert "Sources for:" in result.context
    assert len(result.sources) > 0
```

## Dependencies

- Existing: `CrawlerManager`, `VectorStore`
- No new packages required
- Reuses existing crawler infrastructure

## Files Modified

| File | Change |
|------|--------|
| `mcp/search/answer.py` | NEW — AnswerEngine + AnswerResult |
| `mcp/server.py` | Add `answer` tool |
| `mcp/tests/test_search/test_answer.py` | NEW — unit tests |

## Files NOT Modified

- `crawlers/` — No changes needed, existing crawl() works
- `search/engine.py` — Optional integration, can be added later
- `db/` — No changes needed
