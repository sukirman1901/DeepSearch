# Design Spec: Docs Search Mode for DeepSearch

**Date:** 2026-07-17
**Status:** Approved
**Approach:** Hybrid (Config-driven + Smart Extraction)

---

## 1. Overview

Add a `docs` mode to the existing `search` tool in DeepSearch MCP that fetches programming documentation directly from official library/framework documentation sites (similar to Context7, but using our own crawler infrastructure).

**Key Goal:** Enable developers to query official documentation for React, Next.js, Vue, Supabase, Prisma, and any other library — with version-specific results, semantic search, and token-budget-aware output.

---

## 2. Problem Statement

Current DeepSearch tools (`search`, `code_context`, `context`) search general web content, GitHub repos, and Stack Overflow. None of them specifically target official documentation sites, which are the authoritative source for:

- API references
- Code examples
- Configuration guides
- Version-specific changes

Context7 solves this but is a separate MCP server with its own API. We want the same capability integrated into DeepSearch using our existing crawler infrastructure.

---

## 3. Requirements

### Functional Requirements

1. **Library Registry:** Define supported libraries via JSON config file
2. **Docs Crawling:** Crawl official documentation sites using generic crawler with config-driven extraction
3. **Semantic Search:** Store crawled docs in ChromaDB for semantic search
4. **Version Support:** Support version-specific documentation queries
5. **Token Budget:** Respect existing `tokens_target` parameter for output size
6. **Caching:** Auto-refresh docs cache based on TTL (default 7 days)
7. **Force Refresh:** Allow manual cache refresh via `docs_refresh=True`

### Non-Functional Requirements

1. **Scalable:** Support unlimited libraries via config
2. **Performance:** Crawl + index should complete within 30 seconds per library
3. **Reliability:** Graceful error handling for unreachable sites
4. **Extensible:** Easy to add new libraries without code changes

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    search tool (mode='docs')                     │
│                                                                  │
│   search(query="React hooks", mode="docs", library="react")     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    DocsSearchEngine (new)                        │
│                                                                  │
│   1. resolve_library("react") → LibraryConfig                   │
│   2. check_cache(library, query) → hit? return cached           │
│   3. crawl_docs(library_config, query) → list[CrawlResult]      │
│   4. index_to_vectorstore(results)                               │
│   5. search_vectorstore(query) → ranked results                 │
│   6. format_output(results, tokens_target)                       │
└───────────┬───────────────────────────┬─────────────────────────┘
            │                           │
┌───────────▼───────────┐  ┌────────────▼────────────────────────┐
│   LibraryRegistry     │  │   DocsCrawler (generic)             │
│                       │  │                                      │
│   - Load config JSON  │  │   1. Fetch start_paths dari config  │
│   - Resolve library   │  │   2. Discover links (sitemap/crawl) │
│   - Get crawl config  │  │   3. Filter by exclude_paths        │
│   - Validate library  │  │   4. Extract content (selective)    │
│                       │  │   5. Return list[CrawlResult]       │
└───────────────────────┘  └──────────────────────────────────────┘
                                      │
                            ┌─────────▼──────────────────────────┐
                            │   VectorStore (existing ChromaDB)   │
                            │   collection: "docs_search"         │
                            └─────────────────────────────────────┘
```

---

## 5. Data Models

### 5.1 LibraryConfig

```python
@dataclass
class LibraryConfig:
    id: str                          # "react", "nextjs", "vue"
    name: str                        # "React", "Next.js", "Vue"
    docs_url: str                    # "https://react.dev"
    start_paths: list[str]           # ["/reference", "/learn"]
    content_selector: str = "main"   # CSS selector untuk content area
    nav_selector: str = ""           # CSS selector untuk navigation links
    exclude_paths: list[str]         # ["/blog", "/community"]
    include_paths: list[str] = []    # Kosong = all paths
    version_url_pattern: str = ""    # "/v{version}"
    max_pages: int = 200             # Max pages per library
    ttl_hours: int = 168             # Auto-refresh interval
    language: str = "en"
```

### 5.2 DocsPage

```python
@dataclass
class DocsPage:
    library_id: str                  # "react"
    title: str                       # "useState"
    url: str                         # "https://react.dev/reference/react/useState"
    content: str                     # Clean markdown content
    code_examples: list[str]         # Extracted code blocks
    section: str                     # "reference", "learn", "api"
    version: str = ""                # "18.2.0" jika versioned
    crawled_at: datetime = field(default_factory=datetime.now)
