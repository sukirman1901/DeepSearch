"""Tests for Websets — containers, items, enrichment."""
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from search.websets import WebsetManager, WebsetItem, WebsetContainer, Enricher
from crawlers.base import CrawlResult
from datetime import datetime


@pytest.fixture
def manager(tmp_path):
    return WebsetManager(data_file=str(tmp_path / "websets.json"))


@pytest.fixture
def container(manager):
    return manager.create_container("Test Webset", "A test container")


def _make_crawl_result(title, url, content="content", source="web"):
    return CrawlResult(
        source=source, title=title, content=content, url=url,
        crawled_at=datetime.now(), score=0.5,
    )


class TestCreateContainer:
    def test_create(self, manager):
        c = manager.create_container("My List", "Companies")
        assert c.name == "My List"
        assert c.description == "Companies"
        assert len(c.id) == 8

    def test_list_containers(self, manager):
        manager.create_container("A")
        manager.create_container("B")
        containers = manager.list_containers()
        assert len(containers) == 2
        names = [c["name"] for c in containers]
        assert "A" in names
        assert "B" in names


class TestAddItem:
    def test_add_item(self, manager, container):
        item = manager.add_item(container.id, "FastAPI", "https://fastapi.tiangolo.com")
        assert item is not None
        assert item.title == "FastAPI"
        assert len(manager.list_items(container.id)) == 1

    def test_duplicate_url_skipped(self, manager, container):
        manager.add_item(container.id, "A", "https://a.com")
        dup = manager.add_item(container.id, "A2", "https://a.com")
        assert dup is None
        assert len(manager.list_items(container.id)) == 1

    def test_add_items_from_search(self, manager, container):
        results = [
            _make_crawl_result("A", "https://a.com"),
            _make_crawl_result("B", "https://b.com"),
            _make_crawl_result("C", "https://c.com"),
        ]
        added = manager.add_items_from_search(container.id, results)
        assert added == 3
        assert len(manager.list_items(container.id)) == 3

    def test_add_items_skips_duplicates(self, manager, container):
        manager.add_item(container.id, "Existing", "https://existing.com")
        results = [_make_crawl_result("New", "https://existing.com")]
        added = manager.add_items_from_search(container.id, results)
        assert added == 0


class TestRemoveItem:
    def test_remove_item(self, manager, container):
        item = manager.add_item(container.id, "X", "https://x.com")
        removed = manager.remove_item(container.id, item.id)
        assert removed is True
        assert len(manager.list_items(container.id)) == 0

    def test_remove_invalid_id(self, manager, container):
        removed = manager.remove_item(container.id, "nonexistent")
        assert removed is False


class TestDeleteContainer:
    def test_delete(self, manager, container):
        deleted = manager.delete_container(container.id)
        assert deleted is True
        assert len(manager.list_containers()) == 0

    def test_delete_invalid_id(self, manager):
        deleted = manager.delete_container("nonexistent")
        assert deleted is False


class TestPersistence:
    def test_survives_reload(self, tmp_path):
        path = str(tmp_path / "websets.json")
        m1 = WebsetManager(data_file=path)
        c = m1.create_container("Persist")
        m1.add_item(c.id, "Item", "https://item.com")

        m2 = WebsetManager(data_file=path)
        containers = m2.list_containers()
        assert len(containers) == 1
        assert containers[0]["name"] == "Persist"
        assert containers[0]["item_count"] == 1


class TestEnricher:
    @pytest.mark.asyncio
    async def test_enrich_extracts_emails(self, manager, container):
        item = manager.add_item(container.id, "Ex", "https://example.com")
        # Mock the enricher's enrich method
        manager.enricher.enrich = MagicMock(return_value={
            "emails": ["contact@example.com", "info@example.com"],
            "page_title": "Example",
        })
        enriched = await manager.enrich_item(container.id, item.id)
        assert enriched.properties["emails"] == ["contact@example.com", "info@example.com"]
        assert enriched.enriched is True

    @pytest.mark.asyncio
    async def test_enrich_extracts_social(self, manager, container):
        item = manager.add_item(container.id, "GH", "https://github.com/example")
        manager.enricher.enrich = MagicMock(return_value={
            "social_links": ["https://github.com/example"],
            "technologies": ["react", "next"],
        })
        enriched = await manager.enrich_item(container.id, item.id)
        assert "https://github.com/example" in enriched.properties["social_links"]
        assert "react" in enriched.properties["technologies"]

    @pytest.mark.asyncio
    async def test_enrich_all(self, manager, container):
        manager.enricher.enrich = MagicMock(return_value={"page_title": "Test"})
        manager.add_item(container.id, "A", "https://a.com")
        manager.add_item(container.id, "B", "https://b.com")
        result = await manager.enrich_all(container.id)
        assert result["count"] == 2
        items = manager.list_items(container.id)
        assert all(i["enriched"] for i in items)

    @pytest.mark.asyncio
    async def test_enrich_item_invalid_container(self, manager):
        result = await manager.enrich_item("nonexistent", "item_id")
        assert result is None
