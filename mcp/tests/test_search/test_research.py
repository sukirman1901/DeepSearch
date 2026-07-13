"""Tests for Agent pattern (deep research)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from search.research import ResearchManager
from crawlers.base import CrawlResult


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client with collection support."""
    client = MagicMock()
    collections = {}

    def get_or_create_collection(name):
        if name not in collections:
            col = MagicMock()
            col.stored = {"ids": [], "embeddings": [], "documents": [], "metadatas": []}
            col.add = MagicMock(side_effect=lambda ids, embeddings, documents, metadatas=None:
                _add_to_mock(col, ids, embeddings, documents, metadatas))
            col.query = MagicMock(side_effect=lambda query_embeddings, n_results:
                _query_mock(col, query_embeddings, n_results))
            col.count = MagicMock(return_value=0)
            collections[name] = col
        return collections[name]

    def get_collection(name):
        if name not in collections:
            raise Exception(f"Collection {name} not found")
        return collections[name]

    def delete_collection(name):
        collections.pop(name, None)

    client.get_or_create_collection = MagicMock(side_effect=get_or_create_collection)
    client.get_collection = MagicMock(side_effect=get_collection)
    client.delete_collection = MagicMock(side_effect=delete_collection)
    return client


def _add_to_mock(col, ids, embeddings, documents, metadatas):
    for i in range(len(ids)):
        col.stored["ids"].append(ids[i])
        col.stored["embeddings"].append(embeddings[i])
        col.stored["documents"].append(documents[i])
        col.stored["metadatas"].append(metadatas[i] if metadatas else {})
    col.count = MagicMock(return_value=len(col.stored["ids"]))


def _query_mock(col, query_embeddings, n_results):
    count = min(n_results, len(col.stored["ids"]))
    return {
        "ids": [col.stored["ids"][:count]],
        "documents": [col.stored["documents"][:count]],
        "metadatas": [col.stored["metadatas"][:count]],
        "distances": [[0.1] * count],
    }


@pytest.fixture
def mock_embedding():
    """Mock embedding model that returns fixed embeddings."""
    model = MagicMock()
    model.embed = MagicMock(return_value=[0.1, 0.2, 0.3])
    return model


@pytest.fixture
def manager(mock_chromadb, mock_embedding, tmp_path):
    return ResearchManager(
        chromadb_client=mock_chromadb,
        embedding_model=mock_embedding,
        data_file=str(tmp_path / "research_sessions.json"),
    )


@pytest.fixture
def mock_crawler():
    return AsyncMock()


@pytest.fixture
def sample_results():
    return [
        CrawlResult(source="web", title="AI Startup in SF", content="AI company in San Francisco",
                    url="https://example.com/1", crawled_at=datetime.now()),
        CrawlResult(source="reddit", title="SF AI Discussion", content="Reddit thread about AI in SF",
                    url="https://reddit.com/r/1", crawled_at=datetime.now()),
    ]


@pytest.mark.asyncio
async def test_start_research_creates_session(manager, mock_crawler, sample_results):
    """Creates session, returns ID + result count."""
    mock_crawler.crawl_all.return_value = sample_results
    with patch.object(manager.query_generator, "generate_variations", return_value=["AI startups"]):
        result = await manager.start_research(
            query="AI startups", crawler_manager=mock_crawler, max_results=10
        )

    assert "session_id" in result
    assert result["result_count"] > 0
    assert len(result["session_id"]) == 8


@pytest.mark.asyncio
async def test_start_research_auto_generates_subqueries(manager, mock_crawler, sample_results):
    """Verify multiple sub-queries are generated and used."""
    mock_crawler.crawl_all.return_value = sample_results
    sub_queries = ["AI startups", "AI companies", "artificial intelligence firms"]
    with patch.object(manager.query_generator, "generate_variations", return_value=sub_queries):
        result = await manager.start_research(
            query="AI startups", crawler_manager=mock_crawler
        )

    assert mock_crawler.crawl_all.await_count == 3
    assert result["sub_queries"] == sub_queries


@pytest.mark.asyncio
async def test_ask_followup_returns_semantic_results(manager, mock_crawler, sample_results):
    """Follow-up query returns results from session."""
    mock_crawler.crawl_all.return_value = sample_results
    with patch.object(manager.query_generator, "generate_variations", return_value=["AI startups"]):
        start_result = await manager.start_research(query="AI startups", crawler_manager=mock_crawler)

    sid = start_result["session_id"]
    results = manager.ask_followup(sid, "funding rounds", num_results=2)

    assert len(results) > 0
    assert all(isinstance(r, CrawlResult) for r in results)


def test_ask_followup_invalid_session(manager):
    """Invalid ID returns empty list."""
    results = manager.ask_followup("nonexistent", "query")
    assert results == []


@pytest.mark.asyncio
async def test_list_sessions(manager, mock_crawler, sample_results):
    """Multiple sessions listed with correct stats."""
    mock_crawler.crawl_all.return_value = sample_results
    with patch.object(manager.query_generator, "generate_variations", return_value=["q1"]):
        await manager.start_research(query="topic1", crawler_manager=mock_crawler)
        await manager.start_research(query="topic2", crawler_manager=mock_crawler)

    sessions = manager.list_sessions()
    assert len(sessions) == 2
    queries = [s["query"] for s in sessions]
    assert "topic1" in queries
    assert "topic2" in queries


@pytest.mark.asyncio
async def test_delete_session(manager, mock_crawler, sample_results):
    """Delete removes session + collection."""
    mock_crawler.crawl_all.return_value = sample_results
    with patch.object(manager.query_generator, "generate_variations", return_value=["q1"]):
        result = await manager.start_research(query="topic", crawler_manager=mock_crawler)

    deleted = manager.delete_session(result["session_id"])
    assert deleted is True
    assert len(manager.list_sessions()) == 0


def test_delete_session_invalid_id(manager):
    """Delete non-existent returns False."""
    deleted = manager.delete_session("nonexistent")
    assert deleted is False


@pytest.mark.asyncio
async def test_persistence(manager, mock_crawler, sample_results, mock_chromadb, mock_embedding, tmp_path):
    """Create session, new ResearchManager with same file, verify loaded."""
    mock_crawler.crawl_all.return_value = sample_results
    with patch.object(manager.query_generator, "generate_variations", return_value=["q1"]):
        result = await manager.start_research(query="persist test", crawler_manager=mock_crawler)

    new_mgr = ResearchManager(
        chromadb_client=mock_chromadb,
        embedding_model=mock_embedding,
        data_file=str(tmp_path / "research_sessions.json"),
    )
    sessions = new_mgr.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["query"] == "persist test"