```

### 5.3 DocsSearchResult

```python
@dataclass
class DocsSearchResult:
    query: str
    library: str                     # "react"
    pages: list[DocsPage]            # Ranked results
    formatted: str                   # Ready-to-display markdown
    tokens_used: int
    tokens_budget: int
    total_pages_found: int
    search_time_ms: float
```

---

## 6. Config Format

**File:** `mcp/data/docs_library_registry.json`

```json
{
  "version": "1.0",
  "libraries": {
    "react": {
      "name": "React",
      "docs_url": "https://react.dev",
      "start_paths": ["/reference", "/learn"],
      "content_selector": "main",
      "nav_selector": "aside a",
      "exclude_paths": ["/blog", "/community", "/versions", "/style-guide"],
      "include_paths": [],
      "max_pages": 200,
      "ttl_hours": 168
    },
    "nextjs": {
      "name": "Next.js",
      "docs_url": "https://nextjs.org/docs",
      "start_paths": ["/app", "/pages", "/api-reference"],
      "content_selector": "main",
      "nav_selector": "nav a",
      "exclude_paths": ["/blog", "/learn"],
      "include_paths": [],
      "max_pages": 300,
      "ttl_hours": 168
    },
    "vue": {
      "name": "Vue.js",
      "docs_url": "https://vuejs.org",
      "start_paths": ["/guide", "/api"],
      "content_selector": ".content",
      "nav_selector": ".sidebar a",
      "exclude_paths": ["/blog", "/partners"],
      "include_paths": [],
      "max_pages": 150,
      "ttl_hours": 168
    },
    "supabase": {
      "name": "Supabase",
      "docs_url": "https://supabase.com/docs",
      "start_paths": ["/guides/getting-started", "/reference"],
      "content_selector": "article",
      "nav_selector": "nav a",
      "exclude_paths": ["/blog", "/pricing"],
      "include_paths": [],
      "max_pages": 250,
      "ttl_hours": 168
    },
    "prisma": {
      "name": "Prisma",
      "docs_url": "https://www.prisma.io/docs",
      "start_paths": ["/orm", "/orm/more"],
      "content_selector": "main",
      "nav_selector": "nav a",
      "exclude_paths": ["/blog", "/community"],
      "include_paths": [],
      "max_pages": 200,
      "ttl_hours": 168
    }
  }
}
```

---

## 7. Tool Interface

### 7.1 Modified `search` Tool

```python
@mcp.tool()
async def search(
    query: str,
    mode: str = "basic",
    # ... existing params ...
    
    # NEW params untuk mode='docs'
    library: str = "",           # "react", "nextjs", "vue"
    version: str = "",           # "18.2.0" - optional
    docs_refresh: bool = False,  # Force refresh cache
) -> str:
    """
    Unified search tool — all search modes in one.

    Modes:
      - "basic": Semantic search across all indexed content (default)
      - "advanced": Search with domain/date/text/source filters
      - "quick": Real-time search without database (DuckDuckGo)
      - "stream": Search with streaming batches + timing metadata
      - "smart": Compact IR overview + full details for top N
      - "code": Search GitHub + Stack Overflow for code snippets
      - "context": Token-budget-aware snippet packing for agents
      - "docs": Search programming documentation from official library docs sites
      
    Args:
      # Docs mode:
      library: Library/framework name (required for docs mode)
      version: Specific version (optional, default: latest)
      docs_refresh: Force refresh docs cache (default: False)
    """
    
    # --- DOCS MODE ---
    if mode == "docs":
        if not library:
            available = ", ".join(docs_engine.registry.list_libraries())
            return f"Error: 'library' required for docs mode. Available: {available}"
        
        result = await docs_engine.search(
            query=query,
            library=library,
            version=version,
            force_refresh=docs_refresh,
            tokens_target=tokens_target,
        )
        return result.formatted
```

### 7.2 Usage Examples

```python
# Basic docs search
search(query="cara pakai useState", mode="docs", library="react")

# Specific version
search(query="middleware setup", mode="docs", library="nextjs", version="14")

# Force refresh cache
search(query="auth setup", mode="docs", library="supabase", docs_refresh=True)

# Token budget
search(query="routing patterns", mode="docs", library="vue", tokens_target=3000)
```

### 7.3 Output Format

```markdown
📚 Documentation: React — "cara pakai useState"

