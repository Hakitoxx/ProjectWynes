# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for Project Wynes (Windows, single windowed exe).

Build with:
    pyinstaller --noconfirm packaging/projectwynes.spec

The result is dist/projectwynes.exe — no Python installation required.
Packed modules are limited to what Wynes actually uses (no Qt WebEngine,
3D, charts, ...), which keeps the artifact small.
"""
from pathlib import Path

ROOT = Path(SPECPATH).parent  # repository root (spec lives in packaging/)

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Qt modules Wynes never uses — keeps the executable lean
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtQuick3D",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DInput",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtWebSockets",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtTest",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="projectwynes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # no UPX: avoids AV heuristics and licensing complications
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(ROOT / "packaging" / "version_info.py"),
)
