# Deep Search Engine Skill

## When to Use
Use this skill when:
- User asks for comprehensive research on any topic
- User needs information from web, Reddit, YouTube, GitHub, Twitter, Wikipedia
- User wants semantic search (not just keyword matching)
- User wants to mine information from social media or web
- User wants to find leads, companies, people, or research papers
- User wants structured output (JSON, Markdown, CSV)
- User needs code snippets or programming examples
- User wants fresh content with caching control
- User wants token-budget-aware results for coding agents
- User wants streaming results with completion order
- User wants to build entity lists with enrichment
- User wants persistent monitoring for topics

## Available Tools (28)

### Core Search

#### `deep_search(query, source, limit, category, format_type)`
Semantic search across all indexed content.
- `query`: Natural language search query
- `source`: Filter by source (reddit, youtube, github, etc.) - optional
- `limit`: Max results (default 10)
- `category`: Category filter (company, people, research_paper, etc.) - optional
- `format_type`: Output format (text, json, markdown) - default text

#### `advanced_search(query, limit, include_domains, exclude_domains, start_date, end_date, include_text, exclude_text, include_sources, exclude_sources, boost_recent, boost_popular, format_type)`
Search with advanced filters.
- `query`: Search query
- `limit`: Max results (default 10)
- `include_domains`: Only include results from these domains
- `exclude_domains`: Exclude results from these domains
- `start_date`: Only include results after this date (ISO 8601)
- `end_date`: Only include results before this date (ISO 8601)
- `include_text`: Only include results containing ALL these terms
- `exclude_text`: Exclude results containing ANY of these terms
- `include_sources`: Only include these sources
- `exclude_sources`: Exclude these sources
- `boost_recent`: Boost more recent results
- `boost_popular`: Boost results with popularity metrics
- `format_type`: Output format (text, json, markdown)

#### `quick_search(query, source)`
Real-time search without using the database.
- `query`: Search query
- `source`: Source to search (duckduckgo, reddit, etc.) - optional

#### `index_topic(topic, max_results_per_source, category, sources)`
Crawl and index a topic with optional category and source filtering.
- `topic`: Topic to index
- `max_results_per_source`: Max results per source (default 10)
- `category`: Category hint (auto, company, people, etc.) - default auto
- `sources`: Specific sources to crawl (optional, default all)

#### `web_crawl(url, max_age_hours, livecrawl_timeout, subpages, subpage_target)`
Crawl a specific URL with optional subpage discovery.
- `url`: URL to crawl
- `max_age_hours`: Cache freshness control (default -1)
- `subpages`: Enable subpage crawling (default false)
- `subpage_target`: Target number of subpages (default 10)

### Answer & Context

#### `answer(query, num_results, output_schema, system_prompt)`
Search all sources and return context + synthesis prompt with inline citations.
- `query`: Question to answer
- `num_results`: Max results (default 10)
- `output_schema`: Optional JSON schema for structured output
- `system_prompt`: Optional system prompt for synthesis

#### `context_search(query, budget_tokens, language, num_results)`
Token-budget-aware snippet packing for coding agents.
- `query`: What to search for
- `budget_tokens`: Max tokens for returned context (default 8000)
- `language`: Filter by programming language
- `num_results`: Max results to consider (default 20)

#### `code_search(query, max_results, language, tokens_target)`
Search for code snippets from GitHub and Stack Overflow.
- `query`: Code search query
- `max_results`: Max snippets to return (default 10)
- `language`: Filter by programming language
- `tokens_target`: Target token count (default 5000)

### Streaming & Research

#### `stream_search(query, num_results, sources)`
Results grouped by completion order with timing metadata.
- `query`: Search query
- `num_results`: Max results per source (default 10)
- `sources`: Comma-separated sources (empty = all)

#### `start_research(query, sources, max_results)`
Deep research session with auto sub-queries.
- `query`: Research topic/question
- `sources`: Comma-separated sources (empty = all)
- `max_results`: Max results per source per sub-query (default 15)

#### `ask_followup(session_id, query, num_results)`
Semantic follow-up within a research session.
- `session_id`: Session ID from start_research
- `query`: Follow-up question
- `num_results`: Number of results (default 5)

#### `list_sessions()`
List all research sessions.

#### `delete_session(session_id)`
Delete a research session.

### Categories & Filters

#### `list_categories()`
List all available search categories and their descriptions.

