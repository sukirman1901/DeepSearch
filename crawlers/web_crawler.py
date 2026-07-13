import httpx
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult

class WebCrawler(BaseCrawler):
    def __init__(self):
        self.client = httpx.Client(
            headers={"User-Agent": "Mozilla/5.0 (compatible; SearchEngine/1.0)"},
            follow_redirects=True,
            timeout=10.0
        )

    async def crawl(self, url: str, max_results: int = 1) -> list[CrawlResult]:
        try:
            response = self.client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            title = soup.title.string if soup.title else url
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            content = soup.get_text(separator="\n", strip=True)
            content = "\n".join(line for line in content.splitlines() if line.strip())
            
            return [CrawlResult(
                source="web",
                title=title,
                content=content[:5000],
                url=url,
                metadata={"status_code": response.status_code}
            )]
        except Exception as e:
            return [CrawlResult(
                source="web",
                title=f"Error: {url}",
                content=str(e),
                url=url,
                metadata={"error": str(e)}
            )]
