"""Five more animated looks, drawn in code so they are sharp at any size:

- Retro LED clock: seven-segment time and date in the colour you pick, a ring of
  LED dots that fills every minute and a pixel bar that grows each minute of the hour
- Aquarium: two fish swim round a frosted card, bubbles rise, seaweed sways
- Night sky: stars twinkle, the moon glows, a shooting star now and then, clouds drift
- Rainy window: drops run down the glass, a cat sleeps on the sill
- Synthwave: a striped sun sets behind palms over an endless neon grid

Everything that moves stays around the card, so the writing in the middle is calm.
The still parts are drawn once per size (see animated.Backdrop).
"""

from __future__ import annotations

import math
import random
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient

from peelpad.animated import Backdrop, now_ms
from peelpad.effects import hue_shift
from peelpad.skins import Skin, cover_with_paper


class Scene(Skin):
    """A drawn, animated look: a still backdrop plus moving parts, and a calm card."""

    key = "anim:scene"
    name = "Scene"
    animated = True
    frame_ms = 40
    card_color = QColor("#FFFFFF")
    ink_color = QColor("#1F1D1A")

    def __init__(self):
        super().__init__(cycle=False)
        self.key, self.name = type(self).key, type(self).name
        self.area = self.auto_area = type(self).AREA
        self.backdrop = Backdrop()

    AREA = (0.16, 0.2, 0.84, 0.76)

    def ink(self, color: int) -> QColor:
        return QColor(self.ink_color)

    def color(self, color: int) -> QColor:
        return QColor(self.card_color)

    def frame_id(self) -> int:
        return int(now_ms() // self.frame_ms)

    def still(self, p: QPainter, w: float, h: float) -> None:
        """The parts that never move."""

    def moving(self, p: QPainter, w: float, h: float, t: float) -> None:
        """The parts that move, at time t (seconds)."""

    def paint_front(self, p: QPainter, w: float, h: float, color: int, t: float | None = None) -> None:
        t = now_ms() / 1000 if t is None else t
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.backdrop.paint(p, w, h, self.still)
        self.moving(p, w, h, t)
        p.restore()

    def paint_back(self, p: QPainter, w: float, h: float, color: int) -> None:
        self.paint_front(p, w, h, color, t=0.0)
        cover_with_paper(p, w, h)


def _rounded(rect: QRectF, r: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, r, r)
    return path


def _card(p: QPainter, rect: QRectF, radius: float, fill, edge: QColor | None = None, shadow: float = 0.18) -> None:
    """A soft-shadowed card, where the writing goes."""
    s = rect.height()
    for i, a in enumerate((0.05, 0.05, 0.06)):
        grow = (3 - i) * s * 0.012
        c = QColor(0, 0, 0, int(255 * a * shadow / 0.18))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(rect.adjusted(-grow, -grow * 0.4, grow, grow * 1.6), radius + grow, radius + grow)
    p.setBrush(fill)
    p.setPen(QPen(edge, max(1.0, s * 0.006)) if edge is not None else Qt.PenStyle.NoPen)
    p.drawRoundedRect(rect, radius, radius)


# ---------------------------------------------------------------- Retro LED clock

class LED:
    """The clock's colour, set from Settings."""
    color = QColor("#FF2B2B")


#   aaa
#  f   b
#   ggg
#  e   c
#   ddd
SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
            "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""}


def _segment(x: float, y: float, w: float, h: float, t: float, name: str) -> QPolygonF:
    """One bar of a seven-segment digit in the box (x, y, w, h), bars t thick."""
    half = t / 2
    if name in "agd":
        cy = {"a": y + half, "g": y + h / 2, "d": y + h - half}[name]
        x0, x1 = x + half + 1, x + w - half - 1
        pts = [(x0, cy), (x0 + half, cy - half), (x1 - half, cy - half), (x1, cy), (x1 - half, cy + half),
               (x0 + half, cy + half)]
    else:
        cx = x + half if name in "fe" else x + w - half
        top = name in "fb"
        y0 = (y + half + 1) if top else (y + h / 2 + 1)
        y1 = (y + h / 2 - 1) if top else (y + h - half - 1)
        pts = [(cx, y0), (cx + half, y0 + half), (cx + half, y1 - half), (cx, y1), (cx - half, y1 - half),
               (cx - half, y0 + half)]
    return QPolygonF([QPointF(px, py) for px, py in pts])


def seven_segment(p: QPainter, rect: QRectF, text: str, on: QColor, off: QColor, slant: float = 0.08) -> None:
    """Digits like an old LED clock: lit bars glow, dark bars stay faintly visible."""
    n = len(text)
    digit_w = rect.width() / max(1, n)
    t = min(digit_w * 0.2, rect.height() * 0.12)
    p.save()
    p.translate(rect.left() + rect.height() * slant, rect.top())
    p.shear(-slant, 0)
    glow = QColor(on)
    glow.setAlpha(70)
    for i, ch in enumerate(text):
        x = i * digit_w + digit_w * 0.08
        w = digit_w * 0.84
        if ch == ":":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(on)
            for fy in (0.32, 0.68):
                p.drawRoundedRect(QRectF(x + w / 2 - t / 2, rect.height() * fy - t / 2, t, t), t * 0.2, t * 0.2)
            continue
        lit = SEGMENTS.get(ch, "")
        for name in "abcdefg":
            poly = _segment(x, 0, w, rect.height(), t, name)
            if name in lit:
                p.setPen(QPen(glow, t * 0.9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.setBrush(on)
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(off)
            p.drawPolygon(poly)
    p.restore()


class LedClock(Scene):
    key = "anim:clock"
    name = "Retro LED clock (animated)"
    frame_ms = 250
    card_color = QColor("#0B0B0F")
    ink_color = QColor("#ECECF2")
    AREA = (0.12, 0.12, 0.88, 0.58)
    DOTS = 60

    def frame_id(self) -> int:
        return int(now_ms() // self.frame_ms) * 1000 + LED.color.rgb() % 1000

    @staticmethod
    def _ring(w: float, h: float) -> QPainterPath:
        s = min(w, h)
        return _rounded(QRectF(0, 0, w, h).adjusted(s * 0.05, s * 0.05, -s * 0.05, -s * 0.05), s * 0.08)

    def still(self, p: QPainter, w: float, h: float) -> None:
        s = min(w, h)
        panel = QRectF(0, 0, w, h).adjusted(s * 0.015, s * 0.015, -s * 0.015, -s * 0.015)
        g = QLinearGradient(panel.topLeft(), panel.bottomLeft())
        g.setColorAt(0, QColor("#16161C"))
        g.setColorAt(1, QColor("#060608"))
        p.setPen(QPen(QColor("#2C2C34"), max(1.0, s * 0.006)))
        p.setBrush(g)
        p.drawRoundedRect(panel, s * 0.1, s * 0.1)
        p.setPen(QPen(QColor(255, 255, 255, 22), max(1.0, s * 0.004)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(panel.adjusted(s * 0.012, s * 0.012, -s * 0.012, -s * 0.012), s * 0.09, s * 0.09)

    def moving(self, p: QPainter, w: float, h: float, t: float) -> None:
        s = min(w, h)
        now = datetime.now()
        on = QColor(LED.color)
        off = QColor(on)
        off.setAlpha(26)
        second_color = hue_shift(on, 200).lighter(125)
        second_off = QColor(second_color)
        second_off.setAlpha(22)
        # the ring: one LED a second, round the whole panel; full when the minute ends
        ring = self._ring(w, h)
        glow = QColor(on)
        glow.setAlpha(60)
        for i in range(self.DOTS):
            pt = ring.pointAtPercent(((i / self.DOTS) + 0.25 / self.DOTS + 0.125) % 1.0)
            lit = i <= now.second
            r = s * 0.011
            p.setPen(Qt.PenStyle.NoPen)
            if lit:
                p.setBrush(glow)
                p.drawEllipse(pt, r * 2.1, r * 2.1)
                p.setBrush(on.lighter(140) if i == now.second else on)
            else:
                p.setBrush(off)
            p.drawEllipse(pt, r, r)
        # the time, big, with the seconds smaller beside it
        colon = ":" if now.microsecond < 500_000 else " "
        big = QRectF(w * 0.13, h * 0.62, w * 0.58, h * 0.17)
        seven_segment(p, big, f"{now.hour:02d}{colon}{now.minute:02d}", on, off)
        seven_segment(p, QRectF(w * 0.73, h * 0.68, w * 0.15, h * 0.11), f"{now.second:02d}", second_color, second_off)
        # the date, and the day in small letters
        seven_segment(p, QRectF(w * 0.13, h * 0.81, w * 0.42, h * 0.065), now.strftime("%d-%m-%y"),
                      second_color, second_off)
        f = QFont("Consolas")
        f.setPixelSize(max(7, round(h * 0.05)))
        f.setBold(True)
        p.setFont(f)
        p.setPen(second_color)
        p.drawText(QRectF(w * 0.58, h * 0.8, w * 0.3, h * 0.075), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   now.strftime("%a").upper())
        # the pixel bar: one pixel more for every minute of the hour
        cells = 60
        bar = QRectF(w * 0.13, h * 0.895, w * 0.74, h * 0.022)
        cw = bar.width() / cells
        for i in range(cells):
            cell = QRectF(bar.left() + i * cw + cw * 0.12, bar.top(), cw * 0.76, bar.height())
            p.fillRect(cell, on if i < now.minute else (on.lighter(150) if i == now.minute and now.second % 2 == 0 else off))


# ---------------------------------------------------------------- Aquarium

WATER_TOP, WATER_BOTTOM = QColor("#56D6EE"), QColor("#0B5A8A")
SAND = QColor("#EBD49B")


def _fish(p: QPainter, c: QPointF, size: float, angle: float, body: QColor, fin: QColor, stripes: bool,
          wag: float) -> None:
    """A round cartoon fish facing along `angle` (radians), its tail wagging by `wag`."""
    p.save()
    p.translate(c)
    p.rotate(-math.degrees(angle))
    if math.cos(angle) < 0:            # swimming left: keep its belly down
        p.scale(1, -1)
    outline = QPen(QColor("#1B1B26"), size * 0.07)
    outline.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    tail = QPainterPath()
    tail.moveTo(-size * 0.45, 0)
    tail.lineTo(-size * 0.95, -size * (0.38 + 0.12 * wag))
    tail.quadTo(QPointF(-size * 0.8, 0), QPointF(-size * 0.95, size * (0.38 - 0.12 * wag)))
    tail.closeSubpath()
    p.setPen(outline)
    p.setBrush(fin)
    p.drawPath(tail)
    top_fin = QPainterPath()
    top_fin.moveTo(-size * 0.2, -size * 0.32)
    top_fin.quadTo(QPointF(0, -size * 0.7), QPointF(size * 0.2, -size * 0.34))
    top_fin.closeSubpath()
    p.drawPath(top_fin)
    p.setBrush(body)
    p.drawEllipse(QPointF(0, 0), size * 0.55, size * 0.38)
    if stripes:
        p.save()
        clip = QPainterPath()
        clip.addEllipse(QPointF(0, 0), size * 0.55, size * 0.38)
        p.setClipPath(clip)
        p.setPen(QPen(QColor("#1B1B26"), size * 0.05))
        p.setBrush(QColor("white"))
        for x in (-size * 0.18, size * 0.2):
            p.drawRect(QRectF(x - size * 0.07, -size * 0.5, size * 0.14, size))
        p.restore()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(size * 0.28, -size * 0.08), size * 0.12, size * 0.12)
    p.setBrush(QColor("#1B1B26"))
    p.drawEllipse(QPointF(size * 0.31, -size * 0.08), size * 0.065, size * 0.065)
    p.setBrush(QColor(255, 140, 160, 150))
    p.drawEllipse(QPointF(size * 0.22, size * 0.12), size * 0.07, size * 0.045)
    p.restore()


class Aquarium(Scene):
    key = "anim:aquarium"
    name = "Aquarium (animated)"
    card_color = QColor("#EEF9FA")
    ink_color = QColor("#12384F")
    AREA = (0.2, 0.2, 0.8, 0.7)

    def __init__(self):
        super().__init__()
        rnd = random.Random(11)
        self.bubbles = [(rnd.choice((0.07, 0.1, 0.9, 0.93)) + rnd.uniform(-0.02, 0.02), rnd.random(),
                         rnd.uniform(0.008, 0.02), rnd.uniform(0.08, 0.16)) for _ in range(14)]

    @staticmethod
    def _tank(w: float, h: float) -> QRectF:
        s = min(w, h)
        return QRectF(0, 0, w, h).adjusted(s * 0.015, s * 0.015, -s * 0.015, -s * 0.015)

    def _card_rect(self, w: float, h: float) -> QRectF:
        return QRectF(w * 0.15, h * 0.15, w * 0.7, h * 0.6)

    def still(self, p: QPainter, w: float, h: float) -> None:
        s = min(w, h)
        tank = self._tank(w, h)
        g = QLinearGradient(tank.topLeft(), tank.bottomLeft())
        g.setColorAt(0, WATER_TOP)
        g.setColorAt(1, WATER_BOTTOM)
        p.setPen(QPen(QColor("#0A3F63"), max(1.0, s * 0.012)))
        p.setBrush(g)
        p.drawRoundedRect(tank, s * 0.08, s * 0.08)
        # sand and pebbles along the bottom
        sand = QPainterPath()
        sand.moveTo(tank.left(), tank.bottom() - s * 0.11)
        sand.cubicTo(QPointF(tank.left() + w * 0.3, tank.bottom() - s * 0.16),
                     QPointF(tank.left() + w * 0.6, tank.bottom() - s * 0.07), QPointF(tank.right(), tank.bottom() - s * 0.12))
        sand.lineTo(tank.right(), tank.bottom())
        sand.lineTo(tank.left(), tank.bottom())
        sand.closeSubpath()
        p.save()
        p.setClipPath(_rounded(tank, s * 0.08))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(SAND)
        p.drawPath(sand)
        rnd = random.Random(5)
        for _ in range(26):
            x = tank.left() + rnd.random() * tank.width()
            y = tank.bottom() - rnd.random() * s * 0.08
            p.setBrush(QColor(rnd.choice(("#C9AE73", "#F7E7BC", "#A88A55", "#8FA3B0"))))
            p.drawEllipse(QPointF(x, y), s * rnd.uniform(0.006, 0.016), s * rnd.uniform(0.005, 0.012))
        p.restore()
        # glass shine
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawRoundedRect(QRectF(tank.left() + s * 0.03, tank.top() + s * 0.03, s * 0.04, tank.height() * 0.5), s * 0.02, s * 0.02)
        _card(p, self._card_rect(w, h), s * 0.05, QColor(238, 249, 250, 240), QColor(255, 255, 255, 200))

    def moving(self, p: QPainter, w: float, h: float, t: float) -> None:
        s = min(w, h)
        tank = self._tank(w, h)
        p.save()
        card = _rounded(self._card_rect(w, h).adjusted(-1, -1, 1, 1), s * 0.05)
        p.setClipPath(_rounded(tank, s * 0.08).subtracted(card))          # never over the writing
        # light rays drifting through the water
        for i in range(4):
            x = tank.left() + ((i * 0.27 + t * 0.03) % 1.2 - 0.1) * tank.width()
            ray = QPolygonF([QPointF(x, tank.top()), QPointF(x + s * 0.07, tank.top()),
                             QPointF(x - s * 0.08, tank.bottom()), QPointF(x - s * 0.18, tank.bottom())])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 18 + int(8 * math.sin(t * 0.8 + i))))
            p.drawPolygon(ray)
        # seaweed swaying in the bottom corners
        for base_x, k in ((0.07, 0), (0.13, 1), (0.88, 2), (0.94, 3)):
            path = QPainterPath()
            bx, by = tank.left() + base_x * w, tank.bottom() - s * 0.04
            path.moveTo(bx, by)
            top = by - s * (0.3 + 0.06 * (k % 2))
            sway = math.sin(t * 1.3 + k) * s * 0.035
            path.cubicTo(QPointF(bx + sway, by - s * 0.1), QPointF(bx - sway, top + s * 0.1), QPointF(bx + sway * 1.4, top))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#1F8A4C") if k % 2 else QColor("#2FB063"), s * 0.022, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            p.drawPath(path)
        # bubbles rising up the sides
        for fx, phase, size, speed in self.bubbles:
            y = 1.0 - ((t * speed + phase) % 1.0)
            x = fx + math.sin(t * 2 + phase * 9) * 0.008
            c = QPointF(tank.left() + x * tank.width(), tank.top() + y * tank.height())
            r = s * size * (0.7 + 0.3 * (1 - y))
            p.setPen(QPen(QColor(255, 255, 255, 170), max(0.8, s * 0.004)))
            p.setBrush(QColor(255, 255, 255, 45))
            p.drawEllipse(c, r, r)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 200))
            p.drawEllipse(c + QPointF(-r * 0.35, -r * 0.35), r * 0.25, r * 0.25)
        p.restore()
        # two fish swimming round the card
        lane = _rounded(self._card_rect(w, h).adjusted(-s * 0.07, -s * 0.075, s * 0.07, s * 0.09), s * 0.09)
        for k, (speed, size, body, fin, stripes) in enumerate((
                (0.045, 0.085, QColor("#FF7A1A"), QColor("#FF9A3C"), True),
                (0.032, 0.075, QColor("#2E6CF6"), QColor("#FFD447"), False))):
            at = (t * speed + k * 0.5) % 1.0
            pt = lane.pointAtPercent(at)
            angle = math.radians(lane.angleAtPercent(at))
            bob = math.sin(t * 3 + k) * s * 0.006
            _fish(p, pt + QPointF(0, bob), s * size, angle, body, fin, stripes, math.sin(t * 9 + k * 2))


# ---------------------------------------------------------------- Night sky

class NightSky(Scene):
    key = "anim:night"
    name = "Night sky (animated)"
    card_color = QColor("#F6F3FF")
    ink_color = QColor("#2B2A55")
    AREA = (0.2, 0.22, 0.8, 0.72)
    SHOOT = 7.0                # a shooting star every this many seconds

    def __init__(self):
        super().__init__()
        rnd = random.Random(3)
        self.stars = []
        while len(self.stars) < 70:
            x, y = rnd.random(), rnd.random()
            if 0.12 < x < 0.88 and 0.14 < y < 0.8:      # not behind the card
                continue
            self.stars.append((x, y, rnd.uniform(0.004, 0.011), rnd.uniform(0, 6.3), rnd.uniform(1.5, 4)))

    @staticmethod
    def _sky(w: float, h: float) -> QRectF:
        s = min(w, h)
        return QRectF(0, 0, w, h).adjusted(s * 0.015, s * 0.015, -s * 0.015, -s * 0.015)

    def still(self, p: QPainter, w: float, h: float) -> None:
        s = min(w, h)
        sky = self._sky(w, h)
        g = QLinearGradient(sky.topLeft(), sky.bottomLeft())
        g.setColorAt(0, QColor("#0A0F2C"))
        g.setColorAt(0.65, QColor("#1E1B4B"))
        g.setColorAt(1, QColor("#3A2A6A"))
        p.setPen(QPen(QColor("#2A2660"), max(1.0, s * 0.01)))
        p.setBrush(g)
        p.drawRoundedRect(sky, s * 0.08, s * 0.08)
        # the moon, with its glow
        moon = QPointF(sky.right() - s * 0.13, sky.top() + s * 0.11)
        halo = QRadialGradient(moon, s * 0.16)
        halo.setColorAt(0, QColor(255, 244, 194, 90))
        halo.setColorAt(1, QColor(255, 244, 194, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(moon, s * 0.16, s * 0.16)
        crescent = QPainterPath()
        crescent.addEllipse(moon, s * 0.065, s * 0.065)
        bite = QPainterPath()
        bite.addEllipse(moon + QPointF(-s * 0.03, -s * 0.018), s * 0.058, s * 0.058)
        p.setBrush(QColor("#FFF4C2"))
        p.drawPath(crescent.subtracted(bite))
        card = QRectF(w * 0.15, h * 0.17, w * 0.7, h * 0.6)
        _card(p, card, s * 0.05, self.card_color, None, shadow=0.35)

    def moving(self, p: QPainter, w: float, h: float, t: float) -> None:
        s = min(w, h)
        sky = self._sky(w, h)
        p.save()
        p.setClipPath(_rounded(sky, s * 0.08))
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, r, phase, speed in self.stars:
            k = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * speed + phase))
            c = QPointF(sky.left() + x * sky.width(), sky.top() + y * sky.height())
            p.setBrush(QColor(255, 255, 240, int(255 * k)))
            p.drawEllipse(c, s * r * k, s * r * k)
            if r > 0.009:                               # the bigger ones sparkle in a cross
                p.setPen(QPen(QColor(255, 255, 240, int(160 * k)), max(0.6, s * 0.002)))
                p.drawLine(c - QPointF(s * r * 2.2 * k, 0), c + QPointF(s * r * 2.2 * k, 0))
                p.drawLine(c - QPointF(0, s * r * 2.2 * k), c + QPointF(0, s * r * 2.2 * k))
                p.setPen(Qt.PenStyle.NoPen)
        # a shooting star now and then, across the top
        k = (t % self.SHOOT) / 0.9
        if k < 1:
            head = QPointF(sky.left() + sky.width() * (0.1 + 0.7 * k), sky.top() + s * (0.03 + 0.08 * k))
            tail = head - QPointF(s * 0.22, s * 0.025)
            g = QLinearGradient(tail, head)
            g.setColorAt(0, QColor(255, 255, 255, 0))
            g.setColorAt(1, QColor(255, 255, 255, int(230 * (1 - k * 0.6))))
            p.setPen(QPen(g, s * 0.008, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(tail, head)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("white"))
            p.drawEllipse(head, s * 0.008, s * 0.008)
        # clouds drifting along the bottom
        for k, (y, speed, size) in enumerate(((0.86, 0.012, 0.11), (0.93, 0.008, 0.14))):
            x = ((t * speed + k * 0.5) % 1.4) - 0.2
            c = QPointF(sky.left() + x * sky.width(), sky.top() + y * sky.height())
            p.setBrush(QColor(201, 198, 240, 120))
            for dx, dy, r in ((-0.9, 0.15, 0.55), (-0.35, -0.2, 0.75), (0.3, -0.1, 0.65), (0.85, 0.15, 0.5)):
                p.drawEllipse(c + QPointF(dx * s * size, dy * s * size), r * s * size, r * s * size * 0.8)
        p.restore()


# ---------------------------------------------------------------- Rainy window

WOOD, WOOD_DARK = QColor("#9A6233"), QColor("#6E421F")


class RainyWindow(Scene):
    key = "anim:rain"
    name = "Rainy window (animated)"
    card_color = QColor("#FFF8EC")
    ink_color = QColor("#3A2A1E")
    AREA = (0.2, 0.2, 0.8, 0.6)

    def __init__(self):
        super().__init__()
        rnd = random.Random(8)
        self.drops = []
        while len(self.drops) < 34:
            x = rnd.uniform(0.07, 0.93)
            if 0.14 < x < 0.86 and rnd.random() < 0.7:  # most run down the sides, some over the top
                continue
            self.drops.append((x, rnd.random(), rnd.uniform(0.05, 0.16), rnd.uniform(0.006, 0.012)))

    @staticmethod
    def _card_rect(w: float, h: float) -> QRectF:
        return QRectF(w * 0.15, h * 0.15, w * 0.7, h * 0.56)

    @staticmethod
    def _glass(w: float, h: float) -> QRectF:
        s = min(w, h)
        return QRectF(0, 0, w, h).adjusted(s * 0.06, s * 0.06, -s * 0.06, -h * 0.2)

    def still(self, p: QPainter, w: float, h: float) -> None:
        s = min(w, h)
        frame = QRectF(0, 0, w, h).adjusted(s * 0.015, s * 0.015, -s * 0.015, -s * 0.015)
        g = QLinearGradient(frame.topLeft(), frame.bottomRight())
        g.setColorAt(0, WOOD.lighter(112))
        g.setColorAt(1, WOOD_DARK)
        p.setPen(QPen(QColor("#4A2C14"), max(1.0, s * 0.008)))
        p.setBrush(g)
        p.drawRoundedRect(frame, s * 0.05, s * 0.05)
        rnd = random.Random(2)
        p.setPen(QPen(QColor(60, 30, 10, 50), max(0.7, s * 0.003)))
        for _ in range(18):                               # wood grain
            y = frame.top() + rnd.random() * frame.height()
            p.drawLine(QPointF(frame.left() + s * 0.01, y), QPointF(frame.right() - s * 0.01, y + rnd.uniform(-3, 3)))
        glass = self._glass(w, h)
        dusk = QLinearGradient(glass.topLeft(), glass.bottomLeft())
        dusk.setColorAt(0, QColor("#2C3E5C"))
        dusk.setColorAt(1, QColor("#7B8FB8"))
        p.setPen(QPen(QColor("#4A2C14"), max(1.0, s * 0.01)))
        p.setBrush(dusk)
        p.drawRect(glass)
        p.save()
        p.setClipRect(glass)
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(16):                               # blurry city lights outside
            c = QPointF(glass.left() + rnd.random() * glass.width(), glass.top() + glass.height() * rnd.uniform(0.45, 1))
            r = s * rnd.uniform(0.02, 0.05)
            light = QRadialGradient(c, r)
            col = QColor(rnd.choice(("#FFD38A", "#FFB86B", "#FFF0C2", "#9FD3FF")))
            col.setAlpha(150)
            light.setColorAt(0, col)
            col.setAlpha(0)
            light.setColorAt(1, col)
            p.setBrush(light)
            p.drawEllipse(c, r, r)
        p.restore()
        # the window bars
        p.setPen(QPen(WOOD_DARK, s * 0.02))
        p.drawLine(QPointF(glass.center().x(), glass.top()), QPointF(glass.center().x(), glass.bottom()))
        # the sill
        sill = QRectF(frame.left() - s * 0.005, h * 0.8, frame.width() + s * 0.01, h * 0.06)
        p.setPen(QPen(QColor("#4A2C14"), max(1.0, s * 0.006)))
        p.setBrush(WOOD.lighter(118))
        p.drawRoundedRect(sill, s * 0.015, s * 0.015)
        # a little plant pot on the sill
        pot = QRectF(w * 0.8, h * 0.72, w * 0.09, h * 0.08)
        p.setBrush(QColor("#D9714E"))
        p.drawRoundedRect(pot, s * 0.01, s * 0.01)
        _card(p, self._card_rect(w, h), s * 0.03, self.card_color, None, shadow=0.3)
        tape = QRectF(w * 0.42, h * 0.13, w * 0.16, h * 0.045)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 214, 150, 190))
        p.drawRect(tape)

    def moving(self, p: QPainter, w: float, h: float, t: float) -> None:
        s = min(w, h)
        glass = self._glass(w, h)
        p.save()
        outside = QPainterPath()
        outside.addRect(glass)
        p.setClipPath(outside.subtracted(_rounded(self._card_rect(w, h).adjusted(-1, -1, 1, 1), s * 0.03)))
        for x, phase, speed, size in self.drops:
            y = (t * speed + phase) % 1.15 - 0.05
            c = QPointF(glass.left() + (x - 0.06) / 0.88 * glass.width(), glass.top() + y * glass.height())
            r = s * size
            trail = QLinearGradient(c - QPointF(0, r * 6), c)
            trail.setColorAt(0, QColor(255, 255, 255, 0))
            trail.setColorAt(1, QColor(255, 255, 255, 70))
            p.setPen(QPen(trail, r * 0.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(c - QPointF(0, r * 6), c)
            drop = QPainterPath()
            drop.moveTo(c.x(), c.y() - r * 1.6)
            drop.quadTo(QPointF(c.x() + r, c.y() - r * 0.2), QPointF(c.x(), c.y() + r))
            drop.quadTo(QPointF(c.x() - r, c.y() - r * 0.2), QPointF(c.x(), c.y() - r * 1.6))
            p.setPen(QPen(QColor(255, 255, 255, 140), max(0.6, s * 0.003)))
            p.setBrush(QColor(200, 225, 255, 90))
            p.drawPath(drop)
        p.restore()
        # leaves of the plant, nodding
        base = QPointF(w * 0.845, h * 0.72)
        for k, a in enumerate((-50, -20, 10, 40)):
            ang = math.radians(a - 90 + 6 * math.sin(t * 1.6 + k))
            tip = base + QPointF(math.cos(ang), math.sin(ang)) * s * 0.085
            leaf = QPainterPath()
            leaf.moveTo(base)
            leaf.quadTo(base + (tip - base) * 0.5 + QPointF(s * 0.03, 0), tip)
            leaf.quadTo(base + (tip - base) * 0.5 - QPointF(s * 0.03, 0), base)
            p.setPen(QPen(QColor("#1F6E3A"), max(0.8, s * 0.004)))
            p.setBrush(QColor("#3FA35A"))
            p.drawPath(leaf)
        # the cat, asleep on the sill: breathing, its tail tip moving, a z now and then
        self._cat(p, QPointF(w * 0.3, h * 0.8), s * 0.1, t)

    @staticmethod
    def _cat(p: QPainter, base: QPointF, r: float, t: float) -> None:
        breathe = 1 + 0.035 * math.sin(t * 2.2)
        fur, dark = QColor("#F3A55B"), QColor("#3A2416")
        p.save()
        p.translate(base)
        tail = QPainterPath()
        tail.moveTo(r * 0.9, -r * 0.15)
        tail.cubicTo(QPointF(r * 1.6, -r * 0.1), QPointF(r * 1.5, -r * (0.7 + 0.15 * math.sin(t * 1.4))),
                     QPointF(r * 1.15, -r * (0.75 + 0.2 * math.sin(t * 1.4))))
        p.setPen(QPen(dark, r * 0.32, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(tail)
        p.setPen(QPen(fur, r * 0.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(tail)
        p.setPen(QPen(dark, r * 0.08))
        p.setBrush(fur)
        p.drawEllipse(QRectF(-r * 1.0, -r * 0.75 * breathe, r * 2.0, r * 0.8 * breathe))
        head = QPointF(-r * 0.75, -r * 0.45)
        for k in (-1, 1):
            ear = QPolygonF([head + QPointF(k * r * 0.12, -r * 0.2), head + QPointF(k * r * 0.42, -r * 0.62),
                             head + QPointF(k * r * 0.48, -r * 0.1)])
            p.drawPolygon(ear)
        p.drawEllipse(head, r * 0.5, r * 0.42)
        p.setPen(QPen(dark, r * 0.07, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for k in (-1, 1):                                  # closed eyes
            e = head + QPointF(k * r * 0.2, -r * 0.02)
            p.drawArc(QRectF(e.x() - r * 0.1, e.y() - r * 0.06, r * 0.2, r * 0.14), 200 * 16, 140 * 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 140, 160, 160))
        for k in (-1, 1):
            p.drawEllipse(head + QPointF(k * r * 0.3, r * 0.14), r * 0.08, r * 0.05)
        cycle = (t % 3.0) / 3.0                           # a z floats up and fades
        f = QFont("Segoe UI")
        f.setBold(True)
        f.setPixelSize(max(6, round(r * (0.35 + 0.25 * cycle))))
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, int(230 * (1 - cycle))))
        p.drawText(head + QPointF(r * 0.5 + cycle * r * 0.7, -r * 0.4 - cycle * r * 0.45), "z")
        p.restore()


# ---------------------------------------------------------------- Synthwave

NEON_PINK, NEON_CYAN = QColor("#FF2EE6"), QColor("#22E3FF")


class Synthwave(Scene):
    key = "anim:synth"
    name = "Synthwave (animated)"
    card_color = QColor("#170A2E")
    ink_color = QColor("#7DF9FF")
    glow = True
    AREA = (0.2, 0.3, 0.8, 0.66)

    def __init__(self):
        super().__init__()
        rnd = random.Random(4)
        self.stars = [(rnd.uniform(0.04, 0.96), rnd.uniform(0.03, 0.2), rnd.uniform(0, 6.3)) for _ in range(22)]

    @staticmethod
    def _box(w: float, h: float) -> QRectF:
        s = min(w, h)
        return QRectF(0, 0, w, h).adjusted(s * 0.015, s * 0.015, -s * 0.015, -s * 0.015)

    @staticmethod
    def _card_rect(w: float, h: float) -> QRectF:
        return QRectF(w * 0.15, h * 0.26, w * 0.7, h * 0.44)

    def still(self, p: QPainter, w: float, h: float) -> None:
        s = min(w, h)
        box = self._box(w, h)
        sky = QLinearGradient(box.topLeft(), box.bottomLeft())
        sky.setColorAt(0, QColor("#12062B"))
        sky.setColorAt(0.45, QColor("#4A0E63"))
        sky.setColorAt(0.74, QColor("#FF3D8B"))
        sky.setColorAt(0.75, QColor("#14072A"))
        sky.setColorAt(1, QColor("#0B0418"))
        p.setPen(QPen(QColor("#3B145E"), max(1.0, s * 0.01)))
        p.setBrush(sky)
        p.drawRoundedRect(box, s * 0.08, s * 0.08)
        # palms, as silhouettes, on both sides of the horizon
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0B0418"))
        for x, k in ((0.1, 1), (0.9, -1)):
            trunk_base = QPointF(box.left() + x * box.width(), box.top() + 0.75 * box.height())
            crown = trunk_base + QPointF(k * s * 0.03, -s * 0.3)
            trunk = QPainterPath()
            trunk.moveTo(trunk_base + QPointF(-s * 0.012, 0))
            trunk.quadTo(trunk_base + QPointF(k * s * 0.05, -s * 0.15), crown)
            trunk.quadTo(trunk_base + QPointF(k * s * 0.07, -s * 0.15), trunk_base + QPointF(s * 0.012, 0))
            p.drawPath(trunk)
            for a in (-160, -120, -75, -35, 10):
                ang = math.radians(a if k > 0 else -180 - a)
                tip = crown + QPointF(math.cos(ang), math.sin(ang) + 0.35) * s * 0.12
                frond = QPainterPath()
                frond.moveTo(crown)
                frond.quadTo(crown + (tip - crown) * 0.5 + QPointF(0, -s * 0.035), tip)
                frond.quadTo(crown + (tip - crown) * 0.5 + QPointF(0, -s * 0.01), crown)
                p.drawPath(frond)
        card = self._card_rect(w, h)
        for i, a in enumerate((26, 40, 70)):              # a neon glow round the glass panel
            c = QColor(NEON_CYAN)
            c.setAlpha(a)
            p.setPen(QPen(c, s * (0.024 - i * 0.008)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(card, s * 0.03, s * 0.03)
        p.setPen(QPen(NEON_CYAN, max(1.0, s * 0.005)))
        p.setBrush(QColor(23, 10, 46, 238))
        p.drawRoundedRect(card, s * 0.03, s * 0.03)

    def moving(self, p: QPainter, w: float, h: float, t: float) -> None:
        s = min(w, h)
        box = self._box(w, h)
        horizon = box.top() + 0.75 * box.height()
        p.save()
        # (behind the glass panel: the sun and stars never cover the writing)
        p.setClipPath(_rounded(box, s * 0.08).subtracted(_rounded(self._card_rect(w, h), s * 0.03)))
        # the sun, slowly sinking stripes cut out of it
        sun_c = QPointF(box.center().x(), box.top() + box.height() * 0.2)
        sun_r = s * 0.17
        sun = QPainterPath()
        sun.addEllipse(sun_c, sun_r, sun_r)
        cuts = QPainterPath()
        for i in range(6):
            y = sun_c.y() + sun_r * (0.05 + ((i / 6 + t * 0.05) % 1.0))
            cuts.addRect(QRectF(sun_c.x() - sun_r, y, sun_r * 2, sun_r * 0.03 + sun_r * 0.05 * ((y - sun_c.y()) / sun_r)))
        g = QLinearGradient(sun_c - QPointF(0, sun_r), sun_c + QPointF(0, sun_r))
        g.setColorAt(0, QColor("#FFE45C"))
        g.setColorAt(1, QColor("#FF2E88"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawPath(sun.subtracted(cuts))
        for x, y, phase in self.stars:
            k = 0.5 + 0.5 * math.sin(t * 2.5 + phase)
            p.setBrush(QColor(255, 255, 255, int(80 + 170 * k)))
            p.drawEllipse(QPointF(box.left() + x * box.width(), box.top() + y * box.height()), s * 0.004 * (1 + k), s * 0.004 * (1 + k))
        # the grid rushing towards you under the horizon
        p.setClipRect(QRectF(box.left(), horizon, box.width(), box.bottom() - horizon))
        glow = QColor(NEON_PINK)
        glow.setAlpha(60)
        for pen in (QPen(glow, s * 0.012), QPen(NEON_PINK, max(0.8, s * 0.004))):
            p.setPen(pen)
            for i in range(-9, 10):                       # lines to the vanishing point
                x_far = box.center().x() + i * s * 0.03
                x_near = box.center().x() + i * s * 0.2
                p.drawLine(QPointF(x_far, horizon), QPointF(x_near, box.bottom() + s * 0.05))
            for i in range(8):                            # rungs coming closer
                k = ((i + t * 0.9) % 8) / 8
                y = horizon + (box.bottom() - horizon) * k * k
                p.drawLine(QPointF(box.left(), y), QPointF(box.right(), y))
        p.restore()
        p.setPen(QPen(NEON_PINK, max(1.0, s * 0.006)))
        p.drawLine(QPointF(box.left() + s * 0.02, horizon), QPointF(box.right() - s * 0.02, horizon))


SCENES = [LedClock, Aquarium, NightSky, RainyWindow, Synthwave]
BY_KEY = {cls.key: cls for cls in SCENES}
