"""What a note looks like: neon paper, a theme (black with glowing blue ink,
plain white...), colours you pick, a picture you made (still or animated), or
the animated Skull parade. Also the writing: its font, size, ink colour and
effect (Solid, Gradient, Neon, Toon, Pop, Gummy, Prism).

A custom skin is a PNG, ideally 600 x 600 px. It is stretched to the note.
Transparent pixels are see-through on the desktop (and clicks go through them).
Text is written inside the safe area: 60 px in from the left, right and bottom,
96 px from the top (the top band is where the glue is, and where you grab a
pinned note).
"""

from __future__ import annotations

import hashlib
import random
import shutil
import unicodedata
from dataclasses import dataclass
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


@dataclass
class Writing:
    """Choices about the writing that hold for every note (set from Settings)."""
    family: str = ""                 # empty: the handwriting default
    scale: float = 1.0
    ink: QColor | None = None        # None: the skin's own ink
    effect: str = "auto"             # auto: the skin's own (Neon on the glowing themes)


WRITING = Writing()


def safe_rect(w: float, h: float, area: tuple = SAFE) -> QRectF:
    """Where the writing goes, for a note w x h. `area` is (left, top, right, bottom) as fractions."""
    return QRectF(w * area[0], h * area[1], w * (area[2] - area[0]), h * (area[3] - area[1]))


def font_px(w: float) -> int:
    return max(8, round(w * 0.058 * WRITING.scale))


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
    f = QFont(WRITING.family or hand_family())
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
    """One look. `color` is the note's neon colour (0..3), which other looks ignore."""

    key = "neon"
    name = "Neon (a new colour each sheet)"
    aspect: float | None = None          # width / height of a picture skin
    glow = False                         # the ink shines
    area: tuple = SAFE                   # the text box (fractions); you can move it in Settings
    auto_area: tuple = SAFE              # where Peelpad would put it
    animated = False                     # moves: notes redraw it every frame_ms
    frame_ms = 0

    def frame_id(self) -> int:
        """Which picture of the animation is showing now (always 0 for a still skin)."""
        return 0

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
        dark = base.lightnessF() < 0.35
        light = QLinearGradient(0, 0, w * 0.4, h)
        light.setColorAt(0, QColor(255, 255, 255, 22 if dark else 46))
        light.setColorAt(0.55, QColor(255, 255, 255, 0))
        light.setColorAt(1, QColor(0, 0, 0, 30 if dark else 16))
        p.fillRect(r, light)
        glue = QLinearGradient(0, 0, 0, h * SAFE[1])
        tone = QColor(255, 255, 255) if dark else QColor(0, 0, 0)
        for at, alpha in ((0, 10), (0.85, 14), (1, 0)):
            tone.setAlpha(alpha)
            glue.setColorAt(at, tone)
        p.fillRect(QRectF(0, 0, w, h * SAFE[1]), glue)
        p.fillRect(r, _grain())

    def paint_back(self, p: QPainter, w: float, h: float, color: int) -> None:
        base = self.color(color)
        p.fillRect(QRectF(0, 0, w, h), base)
        p.fillRect(QRectF(0, 0, w, h), QColor(255, 255, 255, 40 if base.lightnessF() < 0.35 else 92))
        p.fillRect(QRectF(0, 0, w, h), _grain())


class ColorSkin(Skin):
    """One paper colour and one ink: a theme, or the colours you picked."""

    def __init__(self, key: str, name: str, paper: str, ink: str, glow: bool = False):
        self.cycle, self.solid = False, 0
        self.key, self.name = key, name
        self.paper, self._ink, self.glow = QColor(paper), QColor(ink), glow

    def color(self, color: int) -> QColor:
        return QColor(self.paper)

    def ink(self, color: int) -> QColor:
        return QColor(self._ink)


THEMES = [
    ("theme:midnight", "Midnight: black paper, glowing blue ink", "#111318", "#3DB2FF", True),
    ("theme:neon-night", "Neon night: black paper, glowing pink ink", "#14101A", "#FF4FD8", True),
    ("theme:toxic", "Toxic: black paper, glowing green ink", "#0F1410", "#5CFF6B", True),
    ("theme:white", "Paper white", "#FAFAF6", "#1F1D1A", False),
    ("theme:kraft", "Kraft", "#C9A47C", "#2A1E14", False),
]


def mine_skin(mine: dict) -> ColorSkin:
    return ColorSkin("mine", "Your colours", mine.get("paper", "#1B1E2B"), mine.get("ink", "#7DF9FF"),
                     bool(mine.get("glow", True)))


