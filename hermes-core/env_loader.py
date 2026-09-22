"""
HINATA Environment Loader
Safely loads key-value pairs from .env without third-party dependencies.
"""

import os
from pathlib import Path

def load_env_file(env_path: Path) -> None:
    """Read .env key-values into os.environ if not already set."""
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())
