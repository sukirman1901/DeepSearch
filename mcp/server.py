# server.py
import asyncio
import json
from mcp.server.fastmcp import FastMCP
from search.engine import SearchEngine
from search.categories import get_category_info, detect_category
from search.lead_gen import create_icp
from search.code_context import search_code_context
from search.livecrawl import livecrawl_manager
from search.answer import AnswerEngine
from search.monitors import MonitorManager
from crawlers.web_crawler import WebCrawler

mcp = FastMCP("DeepSearchEngine")
engine = SearchEngine()
answer_engine = AnswerEngine(engine.crawler_manager, engine.vector_store)
web_crawler = WebCrawler()
monitor_manager = MonitorManager()


# --- Core Search Tools ---

@mcp.tool()
async def deep_search(
    query: str,
    source: str = "",
    limit: int = 10,
    category: str = "",
    format_type: str = "text",
) -> str:
    """
    Semantic search across all indexed content with optional filtering.

    Args:
        query: Search query in natural language
        source: Filter by source (reddit, youtube, github, etc.) - optional
        limit: Maximum number of results (default 10)
        category: Category filter (company, people, research_paper, etc.) - optional
        format_type: Output format (text, json, markdown) - default text
    """
    if category == "auto":
        category = engine.detect_query_category(query)

    if format_type in ("json", "markdown"):
        output = engine.search_and_format(query, limit, format_type, category)
        return output

    results = engine.search(query, limit, source, category=category)

    if not results:
        return "No results found. Try indexing a topic first with index_topic."

    output = f"Found {len(results)} results for '{query}':\n\n"
    for i, result in enumerate(results, 1):
        output += f"--- Result {i} (Source: {result.source}) ---\n"
        output += f"Title: {result.title}\n"
        output += f"Content: {result.content[:500]}...\n"
        output += f"URL: {result.url}\n\n"

    return output


@mcp.tool()
async def advanced_search(
    query: str,
    limit: int = 10,
    include_domains: list[str] = None,
    exclude_domains: list[str] = None,
    start_date: str = "",
    end_date: str = "",
    include_text: list[str] = None,
    exclude_text: list[str] = None,
    include_sources: list[str] = None,
    exclude_sources: list[str] = None,
    boost_recent: bool = False,
    boost_popular: bool = False,
    format_type: str = "text",
) -> str:
    """
    Search with advanced filters (domains, dates, text, sources).

    Args:
        query: Search query
        limit: Maximum results (default 10)
        include_domains: Only include results from these domains
        exclude_domains: Exclude results from these domains
        start_date: Only include results after this date (ISO 8601)
        end_date: Only include results before this date (ISO 8601)
        include_text: Only include results containing ALL these terms
        exclude_text: Exclude results containing ANY of these terms
        include_sources: Only include these sources
        exclude_sources: Exclude these sources
        boost_recent: Boost more recent results
        boost_popular: Boost results with popularity metrics
        format_type: Output format (text, json, markdown)
    """
    results = engine.search_with_filters(
        query=query,
        limit=limit,
        include_domains=include_domains or [],
        exclude_domains=exclude_domains or [],
        start_date=start_date or None,
        end_date=end_date or None,
        include_text=include_text or [],
        exclude_text=exclude_text or [],
        include_sources=include_sources or [],
        exclude_sources=exclude_sources or [],
        boost_recent=boost_recent,
        boost_popular=boost_popular,
    )

    if not results:
        return "No results found matching filters."

    if format_type == "json":
        from search.structured_output import StructuredOutput
        formatter = StructuredOutput()
        return formatter.format_results(results, "general", "json")

    output = f"Found {len(results)} results for '{query}':\n\n"
    for i, result in enumerate(results, 1):
        output += f"--- Result {i} (Source: {result.source}) ---\n"
        output += f"Title: {result.title}\n"
        output += f"Content: {result.content[:500]}...\n"
        output += f"URL: {result.url}\n\n"

    return output


# --- Code Context Tools ---

@mcp.tool()
def code_search(
    query: str,
    max_results: int = 10,
    language: str = "",
    tokens_target: int = 5000,
) -> str:
    """
    Search for code snippets from GitHub and Stack Overflow.
    Inspired by Exa's Context API for coding agents.

    Args:
        query: Code search query (e.g., "React hooks state management")
        max_results: Maximum snippets to return (default 10)
        language: Filter by programming language (e.g., "python", "javascript")
        tokens_target: Target token count for response (default 5000)
    """
    result = search_code_context(query, max_results, language, tokens_target)

    if not result.snippets:
        return "No code snippets found."

    return result.formatted_response


# --- Lead Generation Tools ---

