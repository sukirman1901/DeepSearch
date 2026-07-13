"""Tests for lead generation"""
import pytest
from search.lead_gen import LeadScorer, LeadEnricher, Lead, IdealCustomerProfile, create_icp
from crawlers.base import CrawlResult
from datetime import datetime


@pytest.fixture
def scorer():
    return LeadScorer()


@pytest.fixture
def enricher():
    return LeadEnricher()


@pytest.fixture
def sample_result():
    return CrawlResult(
        source="web",
        title="CTO at TechCorp",
        content="John Smith is the CTO at TechCorp, a fintech startup in San Francisco. Email: john@techcorp.com. LinkedIn: https://linkedin.com/in/johnsmith",
        url="https://example.com",
        metadata={"title": "CTO", "company": "TechCorp"},
        crawled_at=datetime.now(),
    )


@pytest.fixture
def icp():
    return create_icp(
        industries=["fintech"],
        roles=["CTO"],
        technologies=["Python"],
        locations=["San Francisco"],
    )


def test_no_icp_scores_midpoint(scorer, sample_result):
    lead = scorer.score_lead(sample_result)
    assert lead.score == 50.0
    assert "No ICP defined" in lead.match_reasons


def test_icp_industry_match(scorer, sample_result, icp):
    scorer.set_icp(icp)
    lead = scorer.score_lead(sample_result)
    assert lead.score >= 25
    assert any("fintech" in r.lower() for r in lead.match_reasons)


def test_icp_role_match(scorer, sample_result, icp):
    scorer.set_icp(icp)
    lead = scorer.score_lead(sample_result)
    assert lead.score >= 20
    assert any("cto" in r.lower() for r in lead.match_reasons)


def test_icp_location_match(scorer, sample_result, icp):
    scorer.set_icp(icp)
    lead = scorer.score_lead(sample_result)
    assert lead.score >= 10
    assert any("san francisco" in r.lower() for r in lead.match_reasons)


def test_score_batch_sorted(scorer, icp):
    scorer.set_icp(icp)
    results = [
        CrawlResult(source="web", title="CEO at Corp", content="CEO in NY", url="https://a.com", crawled_at=datetime.now()),
        CrawlResult(source="web", title="CTO at Fintech", content="CTO in San Francisco fintech", url="https://b.com", crawled_at=datetime.now()),
    ]
    leads = scorer.score_batch(results)
    assert leads[0].score >= leads[1].score


def test_enricher_extracts_emails(enricher, sample_result):
    lead = Lead(result=sample_result, score=80.0)
    enriched = enricher.enrich(lead)
    assert "emails" in enriched.enrichment
    assert "john@techcorp.com" in enriched.enrichment["emails"]


def test_enricher_extracts_social_links(enricher, sample_result):
    lead = Lead(result=sample_result, score=80.0)
    enriched = enricher.enrich(lead)
    assert "linkedin_url" in enriched.enrichment
