"""Builds the Microsoft Store package (MSIX).

    .venv\\Scripts\\python.exe packaging\\msix.py [--skip-app]

1. the app with PyInstaller (dist/Peelpad), unless --skip-app
2. the Store icons, drawn from the app's own mark
3. AppxManifest.xml, with the identity Partner Center gives you
4. makeappx: dist/Peelpad-<version>.msix, unsigned (the Store signs it)

The identity comes from packaging/store.json (Partner Center > Product
management > Product identity):

    {"name": "12345Niro54321.Peelpad", "publisher": "CN=...", "publisher_name": "Niro54321"}

makeappx comes from Microsoft's Windows SDK build tools (NuGet package
Microsoft.Windows.SDK.BuildTools), unpacked under build/sdk.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
BUILD, DIST = ROOT / "build", ROOT / "dist"
sys.path.insert(0, str(ROOT))

from peelpad import __version__  # noqa: E402

PLACEHOLDER = {"name": "Niro54321.Peelpad", "publisher": "CN=Niro54321", "publisher_name": "Niro54321"}
LANGUAGES = ["en-us", "ar", "es", "ja", "zh-cn"]
DESCRIPTION = ("Sticky notes that feel like paper: peel a note off the pad, pin it anywhere on top, "
               "check it off and watch it crumple.")


def identity() -> dict:
    path = ROOT / "packaging" / "store.json"
    if path.exists():
        return PLACEHOLDER | json.loads(path.read_text("utf-8"))
    print("  packaging/store.json not found: using placeholder identity (fine for a test, not for the Store)")
    return dict(PLACEHOLDER)


def makeappx() -> Path:
    found = sorted((BUILD / "sdk" / "bin").glob("*/x64/makeappx.exe"))
    if not found:
        sys.exit("makeappx.exe not found: unpack Microsoft.Windows.SDK.BuildTools into build/sdk (see the docstring)")
    return found[-1]


def resources_index(layout: Path) -> None:
    """resources.pri, so Windows picks the right icon size (scale-200, targetsize-48...).
    Only the icons are indexed, not the thousands of files of the app itself."""
    makepri = makeappx().with_name("makepri.exe")
    work = BUILD / "msix" / "pri"
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(layout / "Assets", work / "Assets")
    shutil.copy2(layout / "AppxManifest.xml", work / "AppxManifest.xml")
    config = BUILD / "msix" / "priconfig.xml"
    subprocess.run([str(makepri), "createconfig", "/cf", str(config), "/dq", "en-US", "/pv", "10.0.0", "/o"],
                   check=True)
    # one package, so one index: no separate resource packs per scale or language
    text = config.read_text("utf-8")
    start, end = text.find("<packaging>"), text.find("</packaging>")
    if start != -1 and end != -1:
        config.write_text(text[:start] + text[end + len("</packaging>"):], encoding="utf-8")
    subprocess.run([str(makepri), "new", "/pr", str(work), "/cf", str(config), "/mn", str(work / "AppxManifest.xml"),
                    "/of", str(layout / "resources.pri"), "/o"], check=True)


def icons(assets: Path) -> None:
    """Every size Windows and the Store ask for, from the Peelpad mark."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QGuiApplication, QImage, QPainter

    from peelpad.theme import draw_mark

    app = QGuiApplication.instance() or QGuiApplication(["msix"])  # icons need Qt
    assert app is not None
    assets.mkdir(parents=True, exist_ok=True)

    def save(name: str, w: int, h: int, mark: float = 1.0) -> None:
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(w, h) * mark
        draw_mark(p, QRectF((w - side) / 2, (h - side) / 2, side, side))
        p.end()
        img.save(str(assets / name))

    for scale in (100, 200):
        k = scale / 100
        save(f"StoreLogo.scale-{scale}.png", round(50 * k), round(50 * k))
        save(f"Square44x44Logo.scale-{scale}.png", round(44 * k), round(44 * k))
        save(f"Square150x150Logo.scale-{scale}.png", round(150 * k), round(150 * k), 0.66)
        save(f"Wide310x150Logo.scale-{scale}.png", round(310 * k), round(150 * k), 0.8)
    for size in (16, 24, 32, 48, 256):        # the taskbar and Start use these, without a plate behind
        save(f"Square44x44Logo.targetsize-{size}.png", size, size)
        save(f"Square44x44Logo.targetsize-{size}_altform-unplated.png", size, size)


def manifest(ident: dict, version: str) -> str:
    resources = "\n    ".join(f'<Resource Language="{lang}"/>' for lang in LANGUAGES)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:uap5="http://schemas.microsoft.com/appx/manifest/uap/windows10/5"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap uap5 rescap">
  <Identity Name="{escape(ident["name"])}" Publisher="{escape(ident["publisher"])}" Version="{version}"
            ProcessorArchitecture="x64"/>
  <Properties>
    <DisplayName>Peelpad</DisplayName>
    <PublisherDisplayName>{escape(ident["publisher_name"])}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
    <Description>{escape(DESCRIPTION)}</Description>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0"/>
  </Dependencies>
  <Resources>
    {resources}
  </Resources>
  <Applications>
    <Application Id="Peelpad" Executable="Peelpad.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="Peelpad" Description="{escape(DESCRIPTION)}" BackgroundColor="transparent"
                          Square150x150Logo="Assets\\Square150x150Logo.png" Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" ShortName="Peelpad"/>
      </uap:VisualElements>
      <Extensions>
        <uap5:Extension Category="windows.startupTask" Executable="Peelpad.exe" EntryPoint="Windows.FullTrustApplication">
          <uap5:StartupTask TaskId="PeelpadStartup" Enabled="false" DisplayName="Peelpad"/>
        </uap5:Extension>
      </Extensions>
    </Application>
  </Applications>
  <Capabilities>
    <Capability Name="internetClient"/>
    <rescap:Capability Name="runFullTrust"/>
  </Capabilities>
</Package>
'''


def main() -> None:
    if "--skip-app" not in sys.argv:
        import build

        print("\n== PyInstaller", flush=True)
        build.prepare()
        build.pyinstaller()
    app = DIST / "Peelpad"
    if not (app / "Peelpad.exe").exists():
        sys.exit("dist/Peelpad/Peelpad.exe is missing: run without --skip-app")
    version = ".".join((__version__.split(".") + ["0"] * 4)[:3]) + ".0"     # the Store wants the last part 0
    ident = identity()
    layout = BUILD / "msix" / "layout"
    print(f"\n== Layout for {ident['name']} {version}", flush=True)
    shutil.rmtree(layout, ignore_errors=True)
    shutil.copytree(app, layout)
    icons(layout / "Assets")
    (layout / "AppxManifest.xml").write_text(manifest(ident, version), encoding="utf-8")
    print("\n== makepri: which icon size for which screen", flush=True)
    resources_index(layout)
    out = DIST / f"Peelpad-{version}.msix"
    print("\n== makeappx", flush=True)
    subprocess.run([str(makeappx()), "pack", "/o", "/d", str(layout), "/p", str(out)], check=True)
    print(f"\nDone: {out} ({out.stat().st_size / 1e6:.0f} MB). Upload it in Partner Center > Packages.")


if __name__ == "__main__":
    main()
