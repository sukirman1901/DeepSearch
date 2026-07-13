# Deep Search Engine MCP Server

> **Free, Open-Source Alternative to Exa MCP** — Aggregates 7 sources, semantic search via ChromaDB, zero cost.

## Features

- **7 Data Sources**: Web, Reddit, YouTube, GitHub, Twitter/X, DuckDuckGo, Wikipedia
- **Semantic Search**: ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
- **100% Free**: No API keys, no subscriptions, no paid APIs
- **MCP Standard**: Works with Claude, Cursor, OpenCode, and other AI clients
- **Parallel Crawling**: asyncio-based concurrent data collection

## Installation

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
│   │   ├── base.py        # BaseCrawler ABC
│   │   ├── web_crawler.py
│   │   ├── reddit_crawler.py
│   │   ├── youtube_crawler.py
│   │   ├── github_crawler.py
│   │   ├── twitter_crawler.py
│   │   ├── duckduckgo_crawler.py
│   │   ├── wikipedia_crawler.py
│   │   └── manager.py     # CrawlerManager
│   ├── db/                # Database layer
│   │   ├── embeddings.py  # SentenceTransformer wrapper
│   │   └── vector_store.py # ChromaDB wrapper
│   ├── search/            # Search engine
│   │   └── engine.py      # SearchEngine
│   ├── tests/             # Test suite
│   ├── server.py          # MCP server entry point
│   └── requirements.txt
├── .agents/               # AI skills
│   └── skills/deep-search/SKILL.md
├── docs/                  # Documentation
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

- Claude Desktop
- Cursor
- OpenCode
- Any MCP-compatible client

## License

MIT
