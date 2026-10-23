"""Peelpad: the pad, the notes pinned around the desktop, the tray and the settings."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, QTimer
from PySide6.QtGui import QAction, QColor, QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from peelpad.note import NoteWindow
from peelpad import skins
from peelpad.skins import DARK_INK, LIGHT_INK, note_images, skin_for
from peelpad.stage import CrumpleActor, Stages
from peelpad.store import Store
from peelpad.theme import app_icon
from peelpad.util import app_data_dir

APP_ID = "Niro54321.Peelpad"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class App(QObject):
    def __init__(self, qapp: QApplication):
        super().__init__()
        self.qapp = qapp
        self.data_dir = app_data_dir()
        self.skins_dir = self.data_dir / "skins"
        self.skins_dir.mkdir(exist_ok=True)
        self.store = Store(self.data_dir / "notes.json")
        self._check_skins()
        self.skin = skin_for(self.store.data["skin"], self.skins_dir, self.store.data["mine"], self.store.data["areas"])
        if self.skin.key != self.store.data["skin"]:
            self.store.data["skin"] = self.skin.key        # its picture is gone
        self._writing()
        self.stages = Stages()
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(400)
        self.save_timer.timeout.connect(self.store.save)
        self.settings = None
        self.windows: dict[str, NoteWindow] = {}
        self._weather_setup()

        from peelpad.pad import Pad
        self.pad = Pad(self)
        self._place_pad()
        for note in self.store.pinned():
            self.open_note(note)
        self._tray()
        self.pad.show()

    # ---------------------------------------------------------------- bookkeeping
    def changed(self) -> None:
        self.save_timer.start()

    def wrote(self) -> None:
        self.store.wrote()
        self.changed()

    def _check_skins(self) -> None:
        """Skins uploaded before Peelpad could remove a painted-in checkerboard: check them once."""
        checked = self.store.data["checked_skins"]
        for f in sorted(self.skins_dir.glob("*.png")):
            if f.name not in checked:
                try:
                    skins.clear_fake_background(f)
                except OSError:
                    pass
                checked.append(f.name)

    def _writing(self) -> None:
        """Font, size, ink and effect from the settings, for every note."""
        d = self.store.data
        ink = d.get("ink", "auto")
        skins.WRITING.ink = {"dark": DARK_INK, "light": LIGHT_INK}.get(ink) or (
            QColor(ink) if ink.startswith("#") else None)
        if "effect" not in d:                       # the older on/off glow switch
            d["effect"] = {"on": "neon", "off": "solid"}.get(d.pop("glow", "auto"), "auto")
        skins.WRITING.effect = d["effect"]
        skins.WRITING.family = d.get("font", "")
        from peelpad.scenes import LED

        LED.color = QColor(d.get("clock_color", "#FF2B2B"))
        skins.WRITING.scale = float(d.get("text_scale", 1.0))

    def restyle_all(self) -> None:
        self._writing()
        self.pad.refresh_look()
        for win in self.windows.values():
            win.refresh_look()
        self.changed()

    def _place_pad(self) -> None:
        pos = self.store.data["pad"].get("pos")
        if pos and QGuiApplication.screenAt(QPointF(pos[0] + 60, pos[1] + 60).toPoint()):
            self.pad.move(pos[0], pos[1])
            return
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.pad.move(area.right() - self.pad.width() - 60, area.top() + 80)

    @staticmethod
    def inside(rect: QRectF) -> QRectF:
        """Keep a note on a screen."""
        screen = QGuiApplication.screenAt(rect.center().toPoint()) or QGuiApplication.primaryScreen()
        area = QRectF(screen.availableGeometry())
        r = QRectF(rect)
        r.moveLeft(min(max(r.left(), area.left() + 4), area.right() - r.width() - 4))
        r.moveTop(min(max(r.top(), area.top() + 4), area.bottom() - r.height() - 4))
        return r

    # ---------------------------------------------------------------- notes
    def open_note(self, note: dict) -> NoteWindow:
        x, y, w, h = note["rect"]
        r = self.inside(QRectF(x, y, w, h))
        note["rect"] = [round(r.x()), round(r.y()), round(r.width()), round(r.height())]
        win = NoteWindow(self, note)
        win.show()
        self.windows[note["id"]] = win
        return win

    def peeled(self, rect: QRectF) -> None:
        """The top sheet landed: pin it there."""
        r = self.inside(rect)
        note = self.store.peel((round(r.x()), round(r.y()), round(r.width()), round(r.height())))
        self.store.wrote()
        win = self.open_note(note)
        win.raise_()
        self.changed()
        self._refresh_settings()

    def crumple(self, win: NoteWindow, finished: bool) -> None:
        note = win.note
        r = win.global_paper()
        dpr = max(1.0, win.devicePixelRatioF())
        front, back = note_images(note, self.skin, round(r.width()), round(r.height()), dpr)
        stage = self.stages.at(r.center())
        stage.add(CrumpleActor(r, front, back, dpr, note["id"]))
        QTimer.singleShot(30, win.close)
        QTimer.singleShot(60, win.deleteLater)
        self.windows.pop(note["id"], None)
        self.store.close(note, finished)
        self.changed()
        self._refresh_settings()

    def free_spot(self, pad_paper: QRectF) -> QPointF:
        """Where Ctrl+Enter drops a sheet: beside the pad, stepping down past notes already there."""
        x = pad_paper.left() - pad_paper.width() - 40
        screen = QGuiApplication.screenAt(pad_paper.center().toPoint()) or QGuiApplication.primaryScreen()
        if x < screen.availableGeometry().left():
            x = pad_paper.right() + 40
        y = pad_paper.top()
        taken = [w.global_paper() for w in self.windows.values()]
        while any(abs(t.left() - x) < 24 and abs(t.top() - y) < 24 for t in taken):
            y += 34
            x += 12
        r = self.inside(QRectF(x, y, pad_paper.width(), pad_paper.height()))
        return r.topLeft()

    # ---------------------------------------------------------------- look
    def set_skin(self, key: str) -> None:
        self.skin = skin_for(key, self.skins_dir, self.store.data["mine"], self.store.data["areas"])
        self.store.data["skin"] = self.skin.key
        if self.skin.key == "anim:weather":
            self.refresh_weather()
        self.pad.resize_for_skin()
        for win in self.windows.values():
            win.refresh_look()
        self.changed()
        if self.settings:
            self.settings.fill_skins()

    def delete_skins(self, keys: list[str]) -> None:
        """Delete pictures you uploaded (never Peelpad's own looks)."""
        for key in keys:
            if not key.startswith("custom:"):
                continue
            try:
                (self.skins_dir / key[7:]).unlink()
            except OSError:
                pass
            self.store.data["areas"].pop(key, None)
            if key[7:] in self.store.data["checked_skins"]:
                self.store.data["checked_skins"].remove(key[7:])
        if self.store.data["skin"] in keys:
            self.set_skin("neon")
        elif self.settings:
            self.settings.fill_skins()
        self.changed()

    def set_mine(self, **changes) -> None:
        """Your own paper and ink colours (and glow), worn at once."""
        self.store.data["mine"].update(changes)
        self.set_skin("mine")

    def set_area(self, key: str, area: tuple | None) -> None:
        """Move a skin's text box (None puts it back where Peelpad found it)."""
        if area is None:
            self.store.data["areas"].pop(key, None)
        else:
            self.store.data["areas"][key] = [round(v, 4) for v in area]
        if key == self.skin.key:
            self.set_skin(key)
        self.changed()

    # ---------------------------------------------------------------- the Weather look
    WEATHER_EVERY = 20 * 60 * 1000          # ms between looks at the sky

    def _weather_setup(self) -> None:
        from peelpad import weather

        w = self.store.data["weather"]
        weather.Now.preview = w.get("preview", "live")
        weather.Now.place = w.get("city", "")
        self.fetcher = weather.Fetcher(self)
        self.fetcher.found.connect(self._weather_found)
        self.fetcher.updated.connect(self._weather_updated)
        self.fetcher.failed.connect(self._weather_failed)
        self.weather_timer = QTimer(self)
        self.weather_timer.setInterval(self.WEATHER_EVERY)
        self.weather_timer.timeout.connect(self.refresh_weather)
        self.weather_timer.start()
        self.weather_note = ""
        QTimer.singleShot(1500, self.refresh_weather)

    def refresh_weather(self) -> None:
        """Ask for the weather, but only while the Weather look is in use and a city is set."""
        w = self.store.data["weather"]
        if self.skin.key == "anim:weather" and w.get("lat") is not None:
            self.fetcher.refresh(w["lat"], w["lon"])

    def set_weather_city(self, city: str) -> None:
        if city.strip():
            self.weather_note = "Looking for it…"
            self.fetcher.find(city)
            if self.settings:
                self.settings.fill_weather()

    def set_weather_preview(self, key: str) -> None:
        from peelpad import weather

        self.store.data["weather"]["preview"] = weather.Now.preview = key
        self.changed()

    def _weather_found(self, place) -> None:
        from peelpad import weather

        if place is None:
            self.weather_note = "Couldn't find that city. Try its English name."
        else:
            w = self.store.data["weather"]
            w.update(city=place["city"], lat=place["lat"], lon=place["lon"])
            weather.Now.place = place["city"]
            self.weather_note = ""
            self.changed()
        if self.settings:
            self.settings.fill_weather()

    def _weather_updated(self, now: dict) -> None:
        import time

        from peelpad import weather

        weather.Now.state, weather.Now.day, weather.Now.temp = now["state"], now["day"], now["temp"]
        weather.Now.updated = time.time()
        self.weather_note = ""
        if self.settings:
            self.settings.fill_weather()

    def _weather_failed(self, why: str) -> None:
        self.weather_note = "Couldn't reach the weather service (no internet?). Peelpad tries again later."
        if self.settings:
            self.settings.fill_weather()

    def set_clock_color(self, color: str) -> None:
        self.store.data["clock_color"] = color
        self.restyle_all()
        self.pad.update()
        if self.settings:
            self.settings.fill_clock()

    def wind_speed(self) -> float:
        """How hard the wind blows on pinned notes, m/s (0 when it's off)."""
        d = self.store.data
        return float(d.get("wind_speed", 3.6)) if d.get("wind", True) else 0.0

    def set_wind(self, on: bool | None = None, speed: float | None = None) -> None:
        if on is not None:
            self.store.data["wind"] = bool(on)
        if speed is not None:
            self.store.data["wind_speed"] = round(max(0.0, min(7.2, speed)), 1)
        for win in self.windows.values():
            win.update_wind()
        self.changed()

    def set_writing(self, key: str, value) -> None:
        """ink, effect, font or text_scale."""
        self.store.data[key] = value
        self.restyle_all()
        if self.settings and key in ("ink", "effect"):
            self.settings.fill_writing()

    def set_note_size(self, width: int) -> None:
        self.store.data["note_size"] = max(140, min(640, int(width)))
        self.pad.resize_for_skin()
        self.changed()
        if self.settings:
            self.settings.size_slider.set(self.store.data["note_size"])

    def set_pad_on_top(self, on: bool) -> None:
        self.store.data["pad"]["on_top"] = bool(on)
        self.pad.set_on_top(bool(on))
        self.changed()

    # ---------------------------------------------------------------- start with Windows
    @staticmethod
    def _command() -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        root = Path(__file__).resolve().parent.parent
        return f'"{pythonw}" -c "import sys; sys.path.insert(0, r\'{root}\'); from peelpad.app import main; main()"'

    def startup_enabled(self) -> bool:
        if sys.platform != "win32":
            return False
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, "Peelpad")
                return True
        except OSError:
            return False

    def set_startup(self, on: bool) -> None:
        if sys.platform != "win32":
            return
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if on:
                    winreg.SetValueEx(key, "Peelpad", 0, winreg.REG_SZ, self._command())
                else:
                    winreg.DeleteValue(key, "Peelpad")
        except OSError:
            pass

    # ---------------------------------------------------------------- windows and tray
    def show_pad(self) -> None:
        self.pad.show()
        self.pad.raise_()
        self.pad.activateWindow()

    def show_settings(self, tab: str = "stats") -> None:
        if self.settings is None:
            from peelpad.settings import Settings
            self.settings = Settings(self)
        self.settings.open(tab if isinstance(tab, str) else "stats")

    def _refresh_settings(self) -> None:
        if self.settings and self.settings.isVisible():
            self.settings.refresh_stats()

    def _tray(self) -> None:
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("Peelpad")
        menu = QMenu()
        for text, slot in (("Show the pad", self.show_pad), ("Settings && stats", self.show_settings)):
            act = QAction(text, menu)
            act.triggered.connect(lambda _=False, s=slot: s())
            menu.addAction(act)
        menu.addSeparator()
        quit_act = QAction("Quit Peelpad", menu)
        quit_act.triggered.connect(self.quit)
        menu.addAction(quit_act)
        self.tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.show_pad() if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                                                         QSystemTrayIcon.ActivationReason.DoubleClick) else None)
        self.tray.show()

    def quit(self) -> None:
        self.stages.clear()
        self.store.save()
        self.tray.hide()
        self.qapp.quit()


def _already_running() -> bool:
    """Ask a Peelpad that is already open to show its pad."""
    sock = QLocalSocket()
    sock.connectToServer(APP_ID)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def main() -> None:
    if sys.platform == "win32":
        # its own taskbar button and icon, not python.exe's
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    qapp = QApplication.instance() or QApplication(sys.argv)
    qapp.setApplicationName("Peelpad")
    qapp.setWindowIcon(app_icon())
    qapp.setQuitOnLastWindowClosed(False)
    if _already_running():
        sys.exit(0)
    server = QLocalServer()
    QLocalServer.removeServer(APP_ID)
    server.listen(APP_ID)
    app = App(qapp)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), app.show_pad()))
    qapp.aboutToQuit.connect(app.store.save)
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
