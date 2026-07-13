"""Tests for category system"""
import pytest
from search.categories import detect_category, get_sources_for_category, get_category_info, Category, CATEGORY_CONFIGS


def test_detect_category_company():
    assert detect_category("Find company profile for Anthropic").value == "company"


def test_detect_category_people():
    assert detect_category("Find LinkedIn profile of CTO").value == "people"


def test_detect_category_research():
    assert detect_category("Latest research paper on LLMs").value == "research_paper"


def test_detect_category_financial():
    assert detect_category("SEC filing 10-K for Apple").value == "financial_report"


def test_detect_category_news():
    assert detect_category("Breaking news about AI").value == "news"


def test_detect_category_code():
    assert detect_category("Python code example for API").value == "code"


def test_detect_category_general_fallback():
    assert detect_category("random query xyz").value == "general"


def test_get_sources_for_category():
    sources = get_sources_for_category(Category.COMPANY)
    assert "web" in sources
    assert "twitter" in sources


def test_get_category_info():
    info = get_category_info()
    assert "company" in info
    assert "people" in info
    assert "research_paper" in info
    assert len(info) == 8


def test_all_categories_have_configs():
    for cat in Category:
        assert cat in CATEGORY_CONFIGS
