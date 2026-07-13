"""Tests for Context API — token-budget-aware snippet packing."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from search.context import ContextEngine, ContextSnippet, ContextResult
from crawlers.base import CrawlResult


@pytest.fixture
def mock_crawler():
    return AsyncMock()


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.search = MagicMock(return_value=[])
    return store


@pytest.fixture
def engine(mock_crawler, mock_vector_store):
    return ContextEngine(mock_crawler, mock_vector_store)


def _make_result(title, content, url, score=0.5, language=""):
    metadata = {"language": language} if language else {}
    return CrawlResult(
        source="test", title=title, content=content, url=url,
        metadata=metadata, crawled_at=datetime.now(), score=score,
    )


class TestEstimateTokens:
    def test_basic(self, engine):
        assert engine.estimate_tokens("a" * 100) == 25

    def test_empty(self, engine):
        assert engine.estimate_tokens("") == 0

    def test_whitespace(self, engine):
        assert engine.estimate_tokens(" " * 40) == 10


class TestPackSnippets:
    def test_all_fit(self, engine):
        results = [
            _make_result("A", "x" * 200, "https://a.com", score=0.9),
            _make_result("B", "y" * 200, "https://b.com", score=0.8),
            _make_result("C", "z" * 200, "https://c.com", score=0.7),
        ]
        packed, used = engine.pack_snippets(results, budget_tokens=500)
        assert len(packed) == 3
        assert used > 0
        assert used <= 500

    def test_respects_budget(self, engine):
        results = [
            _make_result("Big", "x" * 2000, "https://big.com", score=0.9),
            _make_result("Small", "y" * 100, "https://small.com", score=0.8),
        ]
        packed, used = engine.pack_snippets(results, budget_tokens=100)
        assert len(packed) == 1
        assert packed[0].title == "Small"
        assert used <= 100

    def test_skips_empty_content(self, engine):
        results = [
            _make_result("Empty", "", "https://empty.com"),
            _make_result("Real", "content here", "https://real.com"),
        ]
        packed, used = engine.pack_snippets(results, budget_tokens=500)
        assert len(packed) == 1
        assert packed[0].title == "Real"


class TestFormatContext:
    def test_markdown_output(self, engine):
        snippets = [
            ContextSnippet(title="Test", content="code here", url="https://example.com",
                          source="github", language="python", tokens=50),
        ]
        output = engine.format_context(snippets, "test query")
        assert "Test" in output
        assert "github" in output
        assert "code here" in output
        assert "50 tokens" in output

    def test_empty_returns_message(self, engine):
        output = engine.format_context([], "query")
        assert "No context found" in output


class TestSearch:
    @pytest.mark.asyncio
    async def test_returns_result(self, engine, mock_crawler, mock_vector_store):
        mock_crawler.crawl_all.return_value = [
            _make_result("Result", "content", "https://example.com"),
        ]
        result = await engine.search("test", budget_tokens=1000)
        assert isinstance(result, ContextResult)
        assert result.tokens_used <= result.tokens_budget

    @pytest.mark.asyncio
    async def test_deduplicates(self, engine, mock_crawler):
        mock_crawler.crawl_all.return_value = [
            _make_result("A", "content", "https://same.com"),
            _make_result("B", "content", "https://same.com"),
        ]
        result = await engine.search("test", budget_tokens=1000)
        assert result.total_snippets_found == 1

    @pytest.mark.asyncio
    async def test_token_usage_stats(self, engine, mock_crawler):
        mock_crawler.crawl_all.return_value = [
            _make_result("A", "x" * 400, "https://a.com"),
        ]
        result = await engine.search("test", budget_tokens=200)
        assert result.tokens_used == 100  # 400 // 4
        assert result.tokens_budget == 200
        assert len(result.snippets) == 1
