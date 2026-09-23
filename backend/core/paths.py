"""Runtime path resolution — works from source tree AND frozen PyInstaller exe.

When frozen (sys.frozen), resources live in the bundle (sys._MEIPASS) and
mutable data (db, logs) lives next to the exe so the app is self-contained
and portable.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _base() -> Path:
    """Directory containing the running program (exe dir when frozen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def _bundle() -> Path:
    """Read-only resources bundled inside the exe (PyInstaller _MEIPASS)."""
    return Path(getattr(sys, "_MEIPASS", _base()))


# Mutable data lives next to the exe (or project root from source)
BASE_DIR = _base()
BUNDLE_DIR = _bundle()

DB_PATH = BASE_DIR / "hinata.db"
LOG_DIR = BASE_DIR / "logs"

# Read-only assets: bundled in the exe, falling back to source tree
SOUL_PATH = BUNDLE_DIR / "config" / "SOUL.md"
if not SOUL_PATH.exists():
    SOUL_PATH = BASE_DIR / "hermes-core" / "config" / "SOUL.md"

NEURAL_TTS_PY = BUNDLE_DIR / "voice" / "neural_tts.py"
if not NEURAL_TTS_PY.exists():
    NEURAL_TTS_PY = BASE_DIR / "voice" / "neural_tts.py"

FRONTEND_DIST = BUNDLE_DIR / "frontend_dist"
if not FRONTEND_DIST.exists():
    FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

VRM_ASSETS = BUNDLE_DIR / "models"
if not VRM_ASSETS.exists():
    VRM_ASSETS = BASE_DIR / "shell-bella" / "models"

# Hermes agent is imported as python source; bundled via hiddenimports when
# frozen, or present in the source tree in dev.
HERMES_DIR = BUNDLE_DIR / "hermes-agent"
if not HERMES_DIR.exists():
    HERMES_DIR = BASE_DIR / "hermes-agent"
