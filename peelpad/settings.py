"""Settings: your stats, a calendar of what you did each day, the look of the
notes (themes, your own colours, your own skins), the writing, and a few switches."""

from __future__ import annotations

import calendar
import html
import subprocess
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QFileDialog, QFontComboBox, QGridLayout,
                               QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QStackedWidget,
                               QVBoxLayout, QWidget)

from peelpad.skins import (GLUE, NEON, SIDE, TEMPLATE, all_skins, hand_family, import_skin, preview,
                           save_template)
from peelpad.widgets import GlassWindow, Segmented, SliderRow, label

WEEKS = 18


class Heatmap(QWidget):
    """The last weeks, one square a day: grey nothing, lemon wrote, lime finished everything."""

    def __init__(self):
        super().__init__()
        self.written: set[str] = set()
        self.completed: set[str] = set()
        self.setMinimumHeight(7 * 15 + 22)

    def set_days(self, written, completed) -> None:
        self.written, self.completed = set(written), set(completed)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        today = date.today()
        start = today - timedelta(days=today.weekday() + 7 * (WEEKS - 1))
        cell = min(15.0, (self.width() - 4) / WEEKS)
        gap = 3
        fg = self.palette().windowText().color()
        for i in range(WEEKS * 7):
            d = start + timedelta(days=i)
            if d > today:
                break
            key = d.isoformat()
            x, y = (i // 7) * cell, (i % 7) * cell
            if key in self.completed:
                c = QColor(NEON[3][1])
            elif key in self.written:
                c = QColor(NEON[0][1])
            else:
                c = QColor(fg)
                c.setAlpha(28)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x, y, cell - gap, cell - gap), 3, 3)
            if d == today:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QColor(NEON[2][1]))
                p.drawRoundedRect(QRectF(x - 0.5, y - 0.5, cell - gap + 1, cell - gap + 1), 3, 3)
        p.end()


