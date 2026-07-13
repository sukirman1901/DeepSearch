"""Tests for Knowledge IR + Context Optimizer (smart search)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from search.smart_search import (
    KnowledgeCompiler, ContextOptimizer, SmartSearchEngine,
    KnowledgeIR, DetailItem, SmartSearchResult,
)
from crawlers.base import CrawlResult


def _make_result(title, url, content, score=0.5, source="web"):
    return CrawlResult(
        source=source, title=title, content=content, url=url,
        crawled_at=datetime.now(), score=score,
    )


class TestKnowledgeCompiler:
    def test_compile_basic(self):
        compiler = KnowledgeCompiler()
        results = [_make_result("FastAPI", "https://fastapi.com", "Python web framework. Async.", score=0.9)]
        ir = compiler.compile(results)
        assert len(ir) == 1
        assert ir[0].title == "FastAPI"
        assert ir[0].score == 0.9
        assert "Python" in ir[0].summary

    def test_compile_multiple(self):
        compiler = KnowledgeCompiler()
        results = [
            _make_result("A", "https://a.com", "Content A.", score=0.8),
            _make_result("B", "https://b.com", "Content B.", score=0.6),
        ]
        ir = compiler.compile(results)
        assert len(ir) == 2
        assert ir[0].n == 1
        assert ir[1].n == 2

    def test_compile_empty_content(self):
        compiler = KnowledgeCompiler()
        results = [_make_result("Empty", "https://empty.com", "")]
        ir = compiler.compile(results)
        assert ir[0].summary == ""

    def test_ir_to_line(self):
        ir = KnowledgeIR(n=1, title="Test", source="web", url="https://test.com", score=0.9, summary="A test")
        line = ir.to_line()
        assert "[1]" in line
        assert "Test" in line
        assert "web" in line
        assert "score:0.9" in line

    def test_ir_to_dict(self):
        ir = KnowledgeIR(n=1, title="T", source="web", url="https://t.com", score=0.5, summary="s")
        d = ir.to_dict()
        assert d["n"] == 1
        assert d["title"] == "T"


class TestContextOptimizer:
    def test_optimize_returns_overview_and_details(self):
        optimizer = ContextOptimizer()
        results = [
            _make_result("A", "https://a.com", "Content A long text here.", score=0.9),
            _make_result("B", "https://b.com", "Content B long text here.", score=0.7),
            _make_result("C", "https://c.com", "Content C long text here.", score=0.5),
        ]
        ir = KnowledgeCompiler().compile(results)
        overview, details, t_ov, t_det = optimizer.optimize(ir, results, top_full=2)
        assert len(overview) == 3
        assert len(details) == 2
        assert details[0].title == "A"  # highest score first

    def test_optimize_limits_overview_tokens(self):
        optimizer = ContextOptimizer()
        results = [_make_result(f"Item {i}", f"https://{i}.com", "x" * 200, score=0.5) for i in range(20)]
        ir = KnowledgeCompiler().compile(results)
        overview, _, t_ov, _ = optimizer.optimize(ir, results, top_full=1, max_overview_tokens=200)
        assert t_ov <= 200

    def test_optimize_skips_empty_content(self):
        optimizer = ContextOptimizer()
        results = [
            _make_result("A", "https://a.com", "Has content.", score=0.9),
            _make_result("B", "https://b.com", "", score=0.7),
        ]
        ir = KnowledgeCompiler().compile(results)
        _, details, _, _ = optimizer.optimize(ir, results, top_full=2)
        assert len(details) == 2


class TestSmartSearchEngine:
    @pytest.fixture
    def engine(self):
        crawler = AsyncMock()
        vs = MagicMock()
        vs.search = MagicMock(return_value=[])
        return SmartSearchEngine(crawler, vs), crawler, vs

    @pytest.mark.asyncio
    async def test_search_returns_result(self, engine):
        eng, crawler, _ = engine
        crawler.crawl_all.return_value = [
            _make_result("A", "https://a.com", "Content A.", score=0.9),
            _make_result("B", "https://b.com", "Content B.", score=0.7),
        ]
        result = await eng.search("test", top_full=1)
        assert isinstance(result, SmartSearchResult)
        assert result.total_results == 2
        assert result.details_count == 1
        assert len(result.overview) == 2

    @pytest.mark.asyncio
    async def test_search_deduplicates(self, engine):
        eng, crawler, _ = engine
        crawler.crawl_all.return_value = [
            _make_result("A", "https://same.com", "Content.", score=0.9),
            _make_result("A", "https://same.com", "Content.", score=0.8),
        ]
        result = await eng.search("test")
        assert result.total_results == 1

    @pytest.mark.asyncio
    async def test_search_top_full_selection(self, engine):
        eng, crawler, _ = engine
        crawler.crawl_all.return_value = [
            _make_result("A", "https://a.com", "Content A.", score=0.9),
            _make_result("B", "https://b.com", "Content B.", score=0.7),
            _make_result("C", "https://c.com", "Content C.", score=0.5),
        ]
        result = await eng.search("test", top_full=2)
        assert result.details_count == 2
        assert result.details[0].title == "A"
        assert result.details[1].title == "B"

    @pytest.mark.asyncio
    async def test_search_token_savings(self, engine):
        eng, crawler, _ = engine
        crawler.crawl_all.return_value = [
            _make_result(f"Item {i}", f"https://{i}.com", "x" * 500, score=0.9 - i * 0.1)
            for i in range(5)
        ]
        result = await eng.search("test", top_full=2)
        assert result.tokens_saved_pct > 0
        assert result.tokens_overview > 0
        assert result.tokens_details > 0

    @pytest.mark.asyncio
    async def test_search_overview_format(self, engine):
        eng, crawler, _ = engine
        crawler.crawl_all.return_value = [
            _make_result("FastAPI", "https://fastapi.com", "Python web framework.", score=0.9),
        ]
        result = await eng.search("fastapi")
        assert result.overview[0].title == "FastAPI"
        assert "Python" in result.overview[0].summary
