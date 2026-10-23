"""Skins that move: your own animated GIF, APNG or WebP, and Peelpad's own
Skull parade (drawn in code, so it is sharp at any size).

All notes read the same clock, so copies of a skin move in step. A note
redraws its paper `frame_ms` apart while its skin moves.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen

from peelpad.skins import PictureSkin, Skin

MAX_FRAMES = 150
MAX_SIDE = 720


def now_ms() -> float:
    return time.monotonic() * 1000


def is_animated(path: Path) -> bool:
    from PIL import Image

    try:
        with Image.open(path) as im:
            return bool(getattr(im, "is_animated", False)) and getattr(im, "n_frames", 1) > 1
    except (OSError, ValueError):
        return False


class AnimatedSkin(PictureSkin):
    """A GIF, APNG or animated WebP you made. It plays on every note, looping."""

    animated = True

    def __init__(self, path: Path):
        from PIL import Image, ImageSequence

        frames, delays = [], []
        try:
            with Image.open(path) as im:
                for frame in ImageSequence.Iterator(im):
                    delays.append(max(20, int(frame.info.get("duration") or 80)))
                    rgba = frame.convert("RGBA")
                    if max(rgba.size) > MAX_SIDE:
                        rgba.thumbnail((MAX_SIDE, MAX_SIDE))
                    w, h = rgba.size
                    img = QImage(rgba.tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888)
                    frames.append(img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied))
                    if len(frames) >= MAX_FRAMES:
                        break
        except (OSError, ValueError) as e:
            raise ValueError(f"Can't read {Path(path).name}") from e
        if not frames:
            raise ValueError(f"Can't read {Path(path).name}")
        self.frames, self.delays = frames, delays
        self.total = sum(delays)
        self.frame_ms = max(30, min(delays))
        super().__init__(path, image=frames[0])

    def frame_index(self) -> int:
        t = now_ms() % self.total
        for i, d in enumerate(self.delays):
            if t < d:
                return i
            t -= d
        return len(self.frames) - 1

    def frame_id(self) -> int:
        return self.frame_index()

    def current(self) -> QImage:
        return self.frames[self.frame_index()]

    def paint_front(self, p: QPainter, w: float, h: float, color: int) -> None:
        p.drawImage(QRectF(0, 0, w, h), self.current())

    def paint_back(self, p: QPainter, w: float, h: float, color: int) -> None:
        p.drawImage(QRectF(0, 0, w, h), self.current())
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        p.fillRect(QRectF(0, 0, w, h), QColor(255, 255, 255, 150))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)


# ---------------------------------------------------------------- Peelpad's own: Skull parade

INK = QColor("#2B1E2E")
CREAM = QColor("#FFF6E2")
FRAME = QColor("#17131B")
BONE = QColor("#F7EEDC")
STAR = QColor("#FFD447")
BLUSH = QColor(255, 130, 150, 150)


def _skull(p: QPainter, c: QPointF, r: float, look: float = 0.0) -> None:
    """A round, friendly skull: big eyes, blush, a little jaw."""
    p.setPen(QPen(FRAME, r * 0.12))
    p.setBrush(BONE)
    head = QPainterPath()
    head.addEllipse(c, r, r * 0.92)
    jaw = QPainterPath()
    jaw.addRoundedRect(QRectF(c.x() - r * 0.48, c.y() + r * 0.45, r * 0.96, r * 0.62), r * 0.2, r * 0.2)
    p.drawPath(head.united(jaw))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(FRAME)
    for side in (-1, 1):
        p.drawEllipse(QPointF(c.x() + side * r * 0.38 + look * r * 0.08, c.y() + r * 0.05), r * 0.24, r * 0.27)
    p.setBrush(QColor(255, 255, 255, 230))
    for side in (-1, 1):
        p.drawEllipse(QPointF(c.x() + side * r * 0.38 + look * r * 0.08 - r * 0.07, c.y() - r * 0.04), r * 0.07, r * 0.07)
    p.setBrush(BLUSH)
    for side in (-1, 1):
        p.drawEllipse(QPointF(c.x() + side * r * 0.62, c.y() + r * 0.38), r * 0.15, r * 0.09)
    p.setBrush(FRAME)
    tri = QPainterPath()
    tri.moveTo(c.x() - r * 0.08, c.y() + r * 0.42)
    tri.lineTo(c.x() + r * 0.08, c.y() + r * 0.42)
    tri.lineTo(c.x(), c.y() + r * 0.3)
    tri.closeSubpath()
    p.drawPath(tri)
    p.setPen(QPen(FRAME, r * 0.07))
    for i in range(-2, 3):
        x = c.x() + i * r * 0.16
        p.drawLine(QPointF(x, c.y() + r * 0.62), QPointF(x, c.y() + r * 0.9))


def _bone(p: QPainter, a: QPointF, b: QPointF, r: float) -> None:
    p.setPen(QPen(FRAME, r * 0.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(a, b)
    p.setPen(QPen(BONE, r * 0.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(a, b)
    p.setPen(QPen(FRAME, r * 0.12))
    p.setBrush(BONE)
    for end in (a, b):
        for k in (-1, 1):
            d = QPointF(b.y() - a.y(), a.x() - b.x())
            n = math.hypot(d.x(), d.y()) or 1
            p.drawEllipse(end + d / n * r * 0.22 * k, r * 0.24, r * 0.24)


def _star(p: QPainter, c: QPointF, r: float) -> None:
    path = QPainterPath()
    for i in range(10):
        a = math.radians(-90 + i * 36)
        k = r if i % 2 == 0 else r * 0.45
        pt = QPointF(c.x() + k * math.cos(a), c.y() + k * math.sin(a))
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    path.closeSubpath()
    p.setPen(QPen(FRAME, r * 0.22, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(STAR)
    p.drawPath(path)


def _bat(p: QPainter, c: QPointF, r: float, flap: float) -> None:
    p.setPen(QPen(BONE, r * 0.06))
    p.setBrush(FRAME)
    p.drawEllipse(c, r * 0.32, r * 0.28)
    for side in (-1, 1):
        wing = QPainterPath()
        tip_y = c.y() - r * (0.35 + 0.45 * flap)
        wing.moveTo(c.x() + side * r * 0.2, c.y() - r * 0.05)
        wing.quadTo(QPointF(c.x() + side * r * 0.8, tip_y - r * 0.2), QPointF(c.x() + side * r * 1.25, tip_y))
        wing.quadTo(QPointF(c.x() + side * r * 0.95, c.y() + r * 0.05), QPointF(c.x() + side * r * 0.75, c.y() + r * 0.2))
        wing.quadTo(QPointF(c.x() + side * r * 0.55, c.y() + r * 0.05), QPointF(c.x() + side * r * 0.2, c.y() + r * 0.15))
        wing.closeSubpath()
        p.drawPath(wing)
    p.setBrush(QColor(255, 255, 255, 220))
    for side in (-1, 1):
        p.drawEllipse(QPointF(c.x() + side * r * 0.1, c.y() - r * 0.03), r * 0.05, r * 0.05)


class SkullParade(Skin):
    """A cream card in a black frame. A little skull runs along the bottom from right
    to left, a bat flaps in the corner, the stars twinkle. The middle stays calm for text."""

    key = "anim:skulls"
    name = "Skull parade (animated)"
    animated = True
    frame_ms = 33
    LOOP = 5.0                # seconds for one run across

    def __init__(self):
        super().__init__(cycle=False)
        self.key, self.name = SkullParade.key, SkullParade.name
        self.area = self.auto_area = (0.15, 0.27, 0.85, 0.68)

    def ink(self, color: int) -> QColor:
        return QColor(INK)

    def color(self, color: int) -> QColor:
        return QColor(CREAM)

    def frame_id(self) -> int:
        return int(now_ms() // self.frame_ms)

    def paint_front(self, p: QPainter, w: float, h: float, color: int, t: float | None = None) -> None:
        t = now_ms() / 1000 if t is None else t
        s = min(w, h)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        outer = QRectF(0, 0, w, h).adjusted(s * 0.02, s * 0.05, -s * 0.02, -s * 0.02)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(FRAME)
        p.drawRoundedRect(outer, s * 0.08, s * 0.08)
        card = outer.adjusted(s * 0.07, s * 0.08, -s * 0.07, -s * 0.07)
        p.setBrush(CREAM)
        p.drawRoundedRect(card, s * 0.06, s * 0.06)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#B89A6A"), max(1.0, s * 0.006), Qt.PenStyle.DashLine))
        p.drawRoundedRect(card.adjusted(s * 0.025, s * 0.025, -s * 0.025, -s * 0.025), s * 0.045, s * 0.045)
        # bones and twinkling stars on the frame
        _bone(p, QPointF(outer.left() + s * 0.035, outer.top() + h * 0.35), QPointF(outer.left() + s * 0.035, outer.top() + h * 0.5), s * 0.05)
        _bone(p, QPointF(outer.right() - s * 0.035, outer.top() + h * 0.5), QPointF(outer.right() - s * 0.035, outer.top() + h * 0.65), s * 0.05)
        for i, (fx, fy) in enumerate(((0.45, 0.07), (0.62, 0.065), (0.04, 0.72), (0.96, 0.3), (0.7, 0.97), (0.3, 0.97))):
            twinkle = 0.75 + 0.35 * math.sin(t * 3.2 + i * 1.7)
            _star(p, QPointF(w * fx, h * fy), s * 0.034 * twinkle)
        # a bat flaps over the top-right corner of the card
        _bat(p, QPointF(card.right() - s * 0.1, card.top() + s * 0.03 + math.sin(t * 2.4) * s * 0.012),
             s * 0.09, 0.5 + 0.5 * math.sin(t * 11))
        # a skull peeks over the top-left edge, holding on with both hands
        peek = QPointF(card.left() + s * 0.14, card.top() - s * 0.02 + math.sin(t * 1.8) * s * 0.01)
        _skull(p, peek, s * 0.085, look=0.6 * math.sin(t * 0.9))
        p.setPen(QPen(FRAME, s * 0.01))
        p.setBrush(BONE)
        for side in (-1, 1):
            p.drawEllipse(QPointF(peek.x() + side * s * 0.075, card.top() + s * 0.045), s * 0.028, s * 0.022)
        # the running skull, along the bottom of the card
        lane = card.bottom() - s * 0.13
        k = (t / self.LOOP) % 1.0
        x = card.right() + s * 0.14 - k * (card.width() + s * 0.28)
        bob = abs(math.sin(t * 12)) * s * 0.024
        r = s * 0.075
        p.save()
        p.setClipRect(card.adjusted(0, 0, 0, s * 0.02))
        swing = math.sin(t * 14)
        p.setPen(QPen(FRAME, r * 0.32, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        hip = QPointF(x + r * 0.1, lane + r * 0.55 - bob)
        for k_leg in (1, -1):
            foot = QPointF(hip.x() + k_leg * swing * r * 0.7, lane + r * 1.25)
            p.drawLine(hip, foot)
            p.drawLine(foot, foot + QPointF(-r * 0.3, 0))
        p.setPen(QPen(BONE, r * 0.16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for k_leg in (1, -1):
            foot = QPointF(hip.x() + k_leg * swing * r * 0.7, lane + r * 1.25)
            p.drawLine(hip, foot)
        # dust puffs behind it
        for i in range(3):
            age = (t * 3 + i / 3) % 1.0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(184, 154, 106, int(110 * (1 - age))))
            p.drawEllipse(QPointF(x + r * (1.2 + age * 2.2), lane + r * 1.15 - age * r * 0.4), r * 0.2 * (1 + age), r * 0.15 * (1 + age))
        _skull(p, QPointF(x, lane - bob), r, look=-1.0)
        p.restore()
        p.restore()

    def paint_back(self, p: QPainter, w: float, h: float, color: int) -> None:
        self.paint_front(p, w, h, color, t=0.0)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        p.fillRect(QRectF(0, 0, w, h), QColor(255, 255, 255, 150))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
