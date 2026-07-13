"""Tests for structured output"""
import pytest
import json
from search.structured_output import StructuredOutput, OutputSchema, format_search_results
from crawlers.base import CrawlResult
from datetime import datetime


@pytest.fixture
def formatter():
    return StructuredOutput()


@pytest.fixture
def sample_results():
    return [
        CrawlResult(
            source="web",
            title="Anthropic",
            content="AI safety company building reliable AI systems.",
            url="https://anthropic.com",
            metadata={"industry": "AI", "founded": "2021"},
            crawled_at=datetime.now(),
        )
    ]


def test_json_format(formatter, sample_results):
    output = formatter.format_results(sample_results, "company", "json")
    parsed = json.loads(output)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "Anthropic"


def test_markdown_format(formatter, sample_results):
    output = formatter.format_results(sample_results, "company", "markdown")
    assert "## Result 1" in output
    assert "Anthropic" in output


def test_csv_format(formatter, sample_results):
    output = formatter.format_results(sample_results, "company", "csv")
    lines = output.strip().split("\n")
    assert len(lines) == 2  # Header + 1 row


def test_format_search_results_function(sample_results):
    output = format_search_results(sample_results, "general", "json")
    parsed = json.loads(output)
    assert len(parsed) == 1


def test_custom_schema_registration(formatter):
    custom = OutputSchema(fields=["title", "url"])
    formatter.register_schema("custom", custom)
    assert "custom" in formatter.custom_schemas


def test_unknown_schema_fallback(formatter, sample_results):
    output = formatter.format_results(sample_results, "nonexistent", "json")
    parsed = json.loads(output)
    assert "title" in parsed[0]
