"""Settings: your stats, the look of the notes (with your own skins), and a few switches."""

from __future__ import annotations

import subprocess
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from peelpad.skins import GLUE, NEON, SIDE, TEMPLATE, all_skins, import_skin, preview, save_template
from peelpad.widgets import GlassWindow, Segmented, label

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


class Settings(GlassWindow):
    def __init__(self, app):
        super().__init__("Peelpad", size=(640, 720), minimum=(560, 600))
        self.app = app
        tabs = Segmented([("stats", "Stats"), ("look", "Look"), ("general", "General")], "stats")
        self.body.addWidget(tabs)
        self.pages = QStackedWidget()
        self.body.addWidget(self.pages, 1)
        self.page_keys = ["stats", "look", "general"]
        self.pages.addWidget(self._stats_page())
        self.pages.addWidget(self._look_page())
        self.pages.addWidget(self._general_page())
        tabs.changed.connect(lambda k: self.pages.setCurrentIndex(self.page_keys.index(k)))
        self.tabs = tabs

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
        legend = label("■ wrote something   ■ checked off everything   □ today", muted=True, size=12)
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

    # ---------------------------------------------------------------- look
    def _look_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 6, 6, 0)
        col.setSpacing(10)
        col.addWidget(label("Note skin", bold=True))
        self.skin_grid = QGridLayout()
        self.skin_grid.setSpacing(8)
        col.addLayout(self.skin_grid)
        self.skin_group = QButtonGroup(self)
        self.skin_group.setExclusive(True)
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
            f"• <b>Size:</b> {TEMPLATE} × {TEMPLATE} px (a square). Other sizes work too: notes keep "
            f"your picture's shape, and anything from 300 px up stays sharp.<br>"
            f"• <b>Format:</b> PNG. Transparent pixels are see-through on your desktop (and clicks go through "
            f"them), so a skin can be any shape: a ghost, a cat, a torn page. JPG and WebP work without transparency.<br>"
            f"• <b>Safe text area:</b> tasks are written inside {TEMPLATE - 2 * SIDE} × {TEMPLATE - GLUE - SIDE} px: "
            f"{SIDE} px in from the left, right and bottom, and {GLUE} px down from the top. "
            f"The top {GLUE} px is the glue band, where the pin sits and where you grab the note. Decorate it, "
            f"but keep the text area calm so tasks stay readable.<br>"
            f"• <b>Ink:</b> picked for you (dark on light pictures, light on dark), or set it below.<br>"
            f"Save the template, paint over it in any editor, upload it, and every note switches to it at once.",
            size=12)
        spec.setTextFormat(Qt.TextFormat.RichText)
        col.addWidget(spec)
        col.addWidget(label("Ink", bold=True))
        self.ink = Segmented([("auto", "Auto"), ("dark", "Dark"), ("light", "Light")], self.app.store.data["ink"])
        self.ink.changed.connect(self.app.set_ink)
        col.addWidget(self.ink)
        col.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self.fill_skins()
        return page

    def fill_skins(self) -> None:
        while self.skin_grid.count():
            w = self.skin_grid.takeAt(0).widget()
            if w:
                self.skin_group.removeButton(w)
                w.deleteLater()
        current = self.app.store.data["skin"]
        for i, skin in enumerate(all_skins(self.app.skins_dir)):
            b = QPushButton()
            b.setCheckable(True)
            b.setProperty("swatch", True)
            b.setFixedSize(96, 96)
            icon = QPixmap(78, 78)
            icon.fill(Qt.GlobalColor.transparent)
            p = QPainter(icon)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            if skin.key == "neon":
                for j in range(4):
                    img = preview(skin, 44, (j + 1) % 4)
                    p.drawImage(QRectF(4 + j * 9, 4 + j * 9, 44, 44), img)
            else:
                img = preview(skin, 78)
                scale = min(78 / img.width(), 78 / img.height())
                w, h = img.width() * scale, img.height() * scale
                p.drawImage(QRectF((78 - w) / 2, (78 - h) / 2, w, h), img)
            p.end()
            b.setIcon(QIcon(icon))
            b.setIconSize(QSize(78, 78))
            b.setToolTip(skin.name if skin.key != "neon" else "Neon (each sheet a new colour)")
            b.setChecked(skin.key == current)
            b.clicked.connect(lambda _=False, k=skin.key: self.app.set_skin(k))
            self.skin_group.addButton(b)
            self.skin_grid.addWidget(b, i // 5, i % 5)
        self.remove_button.setVisible(current.startswith("custom:"))
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
            "• Drag a pinned note by its paper, resize it from the bottom-right corner.<br>"
            "• Check off every task and the note crumples away. ✓ finishes it by hand, ✕ throws it away.<br>"
            "• Close the pad and Peelpad keeps running in the tray.", size=12)
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