class MonthView(QWidget):
    """A month, a square a day, with how many tasks you checked off that day."""

    picked = Signal(str)

    def __init__(self):
        super().__init__()
        self.month = date.today().replace(day=1)
        self.selected = date.today().isoformat()
        self.log: dict = {}
        self.setMinimumHeight(300)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_log(self, log: dict) -> None:
        self.log = log
        self.update()

    def shift(self, months: int) -> None:
        y, m = self.month.year, self.month.month + months
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        self.month = date(y, m, 1)
        self.update()

    def _cells(self):
        head = 22
        cw = self.width() / 7
        ch = (self.height() - head) / 6
        first = self.month - timedelta(days=self.month.weekday())
        for i in range(42):
            d = first + timedelta(days=i)
            yield d, QRectF((i % 7) * cw, head + (i // 7) * ch, cw, ch)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fg = self.palette().windowText().color()
        f = QFont(self.font())
        f.setPixelSize(11)
        p.setFont(f)
        faint = QColor(fg)
        faint.setAlpha(150)
        p.setPen(faint)
        cw = self.width() / 7
        for i, name in enumerate(calendar.day_abbr):
            p.drawText(QRectF(i * cw, 0, cw, 20), Qt.AlignmentFlag.AlignCenter, name)
        today = date.today()
        lime, lemon, pink = QColor(NEON[3][1]), QColor(NEON[0][1]), QColor(NEON[2][1])
        for d, r in self._cells():
            box = r.adjusted(2, 2, -2, -2)
            key = d.isoformat()
            day = self.log.get(key, {})
            done, written = len(day.get("done", [])), len(day.get("written", []))
            inside = d.month == self.month.month
            back = QColor(fg)
            back.setAlpha(26 if inside else 10)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(back)
            p.drawRoundedRect(box, 8, 8)
            if key == self.selected:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(pink)
                p.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
            num = QColor(fg)
            num.setAlpha(255 if inside else 90)
            f.setPixelSize(12)
            f.setBold(d == today)
            p.setFont(f)
            p.setPen(num)
            p.drawText(box.adjusted(7, 4, -4, -4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, str(d.day))
            if done:
                pill = QRectF(box.center().x() - 17, box.bottom() - 22, 34, 17)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(lime)
                p.drawRoundedRect(pill, 8.5, 8.5)
                f.setBold(True)
                f.setPixelSize(11)
                p.setFont(f)
                p.setPen(QColor("#1F1D1A"))
                p.drawText(pill, Qt.AlignmentFlag.AlignCenter, f"✓{done}")
            elif written:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(lemon)
                p.drawEllipse(box.center() + QRectF(0, 0, 0, box.height() * 0.28).bottomLeft(), 4, 4)
        p.end()

    def mousePressEvent(self, event):
        for d, r in self._cells():
            if r.contains(event.position()):
                self.selected = d.isoformat()
                if d.month != self.month.month:
                    self.month = d.replace(day=1)
                self.update()
                self.picked.emit(self.selected)
                return


class AreaEditor(QWidget):
    """The current look with its text box: drag the box to move it, its corners to resize it."""

    moved = Signal(tuple)
    MIN = 0.12

    def __init__(self):
        super().__init__()
        self.setMinimumSize(250, 250)
        self.setMouseTracking(True)
        self.paper: QImage | None = None
        self.aspect = 1.0
        self.area = (0.1, 0.16, 0.9, 0.9)
        self.drag = None

    def set_skin(self, skin) -> None:
        self.aspect = skin.aspect or 1.0
        h = 500
        img = QImage(round(h * self.aspect), h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        skin.paint_front(p, img.width(), img.height(), 0)
        p.end()
        self.paper, self.area = img, tuple(skin.area)
        self.update()

    def _frame(self) -> QRectF:
        side = min(self.width() - 8, self.height() - 8)
        w, h = (side, side / self.aspect) if self.aspect >= 1 else (side * self.aspect, side)
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def _box(self) -> QRectF:
        f, (l, t, r, b) = self._frame(), self.area
        return QRectF(f.left() + l * f.width(), f.top() + t * f.height(), (r - l) * f.width(), (b - t) * f.height())

    def _corners(self) -> dict:
        b = self._box()
        return {"tl": b.topLeft(), "tr": b.topRight(), "bl": b.bottomLeft(), "br": b.bottomRight()}

    def _corner_at(self, pos: QPointF):
        return next((k for k, c in self._corners().items() if (c - pos).manhattanLength() < 14), None)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        f, box = self._frame(), self._box()
        if self.paper is not None:
            p.drawImage(f, self.paper)
        outside = QPainterPath()
        outside.addRect(f)
        hole = QPainterPath()
        hole.addRect(box)
        p.fillPath(outside.subtracted(hole), QColor(0, 0, 0, 70))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#FF4FA8"), 2, Qt.PenStyle.DashLine))
        p.drawRect(box)
        p.setPen(QColor("#FF4FA8"))
        p.drawText(box.adjusted(6, 4, -4, -4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "☐ Your tasks here")
        p.setPen(QPen(QColor("white"), 1.5))
        p.setBrush(QColor("#FF4FA8"))
        for c in self._corners().values():
            p.drawEllipse(c, 6, 6)
        p.end()

    def mousePressEvent(self, event):
        pos = event.position()
        corner = self._corner_at(pos)
        if corner or self._box().contains(pos):
            self.drag = (corner or "move", pos, self.area)

    def mouseMoveEvent(self, event):
        pos = event.position()
        if not self.drag:
            corner = self._corner_at(pos)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor if corner in ("tl", "br") else
                           Qt.CursorShape.SizeBDiagCursor if corner else
                           Qt.CursorShape.SizeAllCursor if self._box().contains(pos) else Qt.CursorShape.ArrowCursor)
            return
        kind, start, (l, t, r, b) = self.drag
        f = self._frame()
        dx, dy = (pos.x() - start.x()) / f.width(), (pos.y() - start.y()) / f.height()
        if kind == "move":
            dx = min(max(dx, -l), 1 - r)
            dy = min(max(dy, -t), 1 - b)
            l, r, t, b = l + dx, r + dx, t + dy, b + dy
        else:
            if "l" in kind:
                l = min(max(0.0, l + dx), r - self.MIN)
            else:
                r = max(min(1.0, r + dx), l + self.MIN)
            if "t" in kind:
                t = min(max(0.0, t + dy), b - self.MIN)
            else:
                b = max(min(1.0, b + dy), t + self.MIN)
        self.area = (l, t, r, b)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.drag:
            self.drag = None
            self.moved.emit(self.area)


def card(number: str, caption: str) -> tuple[QWidget, QLabel]:
    w = QWidget()
    w.setProperty("card", True)
    w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    col = QVBoxLayout(w)
    col.setContentsMargins(14, 10, 14, 10)
    big = label(number, bold=True, size=26)
    col.addWidget(big)
    col.addWidget(label(caption, muted=True, size=12))
    return w, big


def scrolled(inner: QWidget) -> QWidget:
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(inner)
    outer.addWidget(scroll)
    return page


def swatch_icon(color: QColor, size: int = 16) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(color)
    p.setPen(QColor(0, 0, 0, 90))
    p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    p.end()
    return QIcon(pm)


class Settings(GlassWindow):
    TABS = [("stats", "Stats"), ("history", "History"), ("look", "Look"), ("writing", "Writing"),
            ("general", "General")]

    def __init__(self, app):
        super().__init__("Peelpad", size=(700, 780), minimum=(600, 620))
        self.app = app
        tabs = Segmented(self.TABS, "stats")
        self.body.addWidget(tabs)
        self.pages = QStackedWidget()
        self.body.addWidget(self.pages, 1)
        self.page_keys = [k for k, _ in self.TABS]
        for page in (self._stats_page(), self._history_page(), self._look_page(), self._writing_page(),
                     self._general_page()):
            self.pages.addWidget(page)
        tabs.changed.connect(self._tab)
        self.tabs = tabs

    def _tab(self, key: str) -> None:
        self.pages.setCurrentIndex(self.page_keys.index(key))
        if key in ("stats", "history"):
            self.refresh_stats()

    # ---------------------------------------------------------------- stats
    def _stats_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 6, 0, 0)
        col.setSpacing(10)
        grid = QGridLayout()
        grid.setSpacing(10)
        self.numbers = {}
        for i, (key, caption) in enumerate([
                ("days_written", "days you wrote notes"),
                ("days_completed", "days you checked off everything you wrote"),
                ("streak", "day streak right now"),
                ("best_streak", "best streak"),
                ("notes_finished", "notes finished and crumpled"),
                ("tasks", "tasks checked")]):
            w, big = card("0", caption)
            self.numbers[key] = big
            grid.addWidget(w, i // 2, i % 2)
        col.addLayout(grid)
        col.addWidget(label("Last 18 weeks", bold=True))
        self.heatmap = Heatmap()
        col.addWidget(self.heatmap)
        legend = label("", muted=True, size=12)
        legend.setTextFormat(Qt.TextFormat.RichText)
        legend.setText(f"<span style='color:{NEON[0][1]}'>■</span> wrote something &nbsp; "
                       f"<span style='color:{NEON[3][1]}'>■</span> checked off everything &nbsp; "
                       f"<span style='color:{NEON[2][1]}'>□</span> today")
        col.addWidget(legend)
        self.rate = label("", muted=True)
        col.addWidget(self.rate)
        col.addStretch(1)
        return page

    def refresh_stats(self) -> None:
        s = self.app.store.stats()
        for key in ("days_written", "days_completed", "streak", "best_streak", "notes_finished"):
            self.numbers[key].setText(str(s[key]))
        self.numbers["tasks"].setText(f"{s['tasks_done']} / {s['tasks_total']}")
        self.heatmap.set_days(s["written"], s["completed"])
        self.rate.setText(f"{s['completion']}% of all your tasks are done · {s['notes_pinned']} notes pinned now")
        self.month.set_log(self.app.store.history())
        self._show_day(self.month.selected)

    # ---------------------------------------------------------------- history
    def _history_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 6, 0, 0)
        col.setSpacing(8)
        bar = QHBoxLayout()
        back = QPushButton("‹")
        ahead = QPushButton("›")
        this = QPushButton("Today")
        for b in (back, ahead):
            b.setFixedWidth(44)
        self.month_name = label("", bold=True, size=16)
        bar.addWidget(back)
        bar.addWidget(self.month_name, 1, Qt.AlignmentFlag.AlignCenter)
        bar.addWidget(this)
        bar.addWidget(ahead)
        col.addLayout(bar)
        self.month = MonthView()
        col.addWidget(self.month, 3)
        self.day_text = label("", size=13)
        self.day_text.setTextFormat(Qt.TextFormat.RichText)
        self.day_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.day_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        inner = QWidget()
        box = QVBoxLayout(inner)
        box.setContentsMargins(4, 0, 4, 0)
        box.addWidget(self.day_text)
        box.addStretch(1)
        col.addWidget(scrolled(inner), 2)

        def move(months):
            self.month.shift(months)
            self._month_title()

        def go_today():
            self.month.month = date.today().replace(day=1)
            self.month.selected = date.today().isoformat()
            self.month.update()
            self._month_title()
            self._show_day(self.month.selected)

        back.clicked.connect(lambda: move(-1))
        ahead.clicked.connect(lambda: move(1))
        this.clicked.connect(go_today)
        self.month.picked.connect(self._show_day)
        self.month.picked.connect(lambda _: self._month_title())
        self._month_title()
        return page

    def _month_title(self) -> None:
        self.month_name.setText(self.month.month.strftime("%B %Y"))

    def _show_day(self, key: str) -> None:
        day = self.app.store.history().get(key, {"done": [], "written": []})
        when = date.fromisoformat(key).strftime("%A %d %B %Y")
        parts = [f"<b style='font-size:15px'>{when}</b>"]
        if not day["done"] and not day["written"]:
            parts.append("<br>Nothing written or checked off this day.")
        if day["done"]:
            parts.append(f"<br><b style='color:{NEON[3][1]}'>✓ Checked off ({len(day['done'])})</b>")
            parts += [f"&nbsp;&nbsp;✓ {html.escape(t)}" for t in day["done"]]
        if day["written"]:
            parts.append(f"<br><b style='color:{NEON[0][1]}'>✎ Written ({len(day['written'])})</b>")
            parts += [f"&nbsp;&nbsp;• {html.escape(t)}" for t in day["written"]]
        self.day_text.setText("<br>".join(parts))

    # ---------------------------------------------------------------- look
    def _look_page(self) -> QWidget:
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 6, 6, 0)
        col.setSpacing(10)
        col.addWidget(label("Note look", bold=True))
        self.skin_grid = QGridLayout()
        self.skin_grid.setSpacing(8)
        col.addLayout(self.skin_grid)
        self.skin_group = QButtonGroup(self)
        self.skin_group.setExclusive(True)

        col.addWidget(label("Text box", bold=True))
        col.addWidget(label("Where the writing goes on this look. Drag the box to move it, drag its corners to "
                            "make it bigger or smaller. Peelpad finds the calm middle of your own pictures by itself.",
                            muted=True, size=12))
        row = QHBoxLayout()
        self.area_editor = AreaEditor()
        self.area_editor.moved.connect(lambda area: self.app.set_area(self.app.skin.key, area))
        auto = QPushButton("Auto")
        auto.setToolTip("Put the text box back where Peelpad would put it")
        auto.clicked.connect(lambda: self.app.set_area(self.app.skin.key, None))
        row.addWidget(self.area_editor, 1)
        side = QVBoxLayout()
        side.addWidget(auto)
        side.addStretch(1)
        row.addLayout(side)
        col.addLayout(row)

        col.addWidget(label("Your colours", bold=True))
        mine = QHBoxLayout()
        self.paper_button = QPushButton("Paper colour…")
        self.ink_button = QPushButton("Ink colour…")
        self.mine_glow = QCheckBox("Glowing ink")
        self.mine_glow.setChecked(bool(self.app.store.data["mine"].get("glow", True)))
        self.paper_button.clicked.connect(lambda: self._pick_mine("paper", "Paper colour"))
        self.ink_button.clicked.connect(lambda: self._pick_mine("ink", "Ink colour"))
        self.mine_glow.toggled.connect(lambda on: self.app.set_mine(glow=on))
        mine.addWidget(self.paper_button)
        mine.addWidget(self.ink_button)
        mine.addWidget(self.mine_glow)
        mine.addStretch()
        col.addLayout(mine)
        self._mine_icons()

        col.addWidget(label("Size", bold=True))
        self.size_slider = SliderRow("Pad sheets", 140, 640, self.app.store.data.get("note_size", 300), " px")
        self.size_slider.changed.connect(lambda v: self.app.set_note_size(round(v)))
        col.addWidget(self.size_slider)
        col.addWidget(label("Pinned notes can be any size: press ↕ under a note, drag its handles (hold Shift to "
                            "keep its shape), then press ✓. Or hold Ctrl and turn the mouse wheel over it. "
                            "Ctrl + wheel over the pad changes the size of its sheets.", muted=True, size=12))

        col.addWidget(label("Your own skin", bold=True))
        row = QHBoxLayout()
        upload = QPushButton("Upload your own skin…")
        upload.setProperty("primary", True)
        upload.clicked.connect(self.upload)
        template = QPushButton("Save the template PNG…")
        template.clicked.connect(self.template)
        self.remove_button = QPushButton("Remove this skin")
        self.remove_button.clicked.connect(self.remove_skin)
        row.addWidget(upload)
        row.addWidget(template)
        row.addWidget(self.remove_button)
        row.addStretch()
        col.addLayout(row)
        spec = label(
            f"<b>Design your own skin</b> — scary, cute, anything:<br>"
            f"• <b>Size:</b> {TEMPLATE} × {TEMPLATE} px (a square). Other sizes work too: new notes take "
            f"your picture's shape, and anything from 300 px up stays sharp.<br>"
            f"• <b>Format:</b> PNG. Transparent pixels are see-through on your desktop (and clicks go through "
            f"them), so a skin can be any shape: a ghost, a cat, a torn page. JPG and WebP work without transparency.<br>"
            f"• <b>Safe text area:</b> tasks are written inside {TEMPLATE - 2 * SIDE} × {TEMPLATE - GLUE - SIDE} px: "
            f"{SIDE} px in from the left, right and bottom, and {GLUE} px down from the top. "
            f"The top {GLUE} px is the glue band, where the pin sits and where you grab the note. Decorate it, "
            f"but keep the text area calm so tasks stay readable.<br>"
            f"• <b>Ink:</b> picked for you (dark on light pictures, light on dark), or set it in Writing.<br>"
            f"Save the template, paint over it in any editor, upload it, and every note switches to it at once.",
            size=12)
        spec.setTextFormat(Qt.TextFormat.RichText)
        col.addWidget(spec)
        col.addStretch(1)
        self.fill_skins()
        return scrolled(inner)

    def _mine_icons(self) -> None:
        mine = self.app.store.data["mine"]
        self.paper_button.setIcon(swatch_icon(QColor(mine.get("paper", "#1B1E2B"))))
        self.ink_button.setIcon(swatch_icon(QColor(mine.get("ink", "#7DF9FF"))))

    def _pick_mine(self, key: str, title: str) -> None:
        start = QColor(self.app.store.data["mine"].get(key, "#FFFFFF"))
        color = QColorDialog.getColor(start, self, title)
        if color.isValid():
            self.app.set_mine(**{key: color.name()})
            self._mine_icons()

    def fill_skins(self) -> None:
        while self.skin_grid.count():
            w = self.skin_grid.takeAt(0).widget()
            if w:
                self.skin_group.removeButton(w)
                w.deleteLater()
        current = self.app.store.data["skin"]
        for i, skin in enumerate(all_skins(self.app.skins_dir, self.app.store.data["mine"])):
            b = QPushButton()
            b.setCheckable(True)
            b.setProperty("swatch", True)
            b.setFixedSize(88, 88)
            icon = QPixmap(70, 70)
            icon.fill(Qt.GlobalColor.transparent)
            p = QPainter(icon)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            if skin.key == "neon":
                for j in range(4):
                    img = preview(skin, 40, (j + 1) % 4)
                    p.drawImage(QRectF(3 + j * 9, 3 + j * 9, 40, 40), img)
            else:
                img = preview(skin, 70)
                scale = min(70 / img.width(), 70 / img.height())
                w, h = img.width() * scale, img.height() * scale
                p.drawImage(QRectF((70 - w) / 2, (70 - h) / 2, w, h), img)
            p.end()
            b.setIcon(QIcon(icon))
            b.setIconSize(QSize(70, 70))
            b.setToolTip(skin.name)
            b.setChecked(skin.key == current)
            b.clicked.connect(lambda _=False, k=skin.key: self.app.set_skin(k))
            self.skin_group.addButton(b)
            self.skin_grid.addWidget(b, i // 6, i % 6)
        self.remove_button.setVisible(current.startswith("custom:"))
        self.area_editor.set_skin(self.app.skin)
        self.frame.style_children()

    def upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose your skin", str(Path.home() / "Pictures"),
                                              "Pictures (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        try:
            key, notes = import_skin(Path(path), self.app.skins_dir)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Peelpad", str(e))
            return
        self.app.set_skin(key)
        if notes:
            QMessageBox.information(self, "Peelpad", "Your skin is on. A heads-up:\n\n" + "\n".join(notes))

    def template(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save the skin template",
                                              str(Path.home() / "Pictures" / "peelpad-skin-template.png"),
                                              "PNG (*.png)")
        if path:
            save_template(Path(path))

    def remove_skin(self) -> None:
        key = self.app.store.data["skin"]
        if not key.startswith("custom:"):
            return
        self.app.set_skin("neon")
        try:
            (self.app.skins_dir / key[7:]).unlink()
        except OSError:
            pass
        self.fill_skins()

    # ---------------------------------------------------------------- writing
    def _writing_page(self) -> QWidget:
        d = self.app.store.data
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 6, 6, 0)
        col.setSpacing(10)
        col.addWidget(label("Font", bold=True))
        row = QHBoxLayout()
        self.font_box = QFontComboBox()
        self.font_box.setCurrentFont(QFont(d.get("font") or hand_family()))
        self.font_box.currentFontChanged.connect(lambda f: self.app.set_writing("font", f.family()))
        default = QPushButton("Handwriting (default)")
        default.clicked.connect(self._default_font)
        row.addWidget(self.font_box, 1)
        row.addWidget(default)
        col.addLayout(row)
        self.text_size = SliderRow("Text size", 60, 160, round(100 * float(d.get("text_scale", 1.0))), " %")
        self.text_size.changed.connect(lambda v: self.app.set_writing("text_scale", v / 100))
        col.addWidget(self.text_size)

        col.addWidget(label("Ink", bold=True))
        ink = d.get("ink", "auto")
        self.ink = Segmented([("auto", "Auto"), ("dark", "Dark"), ("light", "Light"), ("pick", "Pick a colour…")],
                             "pick" if ink.startswith("#") else ink)
        self.ink.changed.connect(self._ink)
        col.addWidget(self.ink)
        col.addWidget(label("Auto writes in each look's own ink: dark on neon and white paper, glowing blue on "
                            "Midnight, and so on.", muted=True, size=12))

        col.addWidget(label("Neon glow", bold=True))
        self.glow = Segmented([("auto", "Auto"), ("on", "On"), ("off", "Off")], d.get("glow", "auto"))
        self.glow.changed.connect(lambda k: self.app.set_writing("glow", k))
        col.addWidget(self.glow)
        col.addWidget(label("The ink shines in its own colour, like a neon sign. Best on dark paper "
                            "(Midnight, Neon night, Toxic, or your own colours).", muted=True, size=12))
        col.addStretch(1)
        return scrolled(inner)

    def _default_font(self) -> None:
        self.font_box.blockSignals(True)
        self.font_box.setCurrentFont(QFont(hand_family()))
        self.font_box.blockSignals(False)
        self.app.set_writing("font", "")

    def _ink(self, key: str) -> None:
        if key != "pick":
            self.app.set_writing("ink", key)
            return
        now = self.app.store.data.get("ink", "auto")
        color = QColorDialog.getColor(QColor(now if now.startswith("#") else "#3DB2FF"), self, "Ink colour")
        if color.isValid():
            self.app.set_writing("ink", color.name())
        elif not now.startswith("#"):
            self.ink.set(now)

    # ---------------------------------------------------------------- general
    def _general_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 6, 0, 0)
        col.setSpacing(10)
        on_top = QCheckBox("Keep the pad on top of other windows (pinned notes always are)")
        on_top.setChecked(self.app.store.data["pad"]["on_top"])
        on_top.toggled.connect(self.app.set_pad_on_top)
        col.addWidget(on_top)
        startup = QCheckBox("Start Peelpad when Windows starts")
        startup.setChecked(self.app.startup_enabled())
        startup.toggled.connect(self.app.set_startup)
        col.addWidget(startup)
        folder = QPushButton("Open the data folder")
        folder.clicked.connect(lambda: subprocess.Popen(["explorer", str(self.app.data_dir)]))
        row = QHBoxLayout()
        row.addWidget(folder)
        row.addStretch()
        col.addLayout(row)
        help_text = label(
            "<b>How it works</b><br>"
            "• Write on the pad's top sheet. <b>Enter</b> adds a task, <b>Backspace</b> on an empty one removes it.<br>"
            "• Grab the paper (anywhere that isn't writing) and pull: drag in over the sheet to curl it back, "
            "or pull it away to lift it, until it tears off. Drop it anywhere: it stays pinned on top.<br>"
            "• <b>Ctrl+Enter</b> peels the sheet off for you.<br>"
            "• Right-click a check box to make that row a plain line.<br>"
            "• Drag a pinned note by its paper: it swings like a real sheet. To resize it press ↕ under it, "
            "drag the handles, then ✓. Or Ctrl + mouse wheel.<br>"
            "• Check off every task and the note crumples away. ✓ finishes it by hand, ✕ throws it away.<br>"
            "• – minimises the pad to the taskbar. Peelpad also lives in the tray: right-click it to quit.<br>"
            "• Everything you write stays on this PC only, in the data folder above. Nothing is sent anywhere.",
            size=12)
        help_text.setTextFormat(Qt.TextFormat.RichText)
        col.addWidget(help_text)
        col.addStretch(1)
        from peelpad import __version__
        col.addWidget(label(f"Peelpad {__version__} · MIT licence · github.com/Niro54321/Peelpad", muted=True, size=11))
        return page

    def open(self, tab: str = "stats") -> None:
        self.refresh_stats()
        self.tabs.set(tab)
        self.pages.setCurrentIndex(self.page_keys.index(tab))
        if not self.isVisible():
            self.center_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
