import pytest
import json
import tempfile
import os
from search.docs_registry import LibraryRegistry, LibraryConfig

def test_load_registry_from_file():
    """Test loading registry from JSON file."""
    config = {
        "version": "1.0",
        "libraries": {
            "react": {
                "name": "React",
                "docs_url": "https://react.dev",
                "start_paths": ["/reference", "/learn"],
                "content_selector": "main",
                "nav_selector": "aside a",
                "exclude_paths": ["/blog"],
                "include_paths": [],
                "max_pages": 200,
                "ttl_hours": 168
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        registry = LibraryRegistry(temp_path)
        lib = registry.get_library("react")
        
        assert lib is not None
        assert lib.id == "react"
        assert lib.name == "React"
        assert lib.docs_url == "https://react.dev"
        assert lib.start_paths == ["/reference", "/learn"]
        assert lib.content_selector == "main"
        assert lib.nav_selector == "aside a"
        assert lib.exclude_paths == ["/blog"]
        assert lib.max_pages == 200
        assert lib.ttl_hours == 168
    finally:
        os.unlink(temp_path)

def test_list_libraries():
    """Test listing all available libraries."""
    config = {
        "version": "1.0",
        "libraries": {
            "react": {"name": "React", "docs_url": "https://react.dev", "start_paths": []},
            "nextjs": {"name": "Next.js", "docs_url": "https://nextjs.org/docs", "start_paths": []}
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        registry = LibraryRegistry(temp_path)
        libs = registry.list_libraries()
        
        assert "react" in libs
        assert "nextjs" in libs
        assert len(libs) == 2
    finally:
        os.unlink(temp_path)

def test_get_library_not_found():
    """Test getting non-existent library returns None."""
    config = {"version": "1.0", "libraries": {}}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        registry = LibraryRegistry(temp_path)
        lib = registry.get_library("vue")
        
        assert lib is None
    finally:
        os.unlink(temp_path)

def test_validate_library_config():
    """Test that invalid configs raise errors."""
    config = {
        "version": "1.0",
        "libraries": {
            "bad-lib": {
                "name": "Bad Lib"
                # Missing required fields
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="docs_url"):
            LibraryRegistry(temp_path)
    finally:
        os.unlink(temp_path)
