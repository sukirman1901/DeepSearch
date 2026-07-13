"""
Lead generation features with ICP scoring.
Inspired by Exa's lead generation capabilities.
"""
from dataclasses import dataclass, field
from typing import Optional
from crawlers.base import CrawlResult
import json
import re


def _word_match(text: str, keyword: str) -> bool:
    """Check if keyword appears as a whole word in text."""
    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
    return bool(re.search(pattern, text))


@dataclass
class IdealCustomerProfile:
    """Ideal Customer Profile for lead scoring"""
    industries: list[str] = field(default_factory=list)
    company_sizes: list[str] = field(default_factory=list)  # e.g., ["1-10", "11-50", "51-200"]
    roles: list[str] = field(default_factory=list)  # e.g., ["CEO", "CTO", "Developer"]
    technologies: list[str] = field(default_factory=list)  # e.g., ["Python", "React", "AWS"]
    locations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)  # Additional keywords
    min_funding: int = 0  # Minimum funding in USD
    max_funding: int = 0  # Maximum funding (0 = no limit)
    founded_after: Optional[str] = None  # ISO date


@dataclass
class Lead:
    """A scored lead"""
    result: CrawlResult
    score: float = 0.0  # 0-100
    match_reasons: list[str] = field(default_factory=list)
    enrichment: dict = field(default_factory=dict)


class LeadScorer:
    """Score leads against ICP"""

    def __init__(self):
        self.icp: Optional[IdealCustomerProfile] = None

    def set_icp(self, icp: IdealCustomerProfile):
        self.icp = icp

    def score_lead(self, result: CrawlResult) -> Lead:
        if not self.icp:
            return Lead(result=result, score=50.0, match_reasons=["No ICP defined"])

        score = 0.0
        reasons = []

        combined_text = f"{result.title} {result.content}".lower()
        metadata = {k: str(v).lower() for k, v in result.metadata.items()}

        # Industry match (25 points) - word boundary matching
        if self.icp.industries:
            for industry in self.icp.industries:
                if _word_match(combined_text, industry):
                    score += 25
                    reasons.append(f"Industry match: {industry}")
                    break

        # Role match (20 points) - word boundary matching
        if self.icp.roles:
            for role in self.icp.roles:
                if _word_match(combined_text, role) or _word_match(metadata.get("title", ""), role):
                    score += 20
                    reasons.append(f"Role match: {role}")
                    break

        # Technology match (20 points) - word boundary matching
        if self.icp.technologies:
            tech_matches = [t for t in self.icp.technologies if _word_match(combined_text, t)]
            if tech_matches:
                score += 20
                reasons.append(f"Technology match: {', '.join(tech_matches)}")

        # Location match (10 points) - word boundary matching
        if self.icp.locations:
            for location in self.icp.locations:
                if _word_match(combined_text, location):
                    score += 10
                    reasons.append(f"Location match: {location}")
                    break

        # Keyword match (15 points) - word boundary matching
        if self.icp.keywords:
            keyword_matches = [k for k in self.icp.keywords if _word_match(combined_text, k)]
            if keyword_matches:
                score += min(15, len(keyword_matches) * 5)
                reasons.append(f"Keyword matches: {', '.join(keyword_matches[:3])}")

        # Company size match (10 points) - word boundary matching
        if self.icp.company_sizes:
            for size in self.icp.company_sizes:
                if size.lower() in combined_text:
                    score += 10
                    reasons.append(f"Company size match: {size}")
                    break

        return Lead(
            result=result,
            score=min(100, score),
            match_reasons=reasons if reasons else ["No ICP matches found"]
        )

    def score_batch(self, results: list[CrawlResult]) -> list[Lead]:
        leads = [self.score_lead(r) for r in results]
        return sorted(leads, key=lambda x: x.score, reverse=True)


class LeadEnricher:
    """Enrich lead data with additional context"""

    def enrich(self, lead: Lead) -> Lead:
        enriched = lead.result.metadata.copy()

        # Extract email patterns
        emails = re.findall(r'[\w.-]+@[\w.-]+\.\w+', lead.result.content)
        if emails:
            enriched["emails"] = list(set(emails))

        # Extract phone patterns
        phones = re.findall(r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}', lead.result.content)
        if phones:
            enriched["phones"] = list(set(phones))

        # Extract social links
        social_patterns = {
            "linkedin": r'linkedin\.com/in/[\w-]+',
            "twitter": r'twitter\.com/[\w]+|x\.com/[\w]+',
            "github": r'github\.com/[\w-]+',
        }
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, lead.result.content)
            if matches:
                enriched[f"{platform}_url"] = list(set(matches))

        # Extract company info
        company_indicators = ["Inc.", "Ltd.", "LLC", "Corp.", "GmbH", "Co."]
        for indicator in company_indicators:
            if indicator in lead.result.title:
                enriched["company_name"] = lead.result.title
                break

        lead.enrichment = enriched
        return lead


def create_icp(
    industries: list[str] = None,
    roles: list[str] = None,
    technologies: list[str] = None,
    locations: list[str] = None,
    keywords: list[str] = None,
    company_sizes: list[str] = None,
) -> IdealCustomerProfile:
    """Create an ICP from parameters"""
    return IdealCustomerProfile(
        industries=industries or [],
        roles=roles or [],
        technologies=technologies or [],
        locations=locations or [],
        keywords=keywords or [],
        company_sizes=company_sizes or [],
    )
