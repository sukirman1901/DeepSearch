"""Tests for docs search engine."""
import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from search.docs_engine import DocsSearchEngine
from crawlers.base import CrawlResult


@pytest.fixture
def engine_with_mock_deps():
    """Create DocsSearchEngine with mocked dependencies."""
    config = {
        "version": "1.0",
        "libraries": {
            "react": {
                "name": "React",
                "docs_url": "https://react.dev",
                "start_paths": ["/reference"],
                "content_selector": "main",
                "exclude_paths": [],
                "max_pages": 10,
                "ttl_hours": 168
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name

    try:
        with patch('search.docs_engine.VectorStore') as MockVS:
            mock_vs = MagicMock()
            mock_vs.search.return_value = []
            MockVS.return_value = mock_vs

            engine = DocsSearchEngine(temp_path)
            yield engine
    finally:
        os.unlink(temp_path)


@pytest.mark.asyncio
async def test_search_requires_library(engine_with_mock_deps):
    engine = engine_with_mock_deps
    with pytest.raises(ValueError, match="library"):
        await engine.search(query="test", library="")


@pytest.mark.asyncio
async def test_search_library_not_found(engine_with_mock_deps):
    engine = engine_with_mock_deps
    with pytest.raises(ValueError, match="not found"):
        await engine.search(query="test", library="unknown")


@pytest.mark.asyncio
async def test_search_returns_formatted_result(engine_with_mock_deps):
    engine = engine_with_mock_deps

    with patch('search.docs_engine.DocsCrawler') as MockCrawler:
        mock_instance = MagicMock()
        mock_instance.crawl = AsyncMock(return_value=[
            CrawlResult(
                source="docs",
                title="useState",
                content="The useState Hook lets you add state.",
                url="https://react.dev/reference/react/useState",
                metadata={"library_id": "react", "code_examples": ["const [x, setX] = useState(0)"]},
                category="code",
                score=0.9
            )
        ])
        MockCrawler.return_value = mock_instance

        result = await engine.search(query="useState", library="react")

        assert result.library == "react"
        assert result.query == "useState"
        assert len(result.pages) > 0
        assert "useState" in result.formatted
