"""
HINATA Local Model Client
Handles OpenAI-compatible HTTP inference calls to Ollama / local runtime.
"""

import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

def call_local_chat(
    prompt: str,
    system_prompt: str,
    endpoint: str,
    model: str,
    temperature: float = 0.7,
    timeout_secs: int = 120
) -> Dict[str, Any]:
    """Execute chat completion request to local OpenAI-compatible endpoint."""
    url = f"{endpoint}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "temperature": temperature
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_secs) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return {"success": True, "content": content}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"Connection error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Inference failure: {e}"}
