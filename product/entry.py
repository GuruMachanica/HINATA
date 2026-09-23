"""Frozen exe entrypoint — imports the backend package, runs uvicorn.

PyInstaller analyzes THIS file. It imports backend.main as a proper package
module so all relative imports inside backend/ resolve correctly.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.main import app  # noqa: E402  (all features register on import)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("HINATA_PORT", "8080")))
