"""Text effects for the writing on a note: Solid, Gradient, Neon, Toon, Pop,
Gummy and Prism, all in the ink colour you pick. The text is turned into a
path, so it can be filled with a gradient, outlined and shaded.

Neon's halo is a soft blur, so it is added around the whole writing at once
(see skins.bloom); here Neon only paints the bright core.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath, QPen

EFFECTS = [("solid", "Solid"), ("gradient", "Gradient"), ("neon", "Neon"), ("toon", "Toon"),
           ("pop", "Pop"), ("gummy", "Gummy"), ("prism", "Prism")]


def hue_shift(c: QColor, degrees: float) -> QColor:
    h, s, light, a = c.getHslF()
    h = 0.0 if h < 0 else h                      # greys have no hue
    if s < 0.2:                                  # give a grey ink something to shift
        s, light = 0.75, min(max(light, 0.35), 0.7)
    return QColor.fromHslF((h + degrees / 360) % 1.0, s, light, a)


def text_path(text: str, font: QFont, rect: QRectF, right: bool) -> QPainterPath:
    """The text as an outline, centred in the row like a line edit draws it."""
    plain = QFont(font)
    plain.setStrikeOut(False)
    fm = QFontMetricsF(plain)
    text = fm.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
    width = fm.horizontalAdvance(text)
    x = rect.right() - width if right else rect.left()
    y = rect.center().y() + (fm.ascent() - fm.descent()) / 2
    path = QPainterPath()
    path.addText(QPointF(x, y), plain, text)
    return path


def draw_text(p: QPainter, rect: QRectF, text: str, font: QFont, ink: QColor, effect: str,
              right: bool = False, done: bool = False) -> None:
    """Write one row's text in `ink` with `effect`."""
    if not text:
        return
    path = text_path(text, font, rect, right)
    box = path.boundingRect()
    px = font.pixelSize() if font.pixelSize() > 0 else 16
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if done:
        p.setOpacity(p.opacity() * 0.55)
    p.setPen(Qt.PenStyle.NoPen)
    ink = QColor(ink)
    dark = QColor(ink).darker(260) if ink.lightnessF() > 0.25 else QColor(255, 255, 255, 200)
    dark.setAlpha(ink.alpha())
    if effect == "gradient":
        g = QLinearGradient(box.topLeft(), box.topRight())
        g.setColorAt(0, ink)
        g.setColorAt(1, hue_shift(ink, 70))
        p.fillPath(path, g)
    elif effect == "neon":
        core = QColor(ink).lighter(118)
        p.fillPath(path, core)
    elif effect == "toon":
        p.strokePath(path.translated(px * 0.04, px * 0.07), QPen(dark, px * 0.2, Qt.PenStyle.SolidLine,
                                                                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.strokePath(path, QPen(dark, px * 0.16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
        p.fillPath(path, ink)
    elif effect == "pop":
        back = hue_shift(ink, 180).darker(140)
        back.setAlpha(ink.alpha())
        p.fillPath(path.translated(px * 0.09, px * 0.09), back)
        p.strokePath(path, QPen(dark, max(0.8, px * 0.05)))
        p.fillPath(path, ink)
    elif effect == "gummy":
        p.strokePath(path, QPen(QColor(ink).darker(170), px * 0.13, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
        g = QLinearGradient(box.topLeft(), box.bottomLeft())
        g.setColorAt(0, QColor(ink).lighter(165))
        g.setColorAt(0.55, ink)
        g.setColorAt(1, QColor(ink).darker(125))
        p.fillPath(path, g)
        p.save()
        p.setClipPath(path)
        shine = QColor(255, 255, 255, 120)
        p.fillRect(QRectF(box.left(), box.top(), box.width(), box.height() * 0.38), shine)
        p.restore()
    elif effect == "prism":
        g = QLinearGradient(box.topLeft(), box.topRight())
        for i in range(7):
            g.setColorAt(i / 6, hue_shift(ink, i * 300 / 6))
        p.strokePath(path, QPen(QColor(0, 0, 0, 70), max(0.8, px * 0.06)))
        p.fillPath(path, g)
    else:
        p.fillPath(path, ink)
    if done:
        y = box.center().y()
        p.setPen(QPen(ink, max(1.0, px * 0.08)))
        p.drawLine(QPointF(box.left() - 1, y), QPointF(box.right() + 1, y))
    p.restore()


def effect_icon(effect: str, name: str, ink: QColor, w: int = 112, h: int = 44, dpr: float = 1.0) -> QImage:
    """A small sample of an effect, like the buttons in Settings."""
    img = QImage(round(w * dpr), round(h * dpr), QImage.Format.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(dpr)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(28, 28, 34, 235))
    p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 10, 10)
    f = QFont("Segoe UI")
    f.setPixelSize(17)
    f.setBold(True)
    rect = QRectF(0, 0, w, h)
    path = text_path(name, f, rect, False)
    path.translate((w - path.boundingRect().width()) / 2 - path.boundingRect().left(), 0)
    if effect == "neon":
        from peelpad.skins import bloom

        layer = QImage(img.size(), QImage.Format.Format_ARGB32_Premultiplied)
        layer.setDevicePixelRatio(dpr)
        layer.fill(Qt.GlobalColor.transparent)
        q = QPainter(layer)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.fillPath(path, QColor(ink).lighter(118))
        q.end()
        p.drawImage(QPointF(0, 0), bloom(layer, ink, 17 * dpr))
    shift = path.boundingRect().left() - text_path(name, f, rect, False).boundingRect().left()
    draw_text(p, rect.translated(shift, 0), name, f, ink, effect)
    p.end()
    return img
