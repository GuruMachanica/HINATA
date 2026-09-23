"""App/URL launcher tool — opens desktop apps and websites."""
from __future__ import annotations

import os
import subprocess
import webbrowser
from typing import Any

from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel

_EXECUTABLE_SUFFIXES = (".exe", ".bat", ".cmd", ".ps1", ".txt", ".py")
_TLD_SUFFIXES = (".com", ".org", ".net", ".io", ".dev", ".edu", ".gov")

APP_ALIASES = {
    "spotify": "spotify:",
    "steam": "steam:",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "code": "code",
    "vscode": "code",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "settings": "ms-settings:",
    "terminal": "wt.exe",
}


def _looks_like_url(t: str) -> bool:
    if t.startswith(("http://", "https://", "www.")):
        return True
    if "." not in t or t.endswith(_EXECUTABLE_SUFFIXES):
        return False
    return "/" in t or t.endswith(_TLD_SUFFIXES)


class OpenAppOrUrlTool(Tool):
    name = "open_app_or_url"
    description = (
        "Open a desktop application or website/URL in the user's environment. "
        "Supports apps like Chrome, Spotify, Steam, Calculator, Notepad, VS Code, Discord, "
        "File Explorer, or websites like https://youtube.com, https://google.com, https://github.com."
    )
    risk_level = ToolRiskLevel.DANGEROUS
    params = [
        ToolParam("target", "string",
                  "application name (e.g. 'chrome', 'spotify', 'calc') or web URL",
                  required=True, min_len=1, max_len=300),
    ]

    def run(self, target: str = "", **_: Any) -> ToolResult:
        if not target or not target.strip():
            return ToolResult(ok=False, output="missing target to open")

        t = target.strip()
        if _looks_like_url(t):
            return self._open_url(t)
        return self._open_app(t, target)

    @staticmethod
    def _open_url(t: str) -> ToolResult:
        url = t if t.startswith(("http://", "https://")) else f"https://{t}"
        try:
            webbrowser.open(url)
            return ToolResult(ok=True, output=f"opened website in browser: {url}")
        except Exception as exc:
            return ToolResult(ok=False, output=f"failed to open URL '{url}': {exc}")

    @staticmethod
    def _open_app(t: str, original: str) -> ToolResult:
        cmd_target = APP_ALIASES.get(t.lower(), t)

        try:
            os.startfile(cmd_target)  # noqa: S606 - Windows shell launcher
            return ToolResult(ok=True, output=f"opened application: {original}")
        except Exception:
            pass

        try:
            subprocess.Popen(f'start "" "{cmd_target}"', shell=True)
            return ToolResult(ok=True, output=f"launched application: {original}")
        except Exception as exc:
            return ToolResult(ok=False, output=f"failed to launch '{original}': {exc}")
