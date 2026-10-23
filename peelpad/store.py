"""Notes and what you did with them, kept in one JSON file (no Qt here).

A note is a list of rows; a row is a task (with a check box) or a line of text.
Notes are never forgotten: finished and thrown-away ones stay in the file so the
stats can count them.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, timedelta
from pathlib import Path

NEON_COUNT = 4


def today() -> str:
    return date.today().isoformat()


def new_row(text: str = "", kind: str = "task") -> dict:
    return {"text": text, "kind": kind, "done": False, "created": today() if text.strip() else None,
            "done_at": None}


def new_note(color: int = 0) -> dict:
    return {"id": uuid.uuid4().hex[:12], "created": today(), "color": color % NEON_COUNT,
            "rows": [new_row()], "status": "draft", "rect": None, "closed": None}


def has_content(note: dict) -> bool:
    return any(r["text"].strip() for r in note["rows"])


def tasks(note: dict) -> list[dict]:
    return [r for r in note["rows"] if r["kind"] == "task" and r["text"].strip()]


def is_complete(note: dict) -> bool:
    """Every task on it is checked (and it has at least one)."""
    todo = tasks(note)
    return bool(todo) and all(r["done"] for r in todo)


DEFAULTS = {"version": 1, "skin": "neon", "notes": [], "days": [],
            "pad": {"pos": None, "on_top": False, "color": 0, "draft": None},
            "startup": False,
            # how notes look and read
            "ink": "auto",              # auto (the skin's), dark, light, or a #colour
            "glow": "auto",             # auto (the skin's), on, off: neon ink that shines
            "font": "",                 # a font family; empty is the handwriting default
            "text_scale": 1.0,
            "note_size": 300,           # width of the pad's sheets, px
            "mine": {"paper": "#1B1E2B", "ink": "#7DF9FF", "glow": True},   # "Your colours" theme
            "areas": {},                # skin key -> where its text box is, if you moved it
            "checked_skins": [],        # skins already checked for a painted-in checkerboard
            "wind": True,               # pinned notes sway in the wind
            "wind_speed": 3.6,          # m/s, up to 7.2
            "clock_color": "#FF2B2B",   # the Retro LED clock's digits
            "weather": {"city": "", "lat": None, "lon": None, "preview": "live"},   # the Weather look
            "language": "auto",         # auto follows Windows; or en, ar, es, ja, zh
            "auto_crumple": True}       # a note crumples by itself once every task on it is checked


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = json.loads(json.dumps(DEFAULTS))
        try:
            loaded = json.loads(self.path.read_text("utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
                self.data["pad"] = DEFAULTS["pad"] | loaded.get("pad", {})
                self.data["mine"] = DEFAULTS["mine"] | loaded.get("mine", {})
                self.data["weather"] = DEFAULTS["weather"] | loaded.get("weather", {})
        except (OSError, ValueError):
            pass
        if not self.data["pad"].get("draft"):
            self.data["pad"]["draft"] = new_note(self.data["pad"]["color"])

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), "utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass

    @property
    def draft(self) -> dict:
        return self.data["pad"]["draft"]

    def pinned(self) -> list[dict]:
        return [n for n in self.data["notes"] if n["status"] == "pinned"]

    def note(self, note_id: str) -> dict | None:
        return next((n for n in self.data["notes"] if n["id"] == note_id), None)

    def wrote(self, day: str | None = None) -> None:
        day = day or today()
        if day not in self.data["days"]:
            self.data["days"].append(day)

    def peel(self, rect: tuple[int, int, int, int]) -> dict:
        """The pad's top sheet comes off: it becomes a pinned note, and a new sheet is on top."""
        note = self.draft
        note["status"] = "pinned"
        note["rect"] = list(rect)
        self.data["notes"].append(note)
        pad = self.data["pad"]
        pad["color"] = (pad["color"] + 1) % NEON_COUNT
        pad["draft"] = new_note(pad["color"])
        return note

    def close(self, note: dict, finished: bool) -> None:
        """Finished by hand counts every task on it as done."""
        note["status"] = "finished" if finished else "deleted"
        note["closed"] = today()
        if finished:
            for r in tasks(note):
                if not r["done"]:
                    r["done"], r["done_at"] = True, today()

    def stats(self, now: date | None = None) -> dict:
        return compute_stats(self.data, now or date.today())

    def history(self) -> dict[str, dict[str, list[str]]]:
        return day_log(self.data)