@mcp.tool()
async def search_leads(
    query: str,
    limit: int = 20,
    industries: list[str] = None,
    roles: list[str] = None,
    technologies: list[str] = None,
    locations: list[str] = None,
    keywords: list[str] = None,
) -> str:
    """
    Search and score leads against an Ideal Customer Profile.

    Args:
        query: Search query
        limit: Maximum leads to return (default 20)
        industries: Target industries (e.g., ["fintech", "saas"])
        roles: Target roles (e.g., ["CEO", "CTO", "Developer"])
        technologies: Target technologies (e.g., ["Python", "React"])
        locations: Target locations (e.g., ["San Francisco", "Remote"])
        keywords: Additional keywords to match
    """
    icp = create_icp(
        industries=industries,
        roles=roles,
        technologies=technologies,
        locations=locations,
        keywords=keywords,
    )

    leads = engine.search_leads(query, limit, icp=icp)

    if not leads:
        return "No leads found."

    output = f"Found {len(leads)} leads for '{query}':\n\n"
    for i, lead in enumerate(leads[:limit], 1):
        output += f"--- Lead {i} (Score: {lead.score:.0f}/100) ---\n"
        output += f"Title: {lead.result.title}\n"
        output += f"URL: {lead.result.url}\n"
        output += f"Reasons: {', '.join(lead.match_reasons)}\n"
        if lead.enrichment:
            output += f"Enrichment: {json.dumps(lead.enrichment, default=str)[:200]}\n"
        output += "\n"

    return output


# --- Category Tools ---

@mcp.tool()
def list_categories() -> str:
    """List all available search categories and their descriptions."""
    info = get_category_info()
    output = "Available categories:\n\n"
    for cat, desc in info.items():
        output += f"- {cat}: {desc}\n"
    return output


@mcp.tool()
def detect_query_category(query: str) -> str:
    """Auto-detect the best category for a search query.

    Args:
        query: The search query to categorize
    """
    category = engine.detect_query_category(query)
    return f"Detected category: {category}"


# --- Indexing Tools ---

@mcp.tool()
async def index_topic(
    topic: str,
    max_results_per_source: int = 10,
    category: str = "auto",
    sources: list[str] = None,
) -> str:
    """
    Crawl and index a topic with optional category and source filtering.

    Args:
        topic: Topic to index (e.g., "AI Indonesia", "python web framework")
        max_results_per_source: Max results per source (default 10)
        category: Category hint (auto, company, people, etc.) - default auto
        sources: Specific sources to crawl (optional, default all)
    """
    count = await engine.index_topic(topic, max_results_per_source, category, sources)
    return f"Indexed {count} results for topic '{topic}'."


@mcp.tool()
async def web_crawl(
    url: str,
    max_age_hours: int = -1,
    livecrawl_timeout: int = 10000,
    subpages: int = 0,
    subpage_target: str = "",
) -> str:
    """
    Crawl a URL and extract content, optionally crawling subpages.

    Args:
        url: URL to crawl
        max_age_hours: Cache freshness control
            - 24: Use cache if <24 hours old
            - 1: Use cache if <1 hour old
            - 0: Always livecrawl
            - -1: Cache only (default)
        livecrawl_timeout: Timeout in ms for livecrawl (default 10000)
        subpages: Number of subpages to also crawl (default 0 = none)
        subpage_target: Keyword to filter subpages (e.g., "docs", "blog")
    """
    results = await web_crawler.crawl(
        url,
        max_age_hours=max_age_hours,
        livecrawl_timeout=livecrawl_timeout,
        subpages=subpages,
        subpage_target=subpage_target,
    )
    if results:
        for result in results:
            engine.vector_store.add(result)
        if len(results) == 1:
            return f"Crawled and indexed: {results[0].title}"
        titles = [r.title for r in results]
        return f"Crawled and indexed {len(results)} pages:\n" + "\n".join(
            f"  - {t}" for t in titles
        )
    return "Failed to crawl URL."


@mcp.tool()
async def quick_search(query: str, source: str = "") -> str:
    """
    Real-time search without using the database.

    Args:
        query: Search query
        source: Source to search (duckduckgo, reddit, etc.) - optional
    """
    from crawlers.duckduckgo_crawler import DuckDuckGoCrawler

    if not source:
        source = "duckduckgo"

    crawler_map = {
        "duckduckgo": DuckDuckGoCrawler,
    }

    if source not in crawler_map:
        return f"Source '{source}' not available for quick search."

    crawler = crawler_map[source]()
    results = await crawler.crawl(query, max_results=5)

    if not results:
        return "No results found."

    output = f"Quick search results for '{query}':\n\n"
    for i, result in enumerate(results, 1):
        output += f"{i}. {result.title}\n   {result.url}\n   {result.content[:200]}...\n\n"

    return output


