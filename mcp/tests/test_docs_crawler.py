import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from search.docs_crawler import DocsCrawler
from search.docs_registry import LibraryConfig
from crawlers.base import CrawlResult


@pytest.fixture
def react_config():
    return LibraryConfig(
        id="react",
        name="React",
        docs_url="https://react.dev",
        start_paths=["/reference"],
        content_selector="main",
        nav_selector="aside a",
        exclude_paths=["/blog"],
        include_paths=[],
        max_pages=10,
        ttl_hours=168
    )


@pytest.mark.asyncio
async def test_crawl_returns_crawl_results(react_config):
    crawler = DocsCrawler(react_config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <body>
        <main>
            <h1>useState</h1>
            <p>The useState Hook lets you add state to functional components.</p>
            <pre><code>const [count, setCount] = useState(0);</code></pre>
        </main>
        <aside>
            <a href="/reference/react/useState">useState</a>
        </aside>
    </body>
    </html>
    """
    mock_response.raise_for_status = MagicMock()

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await crawler.crawl("useState", max_results=5)

        assert len(results) > 0
        assert isinstance(results[0], CrawlResult)
        assert results[0].source == "docs"
        assert results[0].metadata.get("library_id") == "react"


@pytest.mark.asyncio
async def test_crawl_extracts_code_blocks(react_config):
    crawler = DocsCrawler(react_config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <body>
        <main>
            <h1>Example</h1>
            <pre><code>import { useState } from 'react';

function Counter() {
    const [count, setCount] = useState(0);
    return &lt;button onClick={() => setCount(count + 1)}&gt;{count}&lt;/button&gt;;
}</code></pre>
        </main>
    </body>
    </html>
    """
    mock_response.raise_for_status = MagicMock()

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        results = await crawler.crawl("counter example", max_results=5)

        assert len(results) > 0
        code_examples = results[0].metadata.get("code_examples", [])
        assert len(code_examples) > 0
        assert "useState" in code_examples[0]


def test_should_exclude_path(react_config):
    crawler = DocsCrawler(react_config)
    assert crawler._should_exclude("/blog/my-post") == True
    assert crawler._should_exclude("/reference/react/useState") == False
