"""
HINATA System Diagnostics Tool
Provides real-time hardware telemetry: GPU (Nvidia RTX 4050), RAM, and CPU stats.
Can be executed standalone or imported as a Hermes Agent tool/skill.
"""

import json
import subprocess
import shutil
import sys

def get_gpu_stats() -> dict:
    """Fetch NVIDIA GPU stats via nvidia-smi if available."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {"available": False, "error": "nvidia-smi not found in PATH"}

    try:
        cmd = [
            nvidia_smi,
            "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        gpus = []
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                gpus.append({
                    "name": parts[0],
                    "memory_total_mb": float(parts[1]),
                    "memory_used_mb": float(parts[2]),
                    "memory_free_mb": float(parts[3]),
                    "utilization_pct": float(parts[4]),
                    "temperature_c": float(parts[5])
                })
        return {"available": True, "gpus": gpus}
    except Exception as e:
        return {"available": False, "error": str(e)}

def get_system_memory() -> dict:
    """Fetch system RAM metrics using Windows system info via PowerShell or WMIC."""
    try:
        ps_cmd = (
            "Get-CimInstance Win32_OperatingSystem | "
            "Select-Object TotalVisibleMemorySize, FreePhysicalMemory | "
            "ConvertTo-Json"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            total_mb = round(data.get("TotalVisibleMemorySize", 0) / 1024, 1)
            free_mb = round(data.get("FreePhysicalMemory", 0) / 1024, 1)
            used_mb = round(total_mb - free_mb, 1)
            return {
                "total_ram_mb": total_mb,
                "used_ram_mb": used_mb,
                "free_ram_mb": free_mb,
                "used_pct": round((used_mb / total_mb) * 100, 1) if total_mb > 0 else 0
            }
    except Exception as e:
        return {"error": str(e)}
    return {"error": "Could not query memory"}

def get_system_snapshot() -> dict:
    """Combined diagnostics payload for HINATA companion cortex."""
    return {
        "gpu": get_gpu_stats(),
        "memory": get_system_memory(),
        "companion_status": "online"
    }

if __name__ == "__main__":
    snapshot = get_system_snapshot()
    print(json.dumps(snapshot, indent=2))
