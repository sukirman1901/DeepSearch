# Deep Search Engine MCP Server

> **Free, Open-Source Alternative to Exa MCP** — Aggregates 7 sources, semantic search via ChromaDB, zero cost.

## Features

- **7 Data Sources**: Web, Reddit, YouTube, GitHub, Twitter/X, DuckDuckGo, Wikipedia
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

## Usage

### As MCP Server (Recommended)

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "deep-search": {
      "command": "python",
      "args": ["/path/to/DeepSearch/mcp/server.py"],
      "cwd": "/path/to/DeepSearch/mcp",
      "env": {
        "PYTHONPATH": "/path/to/DeepSearch/mcp"
      }
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `deep_search` | Semantic search across indexed content |
| `index_topic` | Crawl and index a topic from all 7 sources |
| `web_crawl` | Crawl a specific URL and add to index |
| `quick_search` | Real-time search without database |
| `list_sources` | List all available data sources |
| `db_stats` | Get database statistics |

### Example Workflow

```python
# 1. Index a topic
await index_topic("AI Indonesia", max_results_per_source=10)

# 2. Search semantically
results = await deep_search("perkembangan AI di Indonesia")

# 3. Or search specific source
results = await deep_search("AI", source="reddit")
```

## Architecture

```
DeepSearch/
├── mcp/                    # MCP server implementation
│   ├── crawlers/           # 7 specialized crawlers
│   ├── db/                # Database layer
│   ├── search/            # Search engine
│   ├── tests/             # Test suite
│   ├── server.py          # MCP server entry point
│   └── requirements.txt
├── skills/                # AI skills
│   └── using-deep-search/SKILL.md
├── hooks/                 # Session hooks
│   ├── hooks.json         # Claude hooks
│   ├── hooks-cursor.json  # Cursor hooks
│   └── session-start      # Session start script
├── .claude-plugin/        # Claude plugin manifest
├── .cursor-plugin/        # Cursor plugin manifest
├── .codex-plugin/         # Codex plugin manifest
├── .kimi-plugin/          # Kimi plugin manifest
├── .opencode/             # OpenCode plugin
├── package.json           # npm package config
├── CLAUDE.md              # Claude instructions
├── AGENTS.md              # AI agent instructions
├── GEMINI.md              # Gemini instructions
└── README.md
```

## How It Works

1. **Crawlers** gather raw data from 7 sources
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
