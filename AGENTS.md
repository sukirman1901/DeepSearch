# Deep Search — Contributor Guidelines

## If You Are an AI Agent

This plugin provides a Deep Search Engine MCP server with 7 data sources, 29 tools, and semantic search capabilities via ChromaDB.

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

## Available Tools (28)

### Core Search
| Tool | Description |
|------|-------------|
| `deep_search` | Semantic search across indexed content |
| `quick_search` | Real-time search without database |
| `index_topic` | Crawl and index a topic from all 7 sources |
| `web_crawl` | Crawl a URL with optional subpage discovery |
| `list_sources` | List all available data sources |
| `db_stats` | Get database statistics |

### Answer & Context
| Tool | Description |
|------|-------------|
| `answer` | Search + synthesis prompt with inline citations |
| `context_search` | Token-budget-aware snippet packing for agents |
| `code_search` | Search GitHub + Stack Overflow for code snippets |
| `smart_search` | Hybrid: compact IR overview + full details for top N (saves 50-70% tokens) |

### Streaming & Research
| Tool | Description |
|------|-------------|
| `stream_search` | Results grouped by completion order with timing |
| `start_research` | Deep research session with auto sub-queries |
| `ask_followup` | Semantic follow-up within research session |
| `list_sessions` | List all research sessions |
| `delete_session` | Delete a research session |

### Categories & Filters
| Tool | Description |
|------|-------------|
| `advanced_search` | Filter by date range, language, region |
| `detect_query_category` | Auto-detect query category |
| `list_categories` | List all categories with sources |

### Monitors
| Tool | Description |
|------|-------------|
| `create_monitor` | Create persistent monitoring for a topic |
| `list_monitors` | List all monitors |
| `run_monitor` | Run monitor, returns only new results |
| `delete_monitor` | Delete a monitor |

### Websets
| Tool | Description |
|------|-------------|
| `create_webset` | Create named container for entity lists |
| `add_to_webset` | Search and add results to a webset |
| `list_websets` | List all webset containers |
| `get_webset` | Get webset with all items |
| `enrich_webset` | Scrape URLs for emails, social links, technologies |
| `delete_webset` | Delete a webset |

### Lead Generation
| Tool | Description |
|------|-------------|
| `search_leads` | Search + generate Ideal Customer Profile |

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
1. `start_research` - deep research with auto sub-queries
2. `ask_followup` - semantic follow-up questions
3. Review and synthesize findings

### Quick Search
1. `quick_search` - real-time search
2. Review results

### Token-Budget Search (for coding agents)
1. `context_search` - search with token budget limit
2. Inject results into context window

### Entity List Building
1. `create_webset` - create a named container
2. `add_to_webset` - search and collect entities
3. `enrich_webset` - extract emails, social links, technologies

### Monitoring
1. `create_monitor` - set up topic monitoring
2. `run_monitor` - check for new results periodically

## General

- AI validates results - don't just trust crawler output
- Combine multiple sources for comprehensive understanding
- Use semantic search for natural language queries
- Use `context_search` for token-budget-aware results
- Use `stream_search` to see which sources complete first
