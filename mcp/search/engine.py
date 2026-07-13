import asyncio
from crawlers.manager import CrawlerManager
from db.vector_store import VectorStore
from crawlers.base import CrawlResult
from search.filters import SearchFilters, FilterEngine, create_filters
from search.structured_output import StructuredOutput, OutputSchema
from search.categories import detect_category, Category
from search.lead_gen import LeadScorer, LeadEnricher, Lead, IdealCustomerProfile, create_icp


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

    def search(
        self,
        query: str,
        limit: int = 10,
        source: str = "",
        filters: SearchFilters = None,
        category: str = "",
    ) -> list[CrawlResult]:
        results = self.vector_store.search(query, limit * 2)  # Get more for filtering

        # Apply category filter
        if category:
            results = [r for r in results if r.category == category]

        # Apply source filter
        if source:
            results = [r for r in results if r.source == source]

        # Apply advanced filters
        if filters:
            self.filter_engine.set_filters(filters)
            results = self.filter_engine.apply_filters(results)

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
        return self.search(query, limit, filters=filters)

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
