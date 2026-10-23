"""What a note looks like: the neon paper colours, or a picture you made.

A custom skin is a PNG, ideally 600 x 600 px. It is stretched to the note, so
notes with a skin keep its shape when you resize them. Transparent pixels are
see-through on the desktop (and clicks go through them). Text is written inside
the safe area: 60 px in from the left, right and bottom, 96 px from the top
(the top band is where the glue is, and where you grab a pinned note).
"""

from __future__ import annotations

import hashlib
import random
import shutil
import unicodedata
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPen)

from peelpad.store import NEON_COUNT

NEON = [("Lemon", "#F3FF6B"), ("Mango", "#FFD447"), ("Bubblegum", "#FF74C8"), ("Lime", "#CDFF3F")]
assert len(NEON) == NEON_COUNT

TEMPLATE = 600              # px, the size a skin is designed at
GLUE = 96                   # top band
SIDE = 60                   # left, right and bottom margins
SAFE = (SIDE / TEMPLATE, GLUE / TEMPLATE, 1 - SIDE / TEMPLATE, 1 - SIDE / TEMPLATE)
DARK_INK, LIGHT_INK = QColor("#1F1D1A"), QColor("#FBFAF4")


def safe_rect(w: float, h: float) -> QRectF:
    return QRectF(w * SAFE[0], h * SAFE[1], w * (SAFE[2] - SAFE[0]), h * (SAFE[3] - SAFE[1]))


def font_px(w: float) -> int:
    return max(11, round(w * 0.058))


def row_height(px: int) -> int:
    return round(px * 1.75)


@lru_cache(maxsize=1)
def hand_family() -> str:
    """A handwriting face that ships with Windows; Qt falls back for scripts it lacks."""
    families = set(QFontDatabase.families())
    for name in ("Ink Free", "Segoe Print", "Segoe UI"):
        if name in families:
            return name
    return QFont().family()


def hand_font(px: int, done: bool = False) -> QFont:
    f = QFont(hand_family())
    f.setPixelSize(px)
    f.setStrikeOut(done)
    return f


@lru_cache(maxsize=1)
def _grain() -> QImage:
    """A small tile of paper grain, drawn over the plain colours."""
    rnd = random.Random(7)
    size = 96
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    for y in range(size):
        for x in range(size):
            v = rnd.random()
            if v < 0.18:
                img.setPixelColor(x, y, QColor(0, 0, 0, rnd.randint(4, 12)))
            elif v > 0.86:
                img.setPixelColor(x, y, QColor(255, 255, 255, rnd.randint(6, 18)))
    return img


class Skin:
    """One look. `color` is the note's neon colour (0..3), which a picture ignores."""

    key = "neon"
    name = "Neon"
    aspect: float | None = None          # width / height a note keeps, if any

    def __init__(self, cycle: bool = True, solid: int = 0):
        self.cycle, self.solid = cycle, solid
        if not cycle:
            self.key, self.name = f"solid:{solid}", NEON[solid][0]

    def color(self, color: int) -> QColor:
        return QColor(NEON[(color if self.cycle else self.solid) % NEON_COUNT][1])

    def ink(self, color: int) -> QColor:
        return DARK_INK

    def paint_front(self, p: QPainter, w: float, h: float, color: int) -> None:
        base = self.color(color)
        r = QRectF(0, 0, w, h)
        p.fillRect(r, base)
        light = QLinearGradient(0, 0, w * 0.4, h)
        light.setColorAt(0, QColor(255, 255, 255, 46))
        light.setColorAt(0.55, QColor(255, 255, 255, 0))
        light.setColorAt(1, QColor(0, 0, 0, 16))
        p.fillRect(r, light)
        glue = QLinearGradient(0, 0, 0, h * SAFE[1])
        glue.setColorAt(0, QColor(0, 0, 0, 10))
        glue.setColorAt(0.85, QColor(0, 0, 0, 14))
        glue.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(QRectF(0, 0, w, h * SAFE[1]), glue)
        p.fillRect(r, _grain())

    def paint_back(self, p: QPainter, w: float, h: float, color: int) -> None:
        base = self.color(color)
        p.fillRect(QRectF(0, 0, w, h), base)
        p.fillRect(QRectF(0, 0, w, h), QColor(255, 255, 255, 92))
        p.fillRect(QRectF(0, 0, w, h), _grain())


