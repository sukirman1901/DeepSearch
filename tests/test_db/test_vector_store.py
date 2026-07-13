from db.vector_store import VectorStore
from crawlers.base import CrawlResult

def test_vector_store_initializes():
    store = VectorStore()
    assert store is not None

def test_vector_store_add_and_search():
    store = VectorStore()
    result = CrawlResult(
        source="test",
        title="AI in Indonesia",
        content="Artificial intelligence is growing in Indonesia",
        url="https://example.com/ai-indonesia",
        metadata={"author": "test"}
    )
    store.add(result)
    
    results = store.search("artificial intelligence", limit=1)
    assert len(results) == 1
    assert results[0].title == "AI in Indonesia"

def test_vector_store_stats():
    store = VectorStore()
    stats = store.stats()
    assert "total_documents" in stats
    assert "sources" in stats
