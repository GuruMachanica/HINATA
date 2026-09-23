# -*- mode: python ; coding: utf-8 -*-
# HINATA backend — PyInstaller spec
# Build:  pyinstaller product/hinata-backend.spec --noconfirm
# Output: dist/hinata-backend/hinata-backend.exe

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

datas = [
    # Persona and voice script must ship with the binary
    (os.path.join(ROOT, 'hermes-core', 'config', 'SOUL.md'), 'config'),
    (os.path.join(ROOT, 'voice', 'neural_tts.py'), 'voice'),
    (os.path.join(ROOT, 'voice', 'voice_manifest.json'), 'voice'),
    # VRM + animations served by the backend
    (os.path.join(ROOT, 'shell-bella', 'models'), 'models'),
    # React UI build output
    (os.path.join(ROOT, 'frontend', 'dist'), 'frontend_dist'),
]

hiddenimports = [
    'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'anyio._backends._asyncio',
    'edge_tts', 'ddgs',
]

a = Analysis(
    [os.path.join(ROOT, 'backend', 'main.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy.tests'],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='hinata-backend',
    console=True,          # keep console for logs; switch to False when packaged as service
    disable_windowed_traceback=False,
    upx=False,
)
