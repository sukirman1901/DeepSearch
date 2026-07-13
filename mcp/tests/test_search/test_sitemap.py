"""Tests for SiteMapper."""
import pytest
from search.sitemap import SiteMapper, SiteMapResult, SiteMapOutput


def test_site_mapper_initializes():
    mapper = SiteMapper()
    assert mapper is not None
    assert mapper.client is not None


def test_site_map_result_dataclass():
    result = SiteMapResult(url="https://example.com", title="Test", depth=0, links_found=5)
    assert result.url == "https://example.com"
    assert result.title == "Test"
    assert result.depth == 0
    assert result.links_found == 5


def test_site_map_output_dataclass():
    output = SiteMapOutput(root_url="https://example.com", total_pages=10, max_depth_reached=2)
    assert output.root_url == "https://example.com"
    assert output.total_pages == 10
    assert output.max_depth_reached == 2
    assert output.pages == []


def test_parse_instructions_empty():
    mapper = SiteMapper()
    keywords = mapper._parse_instructions("")
    assert keywords == []


def test_parse_instructions_none():
    mapper = SiteMapper()
    keywords = mapper._parse_instructions("")
    assert keywords == []


def test_parse_instructions_single_word():
    mapper = SiteMapper()
    keywords = mapper._parse_instructions("blog")
    assert "blog" in keywords


def test_parse_instructions_multiple_words():
    mapper = SiteMapper()
    keywords = mapper._parse_instructions("only blog posts")
    assert "only" in keywords
    assert "blog" in keywords
    assert "posts" in keywords


def test_parse_instructions_filters_short_words():
    mapper = SiteMapper()
    keywords = mapper._parse_instructions("a an the blog")
    assert "a" not in keywords
    assert "an" not in keywords
    # "the" has 3 chars, so it passes the len > 2 filter
    assert "blog" in keywords


def test_parse_instructions_filters_two_char_words():
    mapper = SiteMapper()
    keywords = mapper._parse_instructions("it is a blog post")
    assert "it" not in keywords
    assert "is" not in keywords
    assert "a" not in keywords
    assert "blog" in keywords
    assert "post" in keywords


def test_matches_instructions_no_keywords():
    mapper = SiteMapper()
    # With no keywords, should always match (no filter)
    result = mapper._matches_instructions("https://blog.example.com/post", "My Blog Post", "content", [])
    assert result is True


def test_matches_instructions_url_match():
    mapper = SiteMapper()
    assert mapper._matches_instructions("https://blog.example.com/post", "Title", "content", ["blog"]) is True


def test_matches_instructions_title_match():
    mapper = SiteMapper()
    assert mapper._matches_instructions("https://example.com/page", "Blog Post Title", "content", ["blog"]) is True


def test_matches_instructions_content_match():
    mapper = SiteMapper()
    assert mapper._matches_instructions("https://example.com/page", "Title", "this is a blog post about tech", ["blog"]) is True


def test_matches_instructions_no_match():
    mapper = SiteMapper()
    assert mapper._matches_instructions("https://example.com/page", "Title", "content about cooking", ["blog"]) is False


def test_site_mapper_has_map_site_method():
    mapper = SiteMapper()
    assert hasattr(mapper, 'map_site')
