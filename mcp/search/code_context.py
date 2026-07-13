"""
Context API (Code Search) - Find code snippets from GitHub, Stack Overflow, docs.
Inspired by Exa's Context API for coding agents.
"""
from dataclasses import dataclass, field
from typing import Optional
import httpx
import json
import re
from datetime import datetime


@dataclass
class CodeSnippet:
    """A code snippet result"""
    title: str
    code: str
    language: str
    url: str
    source: str  # github, stackoverflow, docs
    description: str = ""
    stars: int = 0
    relevance_score: float = 0.0


@dataclass
class CodeContextResult:
    """Result from code context search"""
    query: str
    snippets: list[CodeSnippet] = field(default_factory=list)
    formatted_response: str = ""
    total_results: int = 0
    search_time_ms: float = 0.0


class CodeContextSearch:
    """Search for code context across multiple sources"""

    GITHUB_API = "https://api.github.com"
    SO_API = "https://api.stackexchange.com/2.3"

    def __init__(self):
        self.client = httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "DeepSearch/1.0"}
        )

    def search_code(
        self,
        query: str,
        max_results: int = 10,
        language: str = "",
        tokens_target: int = 5000,
    ) -> CodeContextResult:
        """
        Search for code snippets across GitHub and Stack Overflow.

        Args:
            query: Search query
            max_results: Maximum results to return
            language: Filter by programming language
            tokens_target: Target token count for response

        Returns:
            CodeContextResult with snippets and formatted response
        """
        start_time = datetime.now()
        all_snippets = []

        # Search GitHub
        github_snippets = self._search_github(query, max_results // 2, language)
        all_snippets.extend(github_snippets)

        # Search Stack Overflow
        so_snippets = self._search_stackoverflow(query, max_results // 2, language)
        all_snippets.extend(so_snippets)

        # Sort by relevance
        all_snippets.sort(key=lambda x: x.relevance_score, reverse=True)

        # Format response
        formatted = self._format_response(all_snippets[:max_results], tokens_target)

        search_time = (datetime.now() - start_time).total_seconds() * 1000

        return CodeContextResult(
            query=query,
            snippets=all_snippets[:max_results],
            formatted_response=formatted,
            total_results=len(all_snippets),
            search_time_ms=search_time,
        )

    def _search_github(self, query: str, max_results: int, language: str) -> list[CodeSnippet]:
        """Search GitHub for code snippets"""
        snippets = []
        try:
            search_query = f"{query} language:{language}" if language else query
            params = {
                "q": search_query,
                "per_page": min(max_results, 10),
                "sort": "stars",
                "order": "desc",
            }

            response = self.client.get(f"{self.GITHUB_API}/search/repositories", params=params)
            if response.status_code == 200:
                data = response.json()
                for repo in data.get("items", [])[:max_results]:
                    # Get README or top file for code context
                    code_content = self._get_repo_readme(repo["full_name"])
                    if code_content:
                        snippets.append(CodeSnippet(
                            title=repo["name"],
                            code=code_content[:2000],
                            language=repo.get("language", "unknown"),
                            url=repo["html_url"],
                            source="github",
                            description=repo.get("description", ""),
                            stars=repo.get("stargazers_count", 0),
                            relevance_score=min(1.0, repo.get("stargazers_count", 0) / 10000),
                        ))
        except Exception as e:
            pass  # Silently fail
        return snippets

    def _get_repo_readme(self, full_name: str) -> Optional[str]:
        """Get README content from a GitHub repo"""
        try:
            response = self.client.get(f"{self.GITHUB_API}/repos/{full_name}/readme")
            if response.status_code == 200:
                import base64
                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                return content[:3000]
        except Exception:
            pass
        return None

    def _search_stackoverflow(self, query: str, max_results: int, language: str) -> list[CodeSnippet]:
        """Search Stack Overflow for code answers"""
        snippets = []
        try:
            tagged = language if language else ""
            params = {
                "order": "desc",
                "sort": "relevance",
                "intitle": query,
                "tagged": tagged,
                "site": "stackoverflow",
                "pagesize": min(max_results, 10),
                "filter": "withbody",
            }

            response = self.client.get(f"{self.SO_API}/search/advanced", params=params)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", [])[:max_results]:
                    # Extract code from body
                    code = self._extract_code_from_html(item.get("body", ""))
                    if code:
                        snippets.append(CodeSnippet(
                            title=item["title"],
                            code=code[:2000],
                            language=language or "unknown",
                            url=item["link"],
                            source="stackoverflow",
                            description=item.get("body_markdown", "")[:200],
                            stars=item.get("score", 0),
                            relevance_score=min(1.0, item.get("score", 0) / 100),
                        ))
        except Exception:
            pass
        return snippets

    def _extract_code_from_html(self, html: str) -> Optional[str]:
        """Extract code blocks from HTML content"""
        code_blocks = re.findall(r'<code>(.*?)</code>', html, re.DOTALL)
        if code_blocks:
            return "\n\n".join(code_blocks[:3])
        return None

    def _format_response(self, snippets: list[CodeSnippet], tokens_target: int) -> str:
        """Format snippets into a token-efficient response"""
        if not snippets:
            return "No code snippets found."

        lines = []
        current_tokens = 0
        token_estimate = len  # Simple approximation

        for i, snippet in enumerate(snippets, 1):
            header = f"## {snippet.title} ({snippet.source})"
            code_block = f"```{snippet.language}\n{snippet.code}\n```"
            link = f"Source: {snippet.url}"

            section = f"{header}\n{code_block}\n{link}\n"

            if current_tokens + token_estimate(section) > tokens_target:
                break

            lines.append(section)
            current_tokens += token_estimate(section)

        return "\n".join(lines)


def search_code_context(
    query: str,
    max_results: int = 10,
    language: str = "",
    tokens_target: int = 5000,
) -> CodeContextResult:
    """Convenience function for code context search"""
    searcher = CodeContextSearch()
    return searcher.search_code(query, max_results, language, tokens_target)
