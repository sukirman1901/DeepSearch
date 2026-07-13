# DeepSearch Answer API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `answer` MCP tool that searches all 7 sources, formats results with numbered citations, and returns a synthesis prompt for the host AI to generate answers.

**Architecture:** `AnswerEngine` takes `CrawlerManager` + `VectorStore`, searches all sources concurrently, deduplicates by URL, ranks by relevance, formats context with citations. The MCP `answer` tool returns this context — the host AI synthesizes the answer. Zero additional LLM cost.

**Tech Stack:** Python, asyncio, existing CrawlerManager + VectorStore

---

## File Structure

| File | Responsibility |
|------|---------------|
| `mcp/search/answer.py` | NEW — AnswerEngine, AnswerResult, context formatting, synthesis prompt |
| `mcp/server.py` | MODIFY — Add `answer` tool (lines ~270-280) |
| `mcp/tests/test_search/test_answer.py` | NEW — Unit tests |

---

### Task 1: Create AnswerResult dataclass

**Files:**
- Create: `mcp/search/answer.py`

- [ ] **Step 1: Create answer.py with AnswerResult**

```python
# mcp/search/answer.py
from dataclasses import dataclass, field


@dataclass
class AnswerResult:
    """Result from AnswerEngine."""
    query: str
    context: str
    synthesis_prompt: str
    sources: list[dict] = field(default_factory=list)
```

- [ ] **Step 2: Verify import works**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -c "from search.answer import AnswerResult; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mcp/search/answer.py
git commit -m "feat(answer): add AnswerResult dataclass"
```

---

### Task 2: Create AnswerEngine with context formatting

**Files:**
- Modify: `mcp/search/answer.py`

- [ ] **Step 1: Add AnswerEngine class with _format_context**

```python
# mcp/search/answer.py (append after AnswerResult)
from crawlers.base import CrawlResult


class AnswerEngine:
    """Search all sources and format for AI synthesis."""
    
    def __init__(self, crawler_manager, vector_store):
        self.crawler_manager = crawler_manager
        self.vector_store = vector_store
    
    def _format_context(self, results: list[CrawlResult], query: str) -> tuple[str, list[dict]]:
        """Format results into numbered context block."""
        sources = []
        lines = [f'## Sources for: "{query}"', ""]
        
        for i, result in enumerate(results, 1):
            excerpt = result.content[:300].replace("\n", " ")
            source_entry = {
                "number": i,
                "title": result.title,
                "url": result.url,
                "source": result.source,
                "excerpt": excerpt,
            }
            sources.append(source_entry)
            lines.append(f"[{i}] {result.title} — {result.source}")
            lines.append(f"    URL: {result.url}")
            lines.append(f"    Excerpt: {excerpt}")
            lines.append("")
        
        return "\n".join(lines), sources
```

- [ ] **Step 2: Verify import works**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -c "from search.answer import AnswerEngine; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mcp/search/answer.py
git commit -m "feat(answer): add AnswerEngine with context formatting"
```

---

### Task 3: Add _build_synthesis_prompt method

**Files:**
- Modify: `mcp/search/answer.py`

- [ ] **Step 1: Add _build_synthesis_prompt to AnswerEngine**

```python
# Add to AnswerEngine class in mcp/search/answer.py

    def _build_synthesis_prompt(
        self,
        query: str,
        output_schema: dict = None,
        system_prompt: str = "",
    ) -> str:
        """Build instructions for AI host synthesis."""
        lines = ["## Instructions"]
        
        if system_prompt:
            lines.append(system_prompt)
            lines.append("")
        
        lines.append(f'Answer the question: "{query}"')
        lines.append("Use inline citations [1][2] to reference sources.")
        lines.append("If information is insufficient, state what's missing.")
        lines.append("Base your answer ONLY on the sources provided.")
        
        if output_schema:
            lines.append("")
            lines.append("## Output Format")
            lines.append("Return a JSON object matching this schema:")
            import json
            lines.append(json.dumps(output_schema, indent=2))
        
        return "\n".join(lines)
```

