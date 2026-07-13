# server.py
import asyncio
from mcp.server.fastmcp import FastMCP
from search.engine import SearchEngine
from crawlers.web_crawler import WebCrawler

mcp = FastMCP("DeepSearchEngine")
engine = SearchEngine()
web_crawler = WebCrawler()

@mcp.tool()
async def deep_search(query: str, source: str = "", limit: int = 10) -> str:
    """
    Semantic search across all indexed content.
    
    Args:
        query: Search query in natural language
        source: Filter by source (reddit, youtube, github, etc.) - optional
        limit: Maximum number of results (default 10)
    """
    results = engine.search(query, limit)
    
    if source:
        results = [r for r in results if r.source == source]
    
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
async def index_topic(topic: str, max_results_per_source: int = 10) -> str:
    """
    Crawl and index a topic from all 7 sources.
    
    Args:
        topic: Topic to index (e.g., "AI Indonesia", "python web framework")
        max_results_per_source: Max results per source (default 10)
    """
    count = await engine.index_topic(topic, max_results_per_source)
    return f"Indexed {count} results for topic '{topic}'."

@mcp.tool()
async def web_crawl(url: str) -> str:
    """
    Crawl a specific URL and add to index.
    
    Args:
        url: URL to crawl
    """
    results = await web_crawler.crawl(url)
    if results:
        engine.vector_store.add(results[0])
        return f"Crawled and indexed: {results[0].title}"
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
        "wikipedia - Wikipedia articles"
    ]
    return "Available sources:\n" + "\n".join(f"- {s}" for s in sources)

@mcp.tool()
def db_stats() -> str:
    """Get database statistics."""
    stats = engine.stats()
    return f"Database stats:\n- Total documents: {stats['total_documents']}\n- Sources: {', '.join(stats['sources']) if stats['sources'] else 'none'}"

if __name__ == "__main__":
    mcp.run()