# --- Utility Tools ---

@mcp.tool()
async def answer(
    query: str,
    num_results: int = 10,
    output_schema: str = "",
    system_prompt: str = "",
) -> dict:
    """
    Get an answer with inline citations [1][2].

    Searches all 7 sources (Web, Reddit, YouTube, GitHub,
    Twitter/X, DuckDuckGo, Wikipedia) and returns numbered
    citations with a synthesis prompt for the AI host.

    Args:
        query: Question to answer
        num_results: Number of source results (default 10, max 20)
        output_schema: JSON string of output schema (optional)
        system_prompt: Custom instructions for synthesis (optional)
    """
    import json as _json
    schema = _json.loads(output_schema) if output_schema else None
    result = await answer_engine.answer(
        query=query,
        num_results=min(num_results, 20),
        output_schema=schema,
        system_prompt=system_prompt,
    )
    return {
        "query": result.query,
        "context": result.context,
        "synthesis_prompt": result.synthesis_prompt,
        "sources": result.sources,
    }


@mcp.tool()
def list_sources() -> str:
    """List all available data sources."""
    sources = [
        "web - General web crawling",
        "reddit - Reddit posts and discussions",
        "youtube - YouTube videos and metadata",
        "github - GitHub repositories",
        "twitter - Twitter/X posts via Nitter",
        "duckduckgo - DuckDuckGo search results",
        "wikipedia - Wikipedia articles",
    ]
    return "Available sources:\n" + "\n".join(f"- {s}" for s in sources)


@mcp.tool()
def db_stats() -> str:
    """Get database statistics."""
    stats = engine.stats()
    cache_stats = livecrawl_manager.get_stats()
    return (
        f"Database stats:\n"
        f"- Total documents: {stats['total_documents']}\n"
        f"- Sources: {', '.join(stats['sources']) if stats['sources'] else 'none'}\n"
        f"\nCache stats:\n"
        f"- Size: {cache_stats['size']}\n"
        f"- Hit rate: {cache_stats['hit_rate']}\n"
        f"- Hits: {cache_stats['hits']}\n"
        f"- Misses: {cache_stats['misses']}\n"
        f"- Livecrawls: {cache_stats['livecrawls']}"
    )


# --- Monitor Tools ---


@mcp.tool()
def create_monitor(query: str, sources: str = "", max_results: int = 20) -> str:
    """
    Create a recurring search monitor with deduplication.

    Each run returns only NEW results not seen in previous runs.

    Args:
        query: Search query to monitor
        sources: Comma-separated sources (e.g., "web,reddit") — empty = all
        max_results: Max results per source per run (default 20)
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    mid = monitor_manager.create_monitor(
        query=query, sources=source_list, max_results=max_results
    )
    return f"Monitor created with ID: {mid}\nQuery: {query}\nSources: {sources or 'all'}"


@mcp.tool()
def list_monitors() -> str:
    """List all monitors with stats."""
    monitors = monitor_manager.list_monitors()
    if not monitors:
        return "No monitors found."
    lines = [f"Monitors ({len(monitors)}):"]
    for m in monitors:
        lines.append(
            f"  [{m['id']}] {m['query']}\n"
            f"    Runs: {m['run_count']} | Seen: {m['seen_count']} | "
            f"Last run: {m['last_run'] or 'never'}"
        )
    return "\n".join(lines)


@mcp.tool()
async def run_monitor(monitor_id: str) -> str:
    """
    Run a monitor — returns only NEW results since last run.

    Args:
        monitor_id: Monitor ID from create_monitor
    """
    results = await monitor_manager.run_monitor(monitor_id, engine.crawler_manager)
    if results is None:
        return f"Monitor {monitor_id} not found."
    if not results:
        monitors = monitor_manager.list_monitors()
        seen = next((m["seen_count"] for m in monitors if m["id"] == monitor_id), 0)
        return f"No new results since last run. Total seen: {seen}"

    lines = [f"New results: {len(results)}"]
    for r in results:
        lines.append(f"  - {r.title} ({r.source})\n    {r.url}")
    return "\n".join(lines)


@mcp.tool()
def delete_monitor(monitor_id: str) -> str:
    """
    Delete a monitor and its state.

    Args:
        monitor_id: Monitor ID to delete
    """
    deleted = monitor_manager.delete_monitor(monitor_id)
    if deleted:
        return f"Monitor {monitor_id} deleted."
    return f"Monitor {monitor_id} not found."


if __name__ == "__main__":
    mcp.run()