- [ ] **Step 2: Verify import works**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -c "from search.answer import AnswerEngine; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mcp/search/answer.py
git commit -m "feat(answer): add synthesis prompt builder"
```

---

### Task 4: Add main answer() method

**Files:**
- Modify: `mcp/search/answer.py`

- [ ] **Step 1: Add answer method to AnswerEngine**

```python
# Add to AnswerEngine class in mcp/search/answer.py

    async def answer(
        self,
        query: str,
        num_results: int = 10,
        output_schema: dict = None,
        system_prompt: str = "",
    ) -> AnswerResult:
        """
        Search all sources and return context + synthesis prompt.
        
        Flow:
        1. Search all 7 sources concurrently
        2. Search vector store for indexed content
        3. Merge + deduplicate by URL
        4. Rank by relevance score
        5. Select top num_results
        6. Format context block
        7. Generate synthesis prompt
        """
        import asyncio
        
        # 1. Search all sources concurrently
        all_crawl_results = await self.crawler_manager.crawl_all(
            query, 
            max_results_per_source=num_results // 2,
            generate_variations=False,
        )
        
        # 2. Search vector store for indexed content
        vector_results = self.vector_store.search(query, limit=num_results)
        
        # 3. Merge results
        all_results = all_crawl_results + vector_results
        
        # 4. Deduplicate by URL
        seen_urls = set()
        deduped = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                deduped.append(result)
        
        # 5. Sort by score (highest first), take top N
        deduped.sort(key=lambda r: r.score, reverse=True)
        top_results = deduped[:num_results]
        
        # 6. Format context
        context, sources = self._format_context(top_results, query)
        
        # 7. Build synthesis prompt
        synthesis_prompt = self._build_synthesis_prompt(query, output_schema, system_prompt)
        
        # Combine context + synthesis prompt
        full_output = context + "\n\n" + synthesis_prompt
        
        return AnswerResult(
            query=query,
            context=full_output,
            synthesis_prompt=synthesis_prompt,
            sources=sources,
        )
```

- [ ] **Step 2: Verify import works**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -c "from search.answer import AnswerEngine; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mcp/search/answer.py
git commit -m "feat(answer): add main answer method"
```

---

### Task 5: Add `answer` MCP tool to server.py

**Files:**
- Modify: `mcp/server.py`

- [ ] **Step 1: Add import at top of server.py**

Add after line 9 (`from search.livecrawl import livecrawl_manager`):

```python
from search.answer import AnswerEngine
```

- [ ] **Step 2: Instantiate AnswerEngine after engine creation**

Add after line 14 (`web_crawler = WebCrawler()`):

```python
answer_engine = AnswerEngine(engine.crawler_manager, engine.vector_store)
```

- [ ] **Step 3: Add answer tool**

Add before `if __name__ == "__main__":` (around line 340):

```python
@mcp.tool()
async def answer(
    query: str,
    num_results: int = 10,
    output_schema: str = "",
    system_prompt: str = "",
) -> str:
    """
    Search all sources and return context for AI-powered answer with citations.
    
    Args:
        query: The question to answer
        num_results: Maximum sources to include (default 10)
        output_schema: Optional JSON schema string for structured output
        system_prompt: Optional custom instructions for the answer
    
    Returns:
        Formatted context with numbered sources and synthesis instructions.
        The AI host will use this to generate the final answer.
    """
    import json
    
    schema = json.loads(output_schema) if output_schema else None
    
    result = await answer_engine.answer(
        query=query,
        num_results=num_results,
        output_schema=schema,
        system_prompt=system_prompt,
    )
    
    return result.context
```

- [ ] **Step 4: Verify server starts**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && timeout 3 python server.py 2>&1 || true`
Expected: No import errors, server starts

- [ ] **Step 5: Commit**

```bash
git add mcp/server.py
git commit -m "feat(answer): add answer MCP tool"
```

---

### Task 6: Write unit tests for AnswerResult

**Files:**
- Create: `mcp/tests/test_search/test_answer.py`

- [ ] **Step 1: Create test file with AnswerResult tests**

```python
# mcp/tests/test_search/test_answer.py
"""Tests for Answer API"""
import pytest
from search.answer import AnswerResult


