"""Build a standalone Windows executable with PyInstaller.

Optimized for minimum size:
  - --onefile (single .exe, no directory)
  - --strip (strip debug symbols)
  - --noupx (let PyInstaller auto-detect UPX)
  - Excludes unused Python stdlib modules
  - Excludes unused Qt modules (QtNetwork, QtSql, QtTest, etc.)
  - Sets QT_QPA_PLATFORM_PLUGIN_PATH to avoid bundling unnecessary plugins

Usage:
    uv run python scripts/build.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
APP_NAME = "widget-calculator"
ENTRY = "widget_calc.__main__"

EXCLUDED_MODULES = [
    "tkinter",
    "unittest",
    "xml",
    "xmlrpc",
    "pydoc",
    "doctest",
    "argparse",
    "difflib",
    "pdb",
    "profile",
    "cProfile",
    "traceback",
    "pickletools",
    "lib2to3",
    "test",
    "tests",
    "numpy",
    "scipy",
    "matplotlib",
    "pandas",
    "IPython",
]

EXCLUDED_QT_MODULES = [
    "PySide6.QtNetwork",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtDBus",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtXml",
    "PySide6.QtXmlPatterns",
]


def find_upx() -> str | None:
    """Return the path to UPX if available, else None."""
    return shutil.which("upx")


def build() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        APP_NAME,
        "--onefile",
        "--windowed",
        "--strip",
        "--noconfirm",
        "--clean",
        "--noupx",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(PROJECT_ROOT / "scripts"),
        ENTRY,
    ]

    for mod in EXCLUDED_MODULES + EXCLUDED_QT_MODULES:
        cmd.extend(["--exclude-module", mod])

    upx = find_upx()
    if upx:
        cmd.extend(["--upx-dir", os.path.dirname(upx)])
        print(f"UPX found: {upx}")
    else:
        print("UPX not found - skipping compression (install UPX for smaller exe)")

    env = os.environ.copy()
    env["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"Build did not produce {exe_path}")

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"\nBuild complete: {exe_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    build()