class PictureSkin(Skin):
    """A PNG you made."""

    def __init__(self, path: Path):
        super().__init__()
        self.path = Path(path)
        self.key = f"custom:{self.path.name}"
        self.name = self.path.stem
        self.image = QImage(str(self.path)).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        if self.image.isNull():
            raise ValueError(f"Can't read {self.path.name}")
        self.aspect = self.image.width() / self.image.height()
        self._ink = ink_for(self.image)

    def ink(self, color: int) -> QColor:
        return self._ink

    def paint_front(self, p: QPainter, w: float, h: float, color: int) -> None:
        p.drawImage(QRectF(0, 0, w, h), self.image)

    def paint_back(self, p: QPainter, w: float, h: float, color: int) -> None:
        p.drawImage(QRectF(0, 0, w, h), self.image)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        p.fillRect(QRectF(0, 0, w, h), QColor(255, 255, 255, 150))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)


def ink_for(image: QImage) -> QColor:
    """Dark ink on a light safe area, light ink on a dark one."""
    small = image.scaled(60, 60, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    x0, y0 = round(60 * SAFE[0]), round(60 * SAFE[1])
    x1, y1 = round(60 * SAFE[2]), round(60 * SAFE[3])
    total = weight = 0.0
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = small.pixelColor(x, y)
            a = c.alphaF()
            total += a * (0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF())
            weight += a
    luma = total / weight if weight > 0.5 else 1.0      # see-through: the desktop shows, assume light
    return DARK_INK if luma > 0.5 else LIGHT_INK


def all_skins(folder: Path) -> list[Skin]:
    skins: list[Skin] = [Skin()] + [Skin(cycle=False, solid=i) for i in range(NEON_COUNT)]
    for f in sorted(folder.glob("*.png")):
        try:
            skins.append(PictureSkin(f))
        except ValueError:
            pass
    return skins


def skin_for(key: str, folder: Path) -> Skin:
    if key.startswith("solid:"):
        try:
            return Skin(cycle=False, solid=int(key[6:]) % NEON_COUNT)
        except ValueError:
            return Skin()
    if key.startswith("custom:"):
        try:
            return PictureSkin(folder / key[7:])
        except ValueError:
            return Skin()
    return Skin()


def import_skin(source: Path, folder: Path) -> tuple[str, list[str]]:
    """Copy a picture into Peelpad's skins (as PNG). Returns its key and any warnings."""
    source = Path(source)
    image = QImage(str(source))
    if image.isNull():
        raise ValueError("That file isn't a picture Peelpad can read. Use a PNG.")
    notes = []
    if source.suffix.lower() != ".png":
        notes.append("It isn't a PNG, so it has no transparent parts.")
    if min(image.width(), image.height()) < 300:
        notes.append(f"It's only {image.width()} x {image.height()} px, so it may look soft. "
                     f"{TEMPLATE} x {TEMPLATE} px is best.")
    ratio = image.width() / image.height()
    if not 0.5 <= ratio <= 2:
        notes.append("It's very long or very tall; notes will keep that shape.")
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(source.read_bytes()).hexdigest()[:8]
    stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in source.stem).strip() or "skin"
    target = folder / f"{stem[:40]}-{digest}.png"
    if source.suffix.lower() == ".png":
        shutil.copyfile(source, target)
    elif not image.save(str(target), "PNG"):
        raise ValueError("Couldn't save the skin.")
    return f"custom:{target.name}", notes


