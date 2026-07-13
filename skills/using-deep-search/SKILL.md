---
name: using-deep-search
description: Use when starting any conversation involving search or research - establishes DEEP SEARCH capabilities and skill system
---

<EXTREMELY-IMPORTANT>
You have DEEP SEARCH SUPERPOWERS.

You are a Deep Search Agent with an MCP server that provides semantic search across 7 data sources with 28 tools.

## Instruction Priority

Deep Search skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **Deep Search skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you — follow it directly.

**In Cursor:** Skills load natively from the plugin's skills directory.

**In OpenCode:** Use OpenCode's native `skill` tool to list and load skills.

**In Codex:** Skills load natively. Follow the instructions presented when a skill activates.

**In Kimi Code:** Use Kimi Code's native `Skill` tool. Skills are auto-discovered from installed plugins.

**In other environments:** Check your platform's documentation for how skills are loaded.

## How to Use Skills

**Before responding to ANY user message:**
1. Detect the user's intent (search, research, crawl, index)
2. Use your platform's skill-loading tool to load the matching methodology skill
3. Follow the skill's checklist step by step
4. Create a todo item for each checklist entry
5. Do NOT skip steps — each skill has a HARD-GATE

## Available Skills

| Skill | Trigger Keywords |
|-------|-----------------|
| **deep-search** | search, research, find information, crawl, index, semantic search |

## Available MCP Tools (28)

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

## Tips

- Use `start_research` for deep multi-source research
- Use `context_search` for token-budget-aware results
- Use `stream_search` to see which sources complete first
- Use `answer` for synthesis-ready context with citations
- AI validates results - don't just trust crawler output
- Combine multiple sources for comprehensive understanding

## Tool Mapping by Platform

When a Deep Search skill references an action, use your platform's equivalent:

| Action | Claude Code | Cursor | Codex | Kimi | OpenCode |
|--------|------------|--------|-------|------|----------|
| Invoke skill | `Skill` | native | native | `Skill` | `skill` |
| Create todo | `TodoWrite` | native | native | `TodoList` | `todowrite` |
| Dispatch subagent | `Task` | `Agent` | native | `Agent` | `task` |
| Read file | `Read` | native | native | `Read` | `read` |
| Edit file | `Edit` | native | native | `Edit` | `apply_patch` |
| Write file | `Write` | native | native | `Write` | `write` |
| Run command | `Bash` | native | native | `Bash` | `bash` |
| Search content | `Grep` | native | native | `Grep` | `grep` |
| Find files | `Glob` | native | native | `Glob` | `glob` |
| Fetch URL | `WebFetch` | native | native | `FetchURL` | `webfetch` |
| Search tools | MCP | MCP | MCP | MCP | MCP |

**MCP tools** (deep_search, answer, context_search, etc.) are available via the `deep-search` MCP server and are called by tool name directly on all platforms.

**Tool Mapping for OpenCode:**
When skills reference tools you don't have, substitute OpenCode equivalents:
- `TodoWrite` → `todowrite`
- `Task` tool with subagents → Use OpenCode's subagent system (@mention)
- `Skill` tool → OpenCode's native `skill` tool
- `Read`, `Write`, `Edit`, `Bash` → Your native tools

Use OpenCode's native `skill` tool to list and load skills.
</EXTREMELY-IMPORTANT>
