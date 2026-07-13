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
from search.research import ResearchManager
from search.context import ContextEngine
from search.streaming import StreamSearchManager
from search.websets import WebsetManager
from search.smart_search import SmartSearchEngine
from search.sitemap import SiteMapper
from search.extract import ContentExtractor
from crawlers.web_crawler import WebCrawler

mcp = FastMCP("DeepSearchEngine")
engine = SearchEngine()
answer_engine = AnswerEngine(engine.crawler_manager, engine.vector_store)
web_crawler = WebCrawler()
monitor_manager = MonitorManager()
research_manager = ResearchManager(engine.vector_store.client, engine.vector_store.embedding_model)
context_engine = ContextEngine(engine.crawler_manager, engine.vector_store)
stream_manager = StreamSearchManager(engine.crawler_manager, engine.vector_store)
webset_manager = WebsetManager()
smart_engine = SmartSearchEngine(engine.crawler_manager, engine.vector_store)
site_mapper = SiteMapper()
content_extractor = ContentExtractor()


# --- Core Search Tools ---

@mcp.tool()
async def deep_search(
    query: str,
    source: str = "",
    limit: int = 10,
    category: str = "",
    format_type: str = "text",
    search_depth: str = "basic",
    topic: str = "general",
    max_age_hours: int = -1,
) -> str:
    """
    Semantic search across all indexed content with optional filtering.

    Args:
        query: Search query in natural language
        source: Filter by source (reddit, youtube, github, etc.) - optional
        limit: Maximum number of results (default 10)
        category: Category filter (company, people, research_paper, etc.) - optional
        format_type: Output format (text, json, markdown) - default text
        search_depth: Search depth - "fast" (3/source), "basic" (5/source), "advanced" (20/source + rerank)
        topic: Topic filter - "general" (default) or "news" (boost recent news sites)
        max_age_hours: Freshness filter - -1 (no limit), 1 (last hour), 24 (last day), 168 (last week)
    """
    if category == "auto":
        category = engine.detect_query_category(query)

    if format_type in ("json", "markdown"):
        output = engine.search_and_format(query, limit, format_type, category)
        return output

    results = engine.search(
        query, limit, source, category=category,
        search_depth=search_depth, topic=topic, max_age_hours=max_age_hours,
    )

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
    search_depth: str = "basic",
    topic: str = "general",
    max_age_hours: int = -1,
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
        search_depth: Search depth - "fast", "basic", "advanced"
        topic: Topic filter - "general" or "news"
        max_age_hours: Freshness filter - -1 (no limit), 1 (last hour), 24 (last day), 168 (last week)
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
        search_depth=search_depth,
        topic=topic,
        max_age_hours=max_age_hours,
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


# --- Context Search Tool ---


@mcp.tool()
async def context_search(
    query: str,
    budget_tokens: int = 8000,
    language: str = "",
    num_results: int = 20,
) -> str:
    """
    Search code and docs with token budget limit.

    Returns snippets that fit within the token budget,
    ready to inject into your context window.

    Args:
        query: What to search for
        budget_tokens: Max tokens for returned context (default 8000)
        language: Filter by programming language (e.g., "python", "javascript")
        num_results: Max results to consider before budget packing
    """
    result = await context_engine.search(
        query=query,
        budget_tokens=budget_tokens,
        language=language,
        num_results=num_results,
    )
    lines = [result.formatted]
    lines.append(f"\nBudget: {result.tokens_budget:,} tokens | Used: {result.tokens_used:,} | Snippets: {len(result.snippets)} of {result.total_snippets_found} considered")
    return "\n".join(lines)


# --- Smart Search Tool (Knowledge IR + Context Optimizer) ---


@mcp.tool()
async def smart_search(
    query: str,
    top_full: int = 3,
    num_results: int = 10,
    max_overview_tokens: int = 500,
) -> str:
    """
    Hybrid search: compact overview + full details for top results.

    Returns Knowledge IR (compact one-line summaries for all results)
    plus full content for the top N most relevant. Saves 50-70% tokens
    compared to raw results while maintaining accuracy.

    Args:
        query: Search query
        top_full: Number of top results to get full content for (default 3)
        num_results: Total results to consider (default 10)
        max_overview_tokens: Max tokens for overview section (default 500)
    """
    result = await smart_engine.search(query, top_full, num_results, max_overview_tokens)
    lines = [f'Smart Search: "{result.query}"', ""]

    # Overview (compact IR)
    lines.append(f"Overview ({len(result.overview)} items, ~{result.tokens_overview} tokens):")
    for ir in result.overview:
        lines.append(f"  {ir.to_line()}")
    lines.append("")

    # Details (full content for top N)
    lines.append(f"Details (top {len(result.details)}, ~{result.tokens_details} tokens):")
    for d in result.details:
        lines.append(f"  [{d.n}] {d.title} — {d.source}")
        lines.append(f"      URL: {d.url}")
        lines.append(f"      {d.content[:300]}")
        lines.append("")

    lines.append(f"Token savings: ~{result.tokens_saved_pct}% vs raw results")
    return "\n".join(lines)


