"""HINATA core configuration — single source of truth for paths and settings."""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
DB_PATH = BACKEND_DIR / "hinata.db"
HERMES_DIR = ROOT_DIR / "hermes-agent"
SOUL_PATH = ROOT_DIR / "hermes-core" / "config" / "SOUL.md"
NEURAL_TTS_PY = ROOT_DIR / "voice" / "neural_tts.py"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
VRM_ASSETS = ROOT_DIR / "shell-bella" / "models"

MODEL_ENDPOINT = os.getenv("HINATA_MODEL_ENDPOINT", "http://127.0.0.1:11434/v1")
MODEL_NAME = os.getenv("HINATA_MODEL_NAME", "hinata-brain")
MODEL_API_KEY = os.getenv("HINATA_MODEL_KEY", "ollama")

# Agentic tool-calling (in-prompt JSON protocol; works with non-tool models)
AGENTIC_MODE = os.getenv("HINATA_AGENTIC", "1") == "1"
MAX_TOOL_ROUNDS = int(os.getenv("HINATA_MAX_TOOL_ROUNDS", "4"))

# Proactivity
PROACTIVE_ENABLED = os.getenv("HINATA_PROACTIVE", "1") == "1"
PROACTIVE_MIN_INTERVAL_S = int(os.getenv("HINATA_PROACTIVE_INTERVAL", "600"))

LOG_LEVEL = os.getenv("HINATA_LOG_LEVEL", "INFO")
