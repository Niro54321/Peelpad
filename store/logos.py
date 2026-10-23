"""Draws the Microsoft Store logos from the Peelpad mark (vector, so every size is sharp).

    .venv\\Scripts\\python.exe store\\logos.py

- app-tile-icon-300.png      1:1 app tile icon, 300 x 300, transparent
- box-art-1080.png / -2160   1:1 box art
- poster-art-720x1080.png / -1440x2160   2:3 poster art
- hero-1920x1080.png / -3840x2160        16:9 hero image
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath,  # noqa: E402
                           QRadialGradient)
from PySide6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication([])

from peelpad.skins import NEON  # noqa: E402
from peelpad.theme import draw_mark  # noqa: E402

OUT = ROOT / "store" / "logos"
TAGLINE = "Sticky notes that feel like paper"


def backdrop(p: QPainter, w: int, h: int) -> None:
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor("#1D2033"))
    g.setColorAt(1, QColor("#3A2546"))
    p.fillRect(0, 0, w, h, g)
    s = min(w, h)
    for c, r, col in ((QPointF(w * 0.15, h * 0.9), s * 0.75, QColor(255, 116, 200, 60)),
                      (QPointF(w * 0.9, h * 0.1), s * 0.7, QColor(61, 178, 255, 52))):
        glow = QRadialGradient(c, r)
        glow.setColorAt(0, col)
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(c, r, r)


def sheets(p: QPainter, c: QPointF, size: float) -> None:
    """A fan of neon sticky notes behind the mark."""
    for k, (angle, color) in enumerate(((-18, NEON[2][1]), (-6, NEON[3][1]), (8, NEON[1][1]))):
        p.save()
        p.translate(c)
        p.rotate(angle)
        rect = QRectF(-size / 2, -size / 2, size, size)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(rect.translated(size * 0.02, size * 0.04), size * 0.05, size * 0.05)
        paper = QLinearGradient(rect.topLeft(), rect.bottomRight())
        paper.setColorAt(0, QColor(color).lighter(108))
        paper.setColorAt(1, QColor(color))
        p.setBrush(paper)
        p.drawRoundedRect(rect, size * 0.05, size * 0.05)
        p.restore()


def text(p: QPainter, rect: QRectF, line: str, px: float, bold: bool, alpha: int = 255) -> None:
    f = QFont("Segoe UI")
    f.setPixelSize(max(1, round(px)))
    f.setBold(bold)
    p.setFont(f)
    p.setPen(QColor(255, 255, 255, alpha))
    p.drawText(rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, line)


def new(w: int, h: int, clear: bool = False) -> tuple[QImage, QPainter]:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent if clear else QColor("#1D2033"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    return img, p


def tile(size: int) -> None:
    img, p = new(size, size, clear=True)
    draw_mark(p, QRectF(size * 0.04, size * 0.04, size * 0.92, size * 0.92))
    p.end()
    img.save(str(OUT / f"app-tile-icon-{size}.png"))


def box(size: int) -> None:
    img, p = new(size, size)
    backdrop(p, size, size)
    sheets(p, QPointF(size * 0.5, size * 0.44), size * 0.42)
    draw_mark(p, QRectF(size * 0.3, size * 0.22, size * 0.4, size * 0.4))
    text(p, QRectF(0, size * 0.7, size, size * 0.12), "Peelpad", size * 0.1, True)
    text(p, QRectF(0, size * 0.81, size, size * 0.07), TAGLINE, size * 0.036, False, 215)
    p.end()
    img.save(str(OUT / f"box-art-{size}.png"))


def poster(w: int, h: int) -> None:
    img, p = new(w, h)
    backdrop(p, w, h)
    sheets(p, QPointF(w * 0.5, h * 0.36), w * 0.56)
    draw_mark(p, QRectF(w * 0.24, h * 0.18, w * 0.52, w * 0.52))
    text(p, QRectF(0, h * 0.63, w, h * 0.1), "Peelpad", w * 0.15, True)
    text(p, QRectF(w * 0.06, h * 0.73, w * 0.88, h * 0.06), TAGLINE, w * 0.05, False, 220)
    # three little crumpled-looking dots of colour, a hint of the paper balls
    for k, color in enumerate((NEON[0][1], NEON[2][1], NEON[3][1])):
        c = QPointF(w * (0.38 + 0.12 * k), h * 0.86)
        path = QPainterPath()
        for i in range(9):
            a = 2 * math.pi * i / 9
            r = w * 0.03 * (1 + 0.18 * math.sin(i * 2.3 + k))
            pt = QPointF(c.x() + r * math.cos(a), c.y() + r * math.sin(a))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawPath(path)
    p.end()
    img.save(str(OUT / f"poster-art-{w}x{h}.png"))


def hero(w: int, h: int) -> None:
    img, p = new(w, h)
    backdrop(p, w, h)
    sheets(p, QPointF(w * 0.3, h * 0.5), h * 0.46)
    draw_mark(p, QRectF(w * 0.3 - h * 0.23, h * 0.27, h * 0.46, h * 0.46))
    text(p, QRectF(w * 0.48, h * 0.33, w * 0.46, h * 0.17), "Peelpad", h * 0.15, True)
    text(p, QRectF(w * 0.48, h * 0.5, w * 0.46, h * 0.08), TAGLINE, h * 0.05, False, 220)
    text(p, QRectF(w * 0.48, h * 0.59, w * 0.46, h * 0.07), "Peel · Pin · Check off · Crumple", h * 0.038, False, 170)
    p.end()
    img.save(str(OUT / f"hero-{w}x{h}.png"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tile(300)
    for size in (1080, 2160):
        box(size)
    for w, h in ((720, 1080), (1440, 2160)):
        poster(w, h)
    for w, h in ((1920, 1080), (3840, 2160)):
        hero(w, h)
    print("saved", sorted(f.name for f in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