# --- Streaming Search Tool ---


@mcp.tool()
async def stream_search(
    query: str,
    num_results: int = 10,
    sources: str = "",
) -> str:
    """
    Search with streaming — results grouped by completion order.

    Returns JSON with batches showing which source finished first
    and timing metadata. Faster sources appear earlier.

    Args:
        query: Search query
        num_results: Max results per source
        sources: Comma-separated sources (e.g., "web,github") — empty = all
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    result = await stream_manager.search(query, num_results, source_list)
    data = {
        "query": result.query,
        "total_results": result.total_results,
        "total_time_ms": result.total_time_ms,
        "sources_searched": result.sources_searched,
        "batches": [
            {
                "batch": b.batch_number,
                "source": b.source,
                "time_ms": b.time_ms,
                "result_count": b.result_count,
                "results": b.results,
            }
            for b in result.batches
        ],
    }
    return json.dumps(data, indent=2)


# --- Research Tools ---


@mcp.tool()
async def start_research(query: str, sources: str = "", max_results: int = 15) -> str:
    """
    Start a deep research session on a topic.

    Auto-generates sub-queries, crawls all sources, indexes results
    for semantic follow-up questions.

    Args:
        query: Research topic/question
        sources: Comma-separated sources (e.g., "web,reddit") — empty = all
        max_results: Max results per source per sub-query (default 15)
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    result = await research_manager.start_research(
        query=query,
        sources=source_list,
        max_results=max_results,
        crawler_manager=engine.crawler_manager,
    )
    lines = [
        f"Research session started: {result['session_id']}",
        f"Results indexed: {result['result_count']}",
        f"Sub-queries used: {', '.join(result['sub_queries'])}",
        f"\nTop results:",
    ]
    for title in result["top_titles"]:
        lines.append(f"  - {title}")
    lines.append(f"\nUse ask_followup(session_id='{result['session_id']}', query='...') to ask questions about this research.")
    return "\n".join(lines)


@mcp.tool()
def ask_followup(session_id: str, query: str, num_results: int = 5) -> str:
    """
    Ask a follow-up question about a research session.

    Performs semantic search within the session's indexed results.

    Args:
        session_id: Session ID from start_research
        query: Follow-up question
        num_results: Number of results (default 5)
    """
    results = research_manager.ask_followup(session_id, query, num_results)
    if not results:
        return f"Session {session_id} not found or no results."

    lines = [f"Follow-up results ({len(results)}):"]
    for r in results:
        lines.append(f"  - {r.title} ({r.source})\n    {r.url}\n    {r.content[:200]}")
    return "\n".join(lines)


@mcp.tool()
def list_sessions() -> str:
    """List all research sessions with stats."""
    sessions = research_manager.list_sessions()
    if not sessions:
        return "No research sessions found."
    lines = [f"Research sessions ({len(sessions)}):"]
    for s in sessions:
        lines.append(
            f"  [{s['id']}] {s['query']}\n"
            f"    Results: {s['result_count']} | Follow-ups: {s['followup_count']} | "
            f"Created: {s['created_at']}"
        )
    return "\n".join(lines)


@mcp.tool()
def delete_session(session_id: str) -> str:
    """
    Delete a research session and its indexed data.

    Args:
        session_id: Session ID to delete
    """
    deleted = research_manager.delete_session(session_id)
    if deleted:
        return f"Research session {session_id} deleted."
    return f"Research session {session_id} not found."


# --- Webset Tools ---


@mcp.tool()
def create_webset(name: str, description: str = "") -> str:
    """
    Create a named container for collecting entity items.

    Args:
        name: Webset name (e.g., "AI Startups SF")
        description: Optional description
    """
    container = webset_manager.create_container(name, description)
    return f"Webset created: {container.id}\nName: {container.name}\nDescription: {container.description}"


