# Deep Search Engine Skill

## When to Use
Use this skill when:
- User asks for comprehensive research on any topic
- User needs information from web, Reddit, YouTube, GitHub, Twitter, Wikipedia
- User wants semantic search (not just keyword matching)
- User wants to mine information from social media or web

## Available Tools

### `deep_search(query, source, limit)`
Semantic search across all indexed content.
- `query`: Natural language search query
- `source`: Filter by source (reddit, youtube, github, etc.) - optional
- `limit`: Max results (default 10)

### `index_topic(topic, max_results_per_source)`
Crawl and index a topic from all 7 sources.
- `topic`: Topic to index (e.g., "AI Indonesia", "python web framework")
- `max_results_per_source`: Max results per source (default 10)

### `web_crawl(url)`
Crawl a specific URL and add to index.
- `url`: URL to crawl

### `quick_search(query, source)`
Real-time search without using the database.
- `query`: Search query
- `source`: Source to search (duckduckgo, reddit, etc.) - optional

### `list_sources()`
List all available data sources.

### `db_stats()`
Get database statistics.

## Workflow

### Comprehensive Research
1. `index_topic` - crawl and index data from all sources
2. `deep_search` - semantic search for relevant content
3. Review and summarize findings

### Quick Research
1. `quick_search` - real-time search
2. Review results

### Specific URL Research
1. `web_crawl` - crawl and index the URL
2. `deep_search` - search for related content

## Sources
- Web: General web crawling
- Reddit: Posts and discussions
- YouTube: Videos and metadata
- GitHub: Repositories
- Twitter: Tweets via Nitter
- DuckDuckGo: Search results
- Wikipedia: Articles

## Tips
- For deep research, use `index_topic` first, then `deep_search`
- For quick answers, use `quick_search`
- AI validates results - don't just trust crawler output
- Combine multiple sources for comprehensive understanding