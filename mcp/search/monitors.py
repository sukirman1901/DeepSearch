"""Monitors API — recurring search monitors with cross-run deduplication."""
import json
import os
import uuid
from datetime import datetime
from typing import Optional

from crawlers.base import CrawlResult


class MonitorManager:
    """Manage recurring search monitors with cross-run deduplication."""

    def __init__(self, data_file: str = "data/monitors.json"):
        self.data_file = data_file
        self.monitors: dict = {}
        self._load()

    def create_monitor(
        self,
        query: str,
        sources: Optional[list[str]] = None,
        max_results: int = 20,
    ) -> str:
        """Create a new monitor. Returns monitor ID."""
        monitor_id = str(uuid.uuid4())[:8]
        self.monitors[monitor_id] = {
            "query": query,
            "sources": sources or [],
            "max_results": max_results,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0,
            "seen_urls": [],
        }
        self._save()
        return monitor_id

    def list_monitors(self) -> list[dict]:
        """List all monitors with stats."""
        result = []
        for mid, m in self.monitors.items():
            result.append({
                "id": mid,
                "query": m["query"],
                "sources": m["sources"],
                "created_at": m["created_at"],
                "last_run": m["last_run"],
                "run_count": m["run_count"],
                "seen_count": len(m["seen_urls"]),
            })
        return result

    async def run_monitor(self, monitor_id: str, crawler_manager) -> list[CrawlResult]:
        """Run a monitor. Returns only NEW results since last run."""
        if monitor_id not in self.monitors:
            return []

        monitor = self.monitors[monitor_id]
        results = await crawler_manager.crawl_all(
            monitor["query"],
            max_results_per_source=monitor["max_results"],
            sources=monitor["sources"] or None,
            generate_variations=False,
        )

        seen = set(monitor["seen_urls"])
        new_results = [r for r in results if r.url not in seen]

        for r in new_results:
            monitor["seen_urls"].append(r.url)

        monitor["run_count"] += 1
        monitor["last_run"] = datetime.now().isoformat()
        self._save()

        return new_results

    def delete_monitor(self, monitor_id: str) -> bool:
        """Delete a monitor. Returns True if existed."""
        if monitor_id in self.monitors:
            del self.monitors[monitor_id]
            self._save()
            return True
        return False

    def _load(self):
        """Load monitors from JSON file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    self.monitors = data.get("monitors", {})
        except (json.JSONDecodeError, IOError):
            self.monitors = {}

    def _save(self):
        """Save monitors to JSON file."""
        os.makedirs(os.path.dirname(self.data_file) or ".", exist_ok=True)
        with open(self.data_file, "w") as f:
            json.dump({"monitors": self.monitors}, f, indent=2)
