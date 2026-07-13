"""Tests for subpage discovery."""
import pytest
from unittest.mock import patch, MagicMock
from httpx import Response
from search.subpage import SubpageDiscoverer


@pytest.fixture
def discoverer():
    d = SubpageDiscoverer()
    d.client = MagicMock()
    return d


def _mock_response(text, status=200):
    resp = MagicMock(spec=Response)
    resp.status_code = status
    resp.text = text
    if status >= 400:
        resp.raise_for_status = MagicMock(side_effect=Exception(f"{status}"))
    else:
        resp.raise_for_status = MagicMock()
    return resp


SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
  <url><loc>https://example.com/page3</loc></url>
</urlset>"""


def test_discover_via_sitemap(discoverer):
    """Sitemap.xml returns URLs — verify they are parsed correctly."""
    discoverer.client.get.return_value = _mock_response(SITEMAP_XML)

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert "https://example.com/page1" in urls
    assert "https://example.com/page2" in urls
    assert "https://example.com/page3" in urls


HTML_WITH_LINKS = """<html><body>
<a href="/page4">Page 4</a>
<a href="/page5">Page 5</a>
<a href="https://other.com/external">External</a>
<a href="/page6">Page 6</a>
</body></html>"""


def test_discover_falls_back_to_html(discoverer):
    """When sitemap returns 404, use HTML links from main page."""
    discoverer.client.get.side_effect = [
        _mock_response("", status=404),
        _mock_response(HTML_WITH_LINKS),
    ]

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert "https://example.com/page4" in urls
    assert "https://example.com/page5" in urls
    assert "https://example.com/page6" in urls
    assert "https://other.com/external" not in urls


SITEMAP_MIXED = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/docs/intro</loc></url>
  <url><loc>https://example.com/docs/guide</loc></url>
  <url><loc>https://example.com/blog/post1</loc></url>
  <url><loc>https://example.com/blog/post2</loc></url>
  <url><loc>https://example.com/about</loc></url>
</urlset>"""


def test_discover_filters_by_keyword(discoverer):
    """target_keyword filters URLs by path content."""
    discoverer.client.get.return_value = _mock_response(SITEMAP_MIXED)

    urls = discoverer.discover_subpages(
        "https://example.com",
        max_count=10,
        target_keyword="docs",
    )

    assert all("docs" in u for u in urls)
    assert "https://example.com/docs/intro" in urls
    assert "https://example.com/docs/guide" in urls
    assert "https://example.com/blog/post1" not in urls


SITEMAP_DUPS = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>"""


def test_discover_deduplicates(discoverer):
    """Duplicate URLs in sitemap are deduplicated."""
    discoverer.client.get.return_value = _mock_response(SITEMAP_DUPS)

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert urls.count("https://example.com/page1") == 1
    assert len(urls) == 2


SITEMAP_MANY = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/p1</loc></url>
  <url><loc>https://example.com/p2</loc></url>
  <url><loc>https://example.com/p3</loc></url>
  <url><loc>https://example.com/p4</loc></url>
  <url><loc>https://example.com/p5</loc></url>
</urlset>"""


def test_discover_respects_max_count(discoverer):
    """max_count limits the number of returned URLs."""
    discoverer.client.get.return_value = _mock_response(SITEMAP_MANY)

    urls = discoverer.discover_subpages("https://example.com", max_count=3)

    assert len(urls) == 3


SITEMAP_WITH_MAIN = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com</loc></url>
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>"""


def test_discover_excludes_main_url(discoverer):
    """Main URL itself is not included in subpage list."""
    discoverer.client.get.return_value = _mock_response(SITEMAP_WITH_MAIN)

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert "https://example.com" not in urls
    assert "https://example.com/" not in urls
    assert len(urls) == 2


def test_discover_empty_results(discoverer):
    """Both sitemap and HTML return nothing -> empty list."""
    discoverer.client.get.side_effect = [
        _mock_response("", status=404),
        _mock_response("<html><body></body></html>"),
    ]

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert urls == []


SITEMAP_PARTIAL = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/s1</loc></url>
  <url><loc>https://example.com/s2</loc></url>
  <url><loc>https://example.com/s3</loc></url>
</urlset>"""

HTML_EXTRA_LINKS = """<html><body>
<a href="/h1">H1</a>
<a href="/h2">H2</a>
<a href="/s1">S1 dup</a>
</body></html>"""


def test_discover_merges_sitemap_and_html(discoverer):
    """Sitemap has 3 URLs, HTML has 2 new + 1 dup -> merged has 5."""
    discoverer.client.get.side_effect = [
        _mock_response(SITEMAP_PARTIAL),
        _mock_response(HTML_EXTRA_LINKS),
    ]

    urls = discoverer.discover_subpages("https://example.com", max_count=10)

    assert "https://example.com/s1" in urls
    assert "https://example.com/s2" in urls
    assert "https://example.com/s3" in urls
    assert "https://example.com/h1" in urls
    assert "https://example.com/h2" in urls
    assert urls.count("https://example.com/s1") == 1
