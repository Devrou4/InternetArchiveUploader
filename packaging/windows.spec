# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for Windows.

Build with: python -m PyInstaller packaging/linux.spec --noconfirm
The resulting dist/InternetArchiveUploader/ (containing InternetArchiveUploader.exe) is checked by
uploader/packaging_contract.py before it is archived.
"""

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "README.md"), "."),
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "PySide6.QtWebEngineCore"],

    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="InternetArchiveUploader",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(ROOT / "assets" / "icon.ico") if (ROOT / "assets" / "icon.ico").is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="InternetArchiveUploader",
)
