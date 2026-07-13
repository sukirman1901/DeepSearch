import httpx
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult


class TwitterCrawler(BaseCrawler):
    def __init__(self):
        self.nitter_instances = [
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
            "https://nitter.woodland.cafe"
        ]

    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        for instance in self.nitter_instances:
            try:
                url = f"{instance}/search"
                params = {"f": "tweets", "q": query}

                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=10.0)
                    response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                tweets = soup.find_all("div", class_="timeline-item")

                results = []
                for tweet in tweets[:max_results]:
                    content_elem = tweet.find("div", class_="tweet-content")
                    username_elem = tweet.find("a", class_="username")

                    results.append(CrawlResult(
                        source="twitter",
                        title=username_elem.string if username_elem else "",
                        content=content_elem.get_text(strip=True) if content_elem else "",
                        url=f"https://twitter.com{username_elem['href']}" if username_elem else "",
                        metadata={"instance": instance}
                    ))
                return results
            except Exception:
                continue
        return []
