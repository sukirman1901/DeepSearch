# Tavily-Inspired Features for DeepSearch

## Overview
Add 5 Tavily-inspired features to DeepSearch: search_depth, topic filter, site mapping, content extraction, and max_age freshness.

## Features

### 1. search_depth Parameter
- Add to `deep_search` and `advanced_search` tools
- `basic`: Top 5 results per source, no reranking (fast)
- `advanced`: Top 20 per source + ChromaDB semantic rerank (thorough)
- `fast`: Top 3 per source, skip semantic (instant)
- Implementation: Modifies `SearchEngine.search()` to control `max_results_per_source` and whether to apply ChromaDB reranking

### 2. topic Filter
- Add `topic` param (default: `general`)
- `general`: Standard search (current behavior)
- `news`: Boost recent results, prefer news sites, exclude old content
- Implementation: Post-filter in `SearchEngine`, boost news domains, apply `max_age=168h` implicitly

### 3. Site Mapping Tool
- New MCP tool `site_map`
- BFS traversal using `SubpageDiscoverer`
- `max_depth` (default 2), `instructions` (NL filter), `max_pages` (default 50)
- New file: `mcp/search/sitemap.py`

### 4. Extract Tool
- New MCP tool `extract_content`
- Batch URL extraction with `extract_depth` (basic/advanced)
- `instructions` param for what to extract
- New file: `mcp/search/extract.py`

### 5. max_age Freshness Filter
- Add `max_age_hours` param to `deep_search` and `advanced_search`
- `-1` = no limit, `1` = last hour, `24` = last day, `168` = last week
- Post-filter results by `result.timestamp`

## Impact
- 2 new files: `sitemap.py`, `extract.py`
- Modified files: `engine.py`, `server.py`
- 31 MCP tools total (was 29)
- ~170 tests (was 153)

## Testing
- Unit tests for each feature
- Integration tests for new tools
- All existing tests must pass
