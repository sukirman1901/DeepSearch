"""
Websets — Named containers of entity items with HTML-based enrichment.
No paid APIs — uses httpx + BeautifulSoup for page scraping.
"""
import json
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from crawlers.base import CrawlResult


@dataclass
class WebsetItem:
    """Entity in a webset."""
    id: str = ""
    title: str = ""
    url: str = ""
    description: str = ""
    source: str = ""
    properties: dict = field(default_factory=dict)
    enriched: bool = False
    added_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:8]
        if not self.added_at:
            self.added_at = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)


@dataclass
class WebsetContainer:
    """Named collection of items."""
    id: str = ""
    name: str = ""
    description: str = ""
    items: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:8]
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "items": [i.to_dict() if hasattr(i, "to_dict") else i for i in self.items],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Enricher:
    """Extract structured data from URLs via HTML scraping."""

    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    SOCIAL_DOMAINS = {"twitter.com", "x.com", "github.com", "linkedin.com", "facebook.com", "instagram.com"}

    def __init__(self):
        self.client = httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "DeepSearch/1.0"},
        )

    def enrich(self, url: str) -> dict:
        """Fetch URL and extract structured fields."""
        props = {}
        try:
            resp = self.client.get(url)
            if resp.status_code != 200:
                return props

            soup = BeautifulSoup(resp.text, "html.parser")

            # Title
            title_tag = soup.find("title")
            if title_tag:
                props["page_title"] = title_tag.get_text(strip=True)

            # Description
            desc_tag = soup.find("meta", attrs={"name": "description"})
            if desc_tag and desc_tag.get("content"):
                props["page_description"] = desc_tag["content"][:300]

            # Open Graph
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                props["og_description"] = og_desc["content"][:300]

            # Emails
            text = soup.get_text()
            emails = list(set(self.EMAIL_REGEX.findall(text)))
            if emails:
                props["emails"] = emails[:5]

            # Social links
            social = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                for domain in self.SOCIAL_DOMAINS:
                    if domain in href:
                        social.append(href)
                        break
            if social:
                props["social_links"] = list(set(social))[:10]

            # Technologies (script sources)
            scripts = []
            for script in soup.find_all("script", src=True):
                src = script["src"]
                for tech in ["react", "vue", "angular", "next", "nuxt", "svelte"]:
                    if tech in src.lower():
                        scripts.append(tech)
            if scripts:
                props["technologies"] = list(set(scripts))

        except Exception:
            pass

        return props


class WebsetManager:
    """Manage webset containers with items and enrichment."""

    def __init__(self, data_file=None):
        if data_file is None:
            data_file = os.path.join(os.path.dirname(__file__), "..", "data", "websets.json")
        self.data_file = data_file
        self.containers: dict[str, WebsetContainer] = {}
        self.enricher = Enricher()
        self._load()

    def _load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file) as f:
                    data = json.load(f)
                for c_data in data.get("containers", []):
                    items = [WebsetItem(**i) for i in c_data.get("items", [])]
                    container = WebsetContainer(
                        id=c_data["id"],
                        name=c_data["name"],
                        description=c_data.get("description", ""),
                        items=items,
                        created_at=c_data.get("created_at", ""),
                        updated_at=c_data.get("updated_at", ""),
                    )
                    self.containers[container.id] = container
            except Exception:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        data = {
            "containers": [c.to_dict() for c in self.containers.values()]
        }
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)

    def create_container(self, name: str, description: str = "") -> WebsetContainer:
        container = WebsetContainer(name=name, description=description)
        self.containers[container.id] = container
        self._save()
        return container

    def delete_container(self, container_id: str) -> bool:
        if container_id in self.containers:
            del self.containers[container_id]
            self._save()
            return True
        return False

    def list_containers(self) -> list[dict]:
        return [
            {"id": c.id, "name": c.name, "description": c.description,
             "item_count": len(c.items), "created_at": c.created_at}
            for c in self.containers.values()
        ]

    def get_container(self, container_id: str) -> WebsetContainer | None:
        return self.containers.get(container_id)

    def add_item(self, container_id: str, title: str, url: str,
                 description: str = "", source: str = "") -> WebsetItem | None:
        container = self.containers.get(container_id)
        if not container:
            return None

        # Skip duplicates
        for existing in container.items:
            if existing.url == url:
                return None

        item = WebsetItem(title=title, url=url, description=description, source=source)
        container.items.append(item)
        container.updated_at = datetime.now().isoformat()
        self._save()
        return item

    def add_items_from_search(self, container_id: str, results: list[CrawlResult]) -> int:
        """Add CrawlResults as items. Returns count added."""
        container = self.containers.get(container_id)
        if not container:
            return 0

        existing_urls = {item.url for item in container.items}
        added = 0
        for r in results:
            if r.url in existing_urls:
                continue
            item = WebsetItem(
                title=r.title or "",
                url=r.url or "",
                description=(r.content or "")[:200],
                source=r.source or "",
            )
            container.items.append(item)
            existing_urls.add(r.url)
            added += 1

        if added:
            container.updated_at = datetime.now().isoformat()
            self._save()
        return added

    def remove_item(self, container_id: str, item_id: str) -> bool:
        container = self.containers.get(container_id)
        if not container:
            return False
        for i, item in enumerate(container.items):
            if item.id == item_id:
                container.items.pop(i)
                container.updated_at = datetime.now().isoformat()
                self._save()
                return True
        return False

    def list_items(self, container_id: str) -> list[dict]:
        container = self.containers.get(container_id)
        if not container:
            return []
        return [item.to_dict() for item in container.items]

    async def enrich_item(self, container_id: str, item_id: str) -> WebsetItem | None:
        container = self.containers.get(container_id)
        if not container:
            return None
        for item in container.items:
            if item.id == item_id:
                props = self.enricher.enrich(item.url)
                item.properties.update(props)
                item.enriched = True
                container.updated_at = datetime.now().isoformat()
                self._save()
                return item
        return None

    async def enrich_all(self, container_id: str, progress_callback=None) -> dict:
        """Enrich all un-enriched items. Returns dict with count and details."""
        container = self.containers.get(container_id)
        if not container:
            return {"count": 0, "items": []}

        results = []
        for item in container.items:
            if not item.enriched and item.url:
                if progress_callback:
                    progress_callback(f"Enriching: {item.title[:50]}...")
                props = self.enricher.enrich(item.url)
                item.properties.update(props)
                item.enriched = True
                results.append({
                    "item_id": item.id,
                    "title": item.title,
                    "url": item.url,
                    "props": list(props.keys()),
                })

        if results:
            container.updated_at = datetime.now().isoformat()
            self._save()
        return {"count": len(results), "items": results}
