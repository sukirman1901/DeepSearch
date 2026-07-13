# Installing Deep Search for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed
- Python 3.10+

## Installation

Add deep-search to the `plugin` array in your `opencode.json` (global or project-level):

```json
{
  "plugin": ["deep-search@git+https://github.com/sukirman1901/DeepSearch.git"]
}
```

To pin a specific version:

```json
{
  "plugin": ["deep-search@git+https://github.com/sukirman1901/DeepSearch.git#v1.0.0"]
}
```

Restart OpenCode. The plugin installs through OpenCode's plugin manager and
registers all skills and the MCP server automatically.

Verify by asking: "Tell me about your deep search capabilities"

## MCP Server Setup

The plugin auto-registers the MCP server. If Python dependencies are missing:

```bash
cd /path/to/DeepSearch/mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
```

## Usage

Use OpenCode's native `skill` tool:

```
use skill tool to list skills
use skill tool to load deep-search
```

## Tool Mapping for OpenCode

- "Create a todo" / "mark complete in todo list" → `todowrite`
- `Subagent (general-purpose):` template → `task` tool with `subagent_type: "general"`
- "Invoke a skill" → OpenCode's native `skill` tool
- "Read a file" → `read`
- "Create, edit, or delete a file" → `apply_patch`
- "Run a shell command" → `bash`
- "Search files" → `grep`, `glob`
- "Fetch a URL" → `webfetch`
- Search tools (deep_search, index_topic, etc.) → MCP tools via `deep-search` server

## Updating

To pin a specific version:

```json
{
  "plugin": ["deep-search@git+https://github.com/sukirman1901/DeepSearch.git#v1.0.0"]
}
```

## Troubleshooting

### Plugin not loading

1. Check logs: `opencode run --print-logs "hello" 2>&1 | grep -i deep-search`
2. Verify the plugin line in your `opencode.json`
3. Make sure you're running a recent version of OpenCode

### MCP tools not found

1. Verify the venv exists: `ls mcp/.venv/bin/python3`
2. Test the MCP server: `cd mcp && python server.py`

### Skills not found

1. Use `skill` tool to list what's discovered
2. Check that the plugin is loading
