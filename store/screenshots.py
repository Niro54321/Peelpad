"""Draws the Microsoft Store screenshots (1920 x 1080) from the app's own code,
so they show Peelpad and nothing of anyone's desktop.

    .venv\\Scripts\\python.exe store\\screenshots.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PEELPAD_HOME", tempfile.mkdtemp())

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

from peelpad import skins, store, weather  # noqa: E402
from peelpad.animated import AppleWorm, SkullParade  # noqa: E402
from peelpad.note import MARGIN, draw_pin, paper_image, shadow_image  # noqa: E402
from peelpad.scenes import LED, Arcade, Aquarium, LedClock, NightSky, RainyWindow, Synthwave, WeatherSky  # noqa: E402
from peelpad.skins import NEON  # noqa: E402
from peelpad.stage import CrumpleActor, PeelActor  # noqa: E402

OUT = ROOT / "store" / "screenshots"
W, H = 1920, 1080
K = 1.5          # everything is drawn at 1.5x and placed in logical units, so it stays sharp


def canvas() -> tuple[QImage, QPainter]:
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    g = QLinearGradient(0, 0, W, H)
    g.setColorAt(0, QColor("#1D2033"))
    g.setColorAt(1, QColor("#3A2546"))
    p.fillRect(0, 0, W, H, g)
    for c, r, col in ((QPointF(360, 900), 520, QColor(255, 116, 200, 46)), (QPointF(1620, 180), 480, QColor(61, 178, 255, 42))):
        glow = QRadialGradient(c, r)
        glow.setColorAt(0, col)
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(c, r, r)
    return img, p


def heading(p: QPainter, title: str, line: str, x: float = 90, y: float = 70) -> None:
    f = QFont("Segoe UI")
    f.setPixelSize(56)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(QRectF(x, y, 1700, 80), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
    f.setPixelSize(26)
    f.setBold(False)
    p.setFont(f)
    p.setPen(QColor(255, 255, 255, 210))
    p.drawText(QRectF(x, y + 80, 1700, 44), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)


def note(color: int, rows, done=()) -> dict:
    n = store.new_note(color)
    n["rows"] = [store.new_row(t) for t in rows]
    for i in done:
        n["rows"][i]["done"] = True
    return n


def pinned(p: QPainter, x: float, y: float, n: dict, skin, w: float = 300, pin: bool = True) -> None:
    h = w / (skin.aspect or 1)
    paper = paper_image(skin, round(w), round(h), n["color"], K)
    p.drawImage(QPointF(x - MARGIN, y - MARGIN), shadow_image(paper, MARGIN, K))
    front, _ = skins.note_images(n, skin, round(w), round(h), K)
    p.drawImage(QRectF(x, y, w, h), front)
    if pin:
        draw_pin(p, QPointF(x + w / 2, y + h * 0.07), w * 0.032, QColor(NEON[(n["color"] + 2) % 4][1]).darker(118))


def hero() -> None:
    img, p = canvas()
    neon = skins.Skin()
    px, py, side = 150, 330, 380
    for i in range(7, 0, -1):
        layer = paper_image(neon, side, side, (1 + i) % 4, K)
        if i == 7:
            p.drawImage(QPointF(px - MARGIN, py - MARGIN + 15), shadow_image(layer, MARGIN, K))
        p.drawImage(QPointF(px, py + 15 * i / 7), layer)
    under, _ = skins.note_images(note(2, ["Plan the weekend"]), neon, side, side, K)
    p.drawImage(QRectF(px, py, side, side), under)
    front, back = skins.note_images(note(1, ["Buy milk", "Call mom", "Gym at 6"], done=(1,)), neon, side, side, K)
    a = PeelActor(QRectF(px, py, side, side), QPointF(px + side - 12, py + side - 10), front, back, K, side * 0.16,
                  lambda r: None, lambda: None)
    a.move(QPointF(px + side * 0.5, py + side * 0.4))
    a.step(0.016)
    a.paint(p, QPointF(0, 0))
    p.resetTransform()
    pinned(p, 640, 150, note(0, ["Ship v1.0", "اكتب المهام هنا", "Tweet it"], done=(0,)),
           skins.skin_for("theme:midnight", Path(".")), 330)
    weather.Now.preview, weather.Now.updated = "live", 1
    weather.Now.state, weather.Now.day, weather.Now.temp, weather.Now.place = "partly", True, 22, "Casablanca"
    pinned(p, 1030, 120, note(3, ["Walk at 5", "Water the plants"]), WeatherSky(), 340, pin=False)
    LED.color = QColor("#22E3FF")
    pinned(p, 1440, 150, note(0, ["Stand-up 10:00", "Review PRs"], done=(1,)), LedClock(), 330, pin=False)
    skins.WRITING.ink, skins.WRITING.effect = QColor("#FF4FD8"), "gummy"
    pinned(p, 700, 580, note(0, ["Halloween party", "Buy candy"]), SkullParade(), 330, pin=False)
    skins.WRITING.ink, skins.WRITING.effect = None, "auto"
    f2, b2 = skins.note_images(note(3, ["Done!", "All checked"], done=(0, 1)), neon, 280, 280, K)
    c = CrumpleActor(QRectF(1100, 560, 280, 280), f2, b2, K, "show")
    c.step(0.7)
    c.paint(p, QPointF(0, 0))
    p.resetTransform()
    f = QFont("Segoe UI")
    f.setPixelSize(64)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(QRectF(1380, 640, 520, 80), Qt.AlignmentFlag.AlignLeft, "Peelpad")
    f.setPixelSize(26)
    f.setBold(False)
    p.setFont(f)
    p.setPen(QColor(255, 255, 255, 220))
    p.drawText(QRectF(1380, 730, 500, 260), Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
               "Sticky notes that feel like paper. Peel one off, pin it anywhere, check it off and watch it crumple.")
    p.end()
    img.save(str(OUT / "1-peel-pin-crumple.png"))


def looks() -> None:
    img, p = canvas()
    heading(p, "Make it yours", "Neon colours, themes, your own pictures and animated looks, with glowing or cartoon ink.")
    LED.color = QColor("#FF2B2B")
    path = Path(".")
    grid = [
        (skins.Skin(), note(0, ["Buy milk", "Call mom"]), "auto", None),
        (skins.skin_for("theme:midnight", path), note(0, ["Neon ink", "Ship it"]), "auto", None),
        (skins.skin_for("theme:white", path), note(0, ["Gummy ink", "Plan trip"]), "gummy", QColor("#FF4FD8")),
        (skins.skin_for("theme:kraft", path), note(0, ["Toon ink", "Groceries"]), "toon", QColor("#FFD447")),
        (Synthwave(), note(0, ["Retro wave", "Code review"]), "auto", None),
        (Arcade(), note(0, ["Level up", "Daily quest"]), "auto", None),
        (AppleWorm(), note(0, ["Read 20 pages"]), "auto", None),
        (Aquarium(), note(0, ["Feed the fish"]), "auto", None),
        (NightSky(), note(0, ["Sleep by 11"]), "auto", None),
        (RainyWindow(), note(0, ["Tea and a book"]), "auto", None),
    ]
    side, gap = 300, 52
    left = (W - 5 * side - 4 * gap) / 2
    for i, (skin, n, effect, ink) in enumerate(grid):
        skins.WRITING.effect, skins.WRITING.ink = effect, ink
        x = left + (i % 5) * (side + gap)
        y = 270 + (i // 5) * (side + 60)
        pinned(p, x, y, n, skin, side, pin=not skin.animated)
    skins.WRITING.effect, skins.WRITING.ink = "auto", None
    p.end()
    img.save(str(OUT / "2-make-it-yours.png"))


def weather_shot() -> None:
    img, p = canvas()
    heading(p, "Live weather on your notes", "Sun, soft 3D clouds, rain, snow, storms and the night sky, following your city.")
    sky = WeatherSky()
    side, gap = 330, 50
    left = (W - 4 * side - 3 * gap) / 2
    weather.Now.temp, weather.Now.place, weather.Now.updated = None, "", 1
    for i, st in enumerate(["clear", "partly", "rain", "storm", "snow", "fog", "cloudy", "night"]):
        weather.Now.preview = st
        x = left + (i % 4) * (side + gap)
        y = 260 + (i // 4) * (side + 40)
        img_note = QImage(round(side * K), round(side * K), QImage.Format.Format_ARGB32_Premultiplied)
        img_note.fill(0)
        q = QPainter(img_note)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        q.scale(K, K)
        sky.paint_front(q, side, side, 0, t=4.15 if st == "storm" else 6.0)
        q.end()
        p.drawImage(QRectF(x, y, side, side), img_note)
    weather.Now.preview = "live"
    p.end()
    img.save(str(OUT / "3-live-weather.png"))


def physics_shot() -> None:
    img, p = canvas()
    heading(p, "Real paper physics", "Notes curl as you peel them, swing as you carry them, sway in the wind and crumple when done.")
    neon = skins.Skin()
    side = 330
    steps = [("Peel", 0), ("Carry", 1), ("Wind", 2), ("Crumple", 3)]
    left, gap = 150, 95
    f = QFont("Segoe UI")
    f.setPixelSize(30)
    f.setBold(True)
    for label, i in steps:
        x, y = left + i * (side + gap), 360
        n = note(i, ["Buy milk", "Call mom", "Gym at 6"], done=(1,))
        front, back = skins.note_images(n, neon, side, side, K)
        if i == 0:
            under, _ = skins.note_images(note(i + 1, []), neon, side, side, K)
            p.drawImage(QRectF(x, y, side, side), under)
            a = PeelActor(QRectF(x, y, side, side), QPointF(x + side - 10, y + side - 10), front, back, K, 50,
                          lambda r: None, lambda: None)
            a.move(QPointF(x + side * 0.42, y + side * 0.38))
            a.step(0.016)
            a.paint(p, QPointF(0, 0))
        elif i == 1:
            a = PeelActor(QRectF(x, y, side, side), QPointF(x + side / 2, y + 20), front, back, K, 0,
                          lambda r: None, lambda: None, carry=True)
            for k in range(14):
                a.move(QPointF(x + side / 2 + k * 4, y + 20 + k * 2))
                a.step(1 / 60)
            a.paint(p, QPointF(0, 0))
        elif i == 2:
            from peelpad import physics
            from peelpad.stage import Painted, paint_bands

            shape = physics.wind(side, side, side * 0.16, 1.6, physics.MAX_WIND, 0.4, 0.08)
            shape = physics.move_shape(shape, lambda q: (q[0] + x, q[1] + y))
            paint_bands(p, Painted(shape, K), front, back, QPointF(0, 0))
        else:
            c = CrumpleActor(QRectF(x, y, side, side), front, back, K, "shot")
            c.step(0.62)
            c.paint(p, QPointF(0, 0))
        p.resetTransform()
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(QRectF(x, y + side + 70, side, 50), Qt.AlignmentFlag.AlignHCenter, label)
    p.end()
    img.save(str(OUT / "4-paper-physics.png"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hero()
    looks()
    weather_shot()
    physics_shot()
    print("saved", sorted(f.name for f in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
