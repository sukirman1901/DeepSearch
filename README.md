# Deep Search Engine MCP Server

> **Free, Open-Source Search Engine MCP Server** — 7 sources, 10 consolidated tools, semantic search via ChromaDB, zero cost.

## Features

- **7 Data Sources**: Web, Reddit, YouTube, GitHub, Twitter/X, DuckDuckGo, Wikipedia
- **10 Consolidated Tools**: All features preserved, combined by mode/action parameters
- **Semantic Search**: ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
- **100% Free**: No API keys, no subscriptions, no paid APIs
- **MCP Standard**: Works with Claude, Cursor, OpenCode, and other AI clients
- **Parallel Crawling**: asyncio-based concurrent data collection

## Installation

### Option 1: Plugin Installation (Recommended)

**OpenCode:**
```json
{
  "plugin": ["deep-search@git+https://github.com/sukirman1901/DeepSearch.git"]
}
```

**Claude Code:**
Add to `.mcp.json` or `~/.claude/config.json`:
```json
{
  "mcpServers": {
    "deep-search": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "/path/to/DeepSearch/mcp"
    }
  }
}
```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/sukirman1901/DeepSearch.git
cd DeepSearch

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r mcp/requirements.txt
```

## Available Tools (10)

### `search` — Unified Search (7 modes)
| Mode | Description | Key Params |
|------|-------------|------------|
| `basic` (default) | Semantic search across indexed content | source, limit, category, search_depth, topic, max_age_hours |
| `advanced` | Search with domain/date/text/source filters | include_domains, exclude_domains, start_date, end_date |
| `quick` | Real-time search without database (DuckDuckGo) | source |
| `stream` | Search with streaming batches + timing | sources |
| `smart` | Compact IR overview + full details (saves 50-70% tokens) | top_full, max_overview_tokens |
| `code` | Search GitHub + Stack Overflow for code snippets | language, tokens_target |
| `context` | Token-budget-aware snippet packing | budget_tokens, language |

### `crawl` — Crawl & Extract
| Mode | Description | Key Params |
|------|-------------|------------|
| Single URL | Crawl URL + subpages, index results | url, subpages, subpage_target |
| Batch | Extract content from multiple URLs | urls, extract_depth, instructions |

### `monitor` — Persistent Monitoring
| Action | Description |
|--------|-------------|
| `create` | Create a monitor for a query |
| `list` | List all monitors |
| `run` | Run monitor, returns only NEW results |
| `delete` | Delete a monitor |

### `webset` — Entity Collection
| Action | Description |
|--------|-------------|
| `create` | Create a named container |
| `add` | Search and add results |
| `list` | List all websets |
| `get` | Get webset with all items |
| `enrich` | Scrape for emails, social links, tech |
| `delete` | Delete a webset |

### `info` — Engine Information
| Type | Description |
|------|-------------|
| `categories` | List all search categories |
| `sources` | List all 7 data sources |
| `stats` | Database + cache statistics |
| `detect` | Auto-detect category for a query |

### `research` — Deep Research Sessions
| Action | Description |
|--------|-------------|
| `start` | Start a research session |
| `followup` | Ask follow-up question |
| `list` | List all sessions |
| `delete` | Delete a session |

### Other Tools
| Tool | Description |
|------|-------------|
| `answer` | Search + synthesis with inline citations |
| `search_leads` | Lead generation with ICP scoring |
| `site_map` | BFS website structure mapping |
| `index_topic` | Crawl and index a topic |

## Architecture

```
DeepSearch/
├── mcp/                    # MCP server implementation
│   ├── crawlers/           # 7 specialized crawlers + subpage discovery
│   ├── db/                # ChromaDB + sentence-transformers
│   ├── search/            # Engine, answer, context, streaming, research, monitors, websets, sitemap, extract
│   ├── tests/             # 192 tests
│   ├── server.py          # 10 consolidated MCP tools
│   └── requirements.txt
├── skills/                # AI skills
│   └── using-deep-search/SKILL.md
├── hooks/                 # Session hooks
├── docs/superpowers/specs/ # Design specs
└── README.md
```

## How It Works

1. **Crawlers** gather raw data from 7 sources (parallel async)
2. **Sentence-transformers** embeds text to 384-dim vectors
3. **ChromaDB** stores vectors in memory
4. **Search engine** performs semantic search
5. **AI agent** validates and summarizes results

## AI Validates Results

Crawlers collect raw data. AI agent downstream validates, scores, and summarizes. Don't just trust crawler output.

## Supported Platforms

- **OpenCode** - Plugin installation via `plugin` config
- **Claude Code** - MCP server configuration
- **Cursor** - Plugin installation
- **Codex** - Plugin installation
- **Kimi Code** - Plugin installation
- **Gemini CLI** - Extension support
- Any MCP-compatible client

## License

MIT