--- Page 1: useState — React (2.5k tokens) ---
URL: https://react.dev/reference/react/useState

`useState` is a React Hook that lets you add a state variable to your component.

```jsx
const [count, setCount] = useState(0);
```

When you call `useState`, React returns an array with two items:
1. The current state of the state variable
2. A function that lets you update it

...

--- Page 2: Adding State — Learn React (1.8k tokens) ---
URL: https://react.dev/learn/state-a-components-memory

...

📊 Stats: 2 pages | 4.3k tokens | Found 15 total pages
```

---

## 8. Error Handling

```python
# 1. Library not found
if library not in registry:
    available = ", ".join(registry.keys())
    return f"Library '{library}' not found. Available: {available}"

# 2. Docs site unreachable
try:
    pages = await crawler.crawl_docs(config, query)
except httpx.TimeoutException:
    return f"Timeout fetching docs for {library}. Try again later."
except httpx.HTTPStatusError as e:
    return f"HTTP {e.response.status_code} fetching docs for {library}."

# 3. No relevant pages found
if not pages:
    return f"No documentation pages found for '{query}' in {library} docs."

# 4. Cache expired → auto-refresh
if cache_expired(library):
    # Silently refresh in background
    pass

# 5. Library config invalid
if not config.get("docs_url"):
    return f"Invalid config for '{library}': missing docs_url"
```

---

## 9. File Structure

### New Files

| File | Purpose | LOC Estimate |
|------|---------|--------------|
| `mcp/search/docs_engine.py` | Main orchestrator | ~150 |
| `mcp/search/docs_crawler.py` | Generic docs crawler | ~200 |
| `mcp/search/docs_registry.py` | Config loader | ~80 |
| `mcp/data/docs_library_registry.json` | Library definitions | ~100 |

### Modified Files

| File | Change |
|------|--------|
| `mcp/server.py` | Add `mode="docs"` branch + params |
| `mcp/search/engine.py` | Import & init DocsSearchEngine |
| `mcp/db/vector_store.py` | Add `docs_search` collection |

---

## 10. Implementation Plan

### Phase 1: Foundation (Core)
1. Create `LibraryRegistry` class
2. Create `docs_library_registry.json` with 5 initial libraries
3. Create `DocsCrawler` class
4. Create `DocsSearchEngine` class
5. Add `docs_search` collection to VectorStore
6. Add `mode="docs"` to search tool
7. Test with single library (React)

### Phase 2: Polish
1. Add version support
2. Add force refresh capability
3. Add token budget integration
4. Add error handling
5. Test with multiple libraries

### Phase 3: Scale
1. Add more libraries to registry (10-20)
2. Add sitemap.xml support for better discovery
3. Add robots.txt compliance
4. Performance optimization

---

## 11. Success Criteria

1. ✅ `search(query="...", mode="docs", library="react")` returns relevant React docs
2. ✅ Code examples are extracted and displayed
3. ✅ Token budget is respected
4. ✅ Cache works (second query is faster)
5. ✅ Force refresh works
6. ✅ Error messages are helpful
7. ✅ Adding new library requires only JSON config change

---

## 12. Future Considerations

1. **Auto-discover docs URLs** from npm/GitHub metadata
2. **Multi-language support** for non-English docs
3. **Interactive docs browser** (browse by category, not just search)
4. **Diff between versions** (show what changed in React 18 vs 19)
5. **Community contributions** for library configs

---

## Appendix A: Comparison with Context7

| Aspect | Context7 | DeepSearch Docs Mode |
|--------|----------|---------------------|
| Data source | Private indexed docs | Live crawl official sites |
| Latency | Fast (pre-indexed) | Slower (on-demand crawl) |
| Freshness | Updated within days | On-demand (TTL-based) |
| Coverage | 1000+ libraries | Unlimited (config-driven) |
| Cost | API key required | Free (self-hosted) |
| Integration | Separate MCP server | Integrated into DeepSearch |

## Appendix B: Relevant Existing Code

- `mcp/search/code_context.py` — Pattern reference for standalone search module
- `mcp/search/context.py` — Pattern reference for token-budget packing
- `mcp/crawlers/base.py` — CrawlResult dataclass, BaseCrawler interface
- `mcp/crawlers/manager.py` — CrawlerManager for parallel dispatch
- `mcp/db/vector_store.py` — VectorStore for ChromaDB integration
