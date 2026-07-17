from datetime import datetime

import chromadb
from crawlers.base import CrawlResult
from db.embeddings import EmbeddingModel


class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection("search_engine")
        self.docs_collection = self.client.get_or_create_collection("docs_search")
        self.embedding_model = EmbeddingModel()

    def add(self, result: CrawlResult) -> None:
        embedding = self.embedding_model.embed(result.content)
        self.collection.add(
            ids=[f"{result.source}_{hash(result.url)}"],
            embeddings=[embedding],
            documents=[result.content],
            metadatas=[{
                "source": result.source,
                "title": result.title,
                "url": result.url,
                "author": result.metadata.get("author", ""),
                "crawled_at": result.crawled_at.isoformat()
            }]
        )

    def search(self, query: str, limit: int = 10) -> list[CrawlResult]:
        query_embedding = self.embedding_model.embed(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        crawl_results = []
        for i in range(len(results["ids"][0])):
            crawl_results.append(CrawlResult(
                source=results["metadatas"][0][i]["source"],
                title=results["metadatas"][0][i]["title"],
                content=results["documents"][0][i],
                url=results["metadatas"][0][i]["url"],
                metadata={"author": results["metadatas"][0][i]["author"]}
            ))
        return crawl_results

    def add_docs(self, result: CrawlResult) -> None:
        """Add a documentation result to the docs collection."""
        doc_id = f"docs_{result.metadata.get('library_id', 'unknown')}_{hash(result.url)}"

        self.docs_collection.upsert(
            ids=[doc_id],
            documents=[result.content],
            metadatas=[{
                "source": result.source,
                "title": result.title,
                "url": result.url,
                "library_id": result.metadata.get("library_id", ""),
                "section": result.metadata.get("section", ""),
                "crawled_at": result.crawled_at.isoformat() if result.crawled_at else "",
            }]
        )

    def search_docs(self, query: str, library_id: str = "", limit: int = 10) -> list[CrawlResult]:
        """Search the docs collection."""
        where_filter = {"library_id": library_id} if library_id else None

        results = self.docs_collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_filter,
        )

        if not results or not results.get("documents"):
            return []

        crawl_results = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}

            crawl_results.append(CrawlResult(
                source=metadata.get("source", "docs"),
                title=metadata.get("title", ""),
                content=doc,
                url=metadata.get("url", ""),
                metadata=metadata,
                crawled_at=datetime.fromisoformat(metadata.get("crawled_at", datetime.now().isoformat())),
                category="code",
            ))

        return crawl_results

    def stats(self) -> dict:
        count = self.collection.count()
        return {
            "total_documents": count,
            "sources": list(set(
                meta["source"] 
                for meta in self.collection.get()["metadatas"]
            )) if count > 0 else []
        }
