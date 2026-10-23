"""Smoke tests: the paper physics, the stats, skins, and drawing every effect offscreen.

    python -m pytest tests -q
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PEELPAD_HOME", tempfile.mkdtemp(prefix="peelpad-test-"))

from PySide6.QtCore import QPointF, QRectF  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from peelpad import physics, skins, store  # noqa: E402

APP = QApplication.instance() or QApplication([])


def note_with(*texts, done=()):
    n = store.new_note(0)
    n["rows"] = [store.new_row(t) for t in texts]
    for i in done:
        n["rows"][i]["done"] = True
    return n


# ---------------------------------------------------------------- physics

def test_fold_depth_tracks_the_cursor():
    r = 20.0
    for pull in (0.5, 5, 30, math.pi * r, 80, 250):
        d = physics.fold_depth(pull, r)
        assert abs(d - physics.curl_x(d, r) - pull) < 1e-3


def test_fold_keeps_the_sheet_and_lays_the_flap_on_top():
    shape = physics.fold(300, 300, (290, 290), (150, 150), 20)
    assert shape.fold_line is not None
    zs = [b.z for b in shape.bands]
    assert zs == sorted(zs)
    assert shape.bands[-1].back                      # the flap shows the back of the paper
    area = sum(physics._area(b.poly) for b in shape.bands)
    assert 300 * 300 * 0.98 < area < 300 * 300 * 1.08   # bands overlap only by hairlines


def test_tiny_pull_does_nothing():
    shape = physics.fold(300, 300, (100, 290), (100.2, 290), 20)
    assert len(shape.bands) == 1 and shape.bands[0].dst == shape.bands[0].src


def test_lift_bends_more_then_tears():
    lift = physics.Lift(300, 300, (150, 290), (0.0, 1.0))
    bends = [lift.solve(p)[0] for p in (0, 30, 80, 119)]
    assert bends == sorted(bends) and bends[0] == 0 and bends[-1] > 0.6
    assert lift.solve(100)[1] == 0 and lift.solve(160)[1] == 40
    shape = lift.shape(80)
    assert len(shape.bands) > 10 and shape.stretch == 0


def test_glue_decides_when_a_fold_tears_off():
    small = physics.fold_reaches(300, 300, (290, 290), (250, 250), 20, 48)
    big = physics.fold_reaches(300, 300, (290, 290), (-60, -60), 20, 48)
    assert small == 0 and big > 0.3


def test_flutter_holds_the_grabbed_point_under_the_cursor():
    shape = physics.flutter(300, 300, (150, 290), (500, 400), 0.3, 0, 0, 0)
    band = next(b for b in shape.bands if any(abs(y - 290) < 30 for _, y in b.poly))
    assert band.dst


def test_crumple_shrinks_into_a_ball():
    c = physics.Crumple(300, 300, "seed")
    flat, ball = c.frame(0.0), c.frame(1.0)
    assert len(flat) == len(ball) == 2 * c.n * c.n

    def spread(facets):
        xs = [x for f in facets for x, _ in f.dst]
        return max(xs) - min(xs)
    assert spread(ball) < spread(flat) * 0.6
    assert any(f.back for f in ball)            # some of the back shows when it's crumpled
    assert c.frame(0.0)[0].dst == physics.Crumple(300, 300, "seed").frame(0.0)[0].dst


# ---------------------------------------------------------------- notes and stats

def test_complete_needs_every_task_checked():
    assert not store.is_complete(note_with("a", "b", done=(0,)))
    assert store.is_complete(note_with("a", "b", done=(0, 1)))
    text_only = note_with("just a line")
    text_only["rows"][0]["kind"] = "text"
    assert not store.is_complete(text_only)


def test_stats_count_days_and_streaks(tmp_path):
    s = store.Store(tmp_path / "notes.json")
    a = note_with("one", "two", done=(0, 1))
    b = note_with("three", done=())
    c = note_with("four", done=(0,))
    for n, day in ((a, "2026-10-20"), (b, "2026-10-21"), (c, "2026-10-22")):
        for r in n["rows"]:
            r["created"] = day
        n["status"] = "pinned"
        s.data["notes"].append(n)
        s.wrote(day)
    s.close(c, finished=True)
    st = s.stats(date(2026, 10, 22))
    assert st["days_written"] == 3
    assert st["days_completed"] == 2          # the 20th and the 22nd, not the 21st
    assert st["streak"] == 3 and st["best_streak"] == 3
    assert st["notes_finished"] == 1
    assert st["tasks_done"] == 3 and st["tasks_total"] == 4
    s.save()
    again = store.Store(tmp_path / "notes.json")
    assert again.stats(date(2026, 10, 22))["days_completed"] == 2


def test_thrown_away_tasks_do_not_complete_a_day(tmp_path):
    s = store.Store(tmp_path / "notes.json")
    n = note_with("x")
    n["rows"][0]["created"] = "2026-10-01"
    s.data["notes"].append(n)
    s.close(n, finished=False)
    assert s.stats(date(2026, 10, 2))["days_completed"] == 0


def test_peel_moves_the_draft_and_starts_a_new_sheet(tmp_path):
    s = store.Store(tmp_path / "notes.json")
    s.draft["rows"] = [store.new_row("task")]
    first = s.draft["id"]
    note = s.peel((10, 20, 300, 300))
    assert note["id"] == first and note["status"] == "pinned" and s.pinned() == [note]
    assert s.draft["id"] != first and s.draft["color"] == 1


# ---------------------------------------------------------------- skins and drawing

def test_neon_and_picture_skins(tmp_path):
    folder = tmp_path / "skins"
    dark = QImage(600, 600, QImage.Format.Format_ARGB32_Premultiplied)
    dark.fill(QColor("#120A1A"))
    src = tmp_path / "Spooky.png"
    dark.save(str(src))
    key, notes = skins.import_skin(src, folder)
    assert key.startswith("custom:") and notes == []
    skin = skins.skin_for(key, folder)
    assert skin.aspect == 1.0 and skin.ink(0) == skins.LIGHT_INK
    assert [s.key for s in skins.all_skins(folder)][:2] == ["neon", "solid:0"]
    small = tmp_path / "tiny.jpg"
    dark.scaled(120, 300).save(str(small))
    _, notes = skins.import_skin(small, folder)
    assert len(notes) == 3                      # not PNG, small, tall
    assert skins.skin_for("custom:missing.png", folder).key == "neon"


def test_template_is_600_square(tmp_path):
    path = tmp_path / "template.png"
    skins.save_template(path)
    img = QImage(str(path))
    assert (img.width(), img.height()) == (skins.TEMPLATE, skins.TEMPLATE)


def test_every_effect_draws(tmp_path):
    from peelpad.stage import CrumpleActor, PeelActor

    note = note_with("Buy milk", "Call mom", "اكتب", done=(1,))
    front, back = skins.note_images(note, skins.Skin(), 300, 300, 1.0)
    assert not front.isNull() and front.pixelColor(150, 290).alpha() == 255
    landed = []
    sheet = QRectF(100, 100, 300, 300)
    actor = PeelActor(sheet, QPointF(390, 390), front, back, 1.0, 48, landed.append, lambda: None)
    canvas = QImage(800, 800, QImage.Format.Format_ARGB32_Premultiplied)
    for target in [(330, 330), (200, 200), (60, 60), (300, 500), (500, 600)]:
        actor.move(QPointF(*target))
        actor.step(1 / 60)
        canvas.fill(0)
        p = QPainter(canvas)
        actor.paint(p, QPointF(0, 0))
        p.end()
    assert actor.state == "carry"
    actor.release()
    for _ in range(40):
        actor.step(1 / 60)
    assert landed and landed[0].width() == 300
    crumple = CrumpleActor(sheet, front, back, 1.0, "id")
    steps = 0
    while crumple.step(1 / 30):
        p = QPainter(canvas)
        crumple.paint(p, QPointF(0, 0))
        p.end()
        steps += 1
    assert 30 < steps < 60


def test_let_go_springs_back():
    from peelpad.stage import PeelActor

    front, back = skins.note_images(note_with("x"), skins.Skin(), 300, 300, 1.0)
    home = []
    actor = PeelActor(QRectF(0, 0, 300, 300), QPointF(290, 290), front, back, 1.0, 48,
                      lambda r: None, lambda: home.append(True))
    actor.move(QPointF(240, 240))
    actor.step(1 / 60)
    actor.release()
    for _ in range(300):
        if not actor.step(1 / 60):
            break
    assert home


def test_editor_writes_into_the_note():
    from peelpad.editor import TaskEditor

    note = note_with("first")
    ed = TaskEditor()
    ed.bind(note, skins.DARK_INK, 17)
    ed.add_after(ed.rows[0][2])
    ed.rows[1][2].setText("second")
    ed.rows[1][2].textEdited.emit("second")
    ed.rows[1][1].setChecked(True)
    assert [r["text"] for r in note["rows"]] == ["first", "second"]
    assert note["rows"][1]["done"] and note["rows"][1]["created"] == store.today()
    ed.remove(ed.rows[1][2])
    assert len(note["rows"]) == 1
