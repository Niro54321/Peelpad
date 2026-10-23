"""The pad: a block of sticky notes. Write on the top sheet, then pull it off
(from anywhere on the paper that isn't writing) and drop it where you want it.
Ctrl+Enter peels it off for you.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QMenu, QToolTip

from peelpad import store
from peelpad.note import MARGIN, Paper, paper_image, round_button, shadow_image
from peelpad.skins import GLUE, TEMPLATE, note_images
from peelpad.stage import PeelActor

WIDTH = 300
BLOCK = 13       # how thick the pad looks
BAR = 40
LAYERS = 7


class Pad(Paper):
    def __init__(self, app):
        super().__init__(app, app.store.draft, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setWindowTitle("Peelpad")
        self.press: QPointF | None = None
        self.actor: PeelActor | None = None
        self.peeling = False
        self._layers: dict = {}
        self.editor.submit.connect(self.auto_peel)
        self.buttons = [round_button(self, "⚙", "Settings, stats and history", app.show_settings),
                        round_button(self, "–", "Minimise to the taskbar", self.showMinimized)]
        self.resize_for_skin()
        self.set_on_top(app.store.data["pad"]["on_top"])

    # geometry
    def paper_size(self) -> tuple[int, int]:
        aspect = self.skin().aspect or 1.0
        width = int(self.app.store.data.get("note_size", WIDTH))
        return width, round(width / aspect)

    def paper_rect(self) -> QRectF:
        w, h = self.paper_size()
        return QRectF(MARGIN, MARGIN, w, h)

    def global_paper(self) -> QRectF:
        return self.paper_rect().translated(QPointF(self.geometry().topLeft()))

    def resize_for_skin(self) -> None:
        w, h = self.paper_size()
        self.setFixedSize(w + 2 * MARGIN, h + BLOCK + BAR + 2 * MARGIN)
        self._layers = {}
        self.bind()

    def set_on_top(self, on: bool) -> None:
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        if visible:
            self.show()

    def new_draft(self) -> None:
        self.note = self.app.store.draft
        self.bind()

    # painting
    def _layer(self, color: int, depth: int = 0):
        """A sheet of the pad, `depth` sheets down (darker the deeper), and its shadow.
        Only the paper is darkened, never the see-through parts of a shaped skin."""
        w, h = self.paper_size()
        dpr = self.devicePixelRatioF()
        key = (self.skin().key, color, w, h, dpr, depth)
        if key not in self._layers:
            img = paper_image(self.skin(), w, h, color, dpr)
            if depth:
                p = QPainter(img)
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                p.fillRect(QRectF(0, 0, w, h), QColor(0, 0, 0, 10 + 3 * depth))
                p.end()
            self._layers[key] = (img, shadow_image(img, MARGIN, dpr) if not depth else None)
        return self._layers[key]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = self.paper_rect()
        top = self.note["color"]
        img, shadow = self._layer(top)
        p.drawImage(QPointF(r.left() - MARGIN, r.top() - MARGIN + BLOCK), shadow)
        # the sheets under the top one, their edges showing as the pad's side
        shaped = self.skin().aspect is not None or self.skin().animated
        for i in range(LAYERS, 0, -1):
            layer, _ = self._layer((top + i) % 4, i)
            y = r.top() + BLOCK * i / LAYERS
            p.drawImage(QPointF(r.left(), y), layer)
            if not shaped:
                p.setPen(QPen(QColor(0, 0, 0, 30), 0.7))
                p.drawLine(QPointF(r.left() + 1, y + r.height() - 0.4), QPointF(r.right() - 1, y + r.height() - 0.4))
        if self.peeling:
            under, _ = self._layer((top + 1) % 4)
            p.drawImage(r.topLeft(), under)
        else:
            self.paint_paper(p)
            if self.hover and store.has_content(self.note) and self.skin().aspect is None and not self.skin().animated:
                self._dog_ear(p, r)
        self.paint_bar(p)
        p.end()

    def _dog_ear(self, p: QPainter, r: QRectF) -> None:
        """A hint that the sheet can be peeled: its corner lifts a little."""
        s = r.width() * 0.09
        c = QPointF(r.right(), r.bottom())
        under, _ = self._layer((self.note["color"] + 1) % 4)
        corner = QPainterPath()
        corner.moveTo(c - QPointF(s, 0))
        corner.lineTo(c)
        corner.lineTo(c - QPointF(0, s))
        corner.closeSubpath()
        p.save()
        p.setClipPath(corner)
        p.drawImage(r.topLeft(), under)
        p.restore()
        curl = QPainterPath()
        curl.moveTo(c - QPointF(s, 0))
        curl.quadTo(c - QPointF(s * 0.9, s * 0.9), c - QPointF(0, s))
        curl.lineTo(c - QPointF(s * 0.95, s * 0.95))
        curl.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawPath(curl.translated(1.5, 2))
        back = QColor(self.skin().color(self.note["color"])).lighter(112)
        p.setBrush(back)
        p.drawPath(curl)

    # peeling
    def mousePressEvent(self, event):
        pos = event.position()
        if event.button() == Qt.MouseButton.RightButton:
            self.menu(event.globalPosition().toPoint())
            return
        if event.button() != Qt.MouseButton.LeftButton or self.actor:
            return
        if self.on_paper(pos):
            self.press = pos
        else:
            self.windowHandle().startSystemMove()

    def mouseMoveEvent(self, event):
        g = event.globalPosition()
        if self.actor:
            self.actor.move(g)
            return
        if self.press is None:
            return
        if (event.position() - self.press).manhattanLength() < 5:
            return
        start = self.press
        self.press = None
        if not store.has_content(self.note):
            self.wiggle()
            QToolTip.showText(QCursor.pos(), "Write something on it first", self)
            return
        self.start_peel(QPointF(self.geometry().topLeft()) + start)
        self.actor.move(g)

    def mouseReleaseEvent(self, event):
        if self.actor:
            self.actor.release()
        elif self.press is not None:
            self.editor.focus_end()
        self.press = None

    def bar_rect(self) -> QRectF:
        r = self.paper_rect()
        return QRectF(0, r.bottom() + BLOCK, self.width(), self.height() - r.bottom() - BLOCK)

    def start_peel(self, grab_global: QPointF, by_hand: bool = True) -> None:
        w, h = self.paper_size()
        dpr = max(1.0, self.devicePixelRatioF())
        front, back = note_images(self.note, self.skin(), w, h, dpr)
        self.actor = PeelActor(self.global_paper(), grab_global, front, back, dpr, h * GLUE / TEMPLATE,
                               on_landed=self._landed, on_returned=self._returned, follow=by_hand)
        self.peeling = True
        self.editor.hide()
        self.app.stages.at(grab_global, follow=True).add(self.actor)
        self.update()

    def _returned(self) -> None:
        self.actor = None
        self.peeling = False
        self.editor.show()
        self.update()

    def _landed(self, rect: QRectF) -> None:
        self.actor = None
        self.app.peeled(rect)
        self.peeling = False
        self.new_draft()
        self.editor.show()
        self.update()

    def auto_peel(self) -> None:
        """Ctrl+Enter: the top sheet peels off by itself and lands beside the pad."""
        if self.actor or not store.has_content(self.note):
            if not store.has_content(self.note):
                self.wiggle()
            return
        r = self.global_paper()
        grab = QPointF(r.right() - r.width() * 0.1, r.bottom() - r.height() * 0.06)
        landing = self.app.free_spot(r)
        mid = grab + QPointF(-r.width() * 0.45, -r.height() * 0.55)
        end = landing + (grab - r.topLeft())
        self.start_peel(grab, by_hand=False)
        anim = QVariantAnimation(self)
        anim.setDuration(1150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.Linear)

        def at(t: float) -> QPointF:
            if t < 0.4:
                e = math.sin(t / 0.4 * math.pi / 2)
                return grab + (mid - grab) * e
            e = (t - 0.4) / 0.6
            e = e * e * (3 - 2 * e)
            arc = QPointF(0, -math.sin(e * math.pi) * r.height() * 0.25)
            return mid + (end - mid) * e + arc

        anim.valueChanged.connect(lambda t: self.actor and self.actor.move(at(t)))
        anim.finished.connect(lambda: self.actor and self.actor.release())
        anim.start(QVariantAnimation.DeletionPolicy.DeleteWhenStopped)

    def wiggle(self) -> None:
        x0 = self.x()
        anim = QVariantAnimation(self)
        anim.setDuration(380)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.valueChanged.connect(lambda t: self.move(round(x0 + 7 * math.sin(t * math.pi * 5) * (1 - t)), self.y()))
        anim.start(QVariantAnimation.DeletionPolicy.DeleteWhenStopped)

    def menu(self, at) -> None:
        m = QMenu(self)
        m.addAction("Settings && stats", self.app.show_settings)
        top = m.addAction("Keep the pad on top")
        top.setCheckable(True)
        top.setChecked(self.app.store.data["pad"]["on_top"])
        top.toggled.connect(self.app.set_pad_on_top)
        m.addAction("Hide the pad", self.hide)
        m.addSeparator()
        m.addAction("Quit Peelpad", self.app.quit)
        m.exec(at)

    def wheelEvent(self, event):
        """Ctrl + wheel changes the size of the pad's sheets."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and not self.actor:
            step = 20 if event.angleDelta().y() > 0 else -20
            self.app.set_note_size(self.app.store.data.get("note_size", WIDTH) + step)

    def moveEvent(self, event):
        if not self.actor:
            QTimer.singleShot(0, self._save_pos)

    def _save_pos(self) -> None:
        self.app.store.data["pad"]["pos"] = [self.x(), self.y()]
        self.app.changed()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
