"""Tests for code context search"""
import pytest
from search.code_context import CodeContextSearch, CodeSnippet, CodeContextResult, search_code_context


@pytest.fixture
def searcher():
    return CodeContextSearch()


def test_code_context_result_has_required_fields():
    result = CodeContextResult(
        query="test",
        snippets=[],
        formatted_response="test",
        total_results=0,
        search_time_ms=100.0,
    )
    assert result.query == "test"
    assert result.snippets == []


def test_code_snippet_has_required_fields():
    snippet = CodeSnippet(
        title="test.py",
        code="print('hello')",
        language="python",
        url="https://github.com/test",
        source="github",
    )
    assert snippet.title == "test.py"
    assert snippet.language == "python"


def test_format_response_with_no_snippets(searcher):
    result = searcher._format_response([], 5000)
    assert "No code snippets found" in result


def test_format_response_with_snippets(searcher):
    snippets = [
        CodeSnippet(
            title="Test Repo",
            code="def hello(): pass",
            language="python",
            url="https://github.com/test",
            source="github",
            description="A test repo",
            stars=100,
        )
    ]
    result = searcher._format_response(snippets, 5000)
    assert "Test Repo" in result
    assert "python" in result


def test_search_code_context_function():
    # This is a quick test that doesn't make network calls
    result = search_code_context.__doc__
    assert result is not None  # Just verify function exists
