"""The stage: a small see-through, click-through window where paper moves
while it is off the pad or between states (peeling, carried, dropped,
crumpled). Each moving thing is an actor with step() and paint().
"""

from __future__ import annotations

import math

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPolygonF,
                           QRadialGradient, QTransform)
from PySide6.QtWidgets import QWidget

from peelpad import physics
from peelpad.physics import Shape


def _poly(points, k: float = 1.0) -> QPolygonF:
    return QPolygonF([QPointF(x * k, y * k) for x, y in points])


def affine3(src, dst) -> QTransform:
    """The affine map taking triangle src onto triangle dst."""
    (sx0, sy0), (sx1, sy1), (sx2, sy2) = src
    (dx0, dy0), (dx1, dy1), (dx2, dy2) = dst
    a, b, c, d = sx1 - sx0, sx2 - sx0, sy1 - sy0, sy2 - sy0
    det = a * d - b * c
    if abs(det) < 1e-9:
        return QTransform(0, 0, 0, 0, dx0, dy0)
    ia, ib, ic, id_ = d / det, -b / det, -c / det, a / det
    e, f, g, h = dx1 - dx0, dx2 - dx0, dy1 - dy0, dy2 - dy0
    m11, m12 = e * ia + f * ic, e * ib + f * id_        # x' = m11 x + m12 y
    m21, m22 = g * ia + h * ic, g * ib + h * id_        # y' = m21 x + m22 y
    tx = dx0 - m11 * sx0 - m12 * sy0
    ty = dy0 - m21 * sx0 - m22 * sy0
    return QTransform(m11, m21, m12, m22, tx, ty)


def quad_map(src: QPolygonF, dst: QPolygonF) -> QTransform | None:
    t = QTransform()
    ok = QTransform.quadToQuad(src, dst, t)
    if isinstance(ok, QTransform):           # some PySide6 versions return the transform
        return ok
    return t if ok else None


class Painted:
    """A shape ready to paint: per band its map, its outline on screen and its look."""

    def __init__(self, shape: Shape, k: float):
        self.items = []
        self.shape = shape
        self.k = k
        xs, ys = [], []
        for band in shape.bands:
            t = quad_map(_poly(band.src, k), _poly(band.dst))
            if t is None:
                continue
            poly = _poly(band.poly, k)
            screen = t.map(poly)
            for i in range(screen.size()):
                pt = screen.at(i)
                xs.append(pt.x())
                ys.append(pt.y())
            self.items.append((band, t, poly, screen))
        self.bounds = QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)) if xs else QRectF()


def paint_bands(p: QPainter, painted: Painted, front: QImage, back: QImage, origin: QPointF,
                shadow: float = 1.0) -> None:
    base = QTransform.fromTranslate(-origin.x(), -origin.y())
    fb, bb = QBrush(front), QBrush(back)
    p.setPen(Qt.PenStyle.NoPen)
    # shadows of the lifted parts first, soft by stacking a few
    if shadow > 0:
        for band, t, poly, screen in painted.items:
            if band.z <= 0.5:
                continue
            for spread, alpha in ((1.0, 7), (0.8, 7), (0.6, 8), (0.4, 9), (0.2, 10)):
                off = QPointF(band.z * 0.14 * spread + 1, band.z * 0.24 * spread + 1.5)
                p.setTransform(base)
                p.setBrush(QColor(0, 0, 0, int(alpha * shadow)))
                p.drawPolygon(screen.translated(off))
    fold = painted.shape.fold_line
    for band, t, poly, screen in painted.items:
        p.setTransform(t * base)
        p.setBrush(bb if band.back else fb)
        p.drawPolygon(poly)
        if abs(band.shade) > 0.01:
            c = QColor(255, 255, 255) if band.shade > 0 else QColor(0, 0, 0)
            c.setAlphaF(min(1.0, abs(band.shade)))
            p.setBrush(c)
            p.drawPolygon(poly)
        if fold is not None and band.z == 0.0:
            _curl_shadow(p, band, fold, t, base, painted.k)


