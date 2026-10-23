"""Glass windows and the small controls on them, after Spinvert and Clipnest:
a frameless window you resize by its edges, pill toggles and slider rows."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QSize, Qt, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import (QButtonGroup, QDialog, QHBoxLayout, QLabel, QPushButton, QSlider,
                               QVBoxLayout, QWidget)

from peelpad.glassui import HEADER, MARGIN, GlassFrame
from peelpad.theme import app_icon

EDGE = 9  # px either side of the card's border that resize the window


class GlassMixin:
    """Paint, move, resize and drag handling shared by the glass window and dialog."""

    frame: GlassFrame

    def setup_glass(self, title: str, size, minimum):
        self.setWindowTitle(title)
        self.setWindowIcon(app_icon())
        self.setMouseTracking(True)
        self.least = QSize(*minimum)
        self.setMinimumSize(self.least)
        screen = (QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()).availableGeometry()
        self.resize(min(size[0], int(screen.width() * 0.96)), min(size[1], int(screen.height() * 0.94)))
        self.frame = GlassFrame(self, title)
        root = QVBoxLayout(self)
        root.setContentsMargins(MARGIN + 18, MARGIN + 10, MARGIN + 18, MARGIN + 16)
        root.setSpacing(10)
        self.top_bar = QHBoxLayout()
        self.top_bar.addStretch()
        root.addLayout(self.top_bar)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        root.addLayout(self.body, 1)
        return root

    def center_on_screen(self):
        self.winId()
        screen = (QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()).availableGeometry()
        self.move(screen.center().x() - self.width() // 2, screen.center().y() - self.height() // 2)
        self.frame.refresh_backdrop()

    def paintEvent(self, event):
        p = QPainter(self)
        self.frame.paint(p)
        p.end()

    def moveEvent(self, event):
        self.frame.moved()

    def resizeEvent(self, event):
        self.frame.resized()
        self.frame.moved()

    def _edges(self, pos: QPointF):
        if self.isMaximized():
            return None
        card = self.frame.card()
        x, y = pos.x(), pos.y()
        if not card.adjusted(-EDGE, -EDGE, EDGE, EDGE).contains(pos):
            return None
        edges = Qt.Edge(0)
        if abs(x - card.left()) <= EDGE:
            edges |= Qt.Edge.LeftEdge
        elif abs(x - card.right()) <= EDGE:
            edges |= Qt.Edge.RightEdge
        if abs(y - card.top()) <= EDGE:
            edges |= Qt.Edge.TopEdge
        elif abs(y - card.bottom()) <= EDGE:
            edges |= Qt.Edge.BottomEdge
        return edges if edges != Qt.Edge(0) else None

    def mouseMoveEvent(self, event):
        edges = self._edges(event.position())
        if edges is None:
            self.unsetCursor()
            return
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            forward = edges in (Qt.Edge.LeftEdge | Qt.Edge.TopEdge, Qt.Edge.RightEdge | Qt.Edge.BottomEdge)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor if forward else Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeHorCursor if horizontal else Qt.CursorShape.SizeVerCursor)

    def mousePressEvent(self, event):
        edges = self._edges(event.position())
        if edges is not None and event.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemResize(edges)
            return
        self.frame.press(event)

    def mouseDoubleClickEvent(self, event):
        if event.position().y() < MARGIN + HEADER:
            self.showNormal() if self.isMaximized() else self.showMaximized()


class GlassWindow(GlassMixin, QWidget):
    def __init__(self, title: str, size=(620, 700), minimum=(520, 560)):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setup_glass(title, size, minimum)
        minimize = self.frame.close_button(self.showMinimized)
        minimize.setText("–")
        minimize.setToolTip("Minimise")
        self.top_bar.addWidget(minimize)
        self.top_bar.addWidget(self.frame.close_button(self.close))

    def changeEvent(self, event):
        # back from the taskbar: the desktop behind may have changed, so frost it again
        if event.type() == QEvent.Type.WindowStateChange and not self.isMinimized() \
                and event.oldState() & Qt.WindowState.WindowMinimized:
            self.hide()
            self.frame.refresh_backdrop()
            self.show()
        super().changeEvent(event)


class GlassDialog(GlassMixin, QDialog):
    def __init__(self, title: str, size=(1000, 700), minimum=(820, 560), primary: str = "Export"):
        super().__init__(None, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        root = self.setup_glass(title, size, minimum)
        self.top_bar.addWidget(self.frame.close_button(self.reject))
        self.footer = QHBoxLayout()
        self.footer.setSpacing(8)
        self.footer_left = QHBoxLayout()
        self.footer.addLayout(self.footer_left, 1)
        self.cancel_button = QPushButton("Close")
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button = QPushButton(primary)
        self.ok_button.setProperty("primary", True)
        self.footer.addWidget(self.cancel_button)
        self.footer.addWidget(self.ok_button)
        root.addLayout(self.footer)

    def run(self) -> int:
        self.center_on_screen()
        return self.exec()


def label(text: str = "", muted: bool = False, bold: bool = False, size: int = 13) -> QLabel:
    w = QLabel(text)
    w.setWordWrap(True)
    style = f"font-size: {size}px;"
    if bold:
        style += " font-weight: 700;"
    if muted:
        style += " opacity: 0.8;"
    w.setStyleSheet(style)
    return w


class Segmented(QWidget):
    """A row of pill buttons, one checked at a time."""

    changed = Signal(str)

    def __init__(self, options, current=None):
        super().__init__()
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        for key, text in options:
            b = QPushButton(text.replace("&", "&&"))
            b.setCheckable(True)
            b.setProperty("segment", True)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self.group.addButton(b)
            self.buttons[key] = b
            row.addWidget(b)
        row.addStretch()
        self.set(current)

    def get(self):
        return next((k for k, b in self.buttons.items() if b.isChecked()), None)

    def set(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)


class SliderRow(QWidget):
    """Name, slider and the value, on one line."""

    changed = Signal(float)

    def __init__(self, name: str, lo: float, hi: float, value: float, suffix: str = "", scale: int = 1):
        super().__init__()
        self.scale, self.suffix = scale, suffix
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.name = QLabel(name)
        self.name.setMinimumWidth(70)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(lo * scale), int(hi * scale))
        self.slider.setValue(int(value * scale))
        self.value = QLabel()
        self.value.setMinimumWidth(44)
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.name)
        row.addWidget(self.slider, 1)
        row.addWidget(self.value)
        self.slider.valueChanged.connect(self._moved)
        self._moved(self.slider.value())

    def _moved(self, v):
        self.value.setText(f"{v / self.scale:g}{self.suffix}")
        self.changed.emit(v / self.scale)

    def get(self) -> float:
        return self.slider.value() / self.scale

    def set(self, v: float):
        self.slider.setValue(int(round(v * self.scale)))
