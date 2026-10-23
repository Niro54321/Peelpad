# PyInstaller recipe, run by packaging/build.py. Makes dist/Peelpad with Peelpad.exe.

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
BUILD = ROOT / "build"
EXCLUDES = ["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtMultimedia",
            "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtDesigner", "pytest"]

DATAS = [(str(ROOT / "peelpad" / "fonts"), "peelpad/fonts")]      # Aref Ruqaa, for Arabic

app = Analysis([str(ROOT / "packaging" / "launcher.py")], pathex=[str(ROOT)], datas=DATAS,
               hiddenimports=collect_submodules("peelpad"), excludes=EXCLUDES, noarchive=False)
exe = EXE(PYZ(app.pure), app.scripts, [], exclude_binaries=True, name="Peelpad",
          icon=str(BUILD / "peelpad.ico"), version=str(BUILD / "version.txt"), console=False, upx=False)
COLLECT(exe, app.binaries, app.datas, name="Peelpad", upx=False)
