"""Diagnostics tools — log bundling and health summary for support."""
from __future__ import annotations

import json
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from ....core.paths import BASE_DIR, LOG_DIR
from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel

_BOOT = time.time()


class BundleLogsTool(Tool):
    name = "bundle_logs"
    description = ("Zip all runtime logs and crash reports into one "
                   "shareable archive for bug reports.")
    risk_level = ToolRiskLevel.READ_ONLY
    params: list = []

    def run(self, **_: Any) -> ToolResult:
        if not LOG_DIR.exists():
            return ToolResult(ok=False, output="No logs directory yet")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out = BASE_DIR / f"hinata-logs-{stamp}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(LOG_DIR.glob("*.log*")):
                z.write(f, arcname=f.name)
            for f in sorted(LOG_DIR.glob("crash-*.json")):
                z.write(f, arcname=f.name)
        size_mb = out.stat().st_size / (1024 * 1024)
        return ToolResult(ok=True, output=(
            f"Created {out.name} ({size_mb:.1f} MB). Contains runtime logs "
            "and crash reports only - never chat content."), data={
                "archive": str(out), "size_mb": round(size_mb, 2)})


class HealthSummaryTool(Tool):
    name = "get_health_summary"
    description = ("Compact runtime status: engine reachability, model, "
                   "log/crash counts, and uptime.")
    risk_level = ToolRiskLevel.READ_ONLY
    params: list = []

    def run(self, **_: Any) -> ToolResult:
        from ....core.config import MODEL_NAME, model_endpoint
        engine = "unreachable"
        try:
            with urllib.request.urlopen(
                    f"{model_endpoint().rstrip('/')}/models", timeout=4) as r:
                n = len(json.loads(r.read()).get("data", []))
                engine = f"online ({n} models)"
        except Exception:
            pass
        crashes = len(list(LOG_DIR.glob("crash-*.json"))) if LOG_DIR.exists() else 0
        logs = len(list(LOG_DIR.glob("*.log*"))) if LOG_DIR.exists() else 0
        return ToolResult(ok=True, output=(
            f"engine: {engine}; model: {MODEL_NAME}; log files: {logs}; "
            f"crash reports: {crashes}; uptime: {int(time.time() - _BOOT)}s"),
            data={"engine": engine, "model": MODEL_NAME,
                  "crash_reports": crashes, "uptime_s": int(time.time() - _BOOT)})
