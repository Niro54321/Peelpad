"""A note pinned on the desktop: always on top, moved by dragging the paper,
resized from its bottom-right corner. When every task is checked it crumples.
"""

from __future__ import annotations

from PIL import Image, ImageFilter
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QImage, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QPushButton, QWidget

from peelpad import store
from peelpad.editor import TaskEditor
from peelpad.skins import NEON, Skin, font_px, safe_rect, writing_colors

MARGIN = 18          # room around the paper for its shadow (and the pin)
GRIP = 22            # the corner that resizes
MIN_SIZE = 90
MAX_SIZE = 1400


def shadow_image(paper: QImage, margin: int, dpr: float) -> QImage:
    """A soft drop shadow in the paper's own shape (so cut-out skins get one too)."""
    w, h = paper.width(), paper.height()
    m = round(margin * dpr)
    alpha = paper.convertToFormat(QImage.Format.Format_RGBA8888)
    a = Image.frombuffer("RGBA", (w, h), bytes(alpha.constBits()), "raw", "RGBA", alpha.bytesPerLine(), 1).getchannel("A")
    mask = Image.new("L", (w + 2 * m, h + 2 * m), 0)
    mask.paste(a.point(lambda v: v * 70 // 255), (m, m + round(5 * dpr)))
    mask = mask.filter(ImageFilter.GaussianBlur(7 * dpr))
    rgba = Image.merge("RGBA", (Image.new("L", mask.size, 0),) * 3 + (mask,))
    out = QImage(rgba.tobytes(), rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888).copy()
    out.setDevicePixelRatio(dpr)
    return out


def paper_image(skin: Skin, w: int, h: int, color: int, dpr: float) -> QImage:
    img = QImage(round(w * dpr), round(h * dpr), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(dpr, dpr)
    skin.paint_front(p, w, h, color)
    p.end()
    img.setDevicePixelRatio(dpr)
    return img


def draw_pin(p: QPainter, at: QPointF, r: float, color: QColor) -> None:
    """A push pin seen from above, with its shadow on the paper."""
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 55))
    p.drawEllipse(at + QPointF(r * 0.45, r * 0.6), r * 0.95, r * 0.8)
    g = QRadialGradient(at - QPointF(r * 0.35, r * 0.4), r * 1.4)
    g.setColorAt(0, color.lighter(165))
    g.setColorAt(0.45, color)
    g.setColorAt(1, color.darker(150))
    p.setBrush(g)
    p.setPen(QPen(QColor(0, 0, 0, 70), 0.8))
    p.drawEllipse(at, r, r)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 170))
    p.drawEllipse(at - QPointF(r * 0.35, r * 0.4), r * 0.28, r * 0.22)
    p.restore()


class Paper(QWidget):
    """A window that shows one note's paper and its writing."""

    def __init__(self, app, note: dict, flags):
        super().__init__(None, flags)
        self.app, self.note = app, note
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.editor = TaskEditor(self)
        self.editor.changed.connect(app.changed)
        self.editor.wrote.connect(app.wrote)
        self._cache_key = None
        self._paper = self._shadow = None

    def paper_rect(self) -> QRectF:
        raise NotImplementedError

    def skin(self) -> Skin:
        return self.app.skin

    def refresh_look(self) -> None:
        self._cache_key = None
        r = self.paper_rect()
        area = safe_rect(r.width(), r.height()).translated(r.topLeft())
        m = round(font_px(r.width()) * 0.7)       # the editor's own margin, room for a neon halo
        self.editor.setGeometry(area.adjusted(-m, -m, m, m).toAlignedRect())
        ink, glow = self._writing()
        self.editor.set_look(ink, font_px(r.width()), glow)
        self.update()

    def bind(self) -> None:
        r = self.paper_rect()
        ink, glow = self._writing()
        self.editor.bind(self.note, ink, font_px(r.width()), glow)
        self.refresh_look()

    def _writing(self):
        return writing_colors(self.skin(), self.note["color"])

    def paint_paper(self, p: QPainter, color: int | None = None) -> None:
        r = self.paper_rect()
        color = self.note["color"] if color is None else color
        dpr = self.devicePixelRatioF()
        key = (round(r.width()), round(r.height()), self.skin().key, color, dpr)
        if key != self._cache_key:
            self._paper = paper_image(self.skin(), key[0], key[1], color, dpr)
            self._shadow = shadow_image(self._paper, MARGIN, dpr)
            self._cache_key = key
        p.drawImage(QPointF(r.left() - MARGIN, r.top() - MARGIN), self._shadow)
        p.drawImage(r.topLeft(), self._paper)

    def on_paper(self, pos: QPointF) -> bool:
        """Is this point on the paper (not on a see-through part of a skin)?"""
        r = self.paper_rect()
        if not r.contains(pos) or self._paper is None:
            return r.contains(pos)
        dpr = self._paper.devicePixelRatio()
        x, y = int((pos.x() - r.left()) * dpr), int((pos.y() - r.top()) * dpr)
        if 0 <= x < self._paper.width() and 0 <= y < self._paper.height():
            return self._paper.pixelColor(x, y).alpha() > 20
        return False


