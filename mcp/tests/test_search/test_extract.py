"""Tests for ContentExtractor."""
import pytest
from search.extract import ContentExtractor, ExtractedContent, ExtractOutput


def test_content_extractor_initializes():
    extractor = ContentExtractor()
    assert extractor is not None
    assert extractor.client is not None


def test_extracted_content_dataclass():
    content = ExtractedContent(
        url="https://example.com",
        title="Test Page",
        text="Hello world",
        links=["https://example.com/link1"],
        metadata={"description": "A test page"},
    )
    assert content.url == "https://example.com"
    assert content.title == "Test Page"
    assert content.text == "Hello world"
    assert len(content.links) == 1
    assert content.metadata["description"] == "A test page"


def test_extract_output_dataclass():
    output = ExtractOutput(
        urls_processed=5,
        extract_depth="basic",
        instructions="find prices",
    )
    assert output.urls_processed == 5
    assert output.extract_depth == "basic"
    assert output.instructions == "find prices"
    assert output.contents == []


def test_parse_instructions_empty():
    extractor = ContentExtractor()
    keywords = extractor._parse_instructions("")
    assert keywords == []


def test_parse_instructions_single_word():
    extractor = ContentExtractor()
    keywords = extractor._parse_instructions("prices")
    assert "prices" in keywords


def test_parse_instructions_multiple_words():
    extractor = ContentExtractor()
    keywords = extractor._parse_instructions("product prices and reviews")
    assert "product" in keywords
    assert "prices" in keywords
    assert "and" in keywords
    assert "reviews" in keywords


def test_parse_instructions_filters_short_words():
    extractor = ContentExtractor()
    keywords = extractor._parse_instructions("a an the prices")
    assert "a" not in keywords
    assert "an" not in keywords
    # "the" has 3 chars, so it passes the len > 2 filter
    assert "prices" in keywords


def test_parse_instructions_filters_two_char_words():
    extractor = ContentExtractor()
    keywords = extractor._parse_instructions("it is a prices list")
    assert "it" not in keywords
    assert "is" not in keywords
    assert "a" not in keywords
    assert "prices" in keywords
    assert "list" in keywords


def test_filter_by_instructions_match():
    extractor = ContentExtractor()
    text = "This page has great product prices.\n\nThe reviews are also good.\n\nShipping is fast."
    result = extractor._filter_by_instructions(text, ["prices"])
    assert "product prices" in result
    assert "reviews" not in result


def test_filter_by_instructions_no_match():
    extractor = ContentExtractor()
    text = "This page is about cooking recipes.\n\nNothing about electronics here."
    result = extractor._filter_by_instructions(text, ["prices"])
    assert result == ""


def test_filter_by_instructions_multiple_keywords():
    extractor = ContentExtractor()
    text = "Product prices are good.\n\nReviews are excellent.\n\nShipping info available."
    result = extractor._filter_by_instructions(text, ["prices", "reviews"])
    assert "prices" in result.lower()
    assert "reviews" in result.lower()
    assert "shipping" not in result.lower()


def test_content_extractor_has_extract_method():
    extractor = ContentExtractor()
    assert hasattr(extractor, 'extract')