#### `detect_query_category(query)`
Auto-detect the best category for a search query.

### Monitors

#### `create_monitor(name, query, sources, interval_hours, max_results)`
Create persistent monitoring for a topic.
- `name`: Monitor name
- `query`: What to monitor
- `sources`: Comma-separated sources (empty = all)
- `interval_hours`: Check interval (default 24)
- `max_results`: Max results per check (default 10)

#### `list_monitors()`
List all monitors.

#### `run_monitor(monitor_id)`
Run monitor, returns only new results since last check.

#### `delete_monitor(monitor_id)`
Delete a monitor.

### Websets

#### `create_webset(name, description)`
Create a named container for entity lists.

#### `add_to_webset(webset_id, query, max_results)`
Search and add results to a webset container.

#### `list_websets()`
List all webset containers.

#### `get_webset(webset_id)`
Get webset container with all items.

#### `enrich_webset(webset_id)`
Scrape URLs for emails, social links, technologies.

#### `delete_webset(webset_id)`
Delete a webset container.

### Lead Generation

#### `search_leads(query, limit, industries, roles, technologies, locations, keywords)`
Search and score leads against an Ideal Customer Profile (ICP).

### Utility

#### `list_sources()`
List all available data sources.

#### `db_stats()`
Get database statistics.

## Livecrawling (Content Freshness)

Control how fresh content should be with `max_age_hours` parameter:

| Value | Behavior | Best For |
|-------|----------|----------|
| `24` | Use cache if <24 hours old, otherwise livecrawl | Daily-fresh content |
| `1` | Use cache if <1 hour old, otherwise livecrawl | Near real-time data |
| `0` | Always livecrawl (ignore cache) | Real-time data |
| `-1` | Never livecrawl (cache only) | Static/historical content |
| *(omit)* | Default behavior | Balanced speed and freshness |

## Categories

| Category | Description | Best For |
|----------|-------------|----------|
| company | Company profiles, competitors, funding | Business research |
| people | Professional profiles, expertise | Finding experts |
| research_paper | Academic papers, arXiv | Scientific research |
| financial_report | SEC filings, earnings | Financial analysis |
| personal_site | Personal blogs, portfolios | Independent content |
| news | Recent news articles | Current events |
| code | Code examples, API docs | Technical implementation |
| general | All sources | Broad research |

## Workflow

### Comprehensive Research
1. `start_research` - deep research with auto sub-queries
2. `ask_followup` - semantic follow-up questions
3. Review and synthesize findings

### Token-Budget Search (for coding agents)
1. `context_search` - search with token budget limit
2. Inject results into context window

### Streaming Search
1. `stream_search` - see which sources complete first
2. Fast sources (DuckDuckGo, Wikipedia) appear first

### Code Search
1. `code_search` - find code snippets from GitHub/Stack Overflow
2. Review code examples and documentation

### Company Research
1. `detect_query_category` - confirm category is "company"
2. `search_leads` with ICP filters
3. Review company profiles and contact info

### Entity List Building
1. `create_webset` - create a named container
2. `add_to_webset` - search and collect entities
3. `enrich_webset` - extract emails, social links, technologies

### Monitoring
1. `create_monitor` - set up topic monitoring
2. `run_monitor` - check for new results periodically

### Quick Research
1. `quick_search` - real-time search
2. Review results

### Specific URL Research
1. `web_crawl` - crawl and index the URL (use `subpages=true` for more)
2. `deep_search` - search for related content

## Sources
- Web: General web crawling
- Reddit: Posts and discussions
- YouTube: Videos and metadata
- GitHub: Repositories + Code search
- Stack Overflow: Code answers
- Twitter: Tweets via Nitter
- DuckDuckGo: Search results
- Wikipedia: Articles

## Tips
- Use `start_research` for deep multi-source research
- Use `context_search` for token-budget-aware results
- Use `stream_search` to see which sources complete first
- Use `answer` for synthesis-ready context with citations
- Use `detect_query_category` to auto-categorize queries
- Use `advanced_search` for precise filtering by domain, date, or text
- Use `search_leads` with ICP for B2B lead generation
- Use `code_search` with `language` filter for specific programming languages
- For deep research, use `index_topic` first, then `deep_search`
- For quick answers, use `quick_search`
- For fresh content, use `web_crawl` with `max_age_hours=0` or `1`
- AI validates results - don't just trust crawler output
- Combine multiple sources for comprehensive understanding
