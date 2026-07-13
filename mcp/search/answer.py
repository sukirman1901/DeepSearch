import json
from dataclasses import dataclass, field

from crawlers.base import CrawlResult


@dataclass
class AnswerResult:
    """Result from AnswerEngine."""
    query: str
    context: str
    synthesis_prompt: str
    sources: list[dict] = field(default_factory=list)


class AnswerEngine:
    """Search all sources and format for AI synthesis."""

    def __init__(self, crawler_manager, vector_store):
        self.crawler_manager = crawler_manager
        self.vector_store = vector_store

    def _format_context(self, results: list[CrawlResult], query: str) -> tuple[str, list[dict]]:
        """Format results into numbered context block."""
        sources = []
        lines = [f'## Sources for: "{query}"', ""]

        for i, result in enumerate(results, 1):
            excerpt = result.content[:300].replace("\n", " ")
            source_entry = {
                "number": i,
                "title": result.title,
                "url": result.url,
                "source": result.source,
                "excerpt": excerpt,
            }
            sources.append(source_entry)
            lines.append(f"[{i}] {result.title} — {result.source}")
            lines.append(f"    URL: {result.url}")
            lines.append(f"    Excerpt: {excerpt}")
            lines.append("")

        return "\n".join(lines), sources

    def _build_synthesis_prompt(
        self,
        query: str,
        output_schema: dict = None,
        system_prompt: str = "",
    ) -> str:
        """Build instructions for AI host synthesis."""
        lines = ["## Instructions"]

        if system_prompt:
            lines.append(system_prompt)
            lines.append("")

        lines.append(f'Answer the question: "{query}"')
        lines.append("Use inline citations [1][2] to reference sources.")
        lines.append("If information is insufficient, state what's missing.")
        lines.append("Base your answer ONLY on the sources provided.")

        if output_schema:
            lines.append("")
            lines.append("## Output Format")
            lines.append("Return a JSON object matching this schema:")
            lines.append(json.dumps(output_schema, indent=2))

        return "\n".join(lines)

    async def answer(
        self,
        query: str,
        num_results: int = 10,
        output_schema: dict = None,
        system_prompt: str = "",
    ) -> AnswerResult:
        """
        Search all sources and return context + synthesis prompt.

        Flow:
        1. Search all 7 sources concurrently
        2. Search vector store for indexed content
        3. Merge + deduplicate by URL
        4. Rank by relevance score
        5. Select top num_results
        6. Format context block
        7. Generate synthesis prompt
        """
        # 1. Search all sources concurrently
        all_crawl_results = await self.crawler_manager.crawl_all(
            query,
            max_results_per_source=num_results // 2,
            generate_variations=False,
        )

        # 2. Search vector store for indexed content
        vector_results = self.vector_store.search(query, limit=num_results)

        # 3. Merge results
        all_results = all_crawl_results + vector_results

        # 4. Deduplicate by URL
        seen_urls = set()
        deduped = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                deduped.append(result)

        # 5. Sort by score (highest first), take top N
        deduped.sort(key=lambda r: r.score, reverse=True)
        top_results = deduped[:num_results]

        # 6. Format context
        context, sources = self._format_context(top_results, query)

        # 7. Build synthesis prompt
        synthesis_prompt = self._build_synthesis_prompt(query, output_schema, system_prompt)

        # Combine context + synthesis prompt
        full_output = context + "\n\n" + synthesis_prompt

        return AnswerResult(
            query=query,
            context=full_output,
            synthesis_prompt=synthesis_prompt,
            sources=sources,
        )
