# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Mewgent — one-folder bundle.

Build:  uv run pyinstaller mewgent.spec --noconfirm
Output: dist/mewgent/mewgent.exe

Never bundle API keys in public releases. ``src/.env`` is included in the
bundle only when ``MEWGENT_BUNDLE_SRC_ENV=1`` is set (private/debug builds).
"""
import os
import tomllib
from pathlib import Path

ROOT = Path(SPECPATH)


def _semver_to_quad(ver: str) -> tuple[int, int, int, int]:
    """Map pyproject semver to Windows FILEVERSION (four uint16 components)."""
    base = ver.split("+", 1)[0].split("-", 1)[0]
    parts: list[int] = []
    for p in base.split("."):
        if p.isdigit():
            parts.append(int(p))
        else:
            break
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def _win_version_info_text(version_str: str, description: str) -> str:
    quad = _semver_to_quad(version_str)
    desc_lit = repr(description)
    ver_lit = repr(version_str)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={quad},
    prodvers={quad},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', ''),
            StringStruct('FileDescription', {desc_lit}),
            StringStruct('FileVersion', {ver_lit}),
            StringStruct('InternalName', 'mewgent'),
            StringStruct('LegalCopyright', ''),
            StringStruct('OriginalFilename', 'mewgent.exe'),
            StringStruct('ProductName', 'Mewgent'),
            StringStruct('ProductVersion', {ver_lit})
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)"""


with open(ROOT / "pyproject.toml", "rb") as f:
    _project = tomllib.load(f)["project"]
_VERSION_STR = _project["version"]
_DESCRIPTION = _project["description"]

_win_ver_path = ROOT / "build" / "win-file-version.txt"
_win_ver_path.parent.mkdir(parents=True, exist_ok=True)
_win_ver_path.write_text(_win_version_info_text(_VERSION_STR, _DESCRIPTION), encoding="utf-8")

# ── Data files to bundle alongside the executable ────────────────────────
datas = [
    (str(ROOT / "ui" / "dist"), os.path.join("ui", "dist")),
    (str(ROOT / "config"), "config"),
    (str(ROOT / "images"), "images"),
    (str(ROOT / "src" / "llm" / "breeding_strategy_context.md"), "src/llm"),
    (str(ROOT / "src" / "data" / "item_effects_wiki.json"), os.path.join("src", "data")),
    (str(ROOT / "src" / "data" / "item_icons_wiki.json"), os.path.join("src", "data")),
    (str(ROOT / "src" / "data" / "item_slots_wiki.json"), os.path.join("src", "data")),
]

_env_file = ROOT / "src" / ".env"
if os.environ.get("MEWGENT_BUNDLE_SRC_ENV") == "1" and _env_file.exists():
    datas.append((str(_env_file), "."))

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
    icon=str(ROOT / "images" / "mewgent.ico"),
    version=str(_win_ver_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="mewgent",
)
