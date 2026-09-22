"""ServerFeature — assembles the FastAPI application."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from ...core.base_feature import BaseFeature, register
from ...core.config import FRONTEND_DIST, VRM_ASSETS
from .rest import build_api_router
from .state import ConnectionState
from .ws_handler import WSChatHandler


@register
class ServerFeature(BaseFeature):
    name = "server"

    def __init__(self) -> None:
        super().__init__()
        self.app = FastAPI(title="HINATA", version="3.0.0")
        self.chat: WSChatHandler | None = None

    def setup(self) -> None:
        from ...features.brain import BrainFeature
        from ...core.base_feature import get
        brain = get(BrainFeature.name)
        self.chat = WSChatHandler(self.bus, brain.think)
        self._mount_api()
        self._mount_assets()
        self.app.add_api_websocket_route("/ws", self._ws_endpoint)

    def _mount_api(self) -> None:
        from ...features.voice import VoiceFeature
        from ...core.base_feature import get
        voice: VoiceFeature = get(VoiceFeature.name)
        self.app.include_router(build_api_router(voice.audio_bytes))

    def _mount_assets(self) -> None:
        if VRM_ASSETS.exists():
            self.app.mount("/models", StaticFiles(directory=str(VRM_ASSETS)), name="models")
        if FRONTEND_DIST.exists():
            self.app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True),
                           name="frontend")

    async def _ws_endpoint(self, ws: WebSocket) -> None:
        await ws.accept()
        conn = ConnectionState(ws)
        await conn.send("connection_status", {"connected": True, "companion": "HINATA"})
        await conn.send("agent_state", {"state": conn.state})
        try:
            while True:
                msg = await ws.receive_json()
                if msg.get("type") == "chat":
                    await self.chat.handle_chat(conn, (msg.get("payload") or {}).get("query", ""))
                elif msg.get("type") == "tts_request":
                    from ...features.voice import VoiceFeature
                    from ...core.base_feature import get
                    text = (msg.get("payload") or {}).get("text", "")
                    audio = get(VoiceFeature.name).synthesize(text)
                    if audio:
                        await conn.send("speech_chunk", {"text": text, "audio": audio})
        except (WebSocketDisconnect, Exception):
            self.log.info("client disconnected")
