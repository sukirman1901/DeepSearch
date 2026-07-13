"""Agent pattern — deep research sessions with auto sub-queries and semantic follow-up."""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

from crawlers.base import CrawlResult
from search.query_variation import QueryVariationGenerator


class ResearchManager:
    """Deep research sessions with auto sub-queries and semantic follow-up."""

    def __init__(self, chromadb_client, embedding_model, data_file="data/research_sessions.json"):
        self.chromadb_client = chromadb_client
        self.embedding_model = embedding_model
        self.data_file = data_file
        self.sessions: dict = {}
        self.query_generator = QueryVariationGenerator()
        self._load()

    async def start_research(
        self,
        query: str,
        sources: Optional[list[str]] = None,
        max_results: int = 15,
        crawler_manager=None,
    ) -> dict:
        """Start a research session. Auto-generates sub-queries, crawls, indexes."""
        session_id = str(uuid.uuid4())[:8]

        sub_queries = self.query_generator.generate_variations(
            query, category="general", max_variations=3
        )

        all_results = []
        seen_urls = set()

        for sq in sub_queries:
            results = await crawler_manager.crawl_all(
                sq,
                max_results_per_source=max_results,
                sources=sources,
                generate_variations=False,
            )
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r)

        collection_name = f"session_{session_id}"
        collection = self.chromadb_client.get_or_create_collection(collection_name)

        for r in all_results:
            embedding = self.embedding_model.embed(r.content)
            collection.add(
                ids=[f"{session_id}_{hash(r.url)}"],
                embeddings=[embedding],
                documents=[r.content],
                metadatas=[{
                    "source": r.source,
                    "title": r.title,
                    "url": r.url,
                    "crawled_at": r.crawled_at.isoformat(),
                }],
            )

        self.sessions[session_id] = {
            "query": query,
            "sources": sources or [],
            "created_at": datetime.now().isoformat(),
            "result_count": len(all_results),
            "followup_count": 0,
            "sub_queries": sub_queries,
        }
        self._save()

        top_titles = [r.title for r in all_results[:5]]

        return {
            "session_id": session_id,
            "result_count": len(all_results),
            "sub_queries": sub_queries,
            "top_titles": top_titles,
        }

    def ask_followup(self, session_id: str, query: str, num_results: int = 5) -> list[CrawlResult]:
        """Semantic search within a session's indexed results."""
        if session_id not in self.sessions:
            return []

        collection_name = f"session_{session_id}"
        try:
            collection = self.chromadb_client.get_collection(collection_name)
        except Exception:
            return []

        query_embedding = self.embedding_model.embed(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=num_results,
        )

        self.sessions[session_id]["followup_count"] += 1
        self._save()

        crawl_results = []
        for i in range(len(results["ids"][0])):
            crawl_results.append(CrawlResult(
                source=results["metadatas"][0][i]["source"],
                title=results["metadatas"][0][i]["title"],
                content=results["documents"][0][i],
                url=results["metadatas"][0][i]["url"],
                metadata={"crawled_at": results["metadatas"][0][i]["crawled_at"]},
            ))
        return crawl_results

    def list_sessions(self) -> list[dict]:
        """List all research sessions with stats."""
        result = []
        for sid, s in self.sessions.items():
            result.append({
                "id": sid,
                "query": s["query"],
                "sources": s["sources"],
                "created_at": s["created_at"],
                "result_count": s["result_count"],
                "followup_count": s["followup_count"],
            })
        return result

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its ChromaDB collection."""
        if session_id not in self.sessions:
            return False

        collection_name = f"session_{session_id}"
        try:
            self.chromadb_client.delete_collection(collection_name)
        except Exception:
            pass

        del self.sessions[session_id]
        self._save()
        return True

    def _load(self):
        """Load session metadata from JSON file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    self.sessions = data.get("sessions", {})
        except (json.JSONDecodeError, IOError):
            self.sessions = {}

    def _save(self):
        """Save session metadata to JSON file."""
        os.makedirs(os.path.dirname(self.data_file) or ".", exist_ok=True)
        with open(self.data_file, "w") as f:
            json.dump({"sessions": self.sessions}, f, indent=2)
