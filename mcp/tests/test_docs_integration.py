"""Integration test for docs search feature."""
import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from crawlers.base import CrawlResult


@pytest.fixture
def registry_and_engine():
    """Create a registry temp file and DocsSearchEngine with mocked deps."""
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
                "ttl_hours": 168,
            }
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(config, f)
        temp_path = f.name

    cache_file = Path(temp_path).parent / "docs_cache.json"
    if cache_file.exists():
        cache_file.unlink()

    try:
        with patch("search.docs_engine.VectorStore") as MockVS:
            mock_vs = MagicMock()
            mock_vs.search.return_value = []
            MockVS.return_value = mock_vs

            from search.docs_engine import DocsSearchEngine

            engine = DocsSearchEngine(temp_path)
            yield engine
    finally:
        os.unlink(temp_path)
        if cache_file.exists():
            cache_file.unlink()


@pytest.mark.asyncio
async def test_full_docs_search_flow(registry_and_engine):
    """Test complete docs search flow from query to output."""
    engine = registry_and_engine

    mock_crawler = MagicMock()
    mock_crawler.crawl = AsyncMock(
        return_value=[
            CrawlResult(
                source="docs",
                title="useState - React",
                content=(
                    "The useState Hook lets you add state to functional components.\n\n"
                    "```jsx\nconst [count, setCount] = useState(0);\n```"
                ),
                url="https://react.dev/reference/react/useState",
                metadata={
                    "library_id": "react",
                    "code_examples": ["const [count, setCount] = useState(0);"],
                    "section": "reference",
                },
                category="code",
                score=0.95,
            )
        ]
    )

    with patch("search.docs_engine.DocsCrawler") as MockCrawler:
        MockCrawler.return_value = mock_crawler

        result = await engine.search(
            query="useState hook",
            library="react",
            tokens_target=3000,
        )

        assert result.library == "react"
        assert result.query == "useState hook"
        assert len(result.pages) > 0
        assert result.tokens_used > 0
        assert result.tokens_budget == 3000
        assert "useState" in result.formatted