def _curl_shadow(p: QPainter, band, fold, t: QTransform, base: QTransform, k: float) -> None:
    """The flat sheet darkens next to the curl, where the roll blocks the light."""
    foot, n, r = fold
    k0 = foot[0] * n[0] + foot[1] * n[1]
    strip = physics.slab(band.poly, n, k0 - r * 1.6, k0)
    if len(strip) < 3:
        return
    g = QLinearGradient(QPointF((foot[0] - n[0] * r * 1.6) * k, (foot[1] - n[1] * r * 1.6) * k),
                        QPointF(foot[0] * k, foot[1] * k))
    g.setColorAt(0, QColor(0, 0, 0, 0))
    g.setColorAt(1, QColor(0, 0, 0, 60))
    p.setTransform(t * base)
    p.setBrush(QBrush(g))
    p.drawPolygon(_poly(strip, k))


class Stage(QWidget):
    """A see-through, click-through window only as big as the paper moving in it.
    It grows or moves when the paper gets near its edge, and goes away the moment
    the paper stops, so nothing ever sits over the rest of the screen."""

    ROOM = 140          # spare room around the paper, so the window rarely has to move

    def __init__(self, stages: "Stages"):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.stages = stages
        self.actors: list = []
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(15)
        self.timer.timeout.connect(self.tick)
        self.clock = QElapsedTimer()
        self.dirty = QRectF()

    def add(self, actor) -> None:
        actor.stage = self
        self.actors.append(actor)
        actor.step(0.0)
        self._refresh()
        if not self.isVisible():
            self.show()
        self.raise_()
        if not self.timer.isActive():
            self.clock.start()
            self.timer.start()

    def tick(self) -> None:
        dt = min(0.05, self.clock.restart() / 1000)
        self.actors = [a for a in self.actors if a.step(dt)]
        if self.actors:
            self._refresh()
            return
        self.timer.stop()
        self.hide()
        self.stages.done(self)

    def _needed(self) -> QRectF:
        now = QRectF()
        for a in self.actors:
            now = now.united(a.bounds())
        return now.adjusted(-36, -30, 48, 56)          # the shadows reach down and right

    def _refresh(self) -> None:
        needed = self._needed()
        if needed.isEmpty():
            return
        here = QRectF(self.geometry())
        if not here.contains(needed):
            room = needed.adjusted(-self.ROOM, -self.ROOM, self.ROOM, self.ROOM).toAlignedRect()
            self.setGeometry(room)
            self.dirty = needed
            self.update()
            return
        area = self.dirty.united(needed)
        self.dirty = needed
        self.update(area.translated(-here.topLeft()).toAlignedRect())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(event.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        origin = QPointF(self.geometry().topLeft())
        for a in self.actors:
            a.paint(p, origin)
        p.end()


class Stages:
    """A small stage for each moving piece of paper, gone when it stops."""

    def __init__(self):
        self.live: set[Stage] = set()

    def at(self, global_pt: QPointF | None = None) -> Stage:
        stage = Stage(self)
        self.live.add(stage)
        return stage

    def done(self, stage: Stage) -> None:
        self.live.discard(stage)
        stage.deleteLater()


def _ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


class PeelActor:
    """The pad's top sheet: peeled, torn off, carried, dropped, or let go back."""

    DETACH_FOLD = 0.3          # share of the glue band the flap has pulled up

    def __init__(self, sheet: QRectF, grab: QPointF, front: QImage, back: QImage, k: float, glue: float,
                 on_landed, on_returned, on_torn=None):
        self.stage: Stage | None = None
        self.sheet = QRectF(sheet)
        self.w, self.h = sheet.width(), sheet.height()
        self.g = (grab.x() - sheet.left(), grab.y() - sheet.top())
        self.front, self.back, self.k, self.glue = front, back, k, glue
        self.on_landed, self.on_returned, self.on_torn = on_landed, on_returned, on_torn
        self.cursor = QPointF(grab)
        self.state = "peel"
        self.r = min(self.w, self.h) * 0.075
        self.lifts: dict[tuple, physics.Lift] = {}
        self.painted: Painted | None = None
        self.vel = QPointF()
        self.angle = self.spin = 0.0
        self.wave = self.wave_v = 0.0
        self.phase = 0.0
        self.lift = 0.0
        self.unfold = 1.0
        self.detach_pull = (0.0, 0.0)
        self.back_v = QPointF()
        self.linger = 0.0
        self.t = 0.0

    # input from the pad
    def move(self, global_pt: QPointF) -> None:
        if self.state in ("peel", "carry"):
            self.cursor = QPointF(global_pt)

    def release(self) -> None:
        if self.state == "peel":
            self.state = "back"
        elif self.state == "carry":
            self.state = "drop"
            self.t = 0.0
            self.drop_from = (self.angle, self.lift, self.wave)

    # physics
    def _local(self) -> tuple[float, float]:
        return self.cursor.x() - self.sheet.left(), self.cursor.y() - self.sheet.top()

    def _peel_shape(self, c) -> tuple[Shape, bool]:
        g = self.g
        dx, dy = c[0] - g[0], c[1] - g[1]
        inward = (self.w / 2 - g[0]) * dx + (self.h / 2 - g[1]) * dy
        pull = math.hypot(dx, dy)
        if pull < 0.5:
            return physics.identity(self.w, self.h), False
        if inward >= 0:
            shape = physics.fold(self.w, self.h, g, c, self.r)
            torn = physics.fold_reaches(self.w, self.h, g, c, self.r, self.glue) > self.DETACH_FOLD \
                or pull > max(self.w, self.h) * 1.15
            return shape, torn
        d = (round(dx / pull, 2), round(dy / pull, 2))
        lift = self.lifts.get(d)
        if lift is None:
            n = math.hypot(*d) or 1
            lift = self.lifts[d] = physics.Lift(self.w, self.h, g, (d[0] / n, d[1] / n))
        shape = lift.shape(pull)
        return shape, shape.stretch > 0

    def _offset(self, shape: Shape) -> Shape:
        ox, oy = self.sheet.left(), self.sheet.top()
        return physics.move_shape(shape, lambda q: (q[0] + ox, q[1] + oy))

    def step(self, dt: float) -> bool:
        if self.state == "peel":
            c = self._local()
            shape, torn = self._peel_shape(c)
            if torn:
                self.state = "carry"
                self.unfold = 0.0
                self.detach_pull = (c[0] - self.g[0], c[1] - self.g[1])
                self.lift = min(self.w, self.h) * 0.05
                if self.on_torn:
                    self.on_torn()
            else:
                self.painted = Painted(self._offset(shape), self.k)
                return True
        if self.state == "back":
            c = self._local()
            # a quick spring pulls the grabbed point home, with a little overshoot
            ax = -260 * (c[0] - self.g[0]) - 20 * self.back_v.x()
            ay = -260 * (c[1] - self.g[1]) - 20 * self.back_v.y()
            self.back_v += QPointF(ax * dt, ay * dt)
            self.cursor += self.back_v * dt
            c = self._local()
            if math.hypot(c[0] - self.g[0], c[1] - self.g[1]) < 0.6 and abs(self.back_v.x()) + abs(self.back_v.y()) < 20:
                self.on_returned()
                return False
            shape, _ = self._peel_shape(c)
            self.painted = Painted(self._offset(shape), self.k)
            return True
        if self.state in ("carry", "drop"):
            return self._carry(dt)
        if self.state == "landed":
            self.linger -= dt
            return self.linger > 0
        return False

    def _carry(self, dt: float) -> bool:
        size = min(self.w, self.h)
        if dt > 0:
            if not hasattr(self, "_last"):
                self._last = QPointF(self.cursor)
            v = (self.cursor - self._last) / dt
            self._last = QPointF(self.cursor)
            self.vel = self.vel * 0.75 + v * 0.25
        speed = math.hypot(self.vel.x(), self.vel.y())
        bx, by = self.w / 2 - self.g[0], self.h / 2 - self.g[1]
        bl = math.hypot(bx, by) or 1
        if self.state == "carry":
            # the sheet trails behind the way it is pulled, and ripples with the speed
            target = max(-0.42, min(0.42, (by * self.vel.x() - bx * self.vel.y()) / bl * 0.0006))
            self.angle, self.spin = physics.spring(self.angle, self.spin, target, 60, 9, dt)
            self.wave, self.wave_v = physics.spring(self.wave, self.wave_v, min(speed * 0.012, size * 0.09), 40, 8, dt)
            self.phase += dt * (7 + speed * 0.008)
            self.unfold = min(1.0, self.unfold + dt / 0.22)
        else:
            self.t += dt
            e = _ease_out(self.t / 0.32)
            a0, l0, w0 = self.drop_from
            self.angle, self.lift, self.wave = a0 * (1 - e), l0 * (1 - e), w0 * (1 - e)
            self.phase += dt * 6
        at = (self.cursor.x(), self.cursor.y())
        if self.unfold < 1.0:
            e = _ease_out(self.unfold)
            pull = (self.g[0] + self.detach_pull[0] * (1 - e), self.g[1] + self.detach_pull[1] * (1 - e))
            shape = physics.fold(self.w, self.h, self.g, pull, self.r)
            shape = physics.move_shape(shape, physics.turn_about(pull, at, self.angle))
        else:
            shape = physics.flutter(self.w, self.h, self.g, at, self.angle, self.wave, self.phase, self.lift)
        self.painted = Painted(shape, self.k)
        if self.state == "drop" and self.t >= 0.32:
            self.state = "landed"
            self.linger = 0.35
            self.on_landed(QRectF(self.cursor.x() - self.g[0], self.cursor.y() - self.g[1], self.w, self.h))
        return True

    def bounds(self) -> QRectF:
        return self.painted.bounds if self.painted else QRectF(self.sheet)

    def paint(self, p: QPainter, origin: QPointF) -> None:
        if self.painted:
            paint_bands(p, self.painted, self.front, self.back, origin)
            p.resetTransform()


class CrumpleActor:
    """A finished note scrunches into a ball, then pops away."""

    SQUEEZE, VANISH = 0.85, 0.42

    def __init__(self, sheet: QRectF, front: QImage, back: QImage, k: float, seed, on_done=None):
        self.stage = None
        self.sheet = QRectF(sheet)
        self.front, self.back, self.k = front, back, k
        self.model = physics.Crumple(sheet.width(), sheet.height(), seed)
        self.on_done = on_done
        self.t = 0.0
        self.facets = []
        self.scale = 1.0
        self.opacity = 1.0
        self.drop = 0.0

    def step(self, dt: float) -> bool:
        self.t += dt
        squeeze = min(1.0, self.t / self.SQUEEZE)
        self.facets = self.model.frame(squeeze)
        late = (self.t - self.SQUEEZE - 0.12) / self.VANISH
        if late > 0:
            x = min(1.0, late)
            self.scale = max(0.0, 1 + 0.12 * math.sin(math.pi * min(1, x * 2.2)) - x ** 2.2)
            self.opacity = 1 - x ** 3
            self.drop = 26 * x * x
        if late >= 1:
            if self.on_done:
                self.on_done()
            return False
        return True

    def bounds(self) -> QRectF:
        r = QRectF(self.sheet)
        return r.adjusted(-r.width() * 0.2, -r.height() * 0.2, r.width() * 0.2, r.height() * 0.3)

    def paint(self, p: QPainter, origin: QPointF) -> None:
        c = self.sheet.center() - origin + QPointF(0, self.drop)
        base = QTransform.fromTranslate(c.x(), c.y()).scale(self.scale, self.scale)
        p.setOpacity(self.opacity)
        p.setPen(Qt.PenStyle.NoPen)
        # a soft shadow under the ball, smaller as it rolls up
        squeeze = min(1.0, self.t / self.SQUEEZE)
        sw = self.sheet.width() * (1 - 0.55 * squeeze)
        p.setTransform(base.scale(1.0, 0.3))
        centre = QPointF(sw * 0.04, (self.sheet.height() * (0.5 - 0.28 * squeeze) + 6) / 0.3)
        glow = QRadialGradient(centre, sw * 0.6)
        glow.setColorAt(0, QColor(0, 0, 0, 70))
        glow.setColorAt(0.6, QColor(0, 0, 0, 30))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow))
        p.drawEllipse(centre, sw * 0.6, sw * 0.6)
        base = QTransform.fromTranslate(c.x(), c.y()).scale(self.scale, self.scale)
        fb, bb = QBrush(self.front), QBrush(self.back)
        k = self.k
        for f in self.facets:
            cx = sum(x for x, _ in f.src) / 3
            cy = sum(y for _, y in f.src) / 3
            src = [(cx + (x - cx) * 1.06, cy + (y - cy) * 1.06) for x, y in f.src]   # hide seams
            src = [(min(max(x, 0), self.sheet.width()) * k, min(max(y, 0), self.sheet.height()) * k) for x, y in src]
            t = affine3([(x * k, y * k) for x, y in f.src], f.dst)
            p.setTransform(t * base)
            poly = _poly(src)
            p.setBrush(bb if f.back else fb)
            p.drawPolygon(poly)
            if abs(f.shade) > 0.01:
                col = QColor(255, 255, 255) if f.shade > 0 else QColor(0, 0, 0)
                col.setAlphaF(min(1.0, abs(f.shade)))
                p.setBrush(col)
                p.drawPolygon(poly)
        p.resetTransform()
        p.setOpacity(1.0)
