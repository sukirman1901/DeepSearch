"""Library registry for docs search - loads and validates library configs."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LibraryConfig:
    """Configuration for a single library's documentation."""
    id: str
    name: str
    docs_url: str
    start_paths: list[str]
    content_selector: str = "main"
    nav_selector: str = ""
    exclude_paths: list[str] = field(default_factory=list)
    include_paths: list[str] = field(default_factory=list)
    version_url_pattern: str = ""
    max_pages: int = 200
    ttl_hours: int = 168
    language: str = "en"


REQUIRED_FIELDS = ["name", "docs_url", "start_paths"]


class LibraryRegistry:
    """Loads and manages library configurations from JSON file."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.libraries: dict[str, LibraryConfig] = {}
        self._load()
    
    def _load(self):
        """Load and validate library configs from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Registry config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        
        libs = data.get("libraries", {})
        
        for lib_id, lib_data in libs.items():
            # Validate required fields
            missing = [field for field in REQUIRED_FIELDS if field not in lib_data]
            if missing:
                raise ValueError(
                    f"Library '{lib_id}' missing required fields: {', '.join(missing)}"
                )
            
            # Parse config
            config = LibraryConfig(
                id=lib_id,
                name=lib_data["name"],
                docs_url=lib_data["docs_url"],
                start_paths=lib_data.get("start_paths", []),
                content_selector=lib_data.get("content_selector", "main"),
                nav_selector=lib_data.get("nav_selector", ""),
                exclude_paths=lib_data.get("exclude_paths", []),
                include_paths=lib_data.get("include_paths", []),
                version_url_pattern=lib_data.get("version_url_pattern", ""),
                max_pages=lib_data.get("max_pages", 200),
                ttl_hours=lib_data.get("ttl_hours", 168),
                language=lib_data.get("language", "en"),
            )
            
            self.libraries[lib_id] = config
    
    def get_library(self, lib_id: str) -> Optional[LibraryConfig]:
        """Get library config by ID. Returns None if not found."""
        return self.libraries.get(lib_id)
    
    def list_libraries(self) -> list[str]:
        """List all available library IDs."""
        return list(self.libraries.keys())
    
    def get_all(self) -> dict[str, LibraryConfig]:
        """Get all library configs."""
        return self.libraries.copy()
