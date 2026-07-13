import chromadb
from crawlers.base import CrawlResult
from db.embeddings import EmbeddingModel


class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection("search_engine")
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

    def stats(self) -> dict:
        count = self.collection.count()
        return {
            "total_documents": count,
            "sources": list(set(
                meta["source"] 
                for meta in self.collection.get()["metadatas"]
            )) if count > 0 else []
        }