class PictureSkin(Skin):
    """A PNG you made."""

    def __init__(self, path: Path, image: QImage | None = None):
        super().__init__(cycle=False)
        self.path = Path(path)
        self.key = f"custom:{self.path.name}"
        self.name = self.path.stem
        if image is None:
            image = QImage(str(self.path))
        self.image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        if self.image.isNull():
            raise ValueError(f"Can't read {self.path.name}")
        self.aspect = self.image.width() / self.image.height()
        self.area = self.auto_area = detect_area(self.image)
        self._ink = ink_for(self.image, self.area)

    def ink(self, color: int) -> QColor:
        return self._ink

    def paint_front(self, p: QPainter, w: float, h: float, color: int) -> None:
        p.drawImage(QRectF(0, 0, w, h), self.image)

    def paint_back(self, p: QPainter, w: float, h: float, color: int) -> None:
        p.drawImage(QRectF(0, 0, w, h), self.image)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        p.fillRect(QRectF(0, 0, w, h), QColor(255, 255, 255, 150))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)


def detect_area(image: QImage) -> tuple:
    """Find the calm middle of a picture, where text fits: walk out from the centre
    along a few rows and columns until the colour changes or the picture ends.
    A frame gets its inside, a round sticker its middle; a busy picture the default."""
    n = 160
    small = image.scaled(n, n, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    middle = small.pixelColor(n // 2, n // 2)
    if middle.alpha() < 200:
        return SAFE

    def same(x: int, y: int) -> bool:
        c = small.pixelColor(x, y)
        return c.alpha() > 200 and (abs(c.red() - middle.red()) + abs(c.green() - middle.green())
                                    + abs(c.blue() - middle.blue())) < 70

    lefts, rights, tops, bottoms = [], [], [], []
    for off in (-n // 5, -n // 10, 0, n // 10, n // 5):
        row, col = n // 2 + off, n // 2 + off
        x = n // 2
        while x > 0 and same(x - 1, row):
            x -= 1
        lefts.append(x)
        x = n // 2
        while x < n - 1 and same(x + 1, row):
            x += 1
        rights.append(x + 1)
        y = n // 2
        while y > 0 and same(col, y - 1):
            y -= 1
        tops.append(y)
        y = n // 2
        while y < n - 1 and same(col, y + 1):
            y += 1
        bottoms.append(y + 1)
    left, right = sorted(lefts)[-2] / n, sorted(rights)[1] / n         # ignore one stray row
    top, bottom = sorted(tops)[-2] / n, sorted(bottoms)[1] / n
    inset_x, inset_y = (right - left) * 0.07, (bottom - top) * 0.07
    left, right, top, bottom = left + inset_x, right - inset_x, top + inset_y, bottom - inset_y
    if right - left < 0.3 or bottom - top < 0.25:
        return SAFE
    return round(left, 3), round(top, 3), round(right, 3), round(bottom, 3)


def ink_for(image: QImage, area: tuple = SAFE) -> QColor:
    """Dark ink on a light text area, light ink on a dark one."""
    small = image.scaled(60, 60, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    x0, y0 = round(60 * area[0]), round(60 * area[1])
    x1, y1 = round(60 * area[2]), round(60 * area[3])
    total = weight = 0.0
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = small.pixelColor(x, y)
            a = c.alphaF()
            total += a * (0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF())
            weight += a
    luma = total / weight if weight > 0.5 else 1.0      # see-through: the desktop shows, assume light
    return DARK_INK if luma > 0.5 else LIGHT_INK


def text_effect(skin: Skin) -> str:
    if WRITING.effect and WRITING.effect != "auto":
        return WRITING.effect
    return "neon" if skin.glow else "solid"


def writing_colors(skin: Skin, color: int) -> tuple[QColor, QColor | None]:
    """The ink to write with, and the colour of its glow (None: no glow).
    Neon ink keeps its colour, a touch brighter, and shines in that colour."""
    ink = QColor(WRITING.ink) if WRITING.ink is not None else skin.ink(color)
    if text_effect(skin) != "neon":
        return ink, None
    return QColor(ink).lighter(118), ink


PICTURES = ("*.png", "*.gif", "*.webp")


def picture_files(folder: Path) -> list[Path]:
    return sorted(f for pattern in PICTURES for f in folder.glob(pattern))


def picture_skin(path: Path) -> PictureSkin:
    from peelpad.animated import AnimatedSkin, is_animated

    return AnimatedSkin(path) if is_animated(path) else PictureSkin(path)


def all_skins(folder: Path, mine: dict | None = None) -> list[Skin]:
    from peelpad.animated import SkullParade

    skins: list[Skin] = [Skin()] + [Skin(cycle=False, solid=i) for i in range(NEON_COUNT)]
    skins += [ColorSkin(*t) for t in THEMES]
    skins.append(mine_skin(mine or {}))
    skins.append(SkullParade())
    for f in picture_files(folder):
        try:
            skins.append(picture_skin(f))
        except ValueError:
            pass
    return skins


def skin_for(key: str, folder: Path, mine: dict | None = None, areas: dict | None = None) -> Skin:
    skin = _skin_for(key, folder, mine)
    area = (areas or {}).get(skin.key)
    if area and len(area) == 4:
        skin.area = tuple(area)
    return skin


def _skin_for(key: str, folder: Path, mine: dict | None = None) -> Skin:
    if key.startswith("solid:"):
        try:
            return Skin(cycle=False, solid=int(key[6:]) % NEON_COUNT)
        except ValueError:
            return Skin()
    if key.startswith("theme:"):
        return next((ColorSkin(*t) for t in THEMES if t[0] == key), Skin())
    if key == "mine":
        return mine_skin(mine or {})
    if key == "anim:skulls":
        from peelpad.animated import SkullParade

        return SkullParade()
    if key.startswith("custom:"):
        try:
            return picture_skin(folder / key[7:])
        except (ValueError, OSError):
            return Skin()
    return Skin()


def clear_fake_background(path: Path) -> bool:
    """Many "transparent" PNGs online have the grey-and-white checkerboard painted
    in. If the picture's border is such a checkerboard, make it truly see-through
    (only what is joined to the border, so a white middle stays). True if it did."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    img = Image.open(path).convert("RGBA")
    w, h = img.size
    light = img.convert("L")
    grey = ImageChops.subtract(img.convert("RGB").convert("HSV").getchannel("S"), Image.new("L", img.size, 0))
    candidate = ImageChops.multiply(light.point(lambda v: 255 if v >= 180 else 0),
                                    grey.point(lambda v: 255 if v <= 22 else 0))
    alpha = img.getchannel("A")
    candidate = ImageChops.multiply(candidate, alpha.point(lambda v: 255 if v > 200 else 0))
    # is the border a checkerboard: two tones, both common?
    edge = [(x, y) for x in range(0, w, max(1, w // 120)) for y in (0, 1, h - 2, h - 1)]
    edge += [(x, y) for y in range(0, h, max(1, h // 120)) for x in (0, 1, w - 2, w - 1)]
    tones = [light.getpixel(p) for p in edge if candidate.getpixel(p)]
    if len(tones) < len(edge) * 0.8:
        return False
    bright = sum(t >= 245 for t in tones)
    if not (0.15 < bright / len(tones) < 0.85):
        return False
    # flood the checkerboard in from the border, on a small copy, then apply it at full size
    k = max(1, max(w, h) // 360)
    small = candidate.resize((w // k, h // k), Image.Resampling.NEAREST)
    sw, sh = small.size
    for x, y in [(x, 0) for x in range(sw)] + [(x, sh - 1) for x in range(sw)] + \
                [(0, y) for y in range(sh)] + [(sw - 1, y) for y in range(sh)]:
        if small.getpixel((x, y)) == 255:
            ImageDraw.floodfill(small, (x, y), 128)
    flooded = small.point(lambda v: 255 if v == 128 else 0).resize((w, h), Image.Resampling.NEAREST)
    flooded = flooded.filter(ImageFilter.MaxFilter(3))
    gone = ImageChops.multiply(flooded, candidate)
    img.putalpha(ImageChops.subtract(alpha, gone))
    img.save(path)
    return True


def import_skin(source: Path, folder: Path) -> tuple[str, list[str]]:
    """Copy a picture into Peelpad's skins. Returns its key and any warnings.
    Animated GIF, APNG and WebP are kept as they are; still pictures become PNG."""
    from peelpad.animated import AnimatedSkin, is_animated

    source = Path(source)
    if is_animated(source):
        skin = AnimatedSkin(source)
        folder.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(source.read_bytes()).hexdigest()[:8]
        stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in source.stem).strip() or "skin"
        target = folder / f"{stem[:40]}-{digest}{source.suffix.lower()}"
        shutil.copyfile(source, target)
        notes = []
        if min(skin.frames[0].width(), skin.frames[0].height()) < 300:
            notes.append(f"It's only {skin.frames[0].width()} x {skin.frames[0].height()} px, so it may look soft.")
        if len(skin.frames) >= 150:
            notes.append("It has a lot of frames; Peelpad plays the first 150.")
        return f"custom:{target.name}", notes
    image = QImage(str(source))
    if image.isNull():
        raise ValueError("That file isn't a picture Peelpad can read. Use a PNG.")
    notes = []
    if source.suffix.lower() != ".png" and not image.hasAlphaChannel():
        notes.append("It has no transparent parts, so the note will be its whole rectangle.")
    if min(image.width(), image.height()) < 300:
        notes.append(f"It's only {image.width()} x {image.height()} px, so it may look soft. "
                     f"{TEMPLATE} x {TEMPLATE} px is best.")
    ratio = image.width() / image.height()
    if not 0.5 <= ratio <= 2:
        notes.append("It's very long or very tall; new notes will take that shape.")
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(source.read_bytes()).hexdigest()[:8]
    stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in source.stem).strip() or "skin"
    target = folder / f"{stem[:40]}-{digest}.png"
    if source.suffix.lower() == ".png":
        shutil.copyfile(source, target)
    elif not image.save(str(target), "PNG"):
        raise ValueError("Couldn't save the skin.")
    if clear_fake_background(target):
        notes.append("Its checkerboard background was painted in, not transparent; Peelpad removed it.")
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
               "- Other sizes work too; new notes take your picture's shape\n\n"
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


def paint_rows(p: QPainter, note: dict, skin: Skin, w: float, h: float, alpha: float = 1.0,
               ink: QColor | None = None, effect: str = "solid") -> None:
    """The note's rows, laid out like the live editor does."""
    from peelpad.effects import draw_text

    ink = QColor(ink if ink is not None else writing_colors(skin, note.get("color", 0))[0])
    ink.setAlphaF(ink.alphaF() * alpha)
    area = safe_rect(w, h, skin.area)
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
        text_rect = QRectF(box.right() + gap + 2, y, area.right() - box.right() - gap - 4, rh)
        draw_text(p, text_rect, row["text"], hand_font(px), ink, effect, right_to_left(row["text"]), row["done"])
        y += rh


def bloom(layer: QImage, color: QColor, size: float) -> QImage:
    """The neon light around whatever is drawn on `layer`: a bright tight halo
    and a wide soft one, in `color`. `size` is the text size in pixels."""
    from PIL import Image, ImageChops, ImageFilter

    rgba = layer.convertToFormat(QImage.Format.Format_RGBA8888)
    a = Image.frombuffer("RGBA", (rgba.width(), rgba.height()), bytes(rgba.constBits()), "raw", "RGBA",
                         rgba.bytesPerLine(), 1).getchannel("A")
    tight = a.filter(ImageFilter.GaussianBlur(max(1.0, size * 0.12))).point(lambda v: min(255, int(v * 1.7)))
    wide = a.filter(ImageFilter.GaussianBlur(max(2.0, size * 0.45))).point(lambda v: min(200, int(v * 1.25)))
    halo = ImageChops.add(tight, wide)
    solid = Image.new("RGB", a.size, (color.red(), color.green(), color.blue()))
    out = Image.merge("RGBA", (*solid.split(), halo))
    img = QImage(out.tobytes(), out.width, out.height, out.width * 4, QImage.Format.Format_RGBA8888).copy()
    img.setDevicePixelRatio(layer.devicePixelRatio())
    return img


def paint_writing(p: QPainter, note: dict, skin: Skin, w: float, h: float, dpr: float) -> None:
    """The rows on a front, with their neon glow if the ink shines."""
    core, glow = writing_colors(skin, note.get("color", 0))
    if glow is None:
        paint_rows(p, note, skin, w, h, ink=core, effect=text_effect(skin))
        return
    layer = QImage(max(1, round(w * dpr)), max(1, round(h * dpr)), QImage.Format.Format_ARGB32_Premultiplied)
    layer.fill(Qt.GlobalColor.transparent)
    q = QPainter(layer)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    q.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    q.scale(dpr, dpr)
    paint_rows(q, note, skin, w, h, ink=core, effect="neon")
    q.end()
    halo = bloom(layer, glow, font_px(w) * dpr)
    p.save()
    p.resetTransform()
    p.drawImage(0, 0, halo)
    p.drawImage(0, 0, layer)
    p.restore()


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
            paint_writing(p, note, skin, w, h, dpr)
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
    if skin.key != "neon" and not skin.animated:
        sample = {"color": color, "rows": [{"text": "Aa", "kind": "task", "done": False}]}
        paint_writing(p, sample, skin, img.width(), img.height(), 1.0)
    p.end()
    return img
