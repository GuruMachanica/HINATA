"""REST routes — health, knowledge graph, memory, TTS."""
from __future__ import annotations

from typing import Callable, Dict

from fastapi import APIRouter, HTTPException, Query, Response

from ...core.base_feature import get


def build_api_router(tts_bytes: Callable[[str], bytes | None]) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health() -> Dict:
        from ...features.brain import BrainFeature
        from ...features.memory import MemoryFeature
        from ...features.knowledge import KnowledgeFeature
        brain = get(BrainFeature.name)
        return {
            "status": "online", "companion": "HINATA",
            "model": brain.engine.engine_model() if hasattr(brain.engine, "engine_model") else "hinata-brain",
            "memory": get(MemoryFeature.name).stats(),
            "kg": get(KnowledgeFeature.name).summary(),
        }

    @router.get("/kg/graph")
    def kg_graph(limit: int = Query(default=200, ge=1, le=200)) -> Dict:
        from ...features.knowledge import KnowledgeFeature
        store = get(KnowledgeFeature.name).store
        safe_limit = max(1, min(limit, 200))
        return {"nodes": store.search("", limit=safe_limit), "edges": store.related("", limit=safe_limit)}

    @router.get("/kg/summary")
    def kg_summary() -> Dict:
        from ...features.knowledge import KnowledgeFeature
        return get(KnowledgeFeature.name).summary()

    @router.get("/kg/search")
    def kg_search(term: str = Query(..., min_length=1, max_length=100), limit: int = Query(default=20, ge=1, le=50)) -> Dict:
        from ...features.knowledge import KnowledgeFeature
        safe_limit = max(1, min(limit, 50))
        return {"term": term, "results": get(KnowledgeFeature.name).store.search(term, safe_limit)}

    @router.get("/kg/facts")
    def kg_facts(limit: int = Query(default=30, ge=1, le=100)) -> Dict:
        from ...features.knowledge import KnowledgeFeature
        safe_limit = max(1, min(limit, 100))
        return {"facts": get(KnowledgeFeature.name).store.stated_facts(safe_limit)}

    @router.get("/memory/search")
    def memory_search(term: str = Query(..., min_length=1, max_length=100), limit: int = Query(default=10, ge=1, le=50)) -> Dict:
        from ...features.memory import MemoryFeature
        safe_limit = max(1, min(limit, 50))
        return {"term": term, "results": get(MemoryFeature.name).store.search(term, safe_limit)}

    @router.get("/memory/recent")
    def memory_recent(limit: int = Query(default=20, ge=1, le=100)) -> Dict:
        from ...features.memory import MemoryFeature
        safe_limit = max(1, min(limit, 100))
        return {"turns": get(MemoryFeature.name).store.recent(safe_limit)}

    @router.get("/tts")
    def tts(text: str = Query(..., min_length=1, max_length=500)) -> Response:
        clean = text.strip()
        if not clean:
            raise HTTPException(status_code=400, detail="text cannot be empty")
        if len(clean) > 500:
            raise HTTPException(status_code=400, detail="text exceeds 500 characters limit")
        audio = tts_bytes(clean)
        if not audio:
            raise HTTPException(status_code=503, detail="tts_failed")
        return Response(content=audio, media_type="audio/mpeg")

    return router
