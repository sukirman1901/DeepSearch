# Deep Search — Contributor Guidelines

## If You Are an AI Agent

This plugin provides a Deep Search Engine MCP server with 7 data sources and semantic search capabilities via ChromaDB.

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

## Available Tools

| Tool | Description |
|------|-------------|
| `deep_search` | Semantic search across indexed content |
| `index_topic` | Crawl and index a topic from all 7 sources |
| `web_crawl` | Crawl a specific URL and add to index |
| `quick_search` | Real-time search without database |
| `list_sources` | List all available data sources |
| `db_stats` | Get database statistics |

## Data Sources

- **Web**: General web crawling
- **Reddit**: Posts and discussions
- **YouTube**: Videos and metadata
- **GitHub**: Repositories
- **Twitter**: Tweets via Nitter
- **DuckDuckGo**: Search results
- **Wikipedia**: Articles

## Workflow

1. Use `index_topic` to crawl and index data from all sources
2. Use `deep_search` to perform semantic search
3. Use `quick_search` for real-time search without database

## General

- AI validates results - don't just trust crawler output
- Combine multiple sources for comprehensive understanding
- Use semantic search for natural language queries