@mcp.tool()
def add_to_webset(webset_id: str, query: str, max_results: int = 10) -> str:
    """
    Search and add results to a webset container.

    Crawls all sources for the query and adds unique results as items.

    Args:
        webset_id: Webset ID from create_webset
        query: Search query to find entities
        max_results: Max results per source (default 10)
    """
    import asyncio

    container = webset_manager.get_container(webset_id)
    if not container:
        return f"Webset {webset_id} not found."

    results = asyncio.get_event_loop().run_until_complete(
        engine.crawler_manager.crawl_all(query, max_results_per_source=max_results)
    )
    added = webset_manager.add_items_from_search(webset_id, results)
    return f"Added {added} items to '{container.name}' ({len(container.items)} total)"


@mcp.tool()
def list_websets() -> str:
    """List all webset containers."""
    containers = webset_manager.list_containers()
    if not containers:
        return "No websets found."
    lines = [f"Websets ({len(containers)}):"]
    for c in containers:
        lines.append(f"  [{c['id']}] {c['name']} — {c['item_count']} items\n    {c['description']}")
    return "\n".join(lines)


@mcp.tool()
def get_webset(webset_id: str) -> str:
    """
    Get webset container with all items.

    Args:
        webset_id: Webset ID
    """
    container = webset_manager.get_container(webset_id)
    if not container:
        return f"Webset {webset_id} not found."

    lines = [f"Webset: {container.name} ({container.id})", f"Items: {len(container.items)}", ""]
    for item in container.items:
        enriched_tag = " [enriched]" if item.enriched else ""
        lines.append(f"  [{item.id}] {item.title}{enriched_tag}")
        lines.append(f"    URL: {item.url}")
        lines.append(f"    Source: {item.source}")
        if item.properties:
            lines.append(f"    Properties: {json.dumps(item.properties, indent=6)}")
    return "\n".join(lines)


@mcp.tool()
async def enrich_webset(webset_id: str) -> str:
    """
    Enrich all items in a webset by scraping their URLs.

    Extracts emails, social links, technologies, and page metadata.

    Args:
        webset_id: Webset ID
    """
    container = webset_manager.get_container(webset_id)
    if not container:
        return f"Webset {webset_id} not found."

    count = await webset_manager.enrich_all(webset_id)
    return f"Enriched {count} items in '{container.name}'"


@mcp.tool()
def delete_webset(webset_id: str) -> str:
    """
    Delete a webset container and all its items.

    Args:
        webset_id: Webset ID
    """
    deleted = webset_manager.delete_container(webset_id)
    if deleted:
        return f"Webset {webset_id} deleted."
    return f"Webset {webset_id} not found."


# --- Site Map Tool ---


@mcp.tool()
def site_map(
    url: str,
    max_depth: int = 2,
    instructions: str = "",
    max_pages: int = 50,
) -> str:
    """
    Map a website's structure by crawling links breadth-first.

    Args:
        url: Starting URL
        max_depth: How many levels deep to crawl (default 2)
        instructions: Natural language instructions to filter pages (e.g., "only blog posts")
        max_pages: Maximum pages to crawl (default 50)
    """
    result = site_mapper.map_site(
        url=url,
        max_depth=max_depth,
        instructions=instructions,
        max_pages=max_pages,
    )
    if not result.pages:
        return f"No pages found at {url}"

    lines = [
        f"Site map for {result.root_url}",
        f"Total pages: {result.total_pages}",
        f"Max depth reached: {result.max_depth_reached}",
        "",
    ]
    for page in result.pages:
        indent = "  " * page.depth
        lines.append(f"{indent}[depth {page.depth}] {page.title or page.url}")
        lines.append(f"{indent}  URL: {page.url}")
        lines.append(f"{indent}  Links: {page.links_found}")

    return "\n".join(lines)


# --- Extract Content Tool ---


@mcp.tool()
async def extract_content(
    urls: str,
    extract_depth: str = "basic",
    instructions: str = "",
) -> str:
    """
    Extract structured content from URLs.

    Args:
        urls: Comma-separated URLs to extract from
        extract_depth: "basic" (text only) or "advanced" (text + metadata + links)
        instructions: What to extract (e.g., "product prices", "contact info")
    """
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    if not url_list:
        return "No URLs provided."

    result = content_extractor.extract(
        urls=url_list,
        extract_depth=extract_depth,
        instructions=instructions,
    )

    if not result.contents:
        return "No content extracted from provided URLs."

    lines = [
        f"Extracted content from {result.urls_processed} URLs",
        f"Depth: {result.extract_depth}",
        f"Instructions: {result.instructions or 'none'}",
        "",
    ]
    for content in result.contents:
        lines.append(f"--- {content.title or content.url} ---")
        lines.append(f"URL: {content.url}")
        lines.append(f"Text: {content.text[:500]}...")
        if content.links:
            lines.append(f"Links: {len(content.links)} found")
        if content.metadata:
            lines.append(f"Metadata: {len(content.metadata)} fields")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
