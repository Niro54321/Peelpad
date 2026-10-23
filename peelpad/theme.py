"""Glass colours and the app icon, drawn in code (no image files to ship)."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

LEMON, BUBBLEGUM = QColor("#F3FF6B"), QColor("#FF74C8")


@dataclass(frozen=True)
class Glass:
    """Colours for frosted glass over a dark or a bright background."""
    tint: QColor
    sheen: int
    rim_top: int
    rim_bottom: int
    outline: QColor
    shadow: int
    segment: QColor
    segment_edge: QColor
    hover: QColor
    hover_text: QColor
    text: QColor
    text_shadow: QColor
    muted: QColor
    hub: QColor
    pill: QColor


ON_DARK = Glass(tint=QColor(22, 22, 30, 64), sheen=46, rim_top=120, rim_bottom=30,
                outline=QColor(0, 0, 0, 40), shadow=70,
                segment=QColor(255, 255, 255, 20), segment_edge=QColor(255, 255, 255, 60),
                hover=QColor(255, 255, 255, 238), hover_text=QColor("#16161D"),
                text=QColor(255, 255, 255, 248), text_shadow=QColor(0, 0, 0, 110),
                muted=QColor(255, 255, 255, 200), hub=QColor(255, 255, 255, 40),
                pill=QColor(255, 255, 255, 46))
ON_BRIGHT = Glass(tint=QColor(246, 246, 250, 96), sheen=70, rim_top=230, rim_bottom=90,
                  outline=QColor(0, 0, 0, 34), shadow=50,
                  segment=QColor(255, 255, 255, 92), segment_edge=QColor(0, 0, 0, 26),
                  hover=QColor(22, 22, 30, 225), hover_text=QColor(255, 255, 255),
                  text=QColor("#17171F"), text_shadow=QColor(255, 255, 255, 120),
                  muted=QColor(23, 23, 31, 170), hub=QColor(255, 255, 255, 120),
                  pill=QColor(0, 0, 0, 16))


def draw_mark(p: QPainter, rect: QRectF) -> None:
    """The Peelpad mark: a lemon sticky note over a pink one, its corner peeling up."""
    s = min(rect.width(), rect.height())
    o = QPointF(rect.center().x() - s / 2, rect.center().y() - s / 2)

    def at(x, y):
        return QPointF(o.x() + x * s, o.y() + y * s)

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    edge = QPen(QColor(20, 20, 26, 90), max(0.8, s * 0.018))
    # the pink sheet underneath, turned a little
    p.save()
    p.translate(at(0.5, 0.5))
    p.rotate(-9)
    p.translate(-at(0.5, 0.5))
    under = QPainterPath()
    under.addRoundedRect(QRectF(at(0.13, 0.1), at(0.84, 0.81)), s * 0.07, s * 0.07)
    p.setPen(edge)
    p.fillPath(under, BUBBLEGUM)
    p.drawPath(under)
    p.restore()
    # the lemon sheet, its bottom-right corner folded back
    cut = 0.3
    top = QPainterPath()
    top.moveTo(at(0.16 + 0.06, 0.17))
    top.lineTo(at(0.9 - 0.06, 0.17))
    top.quadTo(at(0.9, 0.17), at(0.9, 0.23))
    top.lineTo(at(0.9, 0.91 - cut))
    top.lineTo(at(0.9 - cut, 0.91))
    top.lineTo(at(0.22, 0.91))
    top.quadTo(at(0.16, 0.91), at(0.16, 0.85))
    top.lineTo(at(0.16, 0.23))
    top.quadTo(at(0.16, 0.17), at(0.22, 0.17))
    top.closeSubpath()
    fill = QLinearGradient(at(0.16, 0.17), at(0.9, 0.91))
    fill.setColorAt(0, LEMON.lighter(104))
    fill.setColorAt(1, QColor("#E3F046"))
    p.fillPath(top, fill)
    p.setPen(edge)
    p.drawPath(top)
    # glue band
    p.fillRect(QRectF(at(0.17, 0.18), at(0.89, 0.3)), QColor(0, 0, 0, 14))
    # the curl: the back of the paper, lighter, with a soft shadow under it
    shadow = QPainterPath()
    shadow.moveTo(at(0.9, 0.91 - cut))
    shadow.lineTo(at(0.9 - cut, 0.91))
    shadow.lineTo(at(0.9 - cut * 0.92, 0.91 - cut * 0.62))
    shadow.closeSubpath()
    p.fillPath(shadow, QColor(0, 0, 0, 60))
    curl = QPainterPath()
    curl.moveTo(at(0.9, 0.91 - cut))
    curl.quadTo(at(0.9 - cut * 0.55, 0.91 - cut * 0.55), at(0.9 - cut * 0.98, 0.91 - cut * 1.02))
    curl.quadTo(at(0.9 - cut * 0.42, 0.91 - cut * 0.42), at(0.9 - cut, 0.91))
    curl.closeSubpath()
    back = QLinearGradient(at(0.9, 0.91 - cut), at(0.9 - cut, 0.91 - cut))
    back.setColorAt(0, QColor("#FBFFD0"))
    back.setColorAt(1, QColor("#EEF78A"))
    p.fillPath(curl, back)
    p.setPen(edge)
    p.drawPath(curl)
    # two lines of ink
    if s >= 24:
        ink = QPen(QColor(30, 30, 36, 170), max(1.0, s * 0.035), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(ink)
        p.drawLine(at(0.27, 0.43), at(0.72, 0.43))
        p.drawLine(at(0.27, 0.56), at(0.6, 0.56))
    p.restore()


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_mark(p, QRectF(0, 0, size, size))
        p.end()
        icon.addPixmap(pm)
    return icon


def save_ico(path) -> None:
    """Write the icon as .ico (for a shortcut or an installer)."""
    from PIL import Image

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    app_icon().pixmap(256, 256).save(buf, "PNG")
    Image.open(BytesIO(bytes(buf.data()))).save(
        path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])


def soft_text(p: QPainter, rect: QRectF, text: str, color: QColor, shadow: QColor,
              flags=Qt.AlignmentFlag.AlignCenter) -> None:
    """Text with a soft shadow under it, so it reads on any glass."""
    if shadow.alpha():
        faint = QColor(shadow)
        faint.setAlpha(shadow.alpha() // 2)
        for (dx, dy), pen in (((0, 2), faint), ((1, 1), faint), ((-1, 1), faint), ((0, 1), shadow)):
            p.setPen(pen)
            p.drawText(rect.translated(dx, dy), flags, text)
    p.setPen(color)
    p.drawText(rect, flags, text)


def thin_pen(color: QColor, width: float = 1.0) -> QPen:
    pen = QPen(color)
    pen.setWidthF(width)
    return pen
