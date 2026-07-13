import subprocess
import json
from crawlers.base import BaseCrawler, CrawlResult


class YouTubeCrawler(BaseCrawler):
    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        try:
            search_url = f"ytsearch{max_results}:{query}"
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--flat-playlist",
                "--no-download",
                search_url,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return []

            results = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    data = json.loads(line)
                    results.append(
                        CrawlResult(
                            source="youtube",
                            title=data.get("title", ""),
                            content=data.get("description", "")[:2000],
                            url=f"https://youtube.com/watch?v={data.get('id', '')}",
                            metadata={
                                "author": data.get("uploader", ""),
                                "duration": data.get("duration", 0),
                                "view_count": data.get("view_count", 0),
                            },
                        )
                    )
            return results
        except Exception:
            return []
