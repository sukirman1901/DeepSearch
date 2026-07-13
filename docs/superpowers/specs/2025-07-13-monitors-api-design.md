# Monitors API Design Spec

## Overview

Add recurring search monitors with cross-run deduplication. Users create a monitor for a query, then run it periodically — each run returns only NEW results not seen in previous runs. Inspired by Exa's Monitors API.

## Motivation

Current tools return all results every time. For ongoing monitoring (tracking a topic, watching for new content), users re-run the same search and get mostly duplicate results. Monitors solve this by tracking seen URLs and returning only new ones.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Trigger model | Manual trigger | MCP server is request-response, no background process |
| Persistence | JSON file on disk | Survives restarts, no new dependencies |
| Tool count | 4 tools (CRUD) | Full control: create, list, run, delete |
| Search integration | Direct crawl via CrawlerManager | No vector store dependency, returns raw results |
| Deduplication key | URL | Simple, reliable, matches Answer API pattern |

## Architecture

### New Module: `mcp/search/monitors.py`

```python
class MonitorManager:
    """Manage recurring search monitors with cross-run deduplication."""

    def __init__(self, data_file: str = "data/monitors.json"):
        self.data_file = data_file
        self.monitors: dict = {}
        self._load()

    def create_monitor(self, query, sources=None, max_results=20) -> str:
        """Create a new monitor. Returns monitor ID."""

    def list_monitors(self) -> list[dict]:
        """List all monitors with stats."""

    async def run_monitor(self, monitor_id, crawler_manager) -> list[CrawlResult]:
        """Run a monitor. Returns only NEW results since last run."""

    def delete_monitor(self, monitor_id) -> bool:
        """Delete a monitor. Returns True if existed."""

    def _load(self):
        """Load monitors from JSON file."""

    def _save(self):
        """Save monitors to JSON file."""
```

### Monitor JSON Structure

File: `mcp/data/monitors.json`

```json
{
  "monitors": {
    "uuid-1": {
      "query": "AI agent security",
      "sources": ["web", "reddit"],
      "max_results": 20,
      "created_at": "2025-07-13T22:00:00",
      "last_run": null,
      "run_count": 0,
      "seen_urls": []
    }
  }
}
```

### Data Flow

```
create_monitor(query="AI security", sources=["web","reddit"], max_results=20)
  -> generate monitor_id (uuid4)
  -> save to monitors.json
  -> return monitor_id

run_monitor(monitor_id)
  -> load monitor config
  -> crawler_manager.crawl_all(query, sources=sources, max_results_per_source)
  -> filter results: only URLs NOT in seen_urls
  -> add new URLs to seen_urls
  -> increment run_count, update last_run
  -> save to monitors.json
  -> return new results

list_monitors()
  -> return all monitors with stats (id, query, sources, last_run, run_count, seen_count)

delete_monitor(monitor_id)
  -> remove from monitors.json
  -> return True/False
```

### MCP Tools (4 new)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `create_monitor` | query, sources (optional), max_results (default 20) | monitor_id string |
| `list_monitors` | none | formatted list with stats |
| `run_monitor` | monitor_id | new results count + titles, or "no new results" |
| `delete_monitor` | monitor_id | success/failure message |

### Modified: `mcp/server.py`

- Import `MonitorManager`
- Instantiate `monitor_manager = MonitorManager()`
- Add 4 new MCP tools
- Total tools: 17 (13 existing + 4 new)

## Error Handling

| Scenario | Behavior |
|----------|----------|
| monitors.json doesn't exist | Create empty on first save |
| monitors.json corrupted | Start with empty monitors, log warning |
| run_monitor with invalid ID | Return error message |
| delete_monitor with invalid ID | Return "not found" |
| crawl_all fails | Return empty list, still update last_run |
| No new results | Return "No new results since last run. Total seen: N" |

## Testing Strategy

### Unit Tests: `mcp/tests/test_search/test_monitors.py`

1. `test_create_monitor` — Creates monitor, returns ID, monitor exists in list
2. `test_list_monitors` — Multiple monitors created, all listed with correct stats
3. `test_run_monitor_returns_all_on_first_run` — First run: all results are new (seen_urls empty)
4. `test_run_monitor_deduplicates_on_second_run` — Second run: only URLs not in first run returned
5. `test_run_monitor_invalid_id` — Invalid ID returns empty list
6. `test_delete_monitor` — Delete existing monitor, verify removed from list
7. `test_delete_monitor_invalid_id` — Delete non-existent returns False
8. `test_persistence` — Create monitor, create new MonitorManager with same file, verify loaded

### Test mocks
- Mock `CrawlerManager.crawl_all` with `AsyncMock`
- Use `tmp_path` fixture for isolated JSON file testing
- Use `CrawlResult` dataclass for test results

## Dependencies

No new packages. Uses:
- `uuid` (stdlib) — for monitor IDs
- `json` (stdlib) — for persistence
- `datetime` (stdlib) — for timestamps
- `os` (stdlib) — for file path handling
- Existing `CrawlerManager.crawl_all()` — for search

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `mcp/search/monitors.py` | CREATE | MonitorManager class |
| `mcp/data/monitors.json` | AUTO-CREATE | Created on first save |
| `mcp/server.py` | MODIFY | Add 4 new MCP tools |
| `mcp/tests/test_search/test_monitors.py` | CREATE | 8 unit tests |

## Success Criteria

- `create_monitor(query="test")` returns a monitor ID
- `run_monitor(id)` first run returns all results, second run returns only new
- `list_monitors()` shows all monitors with run_count and seen_count
- `delete_monitor(id)` removes monitor
- Monitors persist across server restarts (JSON file)
- All existing 90 tests still pass
- 8 new tests pass
- Total: 98 tests passing