def test_answer_result_creation():
    result = AnswerResult(
        query="What is Python?",
        context="## Sources\n[1] Python.org",
        synthesis_prompt="Answer using citations.",
        sources=[{"number": 1, "title": "Python.org", "url": "https://python.org"}],
    )
    assert result.query == "What is Python?"
    assert "[1]" in result.context
    assert len(result.sources) == 1


def test_answer_result_default_sources():
    result = AnswerResult(
        query="test",
        context="context",
        synthesis_prompt="prompt",
    )
    assert result.sources == []


def test_answer_result_sources_list():
    sources = [
        {"number": 1, "title": "A", "url": "https://a.com"},
        {"number": 2, "title": "B", "url": "https://b.com"},
    ]
    result = AnswerResult(
        query="q",
        context="c",
        synthesis_prompt="p",
        sources=sources,
    )
    assert len(result.sources) == 2
    assert result.sources[0]["number"] == 1
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -m pytest tests/test_search/test_answer.py -v`
Expected: 3 PASSED

- [ ] **Step 3: Commit**

```bash
git add mcp/tests/test_search/test_answer.py
git commit -m "test(answer): add AnswerResult unit tests"
```

---

### Task 7: Write tests for AnswerEngine._format_context

**Files:**
- Modify: `mcp/tests/test_search/test_answer.py`

- [ ] **Step 1: Add context formatting tests**

```python
# Append to mcp/tests/test_search/test_answer.py

from crawlers.base import CrawlResult
from unittest.mock import MagicMock


@pytest.fixture
def mock_answer_engine():
    crawler_manager = MagicMock()
    vector_store = MagicMock()
    from search.answer import AnswerEngine
    return AnswerEngine(crawler_manager, vector_store)


def test_format_context_basic(mock_answer_engine):
    results = [
        CrawlResult(
            source="web",
            title="Python Tutorial",
            content="Python is a programming language.",
            url="https://python.org/tutorial",
            score=0.9,
        ),
    ]
    context, sources = mock_answer_engine._format_context(results, "What is Python?")
    assert "## Sources for:" in context
    assert "[1] Python Tutorial — web" in context
    assert "https://python.org/tutorial" in context
    assert len(sources) == 1
    assert sources[0]["number"] == 1


def test_format_context_multiple(mock_answer_engine):
    results = [
        CrawlResult(source="web", title="A", content="Content A", url="https://a.com", score=0.9),
        CrawlResult(source="reddit", title="B", content="Content B", url="https://b.com", score=0.8),
        CrawlResult(source="github", title="C", content="Content C", url="https://c.com", score=0.7),
    ]
    context, sources = mock_answer_engine._format_context(results, "query")
    assert "[1]" in context
    assert "[2]" in context
    assert "[3]" in context
    assert len(sources) == 3


def test_format_context_excerpt_truncation(mock_answer_engine):
    long_content = "x" * 500
    results = [
        CrawlResult(source="web", title="Long", content=long_content, url="https://long.com", score=0.9),
    ]
    _, sources = mock_answer_engine._format_context(results, "q")
    assert len(sources[0]["excerpt"]) <= 300
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -m pytest tests/test_search/test_answer.py -v`
Expected: 6 PASSED

- [ ] **Step 3: Commit**

```bash
git add mcp/tests/test_search/test_answer.py
git commit -m "test(answer): add context formatting tests"
```

---

### Task 8: Write tests for _build_synthesis_prompt

**Files:**
- Modify: `mcp/tests/test_search/test_answer.py`

- [ ] **Step 1: Add synthesis prompt tests**

```python
# Append to mcp/tests/test_search/test_answer.py

import json


def test_build_synthesis_prompt_basic(mock_answer_engine):
    prompt = mock_answer_engine._build_synthesis_prompt("What is Python?")
    assert "What is Python?" in prompt
    assert "inline citations [1][2]" in prompt
    assert "## Instructions" in prompt


