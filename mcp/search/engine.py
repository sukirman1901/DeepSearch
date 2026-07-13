import asyncio
from datetime import datetime, timedelta
from crawlers.manager import CrawlerManager
from db.vector_store import VectorStore
from crawlers.base import CrawlResult
from search.filters import SearchFilters, FilterEngine, create_filters
from search.structured_output import StructuredOutput, OutputSchema
from search.categories import detect_category, Category
from search.lead_gen import LeadScorer, LeadEnricher, Lead, IdealCustomerProfile, create_icp


# Search depth presets: controls results per source and reranking
SEARCH_DEPTH_PRESETS = {
    "fast": {"max_per_source": 3, "rerank": False},
    "basic": {"max_per_source": 5, "rerank": False},
    "advanced": {"max_per_source": 20, "rerank": True},
}

# News domains for topic filtering
NEWS_DOMAINS = [
    "reuters.com", "apnews.com", "bbc.com", "cnn.com", "nytimes.com",
    "theguardian.com", "washingtonpost.com", "bloomberg.com", "wsj.com",
    "ft.com", "cnbc.com", "nbcnews.com", "cbsnews.com", "abcnews.go.com",
    "aljazeera.com", "vice.com", "theverge.com", "arstechnica.com",
    "techcrunch.com", "engadget.com", "wired.com", "mashable.com",
]


class SearchEngine:
    def __init__(self):
        self.crawler_manager = CrawlerManager()
        self.vector_store = VectorStore()
        self.filter_engine = FilterEngine()
        self.structured_output = StructuredOutput()
        self.lead_scorer = LeadScorer()
        self.lead_enricher = LeadEnricher()

    async def index_topic(
        self,
        topic: str,
        max_results_per_source: int = 10,
        category: str = "auto",
        sources: list[str] = None,
    ) -> int:
        results = await self.crawler_manager.crawl_all(
            topic, max_results_per_source, category, sources
        )

        for result in results:
            self.vector_store.add(result)

        return len(results)

    async def index_topic_with_details(
        self,
        topic: str,
        max_results_per_source: int = 10,
        category: str = "auto",
        sources: list[str] = None,
    ) -> dict:
        """Index a topic and return detailed breakdown by source."""
        results = await self.crawler_manager.crawl_all(
            topic, max_results_per_source, category, sources
        )

        by_source = {}
        for result in results:
            by_source[result.source] = by_source.get(result.source, 0) + 1
            self.vector_store.add(result)

        return {
            "total": len(results),
            "by_source": by_source,
        }

    def search(
        self,
        query: str,
        limit: int = 10,
        source: str = "",
        filters: SearchFilters = None,
        category: str = "",
        search_depth: str = "basic",
        topic: str = "general",
        max_age_hours: int = -1,
    ) -> list[CrawlResult]:
        # Get more results based on search depth
        depth_preset = SEARCH_DEPTH_PRESETS.get(search_depth, SEARCH_DEPTH_PRESETS["basic"])
        fetch_limit = limit * 3 if search_depth == "advanced" else limit * 2

        results = self.vector_store.search(query, fetch_limit)

        # Apply category filter
        if category:
            results = [r for r in results if r.category == category]

        # Apply source filter
        if source:
            results = [r for r in results if r.source == source]

        # Apply topic filter
        if topic == "news":
            results = self._filter_by_topic_news(results)

        # Apply max_age filter
        if max_age_hours > 0:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            results = [r for r in results if r.crawled_at >= cutoff]

        # Apply advanced filters
        if filters:
            self.filter_engine.set_filters(filters)
            results = self.filter_engine.apply_filters(results)

        # Apply reranking for advanced depth
        if depth_preset["rerank"] and len(results) > limit:
            results = self._rerank_by_relevance(query, results)

        return results[:limit]

    def search_with_filters(
        self,
        query: str,
        limit: int = 10,
        include_domains: list[str] = None,
        exclude_domains: list[str] = None,
        start_date: str = None,
        end_date: str = None,
        include_text: list[str] = None,
        exclude_text: list[str] = None,
        include_sources: list[str] = None,
        exclude_sources: list[str] = None,
        boost_recent: bool = False,
        boost_popular: bool = False,
        search_depth: str = "basic",
        topic: str = "general",
        max_age_hours: int = -1,
    ) -> list[CrawlResult]:
        filters = create_filters(
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            start_date=start_date,
            end_date=end_date,
            include_text=include_text,
            exclude_text=exclude_text,
            include_sources=include_sources,
            exclude_sources=exclude_sources,
            boost_recent=boost_recent,
            boost_popular=boost_popular,
        )
        return self.search(
            query, limit, filters=filters,
            search_depth=search_depth, topic=topic, max_age_hours=max_age_hours,
        )

    def search_and_format(
        self,
        query: str,
        limit: int = 10,
        format_type: str = "json",
        category: str = "",
    ) -> str:
        results = self.search(query, limit, category=category)
        schema_name = category if category else "general"
        return self.structured_output.format_results(results, schema_name, format_type)

    def search_leads(
        self,
        query: str,
        limit: int = 20,
        icp: IdealCustomerProfile = None,
        enrich: bool = True,
    ) -> list[Lead]:
        results = self.search(query, limit)

        if icp:
            self.lead_scorer.set_icp(icp)

        leads = self.lead_scorer.score_batch(results)

        if enrich:
            leads = [self.lead_enricher.enrich(lead) for lead in leads]

        return leads[:limit]

    def stats(self) -> dict:
        return self.vector_store.stats()

    def detect_query_category(self, query: str) -> str:
        category = detect_category(query)
        return category.value

    def _filter_by_topic_news(self, results: list[CrawlResult]) -> list[CrawlResult]:
        """Boost news domains and demote old content for topic=news."""
        now = datetime.now()
        scored = []
        for r in results:
            score = 0.0
            # Boost news domains
            if any(nd in r.url.lower() for nd in NEWS_DOMAINS):
                score += 2.0
            # Boost recent content (within 7 days)
            age_hours = (now - r.crawled_at).total_seconds() / 3600
            if age_hours < 168:  # 7 days
                score += 1.0
            if age_hours < 24:  # 1 day
                score += 1.0
            # Demote old content
            if age_hours > 720:  # 30 days
                score -= 1.0
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]

    def _rerank_by_relevance(self, query: str, results: list[CrawlResult]) -> list[CrawlResult]:
        """Rerank results using ChromaDB similarity scores."""
        query_embedding = self.vector_store.embedding_model.embed(query)
        scored = []
        for r in results:
            doc_embedding = self.vector_store.embedding_model.embed(r.content[:500])
            similarity = sum(a * b for a, b in zip(query_embedding, doc_embedding))
            scored.append((similarity, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]
