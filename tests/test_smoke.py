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


def test_pulling_outwards_still_peels_back_across_the_sheet():
    grab = (150, 290)
    assert physics.peel_target(300, 300, grab, (150, 200)) == (150, 200)        # inwards: the cursor
    assert physics.peel_target(300, 300, grab, (150, 380)) == (150, 200)        # outwards: mirrored back in
    near = physics.flap_share(300, 300, grab, physics.peel_target(300, 300, grab, (150, 330)), 20)
    far = physics.flap_share(300, 300, grab, physics.peel_target(300, 300, grab, (150, 520)), 20)
    assert 0 < near < far
    sideways = physics.peel_target(300, 300, grab, (250, 290))
    assert sideways == (250, 290)                                               # no jump at the border


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
    for target in [(330, 330), (200, 200), (60, 60), (-80, -80), (300, 500), (500, 600)]:
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


def test_themes_and_your_colours(tmp_path):
    keys = [s.key for s in skins.all_skins(tmp_path, {"paper": "#000000", "ink": "#00AAFF", "glow": True})]
    assert {"theme:midnight", "theme:white", "mine"} <= set(keys)
    midnight = skins.skin_for("theme:midnight", tmp_path)
    core, glow = skins.writing_colors(midnight, 0)
    assert glow == QColor("#3DB2FF") and core.lightness() > glow.lightness()
    assert core.hue() == glow.hue()                       # neon keeps the colour you picked
    white = skins.skin_for("theme:white", tmp_path)
    assert skins.writing_colors(white, 0) == (skins.DARK_INK, None)
    mine = skins.skin_for("mine", tmp_path, {"paper": "#102030", "ink": "#FF0000", "glow": False})
    assert mine.color(2) == QColor("#102030") and skins.writing_colors(mine, 0)[0] == QColor("#FF0000")


def test_glowing_ink_shines_around_the_letters(tmp_path):
    note = note_with("Neon")
    midnight = skins.skin_for("theme:midnight", tmp_path)
    front, _ = skins.note_images(note, midnight, 300, 300, 1.0)
    skins.WRITING.effect = "solid"
    try:
        plain, _ = skins.note_images(note, midnight, 300, 300, 1.0)
    finally:
        skins.WRITING.effect = "auto"

    def blue(img):
        return sum(img.pixelColor(x, y).blue() for x in range(30, 200, 2) for y in range(45, 80, 2))
    assert blue(front) > blue(plain) * 1.15


def test_writing_settings_change_the_text():
    try:
        skins.WRITING.scale = 1.5
        assert skins.font_px(300) == round(300 * 0.058 * 1.5)
        skins.WRITING.family = "Segoe UI"
        assert skins.hand_font(17).family() == "Segoe UI"
        skins.WRITING.ink = QColor("#123456")
        assert skins.writing_colors(skins.Skin(), 0)[0] == QColor("#123456")
    finally:
        skins.WRITING.scale, skins.WRITING.family, skins.WRITING.ink = 1.0, "", None


def test_history_lists_each_day(tmp_path):
    s = store.Store(tmp_path / "notes.json")
    n = note_with("a", "b", "c", done=(0,))
    for r in n["rows"]:
        r["created"] = "2026-10-20"
    n["rows"][0]["done_at"] = "2026-10-21"
    n["status"] = "pinned"
    s.data["notes"].append(n)
    log = s.history()
    assert log["2026-10-20"]["written"] == ["a", "b", "c"]
    assert log["2026-10-21"]["done"] == ["a"]
    s.close(n, finished=True)                    # finished by hand: the rest count as done today
    assert sorted(s.history()[store.today()]["done"]) == ["b", "c"]


