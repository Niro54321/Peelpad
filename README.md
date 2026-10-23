# Peelpad

Sticky notes for Windows that feel like paper. Write your tasks on a pad of neon
sticky notes, peel the top sheet off with your mouse and drop it anywhere on
your screen. It stays pinned on top of your other windows. When you've checked
off every task, the note crumples into a ball and disappears.

![Peelpad](docs/peelpad.png)

## What it does

- **A pad you peel from.** Write on the top sheet, then grab the paper and pull.
  Drag in over the sheet and it curls back over a little roll, showing its paler
  back. Pull it away and the glue holds for a moment while the sheet bends up
  toward you, then it tears off. Carried around, it swings and ripples with the
  air. Let go before it tears and it springs back onto the pad.
- **Pinned anywhere, any size.** A torn-off note lands where you drop it and
  stays on top of every app. You can have as many as you like. Drag one by its
  paper to move it. Resize it freely from the bottom-right corner (hold Shift to
  keep its shape), or hold Ctrl and turn the mouse wheel over it. Ctrl + wheel
  over the pad changes the size of its sheets.
- **Tasks and text.** Every row has a check box. Right-click the box to make the
  row a plain line instead. Arabic and other right-to-left text works.
- **Crumple when done.** Check off the last task and the note scrunches into a
  ball (a 3D paper mesh with real shading), then pops away. ✓ finishes a note by
  hand, ✕ throws it away.
- **Stats.** Settings → Stats shows the days you wrote notes, the days you checked
  off everything you wrote, your current and best streak, notes finished, tasks
  checked, and a heat map of the last 18 weeks.
- **History.** Settings → History is a calendar: each day shows how many tasks
  you checked off. Click a day to see what you checked off and what you wrote.
- **Looks.** The default is four neon sticky-note colours (lemon, mango,
  bubblegum, lime), a new one for each sheet. Or pick one colour, or a theme:
  Midnight (black paper, glowing blue ink), Neon night (glowing pink), Toxic
  (glowing green), Paper white, Kraft. Or choose your own paper and ink colours,
  or design your own skin (see below).
- **Writing.** Pick any font (the default is handwriting), the text size, the ink
  colour, and a neon glow that makes the ink shine like a sign.

## Your own skin

Settings → Look → **Upload your own skin…** Every note and the pad switch to it at once.

| | |
|---|---|
| Size | **600 × 600 px.** Other sizes work too: notes keep your picture's shape. 300 px and up stays sharp. |
| Format | **PNG.** Transparent pixels are see-through on your desktop, and clicks go through them, so a skin can be any shape: a ghost, a cat, a torn page. JPG and WebP work too, without transparency. |
| Glue band | The top **96 px**. The pin sits there, and that's where you grab a pinned note. Decorate it freely. |
| Safe text area | **480 × 444 px**: 60 px in from the left, right and bottom, 96 px down from the top. Tasks are written here, so keep it calm enough to read on. |
| Ink | Picked for you: dark ink on light pictures, light ink on dark ones. You can also choose any colour, with or without the neon glow, in Settings → Writing. |

**Save the template PNG…** gives you a 600 × 600 guide with the glue band and safe
area marked. Paint over it in any editor, then upload it.

## Keys

| | |
|---|---|
| Enter | new task below |
| Backspace on an empty row | remove it |
| ↑ ↓ | move between rows |
| Ctrl+Enter | peel the sheet off for you and drop it beside the pad |
| Right-click a check box | plain line ↔ task |
| Right-click the pad | settings, keep the pad on top, hide, quit |

Closing the pad keeps Peelpad running in the tray, along with your pinned notes.
Click the tray icon to bring the pad back.

## Install

Download `Peelpad-Setup-<version>.exe` from
[Releases](https://github.com/Niro54321/Peelpad/releases) and run it. It installs
for your user only (no admin prompt). The installer isn't code-signed yet, so
Windows SmartScreen may warn you: choose **More info → Run anyway**.

## Run from source

Needs Python 3.10+ on Windows 10 or 11.

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m peelpad
```

Tests:

```bash
.venv\Scripts\python -m pytest tests -q
```

Build the installer (needs `pip install pyinstaller` and Inno Setup 6):

```bash
.venv\Scripts\python packaging\build.py
```

## How the paper works

There's no game engine. The sheet is cut into thin bands, and each band is drawn
with an exact projective map of the note's texture (Qt's `QTransform.quadToQuad`),
shaded by how it faces a light at the top left.

- **Curl:** the classic page-curl model. The part past the fold line wraps
  around a cylinder and then lies flat, face down, on top. The fold line is
  solved so the point you grabbed stays under the cursor.
- **Lift:** the sheet bends up from a hinge with even curvature and is seen in
  perspective. It bends more the harder you pull, until the glue lets go.
- **Carry:** the sheet turns on the point you hold, trailing behind your motion
  on a damped spring, and a travelling wave makes it flutter.
- **Crumple:** an 11 × 11 grid of paper (242 triangles) moves toward a noisy sphere. The edges
  go first and wrinkles rise and fall on the way. Each facet is lit by its normal
  and shows the front or the back of the paper.

All of this runs in a small see-through, click-through window that is only as
big as the moving paper and closes the moment it stops, so nothing ever sits
over the rest of your screen.

Your notes are kept in `%APPDATA%\Peelpad\notes.json`, and uploaded skins in
`%APPDATA%\Peelpad\skins`.

## Licence

MIT. See [LICENSE](LICENSE).