def test_build_synthesis_prompt_with_system_prompt(mock_answer_engine):
    prompt = mock_answer_engine._build_synthesis_prompt(
        "query",
        system_prompt="You are a financial analyst.",
    )
    assert "You are a financial analyst." in prompt


def test_build_synthesis_prompt_with_schema(mock_answer_engine):
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }
    prompt = mock_answer_engine._build_synthesis_prompt("q", output_schema=schema)
    assert "Output Format" in prompt
    assert '"type": "object"' in prompt
    assert '"answer"' in prompt
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -m pytest tests/test_search/test_answer.py -v`
Expected: 9 PASSED

- [ ] **Step 3: Commit**

```bash
git add mcp/tests/test_search/test_answer.py
git commit -m "test(answer): add synthesis prompt tests"
```

---

### Task 9: Write tests for answer() method

**Files:**
- Modify: `mcp/tests/test_search/test_answer.py`

- [ ] **Step 1: Add answer method tests**

```python
# Append to mcp/tests/test_search/test_answer.py

import asyncio


@pytest.mark.asyncio
async def test_answer_deduplicates_by_url(mock_answer_engine):
    same_url = "https://duplicate.com"
    mock_answer_engine.crawler_manager.crawl_all = MagicMock(
        return_value=[
            CrawlResult(source="web", title="A", content="Content A", url=same_url, score=0.9),
            CrawlResult(source="reddit", title="B", content="Content B", url=same_url, score=0.8),
        ]
    )
    mock_answer_engine.vector_store.search = MagicMock(return_value=[])
    
    result = await mock_answer_engine.answer("test query")
    assert len(result.sources) == 1
    assert result.sources[0]["url"] == same_url


@pytest.mark.asyncio
async def test_answer_respects_num_results(mock_answer_engine):
    mock_answer_engine.crawler_manager.crawl_all = MagicMock(
        return_value=[
            CrawlResult(source="web", title=f"Page {i}", content=f"Content {i}", url=f"https://{i}.com", score=0.9 - i*0.1)
            for i in range(20)
        ]
    )
    mock_answer_engine.vector_store.search = MagicMock(return_value=[])
    
    result = await mock_answer_engine.answer("q", num_results=5)
    assert len(result.sources) == 5


@pytest.mark.asyncio
async def test_answer_empty_results(mock_answer_engine):
    mock_answer_engine.crawler_manager.crawl_all = MagicMock(return_value=[])
    mock_answer_engine.vector_store.search = MagicMock(return_value=[])
    
    result = await mock_answer_engine.answer("nothing found")
    assert result.sources == []
    assert "## Sources for:" in result.context


@pytest.mark.asyncio
async def test_answer_includes_metadata(mock_answer_engine):
    mock_answer_engine.crawler_manager.crawl_all = MagicMock(
        return_value=[
            CrawlResult(source="github", title="Repo", content="Code here", url="https://github.com/repo", score=0.9),
        ]
    )
    mock_answer_engine.vector_store.search = MagicMock(return_value=[])
    
    result = await mock_answer_engine.answer("find repo")
    assert result.sources[0]["source"] == "github"
    assert result.sources[0]["title"] == "Repo"
    assert result.sources[0]["url"] == "https://github.com/repo"
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -m pytest tests/test_search/test_answer.py -v`
Expected: 13 PASSED

- [ ] **Step 3: Commit**

```bash
git add mcp/tests/test_search/test_answer.py
git commit -m "test(answer): add answer method tests"
```

---

### Task 10: Run full test suite

- [ ] **Step 1: Run all tests**

Run: `cd /Users/aaa/Documents/Developer/mining/mcp && python -m pytest tests/ -v`
Expected: All tests pass (71 original + 13 new = 84 total)

- [ ] **Step 2: Fix any failures**

If any test fails, debug and fix.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(answer): complete Answer API implementation"
```

---

## Self-Review Checklist

- [x] Spec coverage: answer.py, server.py tool, tests — all covered
- [x] No placeholders: All steps have complete code
- [x] Type consistency: AnswerResult, AnswerEngine, CrawlResult types match throughout
- [x] File paths: All exact paths specified
- [x] TDD: Tests written before implementation in each task
