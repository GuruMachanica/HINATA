# -*- mode: python ; coding: utf-8 -*-
# HINATA backend — PyInstaller spec (self-contained product build)
# Build:  python -m PyInstaller product/hinata-backend.spec --noconfirm
# Output: dist/hinata-backend.exe  (single file, everything bundled)

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

datas = [
    # Persona
    (os.path.join(ROOT, 'hermes-core', 'config', 'SOUL.md'), 'config'),
    # Voice TTS subprocess script
    (os.path.join(ROOT, 'voice', 'neural_tts.py'), 'voice'),
    (os.path.join(ROOT, 'voice', 'voice_manifest.json'), 'voice'),
    # Optional VRM model assets. The repository may intentionally omit these
    # third-party assets (licensing/redistribution), so never make the product
    # build depend on a developer-only shell-bella/models directory.
    # React UI build output
    (os.path.join(ROOT, 'frontend', 'dist'), 'frontend_dist'),
    # Vendored Hermes agent source — slim staging copy (py + configs only)
    (os.path.join(ROOT, 'product', 'hermes-agent-slim'), 'hermes-agent'),
]

# GGUF model files bundled for the embedded llama.cpp engine (own dir so the
# VRM `models/` dir stays untouched).
MODELS_DIR = os.path.join(ROOT, 'product', 'bundled-models')
if os.path.isdir(MODELS_DIR):
    datas.append((MODELS_DIR, 'models_ollama'))

# Embedded llama.cpp inference engine (Vulkan) — makes the exe fully
# self-contained: no Ollama install required.
ENGINE_DIR = os.path.join(ROOT, 'product', 'engine')
if os.path.isdir(ENGINE_DIR):
    datas.append((ENGINE_DIR, 'engine'))

hiddenimports = [
    'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'anyio._backends._asyncio',
    'edge_tts', 'ddgs', 'mss',
    # voice subprocess deps
    'certifi',
]

a = Analysis(
    [os.path.join(ROOT, 'product', 'entry.py')],
    pathex=[ROOT, os.path.join(ROOT, 'product', 'hermes-agent-slim')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy.tests',
        # hermes-agent imports these lazily/optionally — never used by HINATA
        'torch', 'torchvision', 'torchaudio', 'tf_keras', 'tensorflow',
        'pygame', 'scipy', 'pandas', 'IPython', 'jupyter',
        'PIL.ImageQt', 'PyQt5', 'PySide2', 'PySide6',
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='hinata-backend',
    console=True,          # keep console for logs; False when packaged as a service
    disable_windowed_traceback=False,
    upx=False,
)