def day_log(data: dict) -> dict[str, dict[str, list[str]]]:
    """Per day: the tasks you checked off and the tasks you wrote."""
    every = list(data["notes"]) + ([data["pad"]["draft"]] if data["pad"].get("draft") else [])
    log: dict[str, dict[str, list[str]]] = {}
    for n in every:
        for r in tasks(n):
            text = r["text"].strip()
            if r.get("created"):
                log.setdefault(r["created"], {"done": [], "written": []})["written"].append(text)
            if r["done"] and r.get("done_at") and n["status"] != "deleted":
                log.setdefault(r["done_at"], {"done": [], "written": []})["done"].append(text)
    return log


ARCHIVED = ("finished", "deleted")


def day_entries(data: dict, day: str) -> list[dict]:
    """Every task that shows on one day of History, and where it lives. Tasks on a note
    that is still pinned (or on the pad) are `live`: History leaves those alone."""
    every = list(data["notes"]) + ([data["pad"]["draft"]] if data["pad"].get("draft") else [])
    out = []
    for n in every:
        for i, r in enumerate(n["rows"]):
            if r["kind"] != "task" or not r["text"].strip():
                continue
            entry = {"text": r["text"].strip(), "note": n["id"], "row": i, "live": n["status"] not in ARCHIVED}
            if r["done"] and r.get("done_at") == day and n["status"] != "deleted":
                out.append(entry | {"what": "done"})
            if r.get("created") == day:
                out.append(entry | {"what": "written"})
    return out


def forget(data: dict, entries: list[dict]) -> int:
    """Delete tasks from History. Only finished or thrown-away notes are touched; a note
    left with no tasks goes too. Returns how many were skipped because they are live."""
    drop: dict[str, set[int]] = {}
    skipped = 0
    for e in entries:
        if e["live"]:
            skipped += 1
        else:
            drop.setdefault(e["note"], set()).add(e["row"])
    kept = []
    for n in data["notes"]:
        if n["id"] in drop and n["status"] in ARCHIVED:
            n["rows"] = [r for i, r in enumerate(n["rows"]) if i not in drop[n["id"]]]
            if not tasks(n):
                continue
        kept.append(n)
    data["notes"] = kept
    _tidy_days(data)
    return skipped


def forget_day(data: dict, day: str) -> int:
    skipped = forget(data, day_entries(data, day))
    if not any(e["live"] for e in day_entries(data, day)) and day in data["days"]:
        data["days"].remove(day)
    return skipped


def forget_all(data: dict) -> None:
    """Everything finished or thrown away goes; notes still pinned (and the pad) stay."""
    data["notes"] = [n for n in data["notes"] if n["status"] not in ARCHIVED]
    live_days = set(day_log(data))
    data["days"] = [d for d in data["days"] if d in live_days]


def _tidy_days(data: dict) -> None:
    """A day with nothing left on it is no longer a day you wrote."""
    left = set(day_log(data))
    data["days"] = [d for d in data["days"] if d in left]


def _streaks(days: set[date], now: date) -> tuple[int, int]:
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    current = 0
    d = now if now in days else now - timedelta(days=1)
    while d in days:
        current += 1
        d -= timedelta(days=1)
    return current, best


def compute_stats(data: dict, now: date) -> dict:
    """Days you wrote, days you finished everything you wrote, and the rest."""
    every = [n for n in data["notes"]] + ([data["pad"]["draft"]] if data["pad"].get("draft") else [])
    by_day: dict[str, list[bool]] = {}
    tasks_done = tasks_total = 0
    for n in every:
        for r in tasks(n):
            tasks_total += 1
            tasks_done += r["done"]
            day = r.get("created") or n.get("created")
            # a task on a thrown-away note was never done
            by_day.setdefault(day, []).append(bool(r["done"]) and n["status"] != "deleted")
    written = set(data["days"]) | set(by_day)
    completed = {d for d, xs in by_day.items() if xs and all(xs)}
    days = set()
    for d in written:
        try:
            days.add(date.fromisoformat(d))
        except (TypeError, ValueError):
            pass
    current, best = _streaks(days, now)
    finished = sum(n["status"] == "finished" for n in data["notes"])
    return {
        "days_written": len(days),
        "days_completed": len(completed),
        "notes_finished": finished,
        "notes_pinned": sum(n["status"] == "pinned" for n in data["notes"]),
        "tasks_done": tasks_done,
        "tasks_total": tasks_total,
        "completion": round(100 * tasks_done / tasks_total) if tasks_total else 0,
        "streak": current,
        "best_streak": best,
        "written": sorted(d.isoformat() for d in days),
        "completed": sorted(completed),
    }
