from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from search.websets import WebsetManager
from search.engine import SearchEngine
from search.categories import detect_category

app = FastAPI(title="Deep Search API Playground")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

webset_manager = WebsetManager()
search_engine = SearchEngine()

class WebsetCreateRequest(BaseModel):
    query: str
    count: int = 10
    entity_type: Optional[str] = None
    enrichments: Optional[List[str]] = []
    criteria: Optional[str] = None

@app.post("/api/websets")
async def create_webset(req: WebsetCreateRequest, background_tasks: BackgroundTasks):
    container = webset_manager.create_container(name=f"Webset: {req.query}", description=req.criteria or "")
    
    # Run search
    results = search_engine.search(
        query=req.query,
        limit=req.count
    )
    
    # Add items to container
    webset_manager.add_items_from_search(container.id, results)
    
    # Trigger enrichments if any
    if req.enrichments:
        background_tasks.add_task(webset_manager.enrich_all, container.id)
        
    return {"id": container.id, "message": "Webset created", "items_found": len(results)}

@app.get("/api/websets")
def list_websets():
    return webset_manager.list_containers()

@app.get("/api/websets/{container_id}")
def get_webset(container_id: str):
    container = webset_manager.get_container(container_id)
    if not container:
        return {"error": "Not found"}
    items = webset_manager.list_items(container_id)
    return {"container": container.to_dict(), "items": items}
