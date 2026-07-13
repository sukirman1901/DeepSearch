# Deep Search — Contributor Guidelines

## If You Are an AI Agent

This plugin provides a Deep Search Engine MCP server with 7 data sources, 10 consolidated tools, and semantic search capabilities via ChromaDB.

## MCP Server Setup

The Deep Search MCP server provides semantic search tools via stdio transport.

### Install Python dependencies

```bash
cd mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure MCP server

Add to your agent's MCP configuration:

```json
{
  "mcpServers": {
    "deep-search": {
      "command": "/path/to/DeepSearch/mcp/.venv/bin/python3",
      "args": ["server.py"],
      "cwd": "/path/to/DeepSearch/mcp"
    }
  }
}
```

### Verify

```bash
cd mcp
python server.py
```

Expected: Server starts without errors.

## Available Tools (10)

### `search` — Unified Search (7 modes)
The main search tool. Use `mode` parameter to switch behavior:

| Mode | Description | Key Params |
|------|-------------|------------|
| `basic` (default) | Semantic search across indexed content | source, limit, category, search_depth, topic, max_age_hours |
| `advanced` | Search with domain/date/text/source filters | include_domains, exclude_domains, start_date, end_date, include_text, exclude_text |
| `quick` | Real-time search without database (DuckDuckGo) | source |
| `stream` | Search with streaming batches + timing | sources |
| `smart` | Compact IR overview + full details (saves 50-70% tokens) | top_full, max_overview_tokens |
| `code` | Search GitHub + Stack Overflow for code snippets | language, tokens_target |
| `context` | Token-budget-aware snippet packing | budget_tokens, language, num_results |

### `crawl` — Crawl & Extract
Single URL crawl with subpage discovery, or batch URL extraction.

| Mode | Description | Key Params |
|------|-------------|------------|
| Single URL | Crawl URL + subpages, index results | url, subpages, subpage_target, max_age_hours |
| Batch | Extract content from multiple URLs | urls (comma-separated), extract_depth, instructions |

### `monitor` — Persistent Monitoring
Search monitors with deduplication. Each run returns only NEW results.

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `create` | Create a new monitor | query |
| `list` | List all monitors | — |
| `run` | Run monitor, returns new results only | monitor_id |
| `delete` | Delete a monitor | monitor_id |

### `webset` — Entity Collection
Named containers for collecting and enriching entities.

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `create` | Create a named container | name |
| `add` | Search and add results to webset | webset_id, query |
| `list` | List all webset containers | — |
| `get` | Get webset with all items | webset_id |
| `enrich` | Scrape URLs for emails, social links, tech | webset_id |
| `delete` | Delete a webset and all items | webset_id |

### `info` — Engine Information

| Type | Description |
|------|-------------|
| `categories` | List all search categories |
| `sources` | List all 7 data sources |
| `stats` | Database + cache statistics |
| `detect` | Auto-detect category for a query |

### `research` — Deep Research Sessions
Auto-generates sub-queries, crawls all sources, indexes for semantic follow-up.

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `start` | Start a research session | query |
| `followup` | Ask follow-up question within session | session_id, query |
| `list` | List all research sessions | — |
| `delete` | Delete a research session | session_id |

### `answer` — Search + Synthesis
Searches all 7 sources and returns numbered citations with a synthesis prompt.

### `search_leads` — Lead Generation
Search + score leads against an Ideal Customer Profile (industries, roles, tech, locations).

### `site_map` — Website Structure Mapping
BFS crawl to map website structure with natural language filtering.

### `index_topic` — Crawl & Index
Crawl a topic from all 7 sources and index for semantic search.

## Data Sources

- **Web**: General web crawling
- **Reddit**: Posts and discussions
- **YouTube**: Videos and metadata
- **GitHub**: Repositories
- **Twitter**: Tweets via Nitter
- **DuckDuckGo**: Search results
- **Wikipedia**: Articles

## Workflow

### Comprehensive Research
1. `research(action='start', query='...')` — deep research with auto sub-queries
2. `research(action='followup', session_id='...', query='...')` — follow-up questions
3. Review and synthesize findings

### Quick Search
1. `search(query='...', mode='quick')` — real-time search
2. Review results

### Token-Budget Search (for coding agents)
1. `search(query='...', mode='context', budget_tokens=8000)` — search with token budget
2. Inject results into context window

### Smart Search (token-efficient)
1. `search(query='...', mode='smart')` — compact overview + full details for top 3
2. Review overview, dive into details as needed

### Site Mapping
1. `site_map(url='...')` — map website structure
2. Use `instructions` to filter pages (e.g., "blog posts only")
3. Optionally `crawl(url='...')` specific pages

### Content Extraction
1. `crawl(urls='url1,url2,url3')` — batch extract from URLs
2. Use `extract_depth` for basic text or advanced metadata
3. Use `instructions` to filter relevant content

### Entity List Building
1. `webset(action='create', name='...')` — create a container
2. `webset(action='add', webset_id='...', query='...')` — collect entities
3. `webset(action='enrich', webset_id='...')` — extract emails, social links

### Monitoring
1. `monitor(action='create', query='...')` — set up monitoring
2. `monitor(action='run', monitor_id='...')` — check for new results

## General

- AI validates results — don't just trust crawler output
- Combine multiple sources for comprehensive understanding
- Use semantic search for natural language queries
- Use `search(mode='context')` for token-budget-aware results
- Use `search(mode='stream')` to see which sources complete first
