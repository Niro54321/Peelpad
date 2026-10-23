"""A note pinned on the desktop: always on top. Drag its paper and it swings and
ripples in your hand like the sheets from the pad. The buttons under it:
↕ resize (then ✓ when it's the size you want), ✓ done, ● next colour, ✕ throw away.
When every task is checked it crumples.
"""

from __future__ import annotations

from PIL import Image, ImageFilter
from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QImage, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from peelpad import physics, store
from peelpad.editor import TaskEditor
from peelpad.skins import (GLUE, NEON, TEMPLATE, PictureSkin, Skin, font_px, note_images, safe_rect, text_effect,
                           writing_colors, writing_layer)

MARGIN = 18          # room around the paper for its shadow (and the pin)
BAR = 46             # room under the paper for the buttons
HANDLE = 9           # half the size of a resize handle
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


def round_button(parent: QWidget, text: str, tip: str, slot) -> QPushButton:
    """The small round buttons under the pad and the notes."""
    b = QPushButton(text, parent)
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFixedSize(32, 32)
    b.setStyleSheet("QPushButton { color: #1F1D1A; background: rgba(255,255,255,215); border: 1px solid rgba(0,0,0,50);"
                    " border-radius: 16px; font-size: 15px; font-weight: 700; padding: 0; }"
                    "QPushButton:hover { background: white; }"
                    "QPushButton[on=\"true\"] { background: #FF4FA8; color: white; border-color: #FF4FA8; }")
    b.clicked.connect(slot)
    b.hide()
    return b


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
        self._cache_key = self._shadow_key = None
        self._paper = self._shadow = None
        self.hover = False
        self.frames = QTimer(self)                  # an animated skin redraws the paper
        self.frames.timeout.connect(self._next_frame)

    def _next_frame(self) -> None:
        if self.isVisible():
            self.update(self.paper_rect().toAlignedRect())

    def paper_rect(self) -> QRectF:
        raise NotImplementedError

    def bar_rect(self) -> QRectF:
        """The strip under the paper where the buttons are."""
        r = self.paper_rect()
        return QRectF(0, r.bottom(), self.width(), self.height() - r.bottom())

    def skin(self) -> Skin:
        return self.app.skin

    def refresh_look(self) -> None:
        self._cache_key = None
        r = self.paper_rect()
        area = safe_rect(r.width(), r.height(), self.skin().area).translated(r.topLeft())
        m = round(font_px(r.width()) * 0.7)       # the editor's own margin, room for a neon halo
        self.editor.setGeometry(area.adjusted(-m, -m, m, m).toAlignedRect())
        ink, glow = self._writing()
        self.editor.set_look(ink, font_px(r.width()), glow, text_effect(self.skin()))
        self.place_buttons()
        if self.skin().animated:
            self.frames.start(self.skin().frame_ms)
        else:
            self.frames.stop()
        self.update()

    def place_buttons(self) -> None:
        shown = [b for b in self.buttons if b.property("wanted") is not False]
        bar = self.bar_rect()
        x = round(self.paper_rect().center().x() - (len(shown) * 38 - 6) / 2)
        y = round(bar.top() + (bar.height() - 32) / 2 + 2)
        for b in self.buttons:
            b.setVisible(self.hover and b in shown)
        for i, b in enumerate(shown):
            b.move(x + i * 38, y)

    def bind(self) -> None:
        r = self.paper_rect()
        ink, glow = self._writing()
        self.editor.bind(self.note, ink, font_px(r.width()), glow, text_effect(self.skin()))
        self.refresh_look()

    def _writing(self):
        return writing_colors(self.skin(), self.note["color"])

    def paint_paper(self, p: QPainter, color: int | None = None, shadow_only: bool = False) -> None:
        r = self.paper_rect()
        color = self.note["color"] if color is None else color
        dpr = self.devicePixelRatioF()
        skin = self.skin()
        size = (round(r.width()), round(r.height()), skin.key, color, dpr)
        key = size + (skin.frame_id(),)
        if key != self._cache_key:
            self._paper = paper_image(skin, size[0], size[1], color, dpr)
            self._cache_key = key
        if size != self._shadow_key:                # an animation keeps the first frame's shadow
            self._shadow = shadow_image(self._paper, MARGIN, dpr)
            self._shadow_key = size
        p.drawImage(QPointF(r.left() - MARGIN, r.top() - MARGIN), self._shadow)
        if not shadow_only:
            p.drawImage(r.topLeft(), self._paper)

    def paint_bar(self, p: QPainter) -> None:
        """While the mouse is over the window the strip under the paper takes the
        mouse too (nearly invisible), so you can reach the buttons."""
        if not self.hover:
            return
        p.fillRect(self.bar_rect(), QColor(0, 0, 0, 1))
        shown = [b for b in self.buttons if b.isVisible()]
        if shown:
            left = min(b.x() for b in shown) - 6
            right = max(b.x() + b.width() for b in shown) + 6
            pill = QRectF(left, shown[0].y() - 5, right - left, 42)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 20, 26, 120))
            p.drawRoundedRect(pill, 21, 21)

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

    def enterEvent(self, event):
        self.hover = True
        self.place_buttons()
        self.update()

    def leaveEvent(self, event):
        # a leave can come from a child (a button); only hide once the mouse is really gone
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            return
        self.hover = False
        self.place_buttons()
        self.update()


