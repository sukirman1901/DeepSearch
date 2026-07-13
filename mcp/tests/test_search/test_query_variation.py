"""Tests for query variation generator"""
import pytest
from search.query_variation import QueryVariationGenerator


@pytest.fixture
def generator():
    return QueryVariationGenerator()


def test_generates_original_query(generator):
    variations = generator.generate_variations("test query")
    assert variations[0] == "test query"


def test_adds_category_prefix(generator):
    variations = generator.generate_variations("Anthropic", "company")
    assert any("company" in v.lower() for v in variations)


def test_generates_synonym_variations(generator):
    variations = generator.generate_variations("company profile")
    assert len(variations) >= 2


def test_expands_acronyms(generator):
    expanded = generator.expand_acronyms("AI company")
    assert len(expanded) >= 2
    assert any("artificial intelligence" in v.lower() for v in expanded)


def test_max_variations_respected(generator):
    variations = generator.generate_variations("test", max_variations=2)
    assert len(variations) <= 3  # original + 2 variations


def test_generate_domain_queries(generator):
    queries = generator.generate_domain_queries("test", ["example.com", "test.com"])
    assert len(queries) == 2
    assert all("site:" in q for q in queries)
