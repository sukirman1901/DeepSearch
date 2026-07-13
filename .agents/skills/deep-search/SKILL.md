# Deep Search Engine Skill

## When to Use
Use this skill when:
- User asks for comprehensive research on any topic
- User needs information from web, Reddit, YouTube, GitHub, Twitter, Wikipedia
- User wants semantic search (not just keyword matching)
- User wants to mine information from social media or web
- User wants to find leads, companies, people, or research papers
- User wants structured output (JSON, Markdown, CSV)

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

#### `web_crawl(url)`
Crawl a specific URL and add to index.

### Utility Tools

#### `list_sources()`
List all available data sources.

#### `db_stats()`
Get database statistics.

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
- GitHub: Repositories
- Twitter: Tweets via Nitter
- DuckDuckGo: Search results
- Wikipedia: Articles

## Tips
- Use `detect_query_category` to auto-categorize queries
- Use `advanced_search` for precise filtering by domain, date, or text
- Use `search_leads` with ICP for B2B lead generation
- For deep research, use `index_topic` first, then `deep_search`
- For quick answers, use `quick_search`
- AI validates results - don't just trust crawler output
- Combine multiple sources for comprehensive understanding
- Use `format_type="json"` for structured data integration