def save_template(path: Path) -> None:
    """A 600 x 600 guide to design a skin on: the glue band and the safe text area."""
    img = QImage(TEMPLATE, TEMPLATE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor("#F3FF6B"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(QRectF(0, 0, TEMPLATE, GLUE), QColor(0, 0, 0, 30))
    safe = QRectF(SIDE, GLUE, TEMPLATE - 2 * SIDE, TEMPLATE - GLUE - SIDE)
    p.fillRect(safe, QColor(255, 255, 255, 110))
    pen = QPen(QColor("#FF2E9A"), 3, Qt.PenStyle.DashLine)
    p.setPen(pen)
    p.drawRect(safe)
    f = QFont("Segoe UI")
    f.setPixelSize(20)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#1F1D1A"))
    p.drawText(QRectF(0, 0, TEMPLATE, GLUE), Qt.AlignmentFlag.AlignCenter,
               "GLUE BAND  0-96 px  (decoration only, no text)")
    p.drawText(safe.adjusted(0, 16, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
               "SAFE TEXT AREA  480 x 444 px")
    f.setBold(False)
    f.setPixelSize(17)
    p.setFont(f)
    p.drawText(safe.adjusted(24, 60, -24, -24), Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
               "Peelpad skin template\n\n"
               "- Canvas: 600 x 600 px, PNG\n"
               "- Transparent pixels are see-through on your desktop\n"
               "- Keep 60 px free on the left, right and bottom, 96 px at the top\n"
               "- Tasks are written in this box, so keep it calm\n"
               "  (light colours get dark ink, dark ones light ink)\n"
               "- Other sizes work too; notes keep your picture's shape\n\n"
               "Paint over everything here, then upload it in Settings > Look.")
    for x in (SIDE, TEMPLATE - SIDE):
        p.drawText(QRectF(x - 30, TEMPLATE - SIDE + 18, 60, 24), Qt.AlignmentFlag.AlignCenter, f"{x}")
    p.end()
    img.save(str(path), "PNG")


# ---------------------------------------------------------------- whole notes, as pictures

def _draw_check(p: QPainter, box: QRectF, ink: QColor, kind: str, done: bool) -> None:
    pen = QPen(ink, max(1.3, box.width() * 0.11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind != "task":
        c = box.center()
        r = box.width() * 0.12
        p.setBrush(ink)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(c, r, r)
        return
    p.drawRoundedRect(box, box.width() * 0.3, box.width() * 0.3)
    if done:
        tick = QPainterPath()
        tick.moveTo(box.left() + box.width() * 0.22, box.top() + box.height() * 0.52)
        tick.lineTo(box.left() + box.width() * 0.43, box.top() + box.height() * 0.74)
        tick.lineTo(box.left() + box.width() * 0.8, box.top() + box.height() * 0.28)
        p.drawPath(tick)


def right_to_left(text: str) -> bool:
    """Does the text start with a right-to-left letter (Arabic, Hebrew...), as Qt's editor decides?"""
    for ch in text:
        kind = unicodedata.bidirectional(ch)
        if kind in ("R", "AL"):
            return True
        if kind == "L":
            return False
    return False


def check_box(px: int, row_h: int) -> QRectF:
    size = px * 0.95
    return QRectF(0, (row_h - size) / 2, size, size)


def paint_rows(p: QPainter, note: dict, skin: Skin, w: float, h: float, alpha: float = 1.0) -> None:
    """The note's rows, laid out like the live editor does."""
    ink = QColor(skin.ink(note.get("color", 0)))
    ink.setAlphaF(ink.alphaF() * alpha)
    area = safe_rect(w, h)
    px = font_px(w)
    rh = row_height(px)
    gap = px * 0.5
    y = area.top()
    for row in note["rows"]:
        if y + rh > area.bottom() + 1:
            break
        box = check_box(px, rh).translated(area.left(), y)
        if row["text"].strip():
            _draw_check(p, box, ink, row["kind"], row["done"])
        faded = QColor(ink)
        if row["done"]:
            faded.setAlphaF(faded.alphaF() * 0.55)
        p.setPen(faded)
        p.setFont(hand_font(px, row["done"]))
        text_rect = QRectF(box.right() + gap, y, area.right() - box.right() - gap, rh)
        text = p.fontMetrics().elidedText(row["text"], Qt.TextElideMode.ElideRight, int(text_rect.width()))
        side = Qt.AlignmentFlag.AlignRight if right_to_left(row["text"]) else Qt.AlignmentFlag.AlignLeft
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | side, text)
        y += rh


def note_images(note: dict, skin: Skin, w: int, h: int, dpr: float = 1.0) -> tuple[QImage, QImage]:
    """The front (with its writing) and the back of a note, at dpr x its size."""
    out = []
    for side in ("front", "back"):
        img = QImage(max(1, round(w * dpr)), max(1, round(h * dpr)), QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.scale(dpr, dpr)
        if side == "front":
            skin.paint_front(p, w, h, note.get("color", 0))
            paint_rows(p, note, skin, w, h)
        else:
            skin.paint_back(p, w, h, note.get("color", 0))
            # the ink shows through the paper a little
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            paint_rows(p, note, skin, w, h, alpha=0.12)
        p.end()
        out.append(img)
    return out[0], out[1]


def preview(skin: Skin, size: int, color: int = 0) -> QImage:
    img = QImage(size, round(size / (skin.aspect or 1)), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    skin.paint_front(p, img.width(), img.height(), color)
    p.end()
    return img

