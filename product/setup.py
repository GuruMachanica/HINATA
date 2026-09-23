"""HINATA local build & first-run setup.

Two modes:
  python product/setup.py build   — build frontend + bundle models + exe
  python product/setup.py doctor  — verify this machine can run HINATA
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLED = ROOT / "product" / "bundled-models"
GGUF_SOURCES = {
    "hinata-omni-q4km.gguf": ROOT / "models-gguf" / "huihui-q4km.gguf",
    "hinata-omni-mmproj.gguf": ROOT / "models-gguf" / "mmproj-Q8.gguf",
}


def _run(cmd: list, **kw) -> int:
    print(">", " ".join(map(str, cmd)))
    return subprocess.call(map(str, cmd), cwd=ROOT, **kw)


def stage_models() -> bool:
    """Copy local GGUFs into the bundling dir (skipped in CI — workflow downloads)."""
    BUNDLED.mkdir(exist_ok=True)
    ok = True
    for name, src in GGUF_SOURCES.items():
        dst = BUNDLED / name
        if dst.exists():
            continue
        if src.exists():
            print(f"staging {name} ({src.stat().st_size / 1e9:.2f} GB)...")
            shutil.copyfile(src, dst)
        else:
            print(f"MISSING: {src}")
            ok = False
    return ok


def build() -> int:
    print("== HINATA product build ==")
    if _run(["python", "-m", "pip", "install", "-r", "requirements.txt",
             "pyinstaller"]) != 0:
        return 1
    if not (ROOT / "frontend" / "dist").is_dir():
        if _run(["npm", "install"], cwd=ROOT / "frontend") != 0:
            return 1
        if _run(["npm", "run", "build"], cwd=ROOT / "frontend") != 0:
            return 1
    if not stage_models():
        print("model files missing — exe will build WITHOUT the bundled brain")
    if _run(["python", "-m", "PyInstaller", "product/hinata-backend.spec",
             "--noconfirm"]) != 0:
        return 1
    exe = ROOT / "dist" / "hinata-backend.exe"
    print(f"\nOK: {exe} ({exe.stat().st_size / 1e9:.2f} GB)" if exe.exists()
          else "\nBUILD FAILED")
    return 0 if exe.exists() else 1


def doctor() -> int:
    print("== HINATA environment doctor ==")
    checks = [
        ("python", [sys.executable, "--version"]),
        ("ollama", ["ollama", "--version"]),
        ("node", ["node", "--version"]),
    ]
    bad = 0
    for name, cmd in checks:
        try:
            out = subprocess.run(cmd, capture_output=True, text=True)
            print(f"  [OK] {name}: {out.stdout.strip() or out.stderr.strip()}")
        except FileNotFoundError:
            print(f"  [!!] {name}: NOT FOUND")
            bad += 1
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3)
        print("  [OK] ollama server: reachable")
    except Exception:
        print("  [!!] ollama server: not running")
        bad += 1
    print("\nResult:", "READY" if bad == 0 else f"{bad} problem(s) — fix above")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "doctor"
    sys.exit(build() if mode == "build" else doctor())
