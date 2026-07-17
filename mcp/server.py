# server.py — Consolidated MCP tools (31 → 10)
# All features preserved, just combined by action/mode parameter.

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
from search.docs_engine import DocsSearchEngine

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
from pathlib import Path
docs_engine = DocsSearchEngine(
    str(Path(__file__).parent / "data" / "docs_library_registry.json")
)


# =============================================================================
# 1. SEARCH — merges deep_search, advanced_search, quick_search, stream_search,
#    smart_search, code_search, context_search
# =============================================================================


@mcp.tool()
async def search(
    query: str,
    mode: str = "basic",
    source: str = "",
    limit: int = 10,
    category: str = "",
    format_type: str = "text",
    search_depth: str = "basic",
    topic: str = "general",
    max_age_hours: int = -1,
    # advanced filters
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
    # streaming
    sources: str = "",
    # smart
    top_full: int = 3,
    max_overview_tokens: int = 500,
    # code/context
    language: str = "",
    budget_tokens: int = 0,
    num_results: int = 0,
    tokens_target: int = 5000,
    # docs mode
    library: str = "",
    version: str = "",
    docs_refresh: bool = False,
) -> str:
    """
    Unified search tool — all search modes in one.

    Modes:
      - "basic": Semantic search across all indexed content (default)
      - "advanced": Search with domain/date/text/source filters
      - "quick": Real-time search without database (DuckDuckGo)
      - "stream": Search with streaming batches + timing metadata
      - "smart": Compact IR overview + full details for top N (saves 50-70% tokens)
      - "code": Search GitHub + Stack Overflow for code snippets
      - "context": Token-budget-aware snippet packing for agents
      - "docs": Search documentation libraries (requires 'library' param)

    Args:
        query: Search query in natural language
        mode: Search mode (basic, advanced, quick, stream, smart, code, context)
        source: Filter by source (reddit, youtube, github, etc.)
        limit: Maximum number of results (default 10)
        category: Category filter (company, people, etc.) - use "auto" for detection
        format_type: Output format (text, json, markdown) - for basic/advanced modes
        search_depth: "fast" (3/source), "basic" (5/source), "advanced" (20/source + rerank)
        topic: "general" (default) or "news" (boost recent news sites)
        max_age_hours: Freshness - -1 (no limit), 1 (last hour), 24 (last day), 168 (last week)

        # Advanced mode filters:
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

        # Stream mode:
        sources: Comma-separated sources (e.g., "web,github") — empty = all

        # Smart mode:
        top_full: Number of top results to get full content for (default 3)
        max_overview_tokens: Max tokens for overview section (default 500)

        # Code/Context mode:
        language: Filter by programming language (e.g., "python", "javascript")
        budget_tokens: Max tokens for returned context (context mode, default 8000)
        num_results: Max results to consider before budget packing (context mode)
        tokens_target: Target token count for code snippets (default 5000)

        # Docs mode:
        library: Documentation library to search (e.g., "python", "react")
        version: Specific library version (optional, defaults to latest)
        docs_refresh: Force refresh cached docs (default False)
    """
    # --- DOCS MODE ---
    if mode == "docs":
        if not library:
            available = ", ".join(docs_engine.registry.list_libraries())
            return f"Error: 'library' required for docs mode. Available: {available}"

        try:
            result = await docs_engine.search(
                query=query,
                library=library,
                version=version,
                force_refresh=docs_refresh,
                tokens_target=tokens_target,
            )
            return result.formatted
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error searching docs: {str(e)}"

    # --- QUICK MODE ---
    if mode == "quick":
        from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
        from crawlers.youtube_crawler import YouTubeCrawler
        from crawlers.github_crawler import GitHubCrawler
        from crawlers.wikipedia_crawler import WikipediaCrawler
        src = source or "duckduckgo"
        crawler_map = {
            "duckduckgo": DuckDuckGoCrawler,
            "youtube": YouTubeCrawler,
            "github": GitHubCrawler,
            "wikipedia": WikipediaCrawler,
        }
        if src not in crawler_map:
            available = ", ".join(crawler_map.keys())
            return f"Source '{src}' not available. Available: {available}"
        crawler = crawler_map[src]()
        results = await crawler.crawl(query, max_results=5)
        if not results:
            return f"Quick search for '{query}' returned no results."
        source_name = src.capitalize() + " Quick Search"
        output = f"{source_name} results for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            output += f"{i}. {result.title}\n   {result.url}\n   {result.content[:200]}...\n\n"
        return output

    # --- STREAM MODE ---
    if mode == "stream":
        source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
        result = await stream_manager.search(query, limit, source_list)
        if result.total_results == 0:
            # Auto-fallback: all sources failed → try DuckDuckGo live
            from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
            ddg = DuckDuckGoCrawler()
            fallback = await ddg.crawl(query, max_results=limit or 10)
            if fallback:
                data = {
                    "query": query,
                    "total_results": len(fallback),
                    "total_time_ms": 0,
                    "sources_searched": ["duckduckgo (fallback)"],
                    "batches": [
                        {
                            "batch": 1,
                            "source": "duckduckgo (fallback)",
                            "time_ms": 0,
                            "result_count": len(fallback),
                            "results": [
                                {"title": r.title, "url": r.url, "content": r.content[:500], "source": "duckduckgo"}
                                for r in fallback
                            ],
                        }
                    ],
                    "note": "All sources returned no results. Showing DuckDuckGo fallback.",
                }
                return json.dumps(data, indent=2)
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

    # --- SMART MODE ---
    if mode == "smart":
        result = await smart_engine.search(query, top_full, limit or 10, max_overview_tokens)
        lines = [f'Smart Search: "{result.query}"', ""]
        lines.append(f"Overview ({len(result.overview)} items, ~{result.tokens_overview} tokens):")
        for ir in result.overview:
            lines.append(f"  {ir.to_line()}")
        lines.append("")
        lines.append(f"Details (top {len(result.details)}, ~{result.tokens_details} tokens):")
        for d in result.details:
            lines.append(f"  [{d.n}] {d.title} — {d.source}")
            lines.append(f"      URL: {d.url}")
            lines.append(f"      {d.content[:300]}")
            lines.append("")
        lines.append(f"Token savings: ~{result.tokens_saved_pct}% vs raw results")
        return "\n".join(lines)

    # --- CODE MODE ---
    if mode == "code":
        result = search_code_context(query, limit, language, tokens_target)
        if not result.snippets:
            return "No code snippets found."
        return result.formatted_response

    # --- CONTEXT MODE ---
    if mode == "context":
        result = await context_engine.search(
            query=query,
            budget_tokens=budget_tokens or 8000,
            language=language,
            num_results=num_results or 20,
        )
        lines = [result.formatted]
        lines.append(
            f"\nBudget: {result.tokens_budget:,} tokens | Used: {result.tokens_used:,} | "
            f"Snippets: {len(result.snippets)} of {result.total_snippets_found} considered"
        )
        return "\n".join(lines)

    # --- ADVANCED MODE ---
    if mode == "advanced":
        if category == "auto":
            category = engine.detect_query_category(query)
        has_filters = any([include_domains, exclude_domains, start_date, end_date,
                          include_text, exclude_text, include_sources, exclude_sources])
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
            # Auto-fallback: only when no active filters
            if not has_filters:
                from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
                crawler = DuckDuckGoCrawler()
                results = await crawler.crawl(query, max_results=limit)
                if results:
                    # Index fallback results
                    for r in results:
                        engine.vector_store.add(r)
                    output = f"No indexed results. Live search via DuckDuckGo:\n\n"
                    for i, result in enumerate(results, 1):
                        output += f"--- Result {i} ---\n"
                        output += f"Title: {result.title}\n"
                        output += f"Content: {result.content[:500]}...\n"
                        output += f"URL: {result.url}\n\n"
                    return output
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

    # --- BASIC MODE (default) ---
    if category == "auto":
        category = engine.detect_query_category(query)
    if format_type in ("json", "markdown"):
        output = engine.search_and_format(query, limit, format_type, category)
        if "No results" not in output:
            return output
    results = engine.search(
        query, limit, source, category=category,
        search_depth=search_depth, topic=topic, max_age_hours=max_age_hours,
    )
    if not results:
        # Auto-fallback: DB empty → live crawl via DuckDuckGo
        from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
        crawler = DuckDuckGoCrawler()
        results = await crawler.crawl(query, max_results=limit)
        if results:
            # Index fallback results so next search finds them
            for r in results:
                engine.vector_store.add(r)
            source_label = "DuckDuckGo (live)"
            output = f"No indexed results. Live search via {source_label}:\n\n"
            for i, result in enumerate(results, 1):
                output += f"--- Result {i} ---\n"
                output += f"Title: {result.title}\n"
                output += f"Content: {result.content[:500]}...\n"
                output += f"URL: {result.url}\n\n"
            return output
        return "No results found."
    output = f"Found {len(results)} results for '{query}':\n\n"
    for i, result in enumerate(results, 1):
        output += f"--- Result {i} (Source: {result.source}) ---\n"
        output += f"Title: {result.title}\n"
        output += f"Content: {result.content[:500]}...\n"
        output += f"URL: {result.url}\n\n"
    return output


