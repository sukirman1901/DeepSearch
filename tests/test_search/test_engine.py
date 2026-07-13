import pytest
from search.engine import SearchEngine

def test_search_engine_initializes():
    engine = SearchEngine()
    assert engine is not None

@pytest.mark.asyncio
async def test_search_engine_index_and_search():
    engine = SearchEngine()
    await engine.index_topic("python programming", max_results_per_source=1)
    results = engine.search("python", limit=5)
    assert isinstance(results, list)
