"""The writing on a note: rows of tasks (with a check box) or plain lines.

Enter starts a new row, Backspace on an empty row removes it, the arrows move
between rows. Right-click a check box to turn that row into a plain line.
The editor writes straight into the note's dict.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPalette
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from peelpad import store
from peelpad.skins import _draw_check, bloom, check_box, hand_font, row_height


class Sheet(QWidget):
    """Holds the rows. With neon ink it paints one halo behind all of them."""

    def __init__(self, editor: "TaskEditor"):
        super().__init__()
        self.editor = editor
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        ed = self.editor
        if ed.glow is None or not ed.rows:
            return
        dpr = self.devicePixelRatioF()
        layer = QImage(max(1, round(self.width() * dpr)), max(1, round(self.height() * dpr)),
                       QImage.Format.Format_ARGB32_Premultiplied)
        layer.setDevicePixelRatio(dpr)
        layer.fill(Qt.GlobalColor.transparent)
        q = QPainter(layer)
        for _, check, edit in ed.rows:
            for w in (check, edit):
                w.render(q, w.mapTo(self, QPoint(0, 0)), renderFlags=QWidget.RenderFlag(0))
        q.end()
        p = QPainter(self)
        p.drawImage(QPoint(0, 0), bloom(layer, ed.glow, ed.px * dpr))
        p.end()


class Check(QAbstractButton):
    def __init__(self, row: dict, editor: "TaskEditor"):
        super().__init__()
        self.row, self.editor = row, editor
        self.setCheckable(True)
        self.setChecked(row["done"])
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Check it off · right-click: plain line / task")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event):
        p = QPainter(self)
        box = check_box(self.editor.px, self.height())
        box.moveLeft(1)

        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        _draw_check(p, box, self.editor.ink, self.row["kind"], self.isChecked())
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.row["kind"] = "text" if self.row["kind"] == "task" else "task"
            if self.row["kind"] == "text":
                self.row["done"] = False
                self.setChecked(False)
            self.editor.restyle()
            self.editor.changed.emit()
            return
        if self.row["kind"] == "task":
            super().mousePressEvent(event)

    def sizeHint(self):
        return QSize(self.editor.px + 2, row_height(self.editor.px))


class RowEdit(QLineEdit):
    def __init__(self, row: dict, editor: "TaskEditor"):
        super().__init__(row["text"])
        self.row, self.editor = row, editor
        self.setFrame(False)
        self.setMaxLength(400)
        self.textChanged.connect(lambda _: editor.inner.update())

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.editor.submit.emit()
                return
            self.editor.add_after(self)
            return
        if key == Qt.Key.Key_Backspace and not self.text() and len(self.editor.rows) > 1:
            self.editor.remove(self)
            return
        if key == Qt.Key.Key_Up:
            self.editor.focus_step(self, -1)
            return
        if key == Qt.Key.Key_Down:
            self.editor.focus_step(self, 1)
            return
        super().keyPressEvent(event)


class TaskEditor(QScrollArea):
    """Scrolls when a note has more rows than fit."""

    changed = Signal()      # anything about the rows changed
    toggled = Signal()      # a box was checked or unchecked
    wrote = Signal()        # some text was written
    submit = Signal()       # Ctrl+Enter

    def __init__(self, parent=None):
        super().__init__(parent)
        self.note: dict | None = None
        self.ink = QColor("#1F1D1A")
        self.glow: QColor | None = None
        self.px = 17
        self.rows: list[tuple[QWidget, Check, RowEdit]] = []
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        self.viewport().setAutoFillBackground(False)
        self.inner = Sheet(self)
        self.column = QVBoxLayout(self.inner)
        self.column.setContentsMargins(0, 0, 0, 0)
        self.column.setSpacing(0)
        self.column.addStretch(1)
        self.setWidget(self.inner)

    # clicks on empty paper belong to the note (peel, move), not to the editor
    def mousePressEvent(self, event):
        event.ignore()

    def mouseMoveEvent(self, event):
        event.ignore()

    def mouseReleaseEvent(self, event):
        event.ignore()

    def viewportEvent(self, event):
        if event.type() in (event.Type.MouseButtonPress, event.Type.MouseMove, event.Type.MouseButtonRelease,
                            event.Type.MouseButtonDblClick):
            event.ignore()
            return False
        return super().viewportEvent(event)

    def bind(self, note: dict, ink: QColor, px: int, glow: QColor | None = None) -> None:
        self.note, self.ink, self.px, self.glow = note, QColor(ink), px, glow
        for w, _, _ in self.rows:
            w.deleteLater()
        self.rows = []
        if not note["rows"]:
            note["rows"].append(store.new_row())
        for row in note["rows"]:
            self._make(row, len(self.rows))
        self.restyle()

    def set_look(self, ink: QColor, px: int, glow: QColor | None = None) -> None:
        self.ink, self.px, self.glow = QColor(ink), px, glow
        self.restyle()

    def _make(self, row: dict, index: int) -> RowEdit:
        holder = QWidget()
        holder.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        line = QHBoxLayout(holder)
        line.setContentsMargins(0, 0, 0, 0)
        check = Check(row, self)
        edit = RowEdit(row, self)
        line.addWidget(check)
        line.addWidget(edit, 1)
        check.toggled.connect(lambda on, r=row: self._toggle(r, on))
        check.toggled.connect(lambda _: self.inner.update())
        edit.textEdited.connect(lambda text, r=row: self._edit(r, text))
        edit.focusInEvent = self._focus_in(edit)
        self.column.insertWidget(index, holder)
        self.rows.insert(index, (holder, check, edit))
        return edit

    def _focus_in(self, edit: RowEdit):
        original = QLineEdit.focusInEvent

        def handler(event):
            original(edit, event)
            self.ensureWidgetVisible(edit, 0, 4)
        return handler

    def restyle(self) -> None:
        rh = row_height(self.px)
        placeholder = QColor(self.ink)
        placeholder.setAlphaF(0.4)
        for i, (holder, check, edit) in enumerate(self.rows):
            holder.setFixedHeight(rh)
            check.setFixedSize(round(self.px * 0.95) + 3, rh)
            line = holder.layout()
            line.setSpacing(round(self.px * 0.5))
            done = check.row["done"]
            edit.setFont(hand_font(self.px, done))
            ink = QColor(self.ink)
            if done:
                ink.setAlphaF(0.55)
            pal = edit.palette()
            pal.setColor(QPalette.ColorRole.Text, ink)
            pal.setColor(QPalette.ColorRole.PlaceholderText, placeholder)
            pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
            sel = QColor(self.ink)
            sel.setAlphaF(0.18)
            pal.setColor(QPalette.ColorRole.Highlight, sel)
            pal.setColor(QPalette.ColorRole.HighlightedText, ink)
            edit.setPalette(pal)
            edit.setStyleSheet("QLineEdit { background: transparent; border: none; padding: 0; }")
            edit.setPlaceholderText("Write a task…" if i == 0 and len(self.rows) == 1 else "")
            check.update()
        self.column.setContentsMargins(*(round(self.px * 0.7),) * 4)
        self.inner.update()

    def _toggle(self, row: dict, on: bool) -> None:
        row["done"] = on
        row["done_at"] = store.today() if on else None
        self.restyle()
        self.changed.emit()
        self.toggled.emit()

    def _edit(self, row: dict, text: str) -> None:
        row["text"] = text
        if text.strip():
            if not row.get("created"):
                row["created"] = store.today()
            self.wrote.emit()
        self.changed.emit()

    def add_after(self, edit: RowEdit) -> None:
        index = next(i for i, r in enumerate(self.rows) if r[2] is edit) + 1
        row = store.new_row(kind=edit.row["kind"])
        self.note["rows"].insert(index, row)
        new = self._make(row, index)
        self.restyle()
        new.setFocus()
        self.changed.emit()

    def remove(self, edit: RowEdit) -> None:
        index = next(i for i, r in enumerate(self.rows) if r[2] is edit)
        holder, _, _ = self.rows.pop(index)
        self.note["rows"].remove(edit.row)
        holder.deleteLater()
        self.rows[max(0, index - 1)][2].setFocus()
        self.restyle()
        self.changed.emit()

    def focus_step(self, edit: RowEdit, step: int) -> None:
        index = next(i for i, r in enumerate(self.rows) if r[2] is edit) + step
        if 0 <= index < len(self.rows):
            self.rows[index][2].setFocus()

    def focus_end(self) -> None:
        """Put the cursor at the end: on the last row, or a new one if that has text."""
        if not self.rows:
            return
        last = self.rows[-1][2]
        if last.text().strip():
            self.add_after(last)
        else:
            last.setFocus()

    def text_rect(self) -> QRectF:
        """Where the rows are, in this widget's coordinates."""
        rh = row_height(self.px)
        return QRectF(0, 0, self.width(), min(self.height(), rh * len(self.rows)))