def _frame_png(path, checker=False):
    """A cream card in a black frame, on real transparency or a painted checkerboard."""
    img = QImage(400, 400, QImage.Format.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    if checker:
        for y in range(0, 400, 20):
            for x in range(0, 400, 20):
                p.fillRect(x, y, 20, 20, QColor("#FFFFFF") if (x + y) // 20 % 2 else QColor("#D6D6D6"))
    p.fillRect(40, 60, 320, 300, QColor("#111111"))
    p.fillRect(70, 100, 260, 230, QColor("#FFF8E6"))
    p.end()
    img.save(str(path))
    return path


def test_text_box_finds_the_inside_of_a_frame(tmp_path):
    l, t, r, b = skins.detect_area(QImage(str(_frame_png(tmp_path / "frame.png"))))
    assert 70 / 400 < l < 0.25 and 100 / 400 < t < 0.3 and 0.75 < r < 330 / 400 and 0.75 < b < 330 / 400
    busy = QImage(200, 200, QImage.Format.Format_ARGB32)
    busy.fill(QColor(0, 0, 0, 0))
    assert skins.detect_area(busy) == skins.SAFE
    moved = skins.skin_for("custom:frame.png", tmp_path, areas={"custom:frame.png": [0.2, 0.5, 0.8, 0.9]})
    assert moved.area == (0.2, 0.5, 0.8, 0.9)
    assert skins.safe_rect(400, 400, moved.area) == QRectF(80, 200, 240, 160)


def test_painted_checkerboard_becomes_transparent(tmp_path):
    fake = _frame_png(tmp_path / "fake.png", checker=True)
    assert skins.clear_fake_background(fake)
    img = QImage(str(fake))
    assert img.pixelColor(5, 5).alpha() == 0 and img.pixelColor(25, 5).alpha() == 0
    assert img.pixelColor(200, 200).alpha() == 255          # the cream middle stays
    assert img.pixelColor(50, 70).alpha() == 255            # and the frame
    assert not skins.clear_fake_background(_frame_png(tmp_path / "real.png"))


def test_pinned_note_resize_mode():
    from peelpad.note import NoteWindow

    class App:
        skin = skins.Skin()
        stages = None

        def wind_speed(self):
            return 0.0

        def __getattr__(self, name):
            return lambda *a, **k: None

    n = note_with("one")
    n["rect"] = [100, 100, 300, 300]
    win = NoteWindow(App(), n)
    assert win.global_paper() == QRectF(100, 100, 300, 300)
    win.toggle_sizing()
    assert win.sizing and win.size_button.text() == "✓" and len(win._handles()) == 8
    win._resize_to("br", win.global_paper(), QPointF(60, -40), keep=False)
    assert (win.global_paper().width(), win.global_paper().height()) == (360, 260)
    win._resize_to("tl", win.global_paper(), QPointF(500, 0), keep=False)   # can't go below the minimum
    assert win.global_paper().width() == 90
    win.toggle_sizing()
    assert not win.sizing and n["rect"][2] == 90


def test_every_text_effect_paints_in_the_chosen_colour():
    from peelpad.effects import EFFECTS, draw_text

    ink = QColor("#FF4FD8")
    seen = {}
    for key, _ in EFFECTS:
        img = QImage(240, 40, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        draw_text(p, QRectF(4, 0, 232, 40), "Neon notes", skins.hand_font(22), ink, key)
        p.end()
        colours = {img.pixelColor(x, y).rgb() for x in range(0, 240, 2) for y in range(0, 40, 2)
                   if img.pixelColor(x, y).alpha() > 200}
        assert colours, key
        seen[key] = colours
    assert len(seen["prism"]) > len(seen["solid"]) and len(seen["gradient"]) > len(seen["solid"])


def test_animated_gif_skin_plays(tmp_path, monkeypatch):
    from PIL import Image

    from peelpad import animated

    frames = [Image.new("RGBA", (300, 300), c) for c in ((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255))]
    src = tmp_path / "blink.gif"
    frames[0].save(src, save_all=True, append_images=frames[1:], duration=100, loop=0)
    key, _ = skins.import_skin(src, tmp_path / "skins")
    assert key.endswith(".gif")
    skin = skins.skin_for(key, tmp_path / "skins")
    assert skin.animated and len(skin.frames) == 3 and skin.frame_ms == 100
    monkeypatch.setattr(animated, "now_ms", lambda: 50.0)
    first = skin.frame_id()
    monkeypatch.setattr(animated, "now_ms", lambda: 150.0)
    assert skin.frame_id() != first
    assert key in [s.key for s in skins.all_skins(tmp_path / "skins")]


def test_skull_parade_moves():
    from peelpad.animated import SkullParade

    sk = SkullParade()
    assert sk.animated and skins.skin_for("anim:skulls", Path(".")).key == "anim:skulls"

    def frame(t):
        img = QImage(200, 200, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        sk.paint_front(p, 200, 200, 0, t=t)
        p.end()
        return img
    assert frame(0.5) != frame(2.0)
    calm = skins.safe_rect(200, 200, sk.area)
    a, b = frame(0.5), frame(2.0)
    assert all(a.pixelColor(x, y) == b.pixelColor(x, y)        # nothing moves where the text goes
               for x in range(int(calm.left()), int(calm.right()), 7)
               for y in range(int(calm.top()), int(calm.bottom()), 7))


def test_wind_bends_the_free_part_and_keeps_the_glue():
    calm = physics.wind(300, 300, 48, 1.0, 0.0)
    assert len(calm.bands) == 1
    shape = physics.wind(300, 300, 48, 1.0, physics.MAX_WIND, seed=0.4, grow=0.08)
    glued = shape.bands[0]
    assert glued.dst == glued.src and max(y for _, y in glued.poly) <= 48 + 1e-6
    lifted = [b.z for b in shape.bands[1:]]
    assert lifted[-1] > lifted[0] >= 0                       # further from the glue, higher
    xs = [x for b in shape.bands for x, _ in b.dst]
    assert max(xs) - min(xs) < 300 * 1.12                    # never grows past what was allowed
    strong = physics.wind(300, 300, 48, 1.0, physics.MAX_WIND, seed=0.4).bands[-1].z
    gentle = physics.wind(300, 300, 48, 1.0, physics.MAX_WIND / 4, seed=0.4).bands[-1].z
    assert strong > gentle


def test_double_click_carry_waits_for_a_click():
    from peelpad.stage import PeelActor

    front, back = skins.note_images(note_with("x"), skins.Skin(), 200, 200, 1.0)
    landed = []
    a = PeelActor(QRectF(0, 0, 200, 200), QPointF(100, 100), front, back, 1.0, 0, landed.append, lambda: None,
                  carry=True, follow=True, sticky=True)
    for _ in range(30):
        a.step(1 / 60)                       # no button is held, and still it keeps following
    assert a.state == "carry" and not landed
    a.release()                              # the click on the stage
    for _ in range(40):
        a.step(1 / 60)
    assert landed


def test_apple_worm_crawls_and_keeps_the_middle_calm():
    from peelpad.animated import AppleWorm

    sk = AppleWorm()
    assert skins.skin_for("anim:worm", Path(".")).key == "anim:worm"

    def frame(t):
        img = QImage(240, 240, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        sk.paint_front(p, 240, 240, 0, t=t)
        p.end()
        return img
    a, b = frame(1.0), frame(5.0)
    assert a != b
    calm = skins.safe_rect(240, 240, sk.area)
    assert all(a.pixelColor(x, y) == b.pixelColor(x, y)
               for x in range(int(calm.left()), int(calm.right()), 7)
               for y in range(int(calm.top()), int(calm.bottom()), 7))


def test_history_deletes_ticked_a_day_or_everything(tmp_path):
    s = store.Store(tmp_path / "notes.json")
    old = note_with("old one", "old two", done=(0, 1))
    for r in old["rows"]:
        r["created"], r["done_at"] = "2026-10-01", "2026-10-01"
    old["status"] = "finished"
    pinned = note_with("still pinned")
    pinned["rows"][0]["created"] = "2026-10-01"
    pinned["status"] = "pinned"
    s.data["notes"] += [old, pinned]
    s.wrote("2026-10-01")
    entries = store.day_entries(s.data, "2026-10-01")
    assert sum(e["live"] for e in entries) == 1 and len(entries) == 5
    first = next(e for e in entries if e["text"] == "old one" and e["what"] == "done")
    assert store.forget(s.data, [first]) == 0
    assert [r["text"] for r in old["rows"]] == ["old two"]
    assert store.forget_day(s.data, "2026-10-01") == 1            # the pinned task stays
    assert old not in s.data["notes"] and pinned in s.data["notes"]
    assert "2026-10-01" in s.data["days"]                          # it still has a live task
    store.forget_all(s.data)
    assert s.data["notes"] == [pinned]


def test_animated_skin_keeps_moving_in_your_hand(monkeypatch):
    from peelpad import animated
    from peelpad.scenes import NightSky

    sky = NightSky()
    monkeypatch.setattr(animated, "now_ms", lambda: 1000.0)
    import peelpad.scenes as scenes
    monkeypatch.setattr(scenes, "now_ms", lambda: 1000.0)
    live = skins.LiveTexture(note_with("x"), sky, 200, 200, 1.0)
    first = live.front()
    monkeypatch.setattr(animated, "now_ms", lambda: 3400.0)
    monkeypatch.setattr(scenes, "now_ms", lambda: 3400.0)
    assert live.front() != first
    still = skins.LiveTexture(note_with("x"), skins.Skin(), 200, 200, 1.0)
    assert still.front() is still.front()


def test_the_five_scenes_keep_the_writing_calm():
    from peelpad.scenes import SCENES, LED

    for cls in SCENES:
        sk = cls()
        assert sk.animated and skins.skin_for(sk.key, Path(".")).key == sk.key

        def frame(t):
            img = QImage(240, 240, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(0)
            p = QPainter(img)
            sk.paint_front(p, 240, 240, 0, t=t)
            p.end()
            return img
        a, b = frame(1.0), frame(3.7)
        calm = skins.safe_rect(240, 240, sk.area)
        assert all(a.pixelColor(x, y) == b.pixelColor(x, y)
                   for x in range(int(calm.left()), int(calm.right()), 9)
                   for y in range(int(calm.top()), int(calm.bottom()), 9)), cls.__name__
    before = LED.color
    try:
        LED.color = QColor("#3DFF6E")
        assert skins.skin_for("anim:clock", Path(".")).frame_id() % 1000 == QColor("#3DFF6E").rgb() % 1000
    finally:
        LED.color = before


def test_weather_codes_and_previews():
    from peelpad import weather

    assert [weather.state_for(c) for c in (0, 2, 3, 45, 61, 81, 73, 95)] == \
        ["clear", "partly", "cloudy", "fog", "rain", "rain", "snow", "storm"]
    before = weather.Now.preview
    try:
        weather.Now.preview = "night"
        assert weather.shown() == ("clear", False)
        weather.Now.preview = "rain"
        assert weather.shown() == ("rain", True)
        weather.Now.preview, weather.Now.updated, weather.Now.state, weather.Now.day = "live", 1.0, "snow", True
        assert weather.shown() == ("snow", True)
    finally:
        weather.Now.preview, weather.Now.updated = before, 0.0


def test_weather_look_changes_with_the_sky():
    from peelpad import weather
    from peelpad.scenes import WeatherSky

    sky = WeatherSky()

    def frame(state):
        weather.Now.preview = state
        img = QImage(200, 200, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        sky.paint_front(p, 200, 200, 0, t=2.0)
        p.end()
        return img
    try:
        sunny, rainy = frame("clear"), frame("rain")
        assert sunny.pixelColor(20, 150) != rainy.pixelColor(20, 150)
    finally:
        weather.Now.preview = "live"


def test_arcade_chomper_eats_the_dots_and_they_come_back():
    from peelpad.scenes import Arcade

    arc = Arcade()

    def lit_dots(t):
        img = QImage(240, 240, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        arc.paint_front(p, 240, 240, 0, t=t)
        p.end()
        lane = arc._lane(240, 240)
        return sum(img.pixelColor(lane.pointAtPercent((i + 0.5) / arc.PELLETS).toPoint()).red() > 200
                   for i in range(arc.PELLETS))
    early, late, next_lap = lit_dots(0.5), lit_dots(arc.LOOP * 0.8), lit_dots(arc.LOOP * 1.05)
    assert early > late and next_lap > late


def test_the_row_you_type_in_follows_a_new_ink():
    from peelpad.editor import TaskEditor

    note = note_with("Hello")
    ed = TaskEditor()
    ed.resize(300, 200)
    ed.bind(note, QColor("#B26BFF"), 20)
    ed.set_look(QColor("#000000"), 20)
    img = ed.rows[0][2].grab().toImage()
    pixels = [img.pixelColor(x, y) for x in range(img.width()) for y in range(img.height())]
    assert not any(c.blue() > 150 and c.red() > 120 and c.green() < 160 and c.alpha() > 200 for c in pixels)
    assert any(c.red() + c.green() + c.blue() < 120 and c.alpha() > 200 for c in pixels)


def test_arabic_is_written_with_the_pen_font():
    font = skins.hand_font(20, text="اشترِ الحليب")
    assert skins.pen_arabic() in font.families() and font.pixelSize() > 20
    assert skins.hand_font(20, text="Buy milk").pixelSize() == 20
    try:
        skins.WRITING.arabic = "same"
        assert skins.pen_arabic() not in skins.hand_font(20, text="اشترِ").families()
    finally:
        skins.WRITING.arabic = "pen"


def test_every_language_has_every_line():
    import string

    from peelpad import i18n

    names = {f[1] for k in i18n.T for f in string.Formatter().parse(k) if f[1]}
    assert names <= {"p", "n", "day", "c", "city", "weather", "night", "time", "w", "h", "best",
                     "size", "safe_w", "safe_h", "side", "glue"}
    for key, row in i18n.T.items():
        assert len(row) == 4 and all(row)
        want = {f[1] for f in string.Formatter().parse(key) if f[1]}
        assert all({f[1] for f in string.Formatter().parse(t) if f[1]} == want for t in row), key
    try:
        for code, word in (("ar", "الإحصائيات"), ("es", "Estadísticas"), ("ja", "統計"), ("zh", "统计"), ("en", "Stats")):
            i18n.set_language(code)
            assert i18n.tr("Stats") == word
        assert i18n.tr("a line nobody translated") == "a line nobody translated"
        i18n.set_language("ar")
        assert i18n.right_to_left() and len(i18n.weekday_names()) == 7
    finally:
        i18n.set_language("en")


def test_a_finished_note_stays_when_auto_crumple_is_off():
    from peelpad.note import NoteWindow

    crumpled = []

    class App:
        skin = skins.Skin()
        stages = None
        auto = True

        def wind_speed(self):
            return 0.0

        def auto_crumple(self):
            return self.auto

        def crumple(self, win, finished):
            crumpled.append(finished)

        def __getattr__(self, name):
            return lambda *a, **k: None

    app = App()
    n = note_with("only task")
    n["rect"] = [0, 0, 200, 200]
    win = NoteWindow(app, n)
    win.editor.rows[0][1].setChecked(True)            # every task checked...
    assert win.finish_timer.isActive()                # ...so it is about to crumple
    win.editor.rows[0][1].setChecked(False)
    app.auto = False
    win.editor.rows[0][1].setChecked(True)
    assert not win.finish_timer.isActive()            # turned off: it stays
    win._maybe_finish()
    assert crumpled == []
    win.done()                                        # ✓ still finishes it by hand
    assert crumpled == [True]


def test_a_click_never_adds_an_empty_row_and_empty_rows_go_away():
    from peelpad.editor import TaskEditor

    note = note_with("hello")
    ed = TaskEditor()
    ed.resize(300, 200)
    ed.bind(note, skins.DARK_INK, 17)
    ed.focus_end()                                   # what a click on the paper does
    assert [r["text"] for r in note["rows"]] == ["hello"]
    ed.add_after(ed.rows[0][2])                      # Enter: a new row
    assert len(note["rows"]) == 2
    ed.drop_if_empty(ed.rows[1][2])                  # left empty when you click away: gone
    assert [r["text"] for r in note["rows"]] == ["hello"] and len(ed.rows) == 1
    ed.drop_if_empty(ed.rows[0][2])                  # but the only row always stays
    assert len(ed.rows) == 1
