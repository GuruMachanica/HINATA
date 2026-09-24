"""Logging + crash reporting — rotating file logs and crash dumps.

Every backend run writes rotating logs under logs/. Uncaught exceptions
land in logs/crash-*.json with full traceback + system context, so a user
can share the file directly for support.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import platform
import sys
import time
from pathlib import Path

from .paths import BASE_DIR, LOG_DIR

MAX_LOG_MB = 5
KEEP_CRASHES = 10


def setup_logging(level: str = "INFO") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "hinata.log", maxBytes=MAX_LOG_MB * 1024 * 1024,
        backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=level.upper(),
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler(sys.stdout)],
    )


def _prune_crashes(crash_dir: Path) -> None:
    crashes = sorted(crash_dir.glob("crash-*.json"))
    for old in crashes[:-KEEP_CRASHES]:
        old.unlink(missing_ok=True)


def write_crash_report(exc_type, exc_value, exc_tb) -> None:
    """Dump one crash report; never raises (safe inside excepthook)."""
    try:
        crash_dir = LOG_DIR
        crash_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        report = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": exc_type.__name__ if exc_type else "Unknown",
            "message": str(exc_value)[:2000],
            "traceback": _format_tb(exc_tb),
            "system": {
                "python": platform.python_version(),
                "os": f"{platform.system()} {platform.release()}",
                "machine": platform.machine(),
                "frozen": bool(getattr(sys, "frozen", False)),
            },
        }
        path = crash_dir / f"crash-{stamp}.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        _prune_crashes(crash_dir)
        print(f"[crash] report written to {path}", file=sys.stderr)
    except Exception:
        pass  # nothing else we can do inside a crash hook


def _format_tb(tb) -> str:
    import traceback
    return "".join(traceback.format_exception(None, None, tb))[:8000]


def install_crash_reporter() -> None:
    sys.excepthook = write_crash_report
