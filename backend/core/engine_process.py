"""Engine server process helpers — extract, launch, health-check."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from .paths import BUNDLE_DIR, BASE_DIR

log = logging.getLogger("hinata.engine")


def engine_health(base_url: str, timeout: float = 2.0) -> bool:
    """True when a llama-server answers /health with status ok."""
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=timeout) as r:
            return json.loads(r.read()).get("status") == "ok"
    except Exception:
        return False


def wait_healthy(base_url: str, deadline_s: float) -> bool:
    """Poll /health until the engine is up or the deadline passes."""
    end = time.time() + deadline_s
    while time.time() < end:
        if engine_health(base_url):
            return True
        time.sleep(2)
    return False


def extract_engine() -> Path | None:
    """Copy the bundled engine beside the running exe (one-file exe can't exec
    in-place). BASE_DIR is used instead of AppData because Windows blocks
    unsigned exes spawned from some AppData locations (0xC0000135).

    Returns the path to llama-server.exe, or None when not bundled.
    """
    src = BUNDLE_DIR / "engine"
    if not src.exists():
        return None
    dst = BASE_DIR / "engine"
    if dst.resolve() == src.resolve():
        return dst / "llama-server.exe"  # dev mode: already on disk
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        target = dst / f.name
        if not target.exists() or target.stat().st_size != f.stat().st_size:
            shutil.copyfile(f, target)
    return dst / "llama-server.exe"


def launch(server_exe: Path, model: Path, mmproj: Path, port: int) -> subprocess.Popen:
    """Start llama-server with HINATA's tuned sampling parameters."""
    cmd = [
        str(server_exe),
        "-m", str(model),
        "--mmproj", str(mmproj),
        "--port", str(port),
        "-ngl", "99", "-c", "16384",
        "--temp", "0.5", "--repeat-penalty", "1.2",
        "--presence-penalty", "1.5", "-np", "2",
    ]
    log.info("engine: launching llama-server on :%d ...", port)
    log_path = BASE_DIR / "engine.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_f = open(log_path, "w", encoding="utf-8")  # engine writes its own boot log
    return subprocess.Popen(
        cmd, stdout=log_f, stderr=subprocess.STDOUT, cwd=str(server_exe.parent),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def stop(proc: subprocess.Popen | None) -> None:
    """Terminate the engine process gracefully, then kill if needed."""
    if not proc:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
