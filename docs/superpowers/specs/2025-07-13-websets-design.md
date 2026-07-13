# Websets Design Spec

**Date:** 2025-07-13
**Status:** Draft
**Author:** Superpowers

## Problem

Agents need to build structured lists of entities (companies, tools, people) from search results. Current tools return flat result lists — no persistence, no enrichment, no named collections.

## Solution

Websets — named containers holding entity items with optional enrichment. Search crawlers find entities, items are stored in containers, enrichments extract structured data (emails, social links, descriptions) from item URLs via HTML scraping.

## Architecture

```
WebsetManager
  ├── Container (named, JSON-persisted)
  │   └── Items[] (entities with properties)
  └── Enricher (fetch URL → extract fields)
```

## Data Model

```python
@dataclass
class WebsetItem:
    """Entity in a webset."""
    id: str                  # uuid4
    title: str
    url: str
    description: str = ""
    source: str = ""         # which crawler found it
    properties: dict = {}    # enriched fields (emails, social, etc.)
    enriched: bool = False
    added_at: str = ""       # ISO timestamp

@dataclass
class WebsetContainer:
    """Named collection of items."""
    id: str                  # uuid4
    name: str
    description: str = ""
    items: list[WebsetItem] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
```

## Enrichment (HTML Scraping)

No paid APIs. Fetch page HTML, parse with BeautifulSoup, extract:

| Field | Extraction Method |
|-------|------------------|
| `title` | `<title>` tag or `<h1>` |
| `description` | `<meta name="description">` |
| `emails` | Regex `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` |
| `social_links` | Links to twitter.com, github.com, linkedin.com |
| `technologies` | Meta tags, script sources (react, vue, next.js) |

## WebsetManager

```python
class WebsetManager:
    def __init__(self, data_file="data/websets.json"):
        self.data_file = data_file
        self.containers = {}  # id → WebsetContainer
        self._load()

    # Container operations
    def create_container(self, name, description="") -> WebsetContainer
    def delete_container(self, container_id) -> bool
    def list_containers(self) -> list[dict]
    def get_container(self, container_id) -> WebsetContainer | None

    # Item operations
    def add_items_from_search(self, container_id, results: list[CrawlResult]) -> int
    def add_item(self, container_id, title, url, ...) -> WebsetItem
    def remove_item(self, container_id, item_id) -> bool
    def list_items(self, container_id) -> list[dict]

    # Enrichment
    async def enrich_item(self, container_id, item_id) -> WebsetItem
    async def enrich_all(self, container_id) -> int  # count enriched
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `create_webset` | Create named container |
| `add_to_webset` | Add items from search query |
| `list_websets` | List all containers |
| `get_webset` | Get container with items |
| `enrich_webset` | Enrich all items (scrape URLs) |
| `delete_webset` | Delete container |

## Tests

| # | Test | Asserts |
|---|------|---------|
| 1 | `test_create_container` | Container created with name |
| 2 | `test_add_item` | Item added to container |
| 3 | `test_add_items_from_search` | CrawlResults converted to items |
| 4 | `test_remove_item` | Item removed |
| 5 | `test_delete_container` | Container deleted |
| 6 | `test_persistence` | Survives reload |
| 7 | `test_enrich_extracts_emails` | Emails found in HTML |
| 8 | `test_enrich_extracts_social` | Social links found |
| 9 | `test_list_containers` | Returns all containers |
| 10 | `test_duplicate_url_skipped` | Same URL not added twice |

## File Changes

| File | Change |
|------|--------|
| `mcp/search/websets.py` | NEW — WebsetManager, WebsetItem, WebsetContainer, Enricher |
| `mcp/tests/test_search/test_websets.py` | NEW — 10 tests |
| `mcp/server.py` | Add 6 webset tools |

## Verification

```bash
cd mcp && .venv/bin/python3 -m pytest tests/ -q
# Target: 135 tests (125 existing + 10 new)
```
