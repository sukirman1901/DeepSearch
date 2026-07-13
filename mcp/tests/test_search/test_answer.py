"""Tests for AnswerEngine."""
import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from search.answer import AnswerEngine, AnswerResult
from crawlers.base import CrawlResult


@pytest.fixture
def mock_crawler_manager():
    return AsyncMock()


@pytest.fixture
def mock_vector_store():
    return Mock()


@pytest.fixture
def engine(mock_crawler_manager, mock_vector_store):
    return AnswerEngine(mock_crawler_manager, mock_vector_store)


@pytest.fixture
def sample_results():
    return [
        CrawlResult(
            source="web",
            title="Python Guide",
            content="Python is a programming language.",
            url="https://example.com/1",
            score=0.9,
            crawled_at=datetime.now(),
        ),
        CrawlResult(
            source="reddit",
            title="Reddit Discussion",
            content="Python discussion thread.",
            url="https://reddit.com/r/Python",
            score=0.7,
            crawled_at=datetime.now(),
        ),
    ]


@pytest.mark.asyncio
async def test_answer_searches_all_sources(engine, mock_crawler_manager, mock_vector_store, sample_results):
    """Verify crawler_manager.crawl_all and vector_store.search are both called."""
    mock_crawler_manager.crawl_all.return_value = sample_results
    mock_vector_store.search.return_value = []

    await engine.answer("python")

    mock_crawler_manager.crawl_all.assert_awaited_once()
    mock_vector_store.search.assert_called_once()


@pytest.mark.asyncio
async def test_answer_deduplicates_by_url(engine, mock_crawler_manager, mock_vector_store):
    """Two results with same URL → only one in output."""
    dup_a = CrawlResult(
        source="web",
        title="First",
        content="content a",
        url="https://example.com/dup",
        score=0.9,
        crawled_at=datetime.now(),
    )
    dup_b = CrawlResult(
        source="web",
        title="Second",
        content="content b",
        url="https://example.com/dup",
        score=0.5,
        crawled_at=datetime.now(),
    )
    mock_crawler_manager.crawl_all.return_value = [dup_a]
    mock_vector_store.search.return_value = [dup_b]

    result = await engine.answer("query")

    urls = [s["url"] for s in result.sources]
    assert urls.count("https://example.com/dup") == 1


@pytest.mark.asyncio
async def test_answer_formats_citations(engine, mock_crawler_manager, mock_vector_store, sample_results):
    """Output contains [1], [2] numbered citations."""
    mock_crawler_manager.crawl_all.return_value = sample_results
    mock_vector_store.search.return_value = []

    result = await engine.answer("python")

    assert "[1]" in result.context
    assert "[2]" in result.context


@pytest.mark.asyncio
async def test_answer_with_output_schema(engine, mock_crawler_manager, mock_vector_store, sample_results):
    """synthesis_prompt contains '## Output Format' and the schema JSON."""
    mock_crawler_manager.crawl_all.return_value = sample_results
    mock_vector_store.search.return_value = []

    schema = {"answer": "string", "confidence": "number"}
    result = await engine.answer("python", output_schema=schema)

    assert "## Output Format" in result.synthesis_prompt
    assert '"answer"' in result.synthesis_prompt
    assert '"confidence"' in result.synthesis_prompt


@pytest.mark.asyncio
async def test_answer_empty_results(engine, mock_crawler_manager, mock_vector_store):
    """No results → empty sources list, context still has header."""
    mock_crawler_manager.crawl_all.return_value = []
    mock_vector_store.search.return_value = []

    result = await engine.answer("nothing")

    assert result.sources == []
    assert "## Sources for:" in result.context


@pytest.mark.asyncio
async def test_answer_with_custom_prompt(engine, mock_crawler_manager, mock_vector_store, sample_results):
    """system_prompt appears in synthesis_prompt."""
    mock_crawler_manager.crawl_all.return_value = sample_results
    mock_vector_store.search.return_value = []

    custom = "You are a senior data scientist."
    result = await engine.answer("python", system_prompt=custom)

    assert custom in result.synthesis_prompt


@pytest.mark.asyncio
async def test_answer_respects_num_results(engine, mock_crawler_manager, mock_vector_store):
    """num_results=2 → at most 2 sources."""
    results = [
        CrawlResult(
            source="web",
            title=f"Result {i}",
            content=f"content {i}",
            url=f"https://example.com/{i}",
            score=1.0 - i * 0.1,
            crawled_at=datetime.now(),
        )
        for i in range(5)
    ]
    mock_crawler_manager.crawl_all.return_value = results
    mock_vector_store.search.return_value = []

    result = await engine.answer("query", num_results=2)

    assert len(result.sources) <= 2


@pytest.mark.asyncio
async def test_answer_includes_metadata(engine, mock_crawler_manager, mock_vector_store, sample_results):
    """sources list has number, title, url, source, excerpt keys."""
    mock_crawler_manager.crawl_all.return_value = sample_results
    mock_vector_store.search.return_value = []

    result = await engine.answer("python")

    for source in result.sources:
        assert "number" in source
        assert "title" in source
        assert "url" in source
        assert "source" in source
        assert "excerpt" in source