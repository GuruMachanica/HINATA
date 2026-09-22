"""System awareness tools — clock, hardware, processes."""
from __future__ import annotations

import datetime
import platform
import shutil
import subprocess
from typing import Any

from ..base import Tool, ToolResult


class CurrentTimeTool(Tool):
    name = "get_time"
    description = "Current local date, time, and timezone."
    params = []

    def run(self, **_: Any) -> ToolResult:
        now = datetime.datetime.now().astimezone()
        return ToolResult(ok=True, output=now.strftime("%A, %Y-%m-%d %H:%M:%S %Z"))


class SystemInfoTool(Tool):
    name = "get_system_info"
    description = "OS, CPU, RAM, disk, and GPU summary of this machine."
    params = []

    def run(self, **_: Any) -> ToolResult:
        ram = f"{platform.python_implementation()} on {platform.system()} {platform.release()}"
        disk = shutil.disk_usage("/")
        lines = [
            f"OS: {platform.system()} {platform.release()} ({platform.machine()})",
            f"CPU: {platform.processor() or 'unknown'}",
            f"Disk: {disk.free // (2**30)}GB free / {disk.total // (2**30)}GB",
            f"Python: {ram}",
        ]
        gpu = self._gpu()
        if gpu:
            lines.append(f"GPU: {gpu}")
        return ToolResult(ok=True, output="\n".join(lines), data={"gpu": gpu})

    @staticmethod
    def _gpu() -> str:
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,temperature.gpu",
                 "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            return out.stdout.strip() if out.returncode == 0 else ""
        except Exception:
            return ""


class BatteryTool(Tool):
    name = "get_battery"
    description = "Laptop battery percent and charging state."
    params = []

    def run(self, **_: Any) -> ToolResult:
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WmiObject Win32_Battery).EstimatedChargeRemaining; "
                 "(Get-WmiObject Win32_Battery).BatteryStatus"],
                capture_output=True, text=True, timeout=8,
            )
            values = out.stdout.split()
            if values:
                pct, status = values[0], ("charging" if len(values) > 1 and values[1] == "2" else "on battery")
                return ToolResult(ok=True, output=f"Battery: {pct}% ({status})")
        except Exception as exc:
            return ToolResult(ok=False, output=f"battery query failed: {exc}")
        return ToolResult(ok=False, output="no battery detected")
