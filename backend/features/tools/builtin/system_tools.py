"""System awareness tools — clock, hardware info, battery."""
from __future__ import annotations

import datetime
import os
import platform
import shutil
import subprocess
from typing import Any, Tuple

from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel
from .app_launcher import OpenAppOrUrlTool  # noqa: F401  (re-exported for registration)


class CurrentTimeTool(Tool):
    name = "get_time"
    description = "Current local date, time, and timezone."
    risk_level = ToolRiskLevel.READ_ONLY
    params = []

    def run(self, **_: Any) -> ToolResult:
        now = datetime.datetime.now().astimezone()
        return ToolResult(ok=True, output=now.strftime("%A, %Y-%m-%d %H:%M:%S %Z"))


class SystemInfoTool(Tool):
    name = "get_system_info"
    description = "OS, CPU, RAM, disk, and GPU summary of this machine."
    risk_level = ToolRiskLevel.READ_ONLY
    params = []

    def run(self, **_: Any) -> ToolResult:
        python_env = f"{platform.python_implementation()} on {platform.system()} {platform.release()}"
        disk = shutil.disk_usage(os.path.abspath(os.sep))
        free_gb, total_gb = disk.free // (2**30), disk.total // (2**30)
        free_ratio = disk.free / disk.total if disk.total > 0 else 0.0

        lines = [
            f"OS: {platform.system()} {platform.release()} ({platform.machine()})",
            f"CPU: {platform.processor() or 'unknown'}",
            f"Disk: {free_gb}GB free / {total_gb}GB",
            f"Python: {python_env}",
        ]
        gpu_summary, gpu_temp_c = self._gpu()
        if gpu_summary:
            lines.append(f"GPU: {gpu_summary}")

        data = {
            "disk_free_gb": free_gb, "disk_total_gb": total_gb,
            "disk_free_ratio": round(free_ratio, 4),
            "gpu_temp_c": gpu_temp_c, "gpu": gpu_summary,
        }
        return ToolResult(ok=True, output="\n".join(lines), data=data)

    @staticmethod
    def _gpu() -> Tuple[str, int | None]:
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,temperature.gpu",
                 "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and out.stdout.strip():
                parts = [p.strip() for p in out.stdout.strip().splitlines()[0].split(",")]
                temp_c = None
                if len(parts) >= 4:
                    try:
                        temp_c = int(parts[3])
                    except ValueError:
                        pass
                return ",".join(parts), temp_c
            return "", None
        except Exception:
            return "", None


class BatteryTool(Tool):
    name = "get_battery"
    description = "Laptop battery percent and charging state."
    risk_level = ToolRiskLevel.READ_ONLY
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
                status = "charging" if len(values) > 1 and values[1] == "2" else "on battery"
                return ToolResult(ok=True, output=f"Battery: {values[0]}% ({status})")
        except Exception as exc:
            return ToolResult(ok=False, output=f"battery query failed: {exc}")
        return ToolResult(ok=False, output="no battery detected")