# =============================================================================
# 2. CRAWL — merges web_crawl, extract_content
# =============================================================================


@mcp.tool()
async def crawl(
    url: str = "",
    urls: str = "",
    max_age_hours: int = -1,
    livecrawl_timeout: int = 10000,
    subpages: int = 0,
    subpage_target: str = "",
    extract_depth: str = "basic",
    instructions: str = "",
) -> str:
    """
    Crawl URLs and extract content. Supports single URL or batch extraction.

    Use 'url' for single URL crawl with subpage discovery.
    Use 'urls' (comma-separated) for batch extraction.

    Args:
        url: Single URL to crawl (with subpage support)
        urls: Comma-separated URLs for batch extraction
        max_age_hours: Cache freshness (24 = <24h, 1 = <1h, 0 = live, -1 = cache only)
        livecrawl_timeout: Timeout in ms for livecrawl (default 10000)
        subpages: Number of subpages to also crawl (single URL mode, default 0)
        subpage_target: Keyword to filter subpages (e.g., "docs", "blog")
        extract_depth: "basic" (text only) or "advanced" (text + metadata + links)
        instructions: What to extract (e.g., "product prices", "contact info")
    """
    # Batch mode
    if urls:
        url_list = [u.strip() for u in urls.split(",") if u.strip()]
        if not url_list:
            return "No URLs provided."
        result = content_extractor.extract(
            urls=url_list, extract_depth=extract_depth, instructions=instructions,
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
            if content.error:
                lines.append(f"Error: {content.error}")
            else:
                lines.append(f"Text: {content.text[:500]}...")
                if content.links:
                    lines.append(f"Links: {len(content.links)} found")
                if content.metadata:
                    lines.append(f"Metadata: {len(content.metadata)} fields")
            lines.append("")
        return "\n".join(lines)

    # Single URL mode
    if not url:
        return "Provide either 'url' (single) or 'urls' (batch)."

    results = await web_crawler.crawl(
        url, max_age_hours=max_age_hours, livecrawl_timeout=livecrawl_timeout,
        subpages=subpages, subpage_target=subpage_target,
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


# =============================================================================
# 3. MONITOR — merges create_monitor, list_monitors, run_monitor, delete_monitor
# =============================================================================


@mcp.tool()
async def monitor(
    action: str = "list",
    monitor_id: str = "",
    query: str = "",
    sources: str = "",
    max_results: int = 20,
) -> str:
    """
    Manage persistent search monitors with deduplication.

    Actions:
      - "create": Create a new monitor (requires query)
      - "list": List all monitors with stats
      - "run": Run a monitor, returns only NEW results (requires monitor_id)
      - "delete": Delete a monitor (requires monitor_id)

    Args:
        action: Action to perform (create, list, run, delete)
        monitor_id: Monitor ID (required for run/delete)
        query: Search query to monitor (required for create)
        sources: Comma-separated sources for create (e.g., "web,reddit") — empty = all
        max_results: Max results per source per run (default 20, for create)
    """
    if action == "create":
        if not query:
            return "Error: 'query' is required for create."
        source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
        mid = monitor_manager.create_monitor(query=query, sources=source_list, max_results=max_results)
        return f"Monitor created with ID: {mid}\nQuery: {query}\nSources: {sources or 'all'}"

    if action == "list":
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

    if action == "run":
        if not monitor_id:
            return "Error: 'monitor_id' is required for run."
        if monitor_id not in monitor_manager.monitors:
            return f"Monitor '{monitor_id}' not found. Use monitor(action='list') to see available monitors."
        results = await monitor_manager.run_monitor(monitor_id, engine.crawler_manager)
        if not results:
            monitors = monitor_manager.list_monitors()
            seen = next((m["seen_count"] for m in monitors if m["id"] == monitor_id), 0)
            return f"No new results since last run. Total seen: {seen}"
        lines = [f"New results: {len(results)}"]
        for r in results:
            lines.append(f"  - {r.title} ({r.source})\n    {r.url}")
        return "\n".join(lines)

    if action == "delete":
        if not monitor_id:
            return "Error: 'monitor_id' is required for delete."
        deleted = monitor_manager.delete_monitor(monitor_id)
        if deleted:
            return f"Monitor {monitor_id} deleted."
        return f"Monitor {monitor_id} not found."

    return f"Unknown action '{action}'. Use: create, list, run, delete."


# =============================================================================
# 4. WEBSET — merges create_webset, add_to_webset, list_websets, get_webset,
#    enrich_webset, delete_webset
# =============================================================================


@mcp.tool()
async def webset(
    action: str = "list",
    webset_id: str = "",
    name: str = "",
    description: str = "",
    query: str = "",
    max_results: int = 10,
) -> str:
    """
    Manage webset containers for collecting and enriching entity lists.

    Actions:
      - "create": Create a named container (requires name)
      - "add": Search and add results to a webset (requires webset_id + query)
      - "list": List all webset containers
      - "get": Get webset with all items (requires webset_id)
      - "enrich": Scrape URLs for emails, social links, technologies (requires webset_id)
      - "delete": Delete a webset and all items (requires webset_id)

    Args:
        action: Action to perform (create, add, list, get, enrich, delete)
        webset_id: Webset ID (required for add, get, enrich, delete)
        name: Webset name for create (e.g., "AI Startups SF")
        description: Optional description for create
        query: Search query to find entities (required for add)
        max_results: Max results per source for add (default 10)
    """
    if action == "create":
        if not name:
            return "Error: 'name' is required for create."
        container = webset_manager.create_container(name, description)
        return f"Webset created: {container.id}\nName: {container.name}\nDescription: {container.description}"

    if action == "add":
        if not webset_id:
            return "Error: 'webset_id' is required for add."
        if not query:
            return "Error: 'query' is required for add."
        container = webset_manager.get_container(webset_id)
        if not container:
            return f"Webset {webset_id} not found."
        results = await engine.crawler_manager.crawl_all(query, max_results_per_source=max_results)
        added = webset_manager.add_items_from_search(webset_id, results)
        return f"Added {added} items to '{container.name}' ({len(container.items)} total)"

    if action == "list":
        containers = webset_manager.list_containers()
        if not containers:
            return "No websets found."
        lines = [f"Websets ({len(containers)}):"]
        for c in containers:
            lines.append(f"  [{c['id']}] {c['name']} — {c['item_count']} items\n    {c['description']}")
        return "\n".join(lines)

    if action == "get":
        if not webset_id:
            return "Error: 'webset_id' is required for get."
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

    if action == "enrich":
        if not webset_id:
            return "Error: 'webset_id' is required for enrich."
        container = webset_manager.get_container(webset_id)
        if not container:
            return f"Webset {webset_id} not found."
        result = await webset_manager.enrich_all(webset_id)
        if result["count"] == 0:
            return f"No items to enrich in '{container.name}'"
        lines = [f"Enriched {result['count']} items in '{container.name}':"]
        for item in result["items"]:
            lines.append(f"  - {item['title'][:60]} ({len(item['props'])} fields)")
        return "\n".join(lines)

    if action == "delete":
        if not webset_id:
            return "Error: 'webset_id' is required for delete."
        deleted = webset_manager.delete_container(webset_id)
        if deleted:
            return f"Webset {webset_id} deleted."
        return f"Webset {webset_id} not found."

    return f"Unknown action '{action}'. Use: create, add, list, get, enrich, delete."


# =============================================================================
# 5. INFO — merges list_categories, detect_query_category, list_sources, db_stats
# =============================================================================


@mcp.tool()
def info(
    type: str = "sources",
    query: str = "",
) -> str:
    """
    Get information about the search engine.

    Types:
      - "categories": List all available search categories
      - "sources": List all available data sources
      - "stats": Get database and cache statistics
      - "detect": Auto-detect the best category for a query (requires query)

    Args:
        type: Info type (categories, sources, stats, detect)
        query: Search query for detect mode
    """
    if type == "categories":
        cats = get_category_info()
        output = "Available categories:\n\n"
        for cat, desc in cats.items():
            output += f"- {cat}: {desc}\n"
        return output

    if type == "sources":
        from crawlers.manager import CrawlerManager
        manager = CrawlerManager()
        sources = []
        for source_name in manager.crawlers.keys():
            source_display = source_name.capitalize()
            if source_name == "duckduckgo":
                source_display = "DuckDuckGo (search)"
            elif source_name == "web":
                source_display = "Web (crawler)"
            elif source_name == "reddit":
                source_display = "Reddit (posts)"
            elif source_name == "youtube":
                source_display = "YouTube (videos)"
            elif source_name == "github":
                source_display = "GitHub (repositories)"
            elif source_name == "twitter":
                source_display = "Twitter/X (tweets)"
            elif source_name == "wikipedia":
                source_display = "Wikipedia (articles)"
            sources.append(f"{source_display} - {get_source_description(source_name)}")
        return "Available sources:\n" + "\n".join(f"- {s}" for s in sources)


def get_source_description(source_name: str) -> str:
    """Get human-readable description for a source."""
    descriptions = {
        "web": "General web page crawling with markdown extraction",
        "reddit": "Reddit posts and comments via JSON API",
        "youtube": "YouTube video search via yt-dlp",
        "github": "GitHub repository search via API",
        "twitter": "Twitter/X posts via Nitter instances",
        "duckduckgo": "DuckDuckGo HTML search results",
        "wikipedia": "Wikipedia article search via MediaWiki API",
    }
    return descriptions.get(source_name, "Search source")

    if type == "stats":
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

    if type == "detect":
        if not query:
            return "Error: 'query' is required for detect."
        category = engine.detect_query_category(query)
        return f"Detected category: {category}"

    return f"Unknown type '{type}'. Use: categories, sources, stats, detect."


# =============================================================================
# 6. RESEARCH — merges start_research, ask_followup, list_sessions, delete_session
# =============================================================================


@mcp.tool()
async def research(
    action: str = "list",
    session_id: str = "",
    query: str = "",
    sources: str = "",
    max_results: int = 15,
    num_results: int = 5,
) -> str:
    """
    Manage deep research sessions with auto sub-queries and semantic follow-up.

    Actions:
      - "start": Start a research session (requires query)
      - "followup": Ask a follow-up question (requires session_id + query)
      - "list": List all research sessions
      - "delete": Delete a research session (requires session_id)

    Args:
        action: Action to perform (start, followup, list, delete)
        session_id: Session ID (required for followup, delete)
        query: Research topic or follow-up question (required for start, followup)
        sources: Comma-separated sources for start (e.g., "web,reddit") — empty = all
        max_results: Max results per source per sub-query (default 15, for start)
        num_results: Number of results for followup (default 5)
    """
    if action == "start":
        if not query:
            return "Error: 'query' is required for start."
        source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
        result = await research_manager.start_research(
            query=query, sources=source_list, max_results=max_results,
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
        lines.append(f"\nUse research(action='followup', session_id='{result['session_id']}', query='...') to ask questions.")
        return "\n".join(lines)

    if action == "followup":
        if not session_id:
            return "Error: 'session_id' is required for followup."
        if not query:
            return "Error: 'query' is required for followup."
        results = research_manager.ask_followup(session_id, query, num_results)
        if not results:
            return f"Session {session_id} not found or no results."
        lines = [f"Follow-up results ({len(results)}):"]
        for r in results:
            lines.append(f"  - {r.title} ({r.source})\n    {r.url}\n    {r.content[:200]}")
        return "\n".join(lines)

    if action == "list":
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

    if action == "delete":
        if not session_id:
            return "Error: 'session_id' is required for delete."
        deleted = research_manager.delete_session(session_id)
        if deleted:
            return f"Research session {session_id} deleted."
        return f"Research session {session_id} not found."

    return f"Unknown action '{action}'. Use: start, followup, list, delete."


# =============================================================================
# 7. ANSWER — unchanged (unique: search + synthesis with citations)
# =============================================================================


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


# =============================================================================
# 8. SEARCH_LEADS — unchanged (unique: ICP scoring)
# =============================================================================


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
        industries=industries, roles=roles, technologies=technologies,
        locations=locations, keywords=keywords,
    )
    leads = engine.search_leads(query, limit, icp=icp)
    if not leads:
        # Auto-fallback: DB empty → live crawl via DuckDuckGo
        from crawlers.duckduckgo_crawler import DuckDuckGoCrawler
        ddg = DuckDuckGoCrawler()
        live_results = await ddg.crawl(query, max_results=limit)
        if live_results:
            if icp:
                engine.lead_scorer.set_icp(icp)
            leads = engine.lead_scorer.score_batch(live_results)
            if leads:
                output = f"No indexed leads. Live search via DuckDuckGo ({len(leads)} leads):\n\n"
                for i, lead in enumerate(leads[:limit], 1):
                    output += f"--- Lead {i} (Score: {lead.score:.0f}/100) ---\n"
                    output += f"Title: {lead.result.title}\n"
                    output += f"URL: {lead.result.url}\n"
                    output += f"Reasons: {', '.join(lead.match_reasons)}\n"
                    output += "\n"
                return output
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


# =============================================================================
# 9. SITE_MAP — unchanged (unique: BFS crawl)
# =============================================================================


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
        url=url, max_depth=max_depth, instructions=instructions, max_pages=max_pages,
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


# =============================================================================
# 10. INDEX_TOPIC — unchanged (unique: crawl + index)
# =============================================================================


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
    result = await engine.index_topic_with_details(topic, max_results_per_source, category, sources)
    lines = [f"Indexed {result['total']} results for topic '{topic}':"]
    for source, count in result['by_source'].items():
        lines.append(f"  {source}: {count} results")
    if result['total'] == 0:
        lines.append("\nNo results found. Try a different topic or check sources.")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
