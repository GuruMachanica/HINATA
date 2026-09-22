"""REST routes — health, knowledge graph, memory, TTS."""
from __future__ import annotations

from typing import Callable, Dict

from fastapi import APIRouter, HTTPException, Response

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
    def kg_graph(limit: int = 200) -> Dict:
        from ...features.knowledge import KnowledgeFeature
        store = get(KnowledgeFeature.name).store
        return {"nodes": store.search("", limit=limit), "edges": store.related("", limit=limit)}

    @router.get("/kg/summary")
    def kg_summary() -> Dict:
        from ...features.knowledge import KnowledgeFeature
        return get(KnowledgeFeature.name).summary()

    @router.get("/kg/search")
    def kg_search(term: str, limit: int = 20) -> Dict:
        from ...features.knowledge import KnowledgeFeature
        return {"term": term, "results": get(KnowledgeFeature.name).store.search(term, limit)}

    @router.get("/kg/facts")
    def kg_facts(limit: int = 30) -> Dict:
        from ...features.knowledge import KnowledgeFeature
        return {"facts": get(KnowledgeFeature.name).store.stated_facts(limit)}

    @router.get("/memory/search")
    def memory_search(term: str, limit: int = 10) -> Dict:
        from ...features.memory import MemoryFeature
        return {"term": term, "results": get(MemoryFeature.name).store.search(term, limit)}

    @router.get("/memory/recent")
    def memory_recent(limit: int = 20) -> Dict:
        from ...features.memory import MemoryFeature
        return {"turns": get(MemoryFeature.name).store.recent(limit)}

    @router.get("/tts")
    def tts(text: str) -> Response:
        audio = tts_bytes(text)
        if not audio:
            raise HTTPException(status_code=503, detail="tts_failed")
        return Response(content=audio, media_type="audio/mpeg")

    return router
