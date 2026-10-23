"""Live weather for the Weather look, from Open-Meteo (open-meteo.com: free, no
account, no key). Only the city you type (then its coordinates) is sent, and only
while the Weather look is in use. Your notes never leave your PC.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request

from PySide6.QtCore import QObject, Signal

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&format=json"
FORECAST = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,weather_code,is_day&timezone=auto")

STATES = ["clear", "partly", "cloudy", "fog", "rain", "snow", "storm"]
LABELS = {"clear": "Clear", "partly": "Partly cloudy", "cloudy": "Cloudy", "fog": "Fog", "rain": "Rain",
          "snow": "Snow", "storm": "Thunderstorm"}
PREVIEWS = [("live", "Live"), ("clear", "Sun"), ("partly", "Some clouds"), ("cloudy", "Clouds"), ("rain", "Rain"),
            ("snow", "Snow"), ("storm", "Storm"), ("fog", "Fog"), ("night", "Night")]


def state_for(code: int) -> str:
    """WMO weather code (what Open-Meteo returns) to one of the scenes."""
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "partly"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "rain"
    return "cloudy"


class Now:
    """What the Weather look shows."""
    state = "partly"
    day = True
    temp: float | None = None
    place = ""
    preview = "live"           # or a state (or "night") to see it without waiting for the sky
    updated = 0.0


def shown() -> tuple[str, bool]:
    """The weather on screen: the live one, or the one being previewed."""
    if Now.preview == "night":
        return "clear", False
    if Now.preview in STATES:
        return Now.preview, True
    if not Now.updated:                       # no weather yet: a calm sky by the clock
        hour = time.localtime().tm_hour
        return "partly", 6 <= hour < 19
    return Now.state, Now.day


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Peelpad (github.com/Niro54321/Peelpad)"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode("utf-8"))


def find_place(city: str) -> dict | None:
    data = _get(GEOCODE.format(q=urllib.parse.quote(city.strip())))
    hits = data.get("results") or []
    if not hits:
        return None
    h = hits[0]
    return {"city": h.get("name", city), "country": h.get("country_code", ""), "lat": h["latitude"],
            "lon": h["longitude"]}


def current(lat: float, lon: float) -> dict:
    cur = _get(FORECAST.format(lat=lat, lon=lon)).get("current", {})
    return {"state": state_for(int(cur.get("weather_code", 3))), "day": bool(cur.get("is_day", 1)),
            "temp": cur.get("temperature_2m")}


class Fetcher(QObject):
    """Asks for the weather off the UI thread and reports back on it."""

    found = Signal(object)        # a place dict, or None when the city wasn't found
    updated = Signal(object)      # a weather dict
    failed = Signal(str)

    def find(self, city: str) -> None:
        def work():
            try:
                place = find_place(city)
                self.found.emit(place)
                if place:
                    self.updated.emit(current(place["lat"], place["lon"]))
            except Exception as e:  # no network, a timeout...: shown to the user, not raised
                self.failed.emit(str(e))
        threading.Thread(target=work, daemon=True).start()

    def refresh(self, lat: float, lon: float) -> None:
        def work():
            try:
                self.updated.emit(current(lat, lon))
            except Exception as e:
                self.failed.emit(str(e))
        threading.Thread(target=work, daemon=True).start()
