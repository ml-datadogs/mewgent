# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Mewgent — one-folder bundle.

Build:  uv run pyinstaller mewgent.spec --noconfirm
Output: dist/mewgent/mewgent.exe
"""
import os
from pathlib import Path

ROOT = Path(SPECPATH)

# ── Data files to bundle alongside the executable ────────────────────────
datas = [
    (str(ROOT / "ui" / "dist"), os.path.join("ui", "dist")),
    (str(ROOT / "config"), "config"),
    (str(ROOT / "images"), "images"),
]

env_file = ROOT / "src" / ".env"
if env_file.exists():
    datas.append((str(env_file), "."))

wiki_data = ROOT / "wiki_data"
if wiki_data.exists():
    datas.append((str(wiki_data), "wiki_data"))

# ── Analysis ─────────────────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / "src" / "__main__.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=[
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebChannel",
    ],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "numpy.testing",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="mewgent",
    console=False,
    icon=str(ROOT / "images" / "mewgent-logo.jpg"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="mewgent",
)
