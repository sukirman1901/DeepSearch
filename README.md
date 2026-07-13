# Deep Search Engine MCP Server

> **Free, Open-Source Search Engine MCP Server** — 7 sources, 28 tools, semantic search via ChromaDB, zero cost.

## Features

- **7 Data Sources**: Web, Reddit, YouTube, GitHub, Twitter/X, DuckDuckGo, Wikipedia
- **28 MCP Tools**: Search, answer, context, streaming, research, monitors, websets, and more
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

## Architecture

```
DeepSearch/
├── mcp/                    # MCP server implementation
│   ├── crawlers/           # 7 specialized crawlers + subpage discovery
│   ├── db/                # ChromaDB + sentence-transformers
│   ├── search/            # Engine, answer, context, streaming, research, monitors, websets
│   ├── tests/             # 140 tests
│   ├── server.py          # 28 MCP tools
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
