"""
Structured output formatting for search results.
Inspired by Exa's schema-based output approach.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime
from crawlers.base import CrawlResult
import json


@dataclass
class OutputSchema:
    """Schema for structured output"""
    fields: list[str]
    format: str = "json"  # json, markdown, csv
    include_metadata: bool = True
    max_content_length: int = 500


class StructuredOutput:
    """Format search results in structured ways"""

    SCHEMAS = {
        "company": OutputSchema(
            fields=["name", "description", "url", "industry", "founded", "employees", "funding"]
        ),
        "people": OutputSchema(
            fields=["name", "title", "company", "linkedin", "expertise", "bio"]
        ),
        "research_paper": OutputSchema(
            fields=["title", "authors", "abstract", "url", "date", "citation_count"]
        ),
        "financial_report": OutputSchema(
            fields=["company", "filing_type", "date", "revenue", "profit", "url"]
        ),
        "code": OutputSchema(
            fields=["title", "language", "description", "url", "stars", "last_updated"]
        ),
        "news": OutputSchema(
            fields=["title", "source", "date", "summary", "url", "category"]
        ),
        "personal_site": OutputSchema(
            fields=["name", "bio", "url", "topics", "recent_posts"]
        ),
    }

    def __init__(self):
        self.custom_schemas: dict[str, OutputSchema] = {}

    def register_schema(self, name: str, schema: OutputSchema):
        self.custom_schemas[name] = schema

    def format_results(
        self,
        results: list[CrawlResult],
        schema_name: str = "general",
        format_type: str = "json",
        include_metadata: bool = True,
    ) -> str:
        schema = self._get_schema(schema_name)
        if format_type == "json":
            return self._format_json(results, schema, include_metadata)
        elif format_type == "markdown":
            return self._format_markdown(results, schema, include_metadata)
        elif format_type == "csv":
            return self._format_csv(results, schema, include_metadata)
        return self._format_json(results, schema, include_metadata)

    def _get_schema(self, name: str) -> OutputSchema:
        if name in self.SCHEMAS:
            return self.SCHEMAS[name]
        elif name in self.custom_schemas:
            return self.custom_schemas[name]
        return OutputSchema(fields=["title", "content", "url", "source"])

    def _format_json(self, results: list[CrawlResult], schema: OutputSchema, include_metadata: bool) -> str:
        output = []
        for r in results:
            item = {}
            for fld in schema.fields:
                value = self._extract_field(r, fld)
                if value is not None:
                    item[fld] = value
            if include_metadata and r.metadata:
                item["metadata"] = r.metadata
            output.append(item)
        return json.dumps(output, indent=2, default=str)

    def _format_markdown(self, results: list[CrawlResult], schema: OutputSchema, include_metadata: bool) -> str:
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"## Result {i}")
            for fld in schema.fields:
                value = self._extract_field(r, fld)
                if value is not None:
                    lines.append(f"**{fld}:** {value}")
            if include_metadata and r.metadata:
                lines.append(f"**metadata:** {json.dumps(r.metadata, default=str)}")
            lines.append("")
        return "\n".join(lines)

    def _format_csv(self, results: list[CrawlResult], schema: OutputSchema, include_metadata: bool) -> str:
        headers = schema.fields[:]
        if include_metadata:
            headers.append("metadata")
        lines = [",".join(headers)]
        for r in results:
            row = []
            for fld in schema.fields:
                val = self._extract_field(r, fld)
                row.append(f'"{str(val).replace(chr(34), chr(34)+chr(34))}"' if val is not None else '""')
            if include_metadata:
                row.append(f'"{json.dumps(r.metadata, default=str)}"')
            lines.append(",".join(row))
        return "\n".join(lines)

    def _extract_field(self, result: CrawlResult, field_name: str) -> Optional[str]:
        field_map = {
            "title": result.title,
            "content": result.content[:OutputSchema.max_content_length] if result.content else None,
            "url": result.url,
            "source": result.source,
            "name": result.title,
            "description": result.content[:300] if result.content else None,
            "bio": result.content[:300] if result.content else None,
            "summary": result.content[:300] if result.content else None,
            "date": result.crawled_at.isoformat() if result.crawled_at else None,
            "linkedin": result.metadata.get("linkedin"),
            "expertise": result.metadata.get("expertise"),
            "company": result.metadata.get("company"),
            "title_field": result.metadata.get("title"),
            "industry": result.metadata.get("industry"),
            "founded": result.metadata.get("founded"),
            "employees": result.metadata.get("employees"),
            "funding": result.metadata.get("funding"),
            "authors": result.metadata.get("authors"),
            "abstract": result.content[:500] if result.content else None,
            "citation_count": result.metadata.get("citation_count"),
            "filing_type": result.metadata.get("filing_type"),
            "revenue": result.metadata.get("revenue"),
            "profit": result.metadata.get("profit"),
            "language": result.metadata.get("language"),
            "stars": result.metadata.get("stars"),
            "last_updated": result.metadata.get("last_updated"),
            "category": result.metadata.get("category"),
            "topics": result.metadata.get("topics"),
            "recent_posts": result.metadata.get("recent_posts"),
        }
        return field_map.get(field_name)


def format_search_results(
    results: list[CrawlResult],
    schema_name: str = "general",
    format_type: str = "json",
) -> str:
    formatter = StructuredOutput()
    return formatter.format_results(results, schema_name, format_type)