class NoteWindow(Paper):
    def __init__(self, app, note: dict):
        super().__init__(app, note, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Peelpad note")
        self.sizing = False          # resize mode, after ↕
        self.drag: tuple | None = None
        self.press: QPointF | None = None
        self.carrying = None
        self.finish_timer = QTimer(self)
        self.finish_timer.setSingleShot(True)
        self.finish_timer.setInterval(800)
        self.finish_timer.timeout.connect(self._maybe_finish)
        self.editor.toggled.connect(self._toggled)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(300)
        self.save_timer.timeout.connect(self._save_rect)
        self.size_button = round_button(self, "↕", "Resize: drag the handles, then press ✓", self.toggle_sizing)
        self.done_button = round_button(self, "✓", "Done: crumple it", self.done)
        self.color_button = round_button(self, "●", "Next colour", self.next_color)
        self.away_button = round_button(self, "✕", "Throw it away", self.throw_away)
        self.buttons = [self.size_button, self.done_button, self.color_button, self.away_button]
        self.confirm_timer = QTimer(self)
        self.confirm_timer.setSingleShot(True)
        self.confirm_timer.setInterval(2200)
        self.confirm_timer.timeout.connect(lambda: self.away_button.setText("✕"))
        self.click_timer = QTimer(self)             # one click: write at the end; two: carry it
        self.click_timer.setSingleShot(True)
        self.click_timer.setInterval(QApplication.doubleClickInterval())
        self.click_timer.timeout.connect(self.editor.focus_end)
        # wind: the note sways, glued along its top, and holds still under the mouse
        self.wind = 0.0                             # 0 still .. 1 blowing
        self.wind_seed = sum(map(ord, note["id"])) % 97 / 9.7      # each note sways out of step
        self.wind_clock = QElapsedTimer()
        self.wind_clock.start()
        self.wind_timer = QTimer(self)
        self.wind_timer.setInterval(40)
        self.wind_timer.timeout.connect(self._blow)
        self._writing_key = self._masks_key = self._front_key = None
        self._writing_img = self._masks = self._front_img = None
        self.place_at(QRectF(*note["rect"]))
        self.bind()
        self.update_wind()

    # geometry
    def paper_rect(self) -> QRectF:
        return QRectF(MARGIN, MARGIN, self.width() - 2 * MARGIN, self.height() - 2 * MARGIN - BAR)

    def global_paper(self) -> QRectF:
        return self.paper_rect().translated(QPointF(self.geometry().topLeft()))

    def place_at(self, paper: QRectF) -> None:
        self.setGeometry(round(paper.x() - MARGIN), round(paper.y() - MARGIN),
                         round(paper.width() + 2 * MARGIN), round(paper.height() + 2 * MARGIN + BAR))

    def refresh_look(self) -> None:
        self.color_button.setProperty("wanted", bool(self.skin().cycle) and not self.sizing)
        for b in (self.done_button, self.away_button):
            b.setProperty("wanted", not self.sizing)
        self.size_button.setText("✓" if self.sizing else "↕")
        self.size_button.setToolTip("Keep this size" if self.sizing else "Resize: drag the handles, then press ✓")
        self.size_button.setProperty("on", self.sizing)
        self.size_button.style().unpolish(self.size_button)
        self.size_button.style().polish(self.size_button)
        super().refresh_look()

    # wind
    def update_wind(self) -> None:
        """Start or stop blowing, after Settings change."""
        if self.app.wind_speed() > 0:
            self.wind_timer.start()
        else:
            self.wind_timer.stop()
            self._settle(0.0)

    def _still(self) -> bool:
        focused = any(edit.hasFocus() for _, _, edit in self.editor.rows)
        return self.hover or focused or self.sizing or self.carrying is not None or not self.isVisible()

    def _blow(self) -> None:
        target = 0.0 if self._still() else 1.0
        step = 0.033 / (0.25 if target < self.wind else 0.8)     # calms quickly, picks up slowly
        self._settle(min(target, self.wind + step) if target > self.wind else max(target, self.wind - step))
        if self.wind > 0:
            self.update(self.rect())

    def _settle(self, amount: float) -> None:
        was = self.wind
        self.wind = amount
        if (was > 0) != (amount > 0):
            self.editor.setVisible(amount == 0)       # the live editor shows when the note holds still
            self.update()

    def _front(self) -> QImage:
        """The note as one picture (paper and writing), for the wind to bend."""
        r = self.paper_rect()
        dpr = self.devicePixelRatioF()
        w, h = round(r.width()), round(r.height())
        key = (w, h, dpr, self.skin().key, repr(self.note["rows"]), self.note["color"], text_effect(self.skin()),
               self.editor.ink.name(), font_px(w))
        if key != self._writing_key:
            self._writing_img = writing_layer(self.note, self.skin(), w, h, dpr)
            self._writing_key = key
        if (key, self._cache_key) == self._front_key:    # same writing on the same paper frame
            return self._front_img
        front = QImage(self._writing_img.size(), QImage.Format.Format_ARGB32_Premultiplied)
        front.fill(Qt.GlobalColor.transparent)
        p = QPainter(front)
        p.drawImage(QRectF(0, 0, front.width(), front.height()), self._paper)
        p.drawImage(0, 0, self._writing_img)
        p.end()
        self._front_img, self._front_key = front, (key, self._cache_key)
        return front

    def _paint_blowing(self, p: QPainter) -> None:
        from peelpad.stage import Masks, Painted, paint_bands

        r = self.paper_rect()
        dpr = self.devicePixelRatioF()
        front = self._front()
        if (front.size(), self.skin().key) != self._masks_key:
            self._masks = Masks(front, dpr)
            self._masks_key = (front.size(), self.skin().key)
        t = self.wind_clock.elapsed() / 1000
        speed = self.app.wind_speed() * self.wind
        grow = max(0.0, (MARGIN - 4) * 2 / max(r.width(), r.height()))
        shape = physics.wind(r.width(), r.height(), r.height() * GLUE / TEMPLATE, t, speed, self.wind_seed, grow)
        painted = Painted(shape, dpr)
        paint_bands(p, painted, front, front, QPointF(-r.left(), -r.top()), self._masks)
        p.resetTransform()

    # painting
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = self.paper_rect()
        if self.wind > 0:
            self.paint_paper(p, shadow_only=True)
            self._paint_blowing(p)
        else:
            self.paint_paper(p)
        if not isinstance(self.skin(), PictureSkin) and not self.skin().animated:   # those have their own decoration
            pin = QColor(NEON[(self.note["color"] + 2) % 4][1]).darker(118)
            draw_pin(p, QPointF(r.center().x(), r.top() + r.height() * 0.07), max(6.0, r.width() * 0.032), pin)
        if self.sizing:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#FF4FA8"), 1.6, Qt.PenStyle.DashLine))
            p.drawRect(r.adjusted(-1, -1, 1, 1))
            p.setPen(QPen(QColor("white"), 1.4))
            p.setBrush(QColor("#FF4FA8"))
            for h in self._handles().values():
                p.drawRoundedRect(h, 3, 3)
        self.paint_bar(p)
        p.end()

    # resize mode
    def toggle_sizing(self) -> None:
        self.sizing = not self.sizing
        if not self.sizing:
            self._save_rect()
        self.refresh_look()

    def _handles(self) -> dict:
        r = self.paper_rect()
        xs = {"l": r.left(), "c": r.center().x(), "r": r.right()}
        ys = {"t": r.top(), "m": r.center().y(), "b": r.bottom()}
        out = {}
        for ky, y in ys.items():
            for kx, x in xs.items():
                if kx == "c" and ky == "m":
                    continue
                out[ky + kx] = QRectF(x - HANDLE, y - HANDLE, 2 * HANDLE, 2 * HANDLE)
        return out

    def _handle_at(self, pos: QPointF):
        return next((k for k, h in self._handles().items() if h.adjusted(-3, -3, 3, 3).contains(pos)), None)

    _CURSORS = {"tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
                "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
                "tc": Qt.CursorShape.SizeVerCursor, "bc": Qt.CursorShape.SizeVerCursor,
                "ml": Qt.CursorShape.SizeHorCursor, "mr": Qt.CursorShape.SizeHorCursor}

    def _resize_to(self, handle: str, start: QRectF, d: QPointF, keep: bool) -> None:
        left, top, right, bottom = start.left(), start.top(), start.right(), start.bottom()
        if "l" in handle:
            left = min(right - MIN_SIZE, max(right - MAX_SIZE, left + d.x()))
        if "r" in handle[1:]:
            right = max(left + MIN_SIZE, min(left + MAX_SIZE, right + d.x()))
        if handle[0] == "t":
            top = min(bottom - MIN_SIZE, max(bottom - MAX_SIZE, top + d.y()))
        if handle[0] == "b":
            bottom = max(top + MIN_SIZE, min(top + MAX_SIZE, bottom + d.y()))
        r = QRectF(left, top, right - left, bottom - top)
        if keep:                                   # Shift keeps the shape
            r.setHeight(r.width() * start.height() / start.width())
            if handle[0] == "t":
                r.moveBottom(start.bottom())
        self.place_at(r)

    # mouse
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        if self.sizing:
            handle = self._handle_at(pos)
            if handle:
                self.drag = (handle, self.global_paper(), QCursor.pos())
            elif self.on_paper(pos):
                self.windowHandle().startSystemMove()
            return
        if self.on_paper(pos):
            self.press = pos

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self.drag:
            handle, start, at = self.drag
            d = QPointF(QCursor.pos() - at)
            self._resize_to(handle, start, d, bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            return
        if self.sizing:
            handle = self._handle_at(pos)
            self.setCursor(self._CURSORS[handle] if handle else Qt.CursorShape.SizeAllCursor
                           if self.on_paper(pos) else Qt.CursorShape.ArrowCursor)
            return
        if self.press is not None and (pos - self.press).manhattanLength() > 4:
            start = self.press
            self.press = None
            self.pick_up(QPointF(self.geometry().topLeft()) + start)

    def mouseReleaseEvent(self, event):
        if self.press is not None and not self.sizing:
            self.click_timer.start()
        self.drag = None
        self.press = None

    def mouseDoubleClickEvent(self, event):
        """Double-click the paper: the note follows the mouse, no button held; click to put it down."""
        self.click_timer.stop()
        if not self.sizing and self.on_paper(event.position()):
            self.pick_up(QPointF(self.geometry().topLeft()) + event.position(), sticky=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.sizing:
                self.toggle_sizing()
            self.editor.clearFocus()

    def wheelEvent(self, event):
        """Ctrl + wheel makes the note bigger or smaller, around its middle."""
        if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            return super().wheelEvent(event)
        r = self.global_paper()
        k = 1.08 if event.angleDelta().y() > 0 else 1 / 1.08
        w = min(MAX_SIZE, max(MIN_SIZE, r.width() * k))
        h = min(MAX_SIZE, max(MIN_SIZE, w * r.height() / r.width()))
        c = r.center()
        self.place_at(QRectF(c.x() - w / 2, c.y() - h / 2, w, h))

    # picked up and carried, with the same paper physics as a sheet from the pad
    def pick_up(self, grab: QPointF, sticky: bool = False) -> None:
        from peelpad.stage import PeelActor

        self._settle(0.0)
        r = self.global_paper()
        dpr = max(1.0, self.devicePixelRatioF())
        front, back = note_images(self.note, self.skin(), round(r.width()), round(r.height()), dpr)
        self.carrying = PeelActor(r, grab, front, back, dpr, 0, on_landed=self._landed, on_returned=self._landed_back,
                                  carry=True, follow=True, sticky=sticky)
        self.app.stages.at(grab, follow=True, catch=sticky).add(self.carrying)
        QTimer.singleShot(16, self.hide)            # the stage shows the sheet first, so nothing blinks

    def _landed(self, rect: QRectF) -> None:
        self.carrying = None
        self.place_at(self.app.inside(rect))
        self.hover = False
        self.place_buttons()
        self.show()
        self._save_rect()

    def _landed_back(self) -> None:
        self.carrying = None
        self.show()

    def resizeEvent(self, event):
        self.refresh_look()
        self.save_timer.start()

    def moveEvent(self, event):
        self.save_timer.start()

    def _save_rect(self) -> None:
        r = self.global_paper()
        self.note["rect"] = [round(r.x()), round(r.y()), round(r.width()), round(r.height())]
        self.app.changed()

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
        b = self.away_button
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
