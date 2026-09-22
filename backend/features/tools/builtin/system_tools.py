"""System awareness tools — clock, hardware, processes."""
from __future__ import annotations

import datetime
import os
import platform
import shutil
import subprocess
import webbrowser
from typing import Any, Tuple

from ..base import Tool, ToolParam, ToolResult, ToolRiskLevel


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
        free_gb = disk.free // (2**30)
        total_gb = disk.total // (2**30)
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
            "disk_free_gb": free_gb,
            "disk_total_gb": total_gb,
            "disk_free_ratio": round(free_ratio, 4),
            "gpu_temp_c": gpu_temp_c,
            "gpu": gpu_summary,
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
                line = out.stdout.strip().splitlines()[0]
                temp_c = None
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    try:
                        temp_c = int(parts[3])
                    except ValueError:
                        pass
                return line, temp_c
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
                pct = values[0]
                status = "charging" if len(values) > 1 and values[1] == "2" else "on battery"
                return ToolResult(ok=True, output=f"Battery: {pct}% ({status})")
        except Exception as exc:
            return ToolResult(ok=False, output=f"battery query failed: {exc}")
        return ToolResult(ok=False, output="no battery detected")


class OpenAppOrUrlTool(Tool):
    name = "open_app_or_url"
    description = (
        "Open a desktop application or website/URL in the user's environment. "
        "Supports apps like Chrome, Spotify, Steam, Calculator, Notepad, VS Code, Discord, File Explorer, "
        "or websites like https://youtube.com, https://google.com, https://github.com."
    )
    risk_level = ToolRiskLevel.DANGEROUS
    params = [
        ToolParam("target", "string", "application name (e.g. 'chrome', 'spotify', 'calc') or web URL", required=True, min_len=1, max_len=300),
    ]

    def run(self, target: str = "", **_: Any) -> ToolResult:
        if not target or not target.strip():
            return ToolResult(ok=False, output="missing target to open")

        t = target.strip()

        # Handle URLs
        if t.startswith(("http://", "https://")) or t.startswith("www.") or (
            ("." in t) and not t.endswith((".exe", ".bat", ".cmd", ".ps1", ".txt", ".py"))
            and ("/" in t or t.endswith((".com", ".org", ".net", ".io", ".dev", ".edu", ".gov")))
        ):
            url = t if t.startswith(("http://", "https://")) else f"https://{t}"
            try:
                webbrowser.open(url)
                return ToolResult(ok=True, output=f"opened website in browser: {url}")
            except Exception as exc:
                return ToolResult(ok=False, output=f"failed to open URL '{url}': {exc}")

        # Windows known protocol / app aliases
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
        cmd_target = APP_ALIASES.get(t.lower(), t)

        # Native Windows os.startfile
        try:
            os.startfile(cmd_target)
            return ToolResult(ok=True, output=f"opened application: {target}")
        except Exception:
            pass

        # Subprocess fallback
        try:
            subprocess.Popen(f'start "" "{cmd_target}"', shell=True)
            return ToolResult(ok=True, output=f"launched application: {target}")
        except Exception as exc:
            return ToolResult(ok=False, output=f"failed to launch '{target}': {exc}")
