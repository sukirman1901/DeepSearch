# Deep Search — Deep Search Engine for Claude Code

@./skills/using-deep-search/SKILL.md

## MCP Server Setup

The Deep Search MCP server provides semantic search across 7 data sources. To use it in Claude Code, add the MCP server to your Claude Code configuration:

### Option 1: Project-level MCP config

Create or edit `.mcp.json` in your project root:

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

### Option 2: Global Claude Code config

Add to `~/.claude/config.json`:

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

### Prerequisites

```bash
cd /path/to/DeepSearch/mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Use the venv python path in the MCP config: `"/path/to/DeepSearch/mcp/.venv/bin/python3"` instead of `python3`.

## Tool Mapping for Claude Code

Deep Search skills reference MCP tools by name (e.g., `deep_search`, `index_topic`). These are available via the MCP server and called directly by tool name.

- Create or update todos → `TodoWrite`
- Invoke a skill → `Skill` tool
- Run shell commands → `Bash`
- Read files → `Read`
- Create, edit files → `Edit`, `Write`
- Search files → `Grep`, `Glob`
- Search tools (deep_search, index_topic, etc.) → MCP tools via `deep-search` server
