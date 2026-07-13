"""
Advanced filtering system for search results.
Inspired by Exa's domain, date, and text filtering capabilities.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable
import re
from crawlers.base import CrawlResult


@dataclass
class SearchFilters:
    """Advanced search filters"""
    # Domain filtering
    include_domains: list[str] = field(default_factory=list)
    exclude_domains: list[str] = field(default_factory=list)
    
    # Date filtering
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Text filtering
    include_text: list[str] = field(default_factory=list)  # Must contain ALL
    exclude_text: list[str] = field(default_factory=list)  # Exclude if ANY match
    
    # Source filtering
    include_sources: list[str] = field(default_factory=list)
    exclude_sources: list[str] = field(default_factory=list)
    
    # Content filtering
    min_content_length: int = 0
    max_content_length: int = 0  # 0 = no limit
    
    # Result scoring
    boost_recent: bool = False  # Boost recent results
    boost_popular: bool = False  # Boost popular results (by metadata)


class FilterEngine:
    """Apply filters to search results"""
    
    def __init__(self):
        self.filters: Optional[SearchFilters] = None
    
    def set_filters(self, filters: SearchFilters):
        """Set active filters"""
        self.filters = filters
    
    def apply_filters(self, results: list[CrawlResult]) -> list[CrawlResult]:
        """Apply all active filters to results"""
        if not self.filters:
            return results
        
        filtered = results
        
        # Domain filtering
        if self.filters.include_domains:
            filtered = [r for r in filtered if self._matches_domain(r.url, self.filters.include_domains)]
        
        if self.filters.exclude_domains:
            filtered = [r for r in filtered if not self._matches_domain(r.url, self.filters.exclude_domains)]
        
        # Date filtering
        if self.filters.start_date:
            filtered = [r for r in filtered if r.crawled_at >= self.filters.start_date]
        
        if self.filters.end_date:
            filtered = [r for r in filtered if r.crawled_at <= self.filters.end_date]
        
        # Text filtering
        if self.filters.include_text:
            filtered = [r for r in filtered if self._contains_all_text(r, self.filters.include_text)]
        
        if self.filters.exclude_text:
            filtered = [r for r in filtered if not self._contains_any_text(r, self.filters.exclude_text)]
        
        # Source filtering
        if self.filters.include_sources:
            filtered = [r for r in filtered if r.source in self.filters.include_sources]
        
        if self.filters.exclude_sources:
            filtered = [r for r in filtered if r.source not in self.filters.exclude_sources]
        
        # Content length filtering
        if self.filters.min_content_length > 0:
            filtered = [r for r in filtered if len(r.content) >= self.filters.min_content_length]
        
        if self.filters.max_content_length > 0:
            filtered = [r for r in filtered if len(r.content) <= self.filters.max_content_length]
        
        # Boosting
        if self.filters.boost_recent:
            filtered = self._boost_by_recency(filtered)
        
        if self.filters.boost_popular:
            filtered = self._boost_by_popularity(filtered)
        
        return filtered
    
    def _matches_domain(self, url: str, domains: list[str]) -> bool:
        """Check if URL matches any domain in list"""
        url_lower = url.lower()
        return any(domain.lower() in url_lower for domain in domains)
    
    def _contains_all_text(self, result: CrawlResult, text_list: list[str]) -> bool:
        """Check if result contains all text in list"""
        combined = f"{result.title} {result.content}".lower()
        return all(text.lower() in combined for text in text_list)
    
    def _contains_any_text(self, result: CrawlResult, text_list: list[str]) -> bool:
        """Check if result contains any text in list"""
        combined = f"{result.title} {result.content}".lower()
        return any(text.lower() in combined for text in text_list)
    
    def _boost_by_recency(self, results: list[CrawlResult]) -> list[CrawlResult]:
        """Boost more recent results"""
        now = datetime.now()
        
        def recency_score(result: CrawlResult) -> float:
            age_hours = (now - result.crawled_at).total_seconds() / 3600
            return 1.0 / (1.0 + age_hours / 24)  # Decay over days
        
        return sorted(results, key=recency_score, reverse=True)
    
    def _boost_by_popularity(self, results: list[CrawlResult]) -> list[CrawlResult]:
        """Boost results with popularity metrics"""
        def popularity_score(result: CrawlResult) -> float:
            score = 0
            if "score" in result.metadata:
                score += result.metadata["score"]
            if "upvotes" in result.metadata:
                score += result.metadata["upvotes"]
            if "likes" in result.metadata:
                score += result.metadata["likes"]
            if "stars" in result.metadata:
                score += result.metadata["stars"]
            return score
        
        return sorted(results, key=popularity_score, reverse=True)


def create_filters(
    include_domains: list[str] = None,
    exclude_domains: list[str] = None,
    start_date: str = None,
    end_date: str = None,
    include_text: list[str] = None,
    exclude_text: list[str] = None,
    include_sources: list[str] = None,
    exclude_sources: list[str] = None,
    min_content_length: int = 0,
    max_content_length: int = 0,
    boost_recent: bool = False,
    boost_popular: bool = False
) -> SearchFilters:
    """Create search filters from parameters"""
    filters = SearchFilters(
        include_domains=include_domains or [],
        exclude_domains=exclude_domains or [],
        include_text=include_text or [],
        exclude_text=exclude_text or [],
        include_sources=include_sources or [],
        exclude_sources=exclude_sources or [],
        min_content_length=min_content_length,
        max_content_length=max_content_length,
        boost_recent=boost_recent,
        boost_popular=boost_popular
    )
    
    # Parse dates
    if start_date:
        try:
            filters.start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    if end_date:
        try:
            filters.end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    return filters