class NoteWindow(Paper):
    closed = Signal(object)

    def __init__(self, app, note: dict):
        super().__init__(app, note, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Peelpad note")
        x, y, w, h = note["rect"]
        self.setGeometry(round(x - MARGIN), round(y - MARGIN), round(w + 2 * MARGIN), round(h + 2 * MARGIN))
        self.resizing = None
        self.finish_timer = QTimer(self)
        self.finish_timer.setSingleShot(True)
        self.finish_timer.setInterval(800)
        self.finish_timer.timeout.connect(self._maybe_finish)
        self.editor.toggled.connect(self._toggled)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(300)
        self.save_timer.timeout.connect(self._save_rect)
        self.buttons = []
        for text, tip, slot in (("✓", "Done: crumple it", self.done),
                                ("●", "Next colour", self.next_color),
                                ("✕", "Throw it away", self.throw_away)):
            b = QPushButton(text, self)
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(slot)
            b.hide()
            self.buttons.append(b)
        self.confirm_timer = QTimer(self)
        self.confirm_timer.setSingleShot(True)
        self.confirm_timer.setInterval(2200)
        self.confirm_timer.timeout.connect(lambda: self.buttons[2].setText("✕"))
        self.bind()

    def paper_rect(self) -> QRectF:
        return QRectF(MARGIN, MARGIN, self.width() - 2 * MARGIN, self.height() - 2 * MARGIN)

    def global_paper(self) -> QRectF:
        return self.paper_rect().translated(QPointF(self.geometry().topLeft()))

    def refresh_look(self) -> None:
        super().refresh_look()
        r = self.paper_rect()
        size = max(18, round(r.height() * 0.1))
        ink = self.editor.ink
        dark = ink.lightnessF() < 0.5
        fill, hover = ("255,255,255,70", "255,255,255,170") if dark else ("0,0,0,80", "0,0,0,150")
        for i, b in enumerate(reversed(self.buttons)):
            b.setGeometry(round(r.right() - 8 - (i + 1) * (size + 4)), round(r.top() + 6), size, size)
            b.setStyleSheet(
                f"QPushButton {{ color: rgba({ink.red()},{ink.green()},{ink.blue()},220); background: rgba({fill});"
                f" border: 1px solid rgba(0,0,0,40); border-radius: {size // 2}px; font-size: {round(size * 0.5)}px;"
                f" font-weight: 700; padding: 0; }}"
                f"QPushButton:hover {{ background: rgba({hover}); }}")
        self.buttons[1].setVisible(self.underMouse() and self.skin().cycle)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.paint_paper(p)
        r = self.paper_rect()
        pin = QColor(NEON[(self.note["color"] + 2) % 4][1]).darker(118)
        draw_pin(p, QPointF(r.center().x(), r.top() + r.height() * 0.07), max(6.0, r.width() * 0.032), pin)
        if self.underMouse():
            # the resize corner
            ink = QColor(self.editor.ink)
            ink.setAlpha(90)
            p.setPen(QPen(ink, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for d in (6, 11, 16):
                p.drawLine(QPointF(r.right() - d, r.bottom() - 3), QPointF(r.right() - 3, r.bottom() - d))
        p.end()

    def enterEvent(self, event):
        for b in self.buttons:
            b.show()
        self.refresh_look()

    def leaveEvent(self, event):
        for b in self.buttons:
            b.hide()
        self.update()

    def _in_grip(self, pos: QPointF) -> bool:
        r = self.paper_rect()
        return r.right() - GRIP <= pos.x() <= r.right() + 4 and r.bottom() - GRIP <= pos.y() <= r.bottom() + 4

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self.resizing:
            start, size = self.resizing
            d = QCursor.pos() - start
            w = min(MAX_SIZE, max(MIN_SIZE, size[0] + d.x()))
            h = min(MAX_SIZE, max(MIN_SIZE, size[1] + d.y()))
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                h = w * size[1] / size[0]         # Shift keeps the shape
            self.resize(round(w + 2 * MARGIN), round(h + 2 * MARGIN))
            return
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if self._in_grip(pos) else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        if self._in_grip(pos):
            r = self.paper_rect()
            self.resizing = (QCursor.pos(), (r.width(), r.height()))
        elif self.on_paper(pos):
            self.windowHandle().startSystemMove()

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = None

    def mouseDoubleClickEvent(self, event):
        if self.on_paper(event.position()):
            self.editor.focus_end()

    def wheelEvent(self, event):
        """Ctrl + wheel makes the note bigger or smaller, around its middle."""
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return super().wheelEvent(event)
        r = self.global_paper()
        k = 1.08 if event.angleDelta().y() > 0 else 1 / 1.08
        w = min(MAX_SIZE, max(MIN_SIZE, r.width() * k))
        h = min(MAX_SIZE, max(MIN_SIZE, w * r.height() / r.width()))
        c = r.center()
        self.setGeometry(round(c.x() - w / 2 - MARGIN), round(c.y() - h / 2 - MARGIN),
                         round(w + 2 * MARGIN), round(h + 2 * MARGIN))

    def resizeEvent(self, event):
        self.refresh_look()
        self.save_timer.start()

    def moveEvent(self, event):
        self.save_timer.start()

    def _save_rect(self) -> None:
        r = self.global_paper()
        self.note["rect"] = [round(r.x()), round(r.y()), round(r.width()), round(r.height())]
        self.app.changed()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clearFocus()
            self.editor.clearFocus()

    # what the buttons do
    def _toggled(self) -> None:
        if store.is_complete(self.note):
            self.finish_timer.start()
        else:
            self.finish_timer.stop()

    def _maybe_finish(self) -> None:
        if store.is_complete(self.note):
            self.done()

    def done(self) -> None:
        self.app.crumple(self, finished=True)

    def throw_away(self) -> None:
        b = self.buttons[2]
        if store.tasks(self.note) and not store.is_complete(self.note) and b.text() == "✕":
            b.setText("?")
            b.setToolTip("Click again to throw it away")
            self.confirm_timer.start()
            return
        self.app.crumple(self, finished=False)

    def next_color(self) -> None:
        self.note["color"] = (self.note["color"] + 1) % len(NEON)
        self.refresh_look()
        self.app.changed()
