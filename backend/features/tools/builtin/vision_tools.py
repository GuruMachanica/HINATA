"""Vision tools — HINATA sees the screen via Qwen-3-VL multimodal inference."""
from __future__ import annotations

import base64
import io
import json
import urllib.request
from typing import Any

from ....core.config import MODEL_API_KEY, VISION_MODEL, model_endpoint
from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel

try:
    import mss  # fast multi-monitor capture
except ImportError:
    mss = None

try:
    from PIL import Image
except ImportError:
    Image = None


def _grab_screen_jpeg_b64(monitor: int = 1) -> bytes | None:
    """Capture a monitor to a downscaled JPEG; returns raw JPEG bytes."""
    if mss is None or Image is None:
        return None
    with mss.mss() as sct:
        mon = sct.monitors[monitor] if monitor < len(sct.monitors) else sct.monitors[1]
        raw = sct.grab(mon)
    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    img.thumbnail((1024, 1024))  # keep the payload small for the VLM
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)
    return buf.getvalue()


def ask_vlm(question: str, jpeg_bytes: bytes) -> str:
    """Send image + question to the Qwen-3-VL endpoint (OpenAI-compatible)."""
    b64 = base64.b64encode(jpeg_bytes).decode()
    body = json.dumps({
        "model": VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": question},
            ],
        }],
        "max_tokens": 500, "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{model_endpoint().rstrip('/')}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {MODEL_API_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        msg = json.loads(resp.read().decode())["choices"][0]["message"]
    # Ollama's qwen3-vl parser may put the reply in 'content' OR 'thinking'
    # (the ablated model doesn't always emit clean <think> tags).
    text = msg.get("content") or ""
    if not text.strip():
        text = msg.get("reasoning_content") or msg.get("thinking") or ""
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


class SeeScreenTool(Tool):
    name = "see_screen"
    description = (
        "Look at the user's screen right now and answer a question about what is "
        "visible (apps, code, documents, videos, games). Use whenever the user "
        "asks what you see, to describe their screen, or needs visual help."
    )
    risk_level = ToolRiskLevel.READ_ONLY
    params = [
        ToolParam("question", "string",
                  "what to look for or describe on the screen",
                  required=True, min_len=1, max_len=400),
        ToolParam("monitor", "integer", "monitor number (1 = primary)",
                  required=False, min_val=1, max_val=4),
    ]

    def run(self, question: str = "", monitor: int = 1, **_: Any) -> ToolResult:
        if not question.strip():
            return ToolResult(ok=False, output="empty question")
        try:
            jpeg = _grab_screen_jpeg_b64(int(monitor or 1))
        except Exception as exc:
            return ToolResult(ok=False, output=f"screen capture failed: {exc}")
        if jpeg is None:
            return ToolResult(ok=False, output="vision unavailable: install mss + pillow")
        try:
            answer = ask_vlm(question.strip(), jpeg)
            return ToolResult(ok=True, output=f"Screen observation: {answer}",
                              data={"monitor": int(monitor or 1)})
        except Exception as exc:
            return ToolResult(ok=False, output=f"vision model failed: {exc}")
