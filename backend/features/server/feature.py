"""ServerFeature — assembles the FastAPI application."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
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
        self.app.add_api_websocket_route("/ws", self._ws_endpoint)
        self.app.add_api_websocket_route("/", self._ws_endpoint)
        @self.app.get("/favicon.ico", include_in_schema=False)
        async def _favicon() -> Response:
            return Response(status_code=204)
        self._mount_assets()

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
        origin = ws.headers.get("origin", "")
        if origin:
            allowed = (
                origin.startswith("http://localhost")
                or origin.startswith("https://localhost")
                or origin.startswith("http://127.0.0.1")
                or origin.startswith("https://127.0.0.1")
                or origin.startswith("vscode-webview://")
                or origin.startswith("app://")
                or origin.startswith("file://")
            )
            if not allowed:
                self.log.warning("blocked unauthorized WebSocket origin: %s", origin)
                await ws.close(code=4403, reason="unauthorized origin")
                return

        from ...core.config import AUTH_TOKEN
        if AUTH_TOKEN:
            token = ws.query_params.get("token") or ws.headers.get("authorization", "").replace("Bearer ", "")
            if token != AUTH_TOKEN:
                self.log.warning("blocked WebSocket with invalid token")
                await ws.close(code=4401, reason="unauthorized token")
                return

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
                    import asyncio
                    from ...features.voice import VoiceFeature
                    from ...core.base_feature import get
                    text = (msg.get("payload") or {}).get("text", "")
                    voice = get(VoiceFeature.name)
                    if voice and text:
                        audio = await asyncio.to_thread(voice.synthesize, text)
                        if audio:
                            await conn.send("speech_chunk", {"text": text, "audio": audio})
        except (WebSocketDisconnect, Exception):
            self.log.info("client disconnected")
