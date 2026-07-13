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

## Available Tools

### Core Search Tools

#### `deep_search(query, source, limit, category, format_type)`
Semantic search across all indexed content.
- `query`: Natural language search query
- `source`: Filter by source (reddit, youtube, github, etc.) - optional
- `limit`: Max results (default 10)
- `category`: Category filter (company, people, research_paper, etc.) - optional
- `format_type`: Output format (text, json, markdown) - default text

#### `advanced_search(query, limit, include_domains, exclude_domains, start_date, end_date, include_text, exclude_text, include_sources, exclude_sources, boost_recent, boost_popular, format_type)`
Search with advanced filters inspired by Exa.
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

### Code Context Tools

#### `code_search(query, max_results, language, tokens_target)`
Search for code snippets from GitHub and Stack Overflow.
Inspired by Exa's Context API for coding agents.
- `query`: Code search query (e.g., "React hooks state management")
- `max_results`: Max snippets to return (default 10)
- `language`: Filter by programming language (e.g., "python", "javascript")
- `tokens_target`: Target token count for response (default 5000)

### Lead Generation Tools

#### `search_leads(query, limit, industries, roles, technologies, locations, keywords)`
Search and score leads against an Ideal Customer Profile (ICP).
- `query`: Search query
- `limit`: Max leads (default 20)
- `industries`: Target industries (e.g., ["fintech", "saas"])
- `roles`: Target roles (e.g., ["CEO", "CTO", "Developer"])
- `technologies`: Target technologies (e.g., ["Python", "React"])
- `locations`: Target locations (e.g., ["San Francisco", "Remote"])
- `keywords`: Additional keywords to match

### Category Tools

#### `list_categories()`
List all available search categories and their descriptions.

#### `detect_query_category(query)`
Auto-detect the best category for a search query.

### Indexing Tools

#### `index_topic(topic, max_results_per_source, category, sources)`
Crawl and index a topic with optional category and source filtering.
- `topic`: Topic to index
- `max_results_per_source`: Max results per source (default 10)
- `category`: Category hint (auto, company, people, etc.) - default auto
- `sources`: Specific sources to crawl (optional, default all)

#### `web_crawl(url, max_age_hours, livecrawl_timeout)`
Crawl a specific URL and add to index with caching control.
- `url`: URL to crawl
- `max_age_hours`: Cache freshness control (default -1)
  - `24`: Use cache if <24 hours old
  - `1`: Use cache if <1 hour old
  - `0`: Always livecrawl
  - `-1`: Cache only
- `livecrawl_timeout`: Timeout in ms for livecrawl (default 10000)

### Utility Tools

#### `list_sources()`
List all available data sources.

#### `db_stats()`
Get database and cache statistics.

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
1. `index_topic` - crawl and index data from all sources
2. `deep_search` - semantic search for relevant content
3. Review and summarize findings

### Code Search
1. `code_search` - find code snippets from GitHub/Stack Overflow
2. Review code examples and documentation

### Company Research
1. `detect_query_category` - confirm category is "company"
2. `search_leads` with ICP filters
3. Review company profiles and contact info

### People Search
1. `advanced_search` with category "people"
2. Filter by role, company, expertise
3. Review LinkedIn profiles and backgrounds

### Quick Research
1. `quick_search` - real-time search
2. Review results

### Specific URL Research
1. `web_crawl` - crawl and index the URL
2. `deep_search` - search for related content

### Fresh Content
1. `web_crawl` with `max_age_hours=1` for near real-time
2. `web_crawl` with `max_age_hours=0` for real-time

## Token Isolation Pattern

For heavy search operations, spawn a subagent to keep main context clean:

```python
# Agent pattern for token isolation
async def search_with_isolation(query: str, category: str = "general"):
    # 1. Spawn subagent for search
    # 2. Subagent calls advanced_search or search_leads
    # 3. Subagent merges + deduplicates results
    # 4. Subagent returns distilled output
    # 5. Main context stays clean
    pass
```

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
- Use `detect_query_category` to auto-categorize queries
- Use `advanced_search` for precise filtering by domain, date, or text
- Use `search_leads` with ICP for B2B lead generation
- Use `code_search` with `language` filter for specific programming languages
- For deep research, use `index_topic` first, then `deep_search`
- For quick answers, use `quick_search`
- For fresh content, use `web_crawl` with `max_age_hours=0` or `1`
- AI validates results - don't just trust crawler output
- Combine multiple sources for comprehensive understanding
- Use `format_type="json"` for structured data integration