from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CrawlResult:
    source: str
    title: str
    content: str
    url: str
    metadata: dict[str, Any] = field(default_factory=dict)
    crawled_at: datetime = field(default_factory=datetime.now)


class BaseCrawler(ABC):
    @abstractmethod
    async def crawl(self, query: str, max_results: int = 10) -> list[CrawlResult]:
        pass
