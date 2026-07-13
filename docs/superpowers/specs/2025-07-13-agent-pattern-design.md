# Agent Pattern (Deep Research) Design Spec

## Overview

Add async deep research sessions with auto sub-queries and semantic follow-up. User starts a research session on a topic, system auto-generates sub-queries, crawls all sources, indexes results in a per-session ChromaDB collection. User can then ask follow-up questions that semantically search within the session's collected results.

Inspired by Exa's Agent API with `previousRunId` for follow-up queries.

## Motivation

For complex research tasks ("Find all AI startups in SF"), a single search query misses relevant results. The Agent pattern:
1. Auto-generates sub-query variations to get broader coverage
2. Indexes all results in a session for semantic follow-up
3. Lets users ask natural language follow-ups about the collected data

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Session model | Session + auto sub-queries + follow-up | Most comprehensive — Exa-like |
| Follow-up search | Semantic search in session via ChromaDB | Leverages existing embeddings infrastructure |
| Session storage | ChromaDB collection per session + JSON metadata | Semantic search + persistence |
| Tool count | 4 tools (CRUD) | Matches Monitors API pattern |
| Sub-query generation | Existing QueryVariationGenerator | No new code, already tested |

## Architecture

### New Module: `mcp/search/research.py`

```python
class ResearchManager:
    """Deep research sessions with auto sub-queries and semantic follow-up."""

    def __init__(self, chromadb_client, embedding_model, data_file="data/research_sessions.json"):
        self.chromadb_client = chromadb_client
        self.embedding_model = embedding_model
        self.data_file = data_file
        self.sessions: dict = {}
        self._load()

    async def start_research(self, query, sources=None, max_results=15, crawler_manager=None, query_generator=None) -> dict:
        """Start a research session. Auto-generates sub-queries, crawls, indexes."""

    def ask_followup(self, session_id, query, num_results=5) -> list[CrawlResult]:
        """Semantic search within a session's indexed results."""

    def list_sessions(self) -> list[dict]:
        """List all research sessions with stats."""

    def delete_session(self, session_id) -> bool:
        """Delete a session and its ChromaDB collection."""

    def _load(self):
        """Load session metadata from JSON."""

    def _save(self):
        """Save session metadata to JSON."""
```

### Session JSON Structure

File: `mcp/data/research_sessions.json`

```json
{
  "sessions": {
    "a1b2c3d4": {
      "query": "AI startups in SF",
      "sources": ["web", "reddit"],
      "created_at": "2025-07-13T22:00:00",
      "result_count": 45,
      "followup_count": 3,
      "sub_queries": ["AI startups in SF", "artificial intelligence companies San Francisco", "AI founders Bay Area"]
    }
  }
}
```

### Data Flow

```
start_research(query="AI startups in SF", sources="web,reddit", max_results=15)
  → generate session_id (uuid4[:8])
  → generate sub-queries via QueryVariationGenerator.generate_variations(query, category, max_variations=3)
  → for each sub-query: crawler_manager.crawl_all(sub_query, sources, max_results)
  → merge all results, deduplicate by URL
  → create ChromaDB collection "session_{id}"
  → index all results: embedding + content + metadata
  → save session metadata to JSON
  → return {session_id, result_count, sub_queries, top_titles}

ask_followup(session_id="a1b2c3d4", query="funding rounds", num_results=5)
  → get ChromaDB collection "session_{id}"
  → embedding_model.embed(query)
  → collection.query(query_embeddings, n_results=num_results)
  → increment followup_count
  → return CrawlResult list

list_sessions()
  → return all sessions with stats

delete_session(session_id)
  → chromadb_client.delete_collection("session_{id}")
  → remove from JSON
```

### MCP Tools (4 new)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `start_research` | query, sources (optional), max_results (default 15) | session_id + result count + top 5 titles |
| `ask_followup` | session_id, query, num_results (default 5) | semantic search results from session |
| `list_sessions` | none | formatted list with stats |
| `delete_session` | session_id | success/failure message |

### Modified: `mcp/server.py`

- Import `ResearchManager`
- Instantiate `research_manager = ResearchManager(engine.vector_store.client, engine.vector_store.embedding_model)`
- Add 4 new MCP tools
- Total tools: 20 (16 existing + 4 new)

## Error Handling

| Scenario | Behavior |
|----------|----------|
| research_sessions.json doesn't exist | Create empty on first save |
| research_sessions.json corrupted | Start with empty sessions |
| ask_followup with invalid session_id | Return "Session not found" |
| delete_session with invalid ID | Return "not found" |
| start_research crawl fails partially | Return partial results, still create session |
| ChromaDB collection creation fails | Return error, don't create session |

## Testing Strategy

### Unit Tests: `mcp/tests/test_search/test_research.py`

1. `test_start_research_creates_session` — Creates session, returns ID + result count
2. `test_start_research_auto_generates_subqueries` — Verify multiple sub-queries used
3. `test_ask_followup_returns_semantic_results` — Follow-up query returns results from session
4. `test_ask_followup_invalid_session` — Invalid ID returns empty list
5. `test_list_sessions` — Multiple sessions listed with correct stats
6. `test_delete_session` — Delete removes session + collection
7. `test_delete_session_invalid_id` — Delete non-existent returns False
8. `test_persistence` — Create session, new ResearchManager with same file, verify loaded

### Test mocks
- Mock `CrawlerManager.crawl_all` with `AsyncMock`
- Mock `QueryVariationGenerator.generate_variations` to return predictable sub-queries
- Use real ChromaDB client (in-memory) for collection tests
- Use `tmp_path` fixture for JSON file testing

## Dependencies

No new packages. Uses:
- `uuid` (stdlib) — session IDs
- `json`, `os` (stdlib) — persistence
- `datetime` (stdlib) — timestamps
- Existing `CrawlerManager.crawl_all()` — for crawling
- Existing `QueryVariationGenerator` — for sub-query generation
- Existing `ChromaDB client` + `EmbeddingModel` — for session collections

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `mcp/search/research.py` | CREATE | ResearchManager class |
| `mcp/data/research_sessions.json` | AUTO-CREATE | Created on first save |
| `mcp/server.py` | MODIFY | Add 4 new MCP tools |
| `mcp/tests/test_search/test_research.py` | CREATE | 8 unit tests |

## Success Criteria

- `start_research(query="AI startups")` auto-generates sub-queries, crawls, indexes, returns session ID
- `ask_followup(session_id, query="funding")` returns semantic search results from session
- `list_sessions()` shows all sessions with result_count and followup_count
- `delete_session(id)` removes session + ChromaDB collection
- Sessions persist across restarts (JSON metadata)
- All existing 98 tests still pass
- 8 new tests pass
- Total: 106 tests passing
