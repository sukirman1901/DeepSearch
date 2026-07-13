"""
Category system for organizing search results by type.
Inspired by Exa's category-based search approach.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class Category(str, Enum):
    """Search result categories"""
    COMPANY = "company"
    PEOPLE = "people"
    RESEARCH_PAPER = "research_paper"
    FINANCIAL_REPORT = "financial_report"
    PERSONAL_SITE = "personal_site"
    NEWS = "news"
    CODE = "code"
    GENERAL = "general"


@dataclass
class CategoryConfig:
    """Configuration for each category"""
    name: str
    description: str
    sources: list[str]  # Preferred sources for this category
    keywords: list[str]  # Keywords to detect category
    exclude_sources: list[str] = None  # Sources to exclude

    def __post_init__(self):
        if self.exclude_sources is None:
            self.exclude_sources = []


# Category configurations
CATEGORY_CONFIGS: dict[Category, CategoryConfig] = {
    Category.COMPANY: CategoryConfig(
        name="Company Research",
        description="Company profiles, competitors, funding, news",
        sources=["web", "twitter", "reddit"],
        keywords=["company", "startup", "funding", "acquisition", "IPO", "revenue", "competitor"],
        exclude_sources=["youtube", "github"]
    ),
    Category.PEOPLE: CategoryConfig(
        name="People Search",
        description="Professional profiles, expertise, background",
        sources=["web", "twitter", "github"],
        keywords=["profile", "linkedin", "expert", "founder", "CEO", "developer", "researcher"],
        exclude_sources=["youtube"]
    ),
    Category.RESEARCH_PAPER: CategoryConfig(
        name="Research Papers",
        description="Academic papers, arXiv, scientific research",
        sources=["web", "duckduckgo"],
        keywords=["paper", "arxiv", "research", "study", "abstract", "journal", "conference"],
        exclude_sources=["youtube", "twitter"]
    ),
    Category.FINANCIAL_REPORT: CategoryConfig(
        name="Financial Reports",
        description="SEC filings, earnings, financial documents",
        sources=["web", "duckduckgo"],
        keywords=["SEC", "10-K", "10-Q", "earnings", "financial", "filing", "annual report"],
        exclude_sources=["youtube", "twitter", "github"]
    ),
    Category.PERSONAL_SITE: CategoryConfig(
        name="Personal Sites",
        description="Personal blogs, portfolios, independent content",
        sources=["web", "duckduckgo"],
        keywords=["blog", "portfolio", "personal", "homepage", "about me"],
        exclude_sources=["youtube"]
    ),
    Category.NEWS: CategoryConfig(
        name="News",
        description="Recent news articles and press releases",
        sources=["web", "twitter", "duckduckgo"],
        keywords=["news", "breaking", "latest", "today", "recent", "update"],
        exclude_sources=["github"]
    ),
    Category.CODE: CategoryConfig(
        name="Code",
        description="Code examples, API docs, technical snippets",
        sources=["github", "web"],
        keywords=["code", "implementation", "example", "API", "documentation", "tutorial"],
        exclude_sources=["youtube"]
    ),
    Category.GENERAL: CategoryConfig(
        name="General",
        description="General search across all sources",
        sources=["web", "duckduckgo", "reddit", "wikipedia"],
        keywords=[],
        exclude_sources=[]
    )
}


def detect_category(query: str) -> Category:
    """Auto-detect category from query keywords"""
    query_lower = query.lower()
    
    for category, config in CATEGORY_CONFIGS.items():
        if category == Category.GENERAL:
            continue
        for keyword in config.keywords:
            if keyword.lower() in query_lower:
                return category
    
    return Category.GENERAL


def get_sources_for_category(category: Category) -> list[str]:
    """Get preferred sources for a category"""
    config = CATEGORY_CONFIGS[category]
    return [s for s in config.sources if s not in config.exclude_sources]


def get_category_info() -> dict[str, str]:
    """Get information about all categories"""
    return {
        cat.value: f"{config.name}: {config.description}"
        for cat, config in CATEGORY_CONFIGS.items()
    }