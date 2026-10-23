"""Paper physics as plain geometry (no Qt here, so it can be tested).

A sheet is w x h in its own coordinates (u right, v down). Each effect cuts the
sheet into thin bands and says where every band's corners land; the stage then
draws each band's piece of the texture there with an exact projective map, a
little darker or lighter by how the band faces the light.

- fold:    the page curl. Dragging a point of the sheet rolls that part over a
           small cylinder and lays it face down on top. (Pulling outwards peels
           the same way: the curl travels back across the sheet.)
- flutter: a carried sheet ripples and swings with the air.
- crumple: a grid of triangles squeezed into a crinkled ball.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

P = tuple[float, float]
LIGHT = (-0.35, -0.55, 0.76)          # light from the top left, a little in front
_LN = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _LN for c in LIGHT)


@dataclass
class Band:
    poly: list[P]       # this piece of the sheet, in sheet coordinates
    src: list[P]        # a quad around it (sheet coordinates)...
    dst: list[P]        # ...and where that quad's corners land
    shade: float        # -1 black .. 0 as is .. +1 white
    back: bool          # the back of the paper faces you
    z: float            # height over the pad, for draw order and shadows


@dataclass
class Shape:
    bands: list[Band]
    fold_line: tuple[P, P, float] | None = None   # point, normal into the flap, curl radius
    stretch: float = 0.0                           # how far a lift is pulled past its limit


def _add(a: P, b: P, k: float = 1.0) -> P:
    return a[0] + b[0] * k, a[1] + b[1] * k


def _dot(a: P, b: P) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _rect(w: float, h: float) -> list[P]:
    return [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]


def clip(poly: list[P], n: P, c: float, keep_above: bool) -> list[P]:
    """The part of a convex polygon where dot(p, n) >= c (or <= c)."""
    if not poly:
        return []
    sign = 1.0 if keep_above else -1.0
    out: list[P] = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        da, db = sign * (_dot(a, n) - c), sign * (_dot(b, n) - c)
        if da >= 0:
            out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def slab(poly: list[P], n: P, lo: float, hi: float) -> list[P]:
    return clip(clip(poly, n, lo, True), n, hi, False)


def identity(w: float, h: float) -> Shape:
    r = _rect(w, h)
    return Shape([Band(r, r, r, 0.0, False, 0.0)])


# ---------------------------------------------------------------- fold

def curl_x(s: float, r: float) -> float:
    """Where a point s along the flap lands (measured from the fold line)."""
    if s <= 0:
        return s
    if s <= math.pi * r:
        return r * math.sin(s / r)
    return -(s - math.pi * r)


def fold_depth(pull: float, r: float) -> float:
    """How far the grabbed point is from the fold line for a given pull:
    the s with s - curl_x(s) = pull."""
    if pull <= 0:
        return 0.0
    if pull > math.pi * r:                      # past the cylinder: a flat flap on top
        return (pull + math.pi * r) / 2
    lo, hi = 0.0, math.pi * r
    for _ in range(40):
        mid = (lo + hi) / 2
        if mid - curl_x(mid, r) < pull:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _side_shade(a: float) -> tuple[float, bool]:
    """Shade of a curl band whose surface is turned by angle a."""
    back = a > math.pi / 2
    b = abs(math.cos(a))
    shade = -(1 - b) * 0.55
    if back:
        shade += 0.28 * math.exp(-((a - 0.72 * math.pi) / (0.12 * math.pi)) ** 2)
    return shade, back


def fold(w: float, h: float, grab: P, cursor: P, r: float, bands: int = 14) -> Shape:
    """Page curl: the point `grab` of the sheet is dragged to `cursor`."""
    dx, dy = cursor[0] - grab[0], cursor[1] - grab[1]
    pull = math.hypot(dx, dy)
    if pull < 0.5:
        return identity(w, h)
    n = (-dx / pull, -dy / pull)                 # from the fold towards the flap
    t = (-n[1], n[0])
    d0 = fold_depth(pull, r)
    foot = _add(grab, n, -d0)                    # a point on the fold line
    k0 = _dot(foot, n)
    big = (w + h) * 2
    sheet = _rect(w, h)
    out = [Band(clip(sheet, n, k0, False), sheet, sheet, 0.0, False, 0.0)]

    def quad(s0, s1, x0, x1):
        a0, a1 = _add(foot, n, s0), _add(foot, n, s1)
        b0, b1 = _add(foot, n, x0), _add(foot, n, x1)
        src = [_add(a0, t, -big), _add(a0, t, big), _add(a1, t, big), _add(a1, t, -big)]
        dst = [_add(b0, t, -big), _add(b0, t, big), _add(b1, t, big), _add(b1, t, -big)]
        return src, dst

    seam = 0.6                                    # bands overlap a hair so no gaps show
    for i in range(bands):
        s0, s1 = math.pi * r * i / bands, math.pi * r * (i + 1) / bands
        poly = slab(sheet, n, k0 + s0 - (seam if i else 0), k0 + s1 + seam)
        if len(poly) < 3:
            continue
        src, dst = quad(s0, s1, curl_x(s0, r), curl_x(s1, r))
        a = (s0 + s1) / 2 / r
        shade, back = _side_shade(a)
        out.append(Band(poly, src, dst, shade, back, r * (1 - math.cos(a))))
    flat = clip(sheet, n, k0 + math.pi * r, True)
    if len(flat) >= 3:
        s0, s1 = math.pi * r, math.pi * r + big
        src, dst = quad(s0, s1, curl_x(s0, r), curl_x(s1, r))
        out.append(Band(flat, src, dst, 0.06, True, 2 * r))
    out.sort(key=lambda b: b.z)
    return Shape(out, (foot, n, r))


def fold_reaches(w: float, h: float, grab: P, cursor: P, r: float, glue: float) -> float:
    """How much of the glue band (the top `glue` px) the flap has pulled up, 0..1."""
    dx, dy = cursor[0] - grab[0], cursor[1] - grab[1]
    pull = math.hypot(dx, dy)
    if pull < 0.5 or glue <= 0:
        return 0.0
    n = (-dx / pull, -dy / pull)
    k0 = _dot(_add(grab, n, -fold_depth(pull, r)), n)
    band = _rect(w, glue)
    inside = clip(band, n, k0, True)
    return _area(inside) / (w * glue)


def flap_share(w: float, h: float, grab: P, cursor: P, r: float) -> float:
    """How much of the sheet has peeled up, 0..1."""
    dx, dy = cursor[0] - grab[0], cursor[1] - grab[1]
    pull = math.hypot(dx, dy)
    if pull < 0.5:
        return 0.0
    n = (-dx / pull, -dy / pull)
    k0 = _dot(_add(grab, n, -fold_depth(pull, r)), n)
    return _area(clip(_rect(w, h), n, k0, True)) / (w * h)


def peel_target(w: float, h: float, grab: P, cursor: P) -> P:
    """Where the fold pulls the grabbed point. Pulling in over the sheet: the cursor.
    Pulling outwards: the outward part is mirrored back in, so the sheet still
    peels back across itself, further the further you pull."""
    vx, vy = cursor[0] - grab[0], cursor[1] - grab[1]
    ix, iy = w / 2 - grab[0], h / 2 - grab[1]
    il = math.hypot(ix, iy)
    if il < 1e-6:
        return cursor
    ix, iy = ix / il, iy / il
    along = vx * ix + vy * iy
    if along >= 0:
        return cursor
    return grab[0] + vx - 2 * along * ix, grab[1] + vy - 2 * along * iy


def _area(poly: list[P]) -> float:
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        s += a[0] * b[1] - b[0] * a[1]
    return abs(s) / 2


# ---------------------------------------------------------------- carried

def flutter(w: float, h: float, grab: P, at: P, angle: float, wave: float, phase: float,
            lift: float, bands: int = 14) -> Shape:
    """A loose sheet held at `grab`, which sits under `at` (stage coordinates),
    turned by `angle` and rippling with amplitude `wave`. Bands land in stage coordinates."""
    cx, cy = w / 2 - grab[0], h / 2 - grab[1]
    length = math.hypot(cx, cy)
    body = (cx / length, cy / length) if length > 1 else (0.0, 1.0)
    side = (-body[1], body[0])
    sheet = _rect(w, h)
    proj = [_dot(_add(c, grab, -1), body) for c in sheet]
    lo, hi = min(proj), max(proj)
    span = max(hi - lo, 1.0)
    height = max(w, h) * 2.6
    ca, sa = math.cos(angle), math.sin(angle)
    k0 = _dot(grab, body)
    big = (w + h) * 2

    def z(s: float) -> float:
        reach = max(0.0, s) / max(hi, 1.0) if hi > 0 else 0.0
        return lift + wave * math.sin(math.pi * 1.25 * (s - lo) / span - phase) * (0.35 + 0.65 * reach)

    def land(s: float, lateral: float) -> P:
        x = body[0] * s + side[0] * lateral
        y = body[1] * s + side[1] * lateral
        k = height / max(height - z(s), height * 0.05)
        return at[0] + (x * ca - y * sa) * k, at[1] + (x * sa + y * ca) * k

    out = []
    seam = 0.6
    light = (body[0] * ca - body[1] * sa) * LIGHT[0] + (body[0] * sa + body[1] * ca) * LIGHT[1]
    for i in range(bands):
        s0, s1 = lo + span * i / bands, lo + span * (i + 1) / bands
        poly = slab(sheet, body, k0 + s0 - (seam if i else 0), k0 + s1 + seam)
        if len(poly) < 3:
            continue
        a0, a1 = _add(grab, body, s0), _add(grab, body, s1)
        src = [_add(a0, side, -big), _add(a0, side, big), _add(a1, side, big), _add(a1, side, -big)]
        dst = [land(s0, -big), land(s0, big), land(s1, big), land(s1, -big)]
        slope = (z(s1) - z(s0)) / (s1 - s0)
        shade = max(-0.45, min(0.3, -slope * light * 1.4))
        out.append(Band(poly, src, dst, shade, False, z((s0 + s1) / 2)))
    return Shape(out)


MAX_WIND = 7.2          # m/s, the strongest wind Settings offers


def _arc(phi: float, length: float, s: float) -> tuple[float, float]:
    """A sheet bent with even curvature, turning by `phi` over `length`: (along, up) at arc s."""
    if phi < 1e-6:
        return s, 0.0
    radius = length / phi
    return radius * math.sin(s / radius), radius * (1 - math.cos(s / radius))


def gust(t: float, seed: float) -> float:
    """How hard the wind blows right now, 0.15..1 of its speed: slow swells and quick gusts."""
    swell = 0.5 + 0.5 * math.sin(t * 0.55 + seed) * math.sin(t * 0.23 + seed * 2.1)
    flick = 0.5 + 0.5 * math.sin(t * 2.7 + seed * 3.3)
    return 0.15 + 0.85 * (0.75 * swell + 0.25 * flick)


def wind(w: float, h: float, glue: float, t: float, speed: float, seed: float = 0.0,
         grow: float = 0.08, rows: int = 14) -> Shape:
    """A sheet glued along its top, blowing in the wind (from the left). The free part
    bends up towards you, the further from the glue the more, ripples, and its
    corners flap a little out of step. `grow` caps how much bigger it may look."""
    strength = max(0.0, min(1.0, speed / MAX_WIND))
    if strength <= 0 or h - glue < 4:
        return identity(w, h)
    g = gust(t, seed) * strength
    free = h - glue
    height = max(w, h) * 2.4
    zmax = height * (1 - 1 / (1 + grow))                 # perspective may enlarge it by `grow` at most
    bend = 0.85 * g                                      # radians at the bottom edge
    cam = (w / 2, h / 2)

    def corner(u: float, v: float) -> tuple[P, float]:
        s = max(0.0, (v - glue) / free)
        along, up = _arc(bend, free, s * free)
        ripple = 0.035 * h * strength * s * math.sin(2 * math.pi * (s * 1.1 - t * 1.4) + u / w * 1.8 + seed)
        twist = 0.06 * h * g * s * (u / w - 0.5) * math.sin(t * 2.2 + seed * 1.7)
        z = min(zmax, max(0.0, up + ripple + twist))
        sway = w * 0.03 * g * s * s + w * 0.008 * strength * s * math.sin(t * 3.1 + seed)
        x, y = u + sway, glue + along
        k = height / (height - z)
        return (cam[0] + (x - cam[0]) * k, cam[1] + (y - cam[1]) * k), z

    sheet = _rect(w, h)
    out = [Band(clip(sheet, (0.0, 1.0), glue, False), sheet, sheet, 0.0, False, 0.0)]
    seam = 0.6
    for i in range(rows):
        v0, v1 = glue + free * i / rows, glue + free * (i + 1) / rows
        poly = slab(sheet, (0.0, 1.0), v0 - (seam if i else 0), v1 + seam)
        if len(poly) < 3:
            continue
        (a, za), (b, zb) = corner(0, v0), corner(w, v0)
        (c, zc), (d, zd) = corner(w, v1), corner(0, v1)
        slope = ((zc + zd) - (za + zb)) / 2 / (v1 - v0)
        shade = max(-0.3, min(0.28, slope * 0.55))      # tilted up to the light: brighter
        src = [(0.0, v0), (w, v0), (w, v1), (0.0, v1)]
        out.append(Band(poly, src, [a, b, c, d], shade, False, (za + zb + zc + zd) / 4))
    return Shape(out)


def move_shape(shape: Shape, fn) -> Shape:
    """Move every band's landing corners with fn (an affine map, like a turn and a shift)."""
    for b in shape.bands:
        b.dst = [fn(p) for p in b.dst]
    return shape


def turn_about(origin: P, to: P, angle: float):
    ca, sa = math.cos(angle), math.sin(angle)

    def fn(p: P) -> P:
        x, y = p[0] - origin[0], p[1] - origin[1]
        return to[0] + x * ca - y * sa, to[1] + x * sa + y * ca
    return fn


def spring(x: float, v: float, target: float, k: float, c: float, dt: float) -> tuple[float, float]:
    """One step of a damped spring."""
    v += (-k * (x - target) - c * v) * dt
    return x + v * dt, v


# ---------------------------------------------------------------- crumple

@dataclass
class Facet:
    src: list[P]        # triangle in sheet coordinates
    dst: list[P]        # where it lands (around the sheet's centre)
    shade: float
    back: bool
    z: float


def _smooth(values: list[float], n: int, passes: int = 2) -> list[float]:
    side = n + 1
    for _ in range(passes):
        nxt = values[:]
        for j in range(side):
            for i in range(side):
                acc, cnt = 0.0, 0
                for dj in (-1, 0, 1):
                    for di in (-1, 0, 1):
                        ii, jj = i + di, j + dj
                        if 0 <= ii < side and 0 <= jj < side:
                            acc += values[jj * side + ii]
                            cnt += 1
                nxt[j * side + i] = values[j * side + i] * 0.4 + acc / cnt * 0.6
        values = nxt
    return values


class Crumple:
    """Squeezing a sheet into a ball. frame(t) for t in 0..1."""

    def __init__(self, w: float, h: float, seed: int | str = 0, n: int = 11):
        rnd = random.Random(str(seed))
        self.w, self.h, self.n = w, h, n
        side = n + 1
        size = max(w, h)
        self.radius = size * 0.2
        self.height = size * 2.8

        def noise():
            return _smooth([rnd.uniform(-1, 1) for _ in range(side * side)], n, 1)
        n1, n2, n3, n4 = noise(), noise(), noise(), noise()
        self.flat, self.ball, self.wrinkle, self.delay = [], [], [], []
        for j in range(side):
            for i in range(side):
                k = j * side + i
                u, v = i / n, j / n
                self.flat.append(((u - 0.5) * w, (v - 0.5) * h, 0.0))
                theta = 2 * math.pi * (u * 0.92 + 0.08 * n1[k]) + 0.9 * v
                polar = math.pi * (0.06 + 0.88 * v + 0.12 * n2[k])
                rho = self.radius * (0.82 + 0.3 * n3[k] + 0.12 * rnd.random())
                self.ball.append((rho * math.sin(polar) * math.cos(theta),
                                  rho * math.sin(polar) * math.sin(theta),
                                  self.radius + rho * math.cos(polar)))
                self.wrinkle.append(n4[k] * size * 0.16)
                edge = max(abs(u - 0.5), abs(v - 0.5)) * 2      # 0 middle .. 1 edge
                self.delay.append(0.32 * (1 - edge) + 0.05 * rnd.random())

    @staticmethod
    def _ease(x: float) -> float:
        x = max(0.0, min(1.0, x))
        return x * x * (3 - 2 * x)

    def points(self, t: float) -> list[tuple[float, float, float]]:
        spin = 0.7 * self._ease(t)
        tilt = 0.5 * self._ease(t)
        cs, ss, ct, st = math.cos(spin), math.sin(spin), math.cos(tilt), math.sin(tilt)
        out = []
        for k, (a, b, w) in enumerate(zip(self.flat, self.ball, self.wrinkle)):
            e = self._ease((t - self.delay[k]) / 0.62)
            x = a[0] + (b[0] - a[0]) * e
            y = a[1] + (b[1] - a[1]) * e
            zz = a[2] + (b[2] - a[2]) * e + w * math.sin(math.pi * e)
            x, y = x * cs - y * ss, x * ss + y * cs                    # spin in the screen plane
            y, zz = y * ct - (zz - self.radius) * st, y * st + (zz - self.radius) * ct + self.radius
            out.append((x, y, zz))
        return out

    def frame(self, t: float) -> list[Facet]:
        pts = self.points(t)
        side = self.n + 1
        proj = []
        for x, y, z in pts:
            k = self.height / max(self.height - z, self.height * 0.05)
            proj.append((x * k, y * k))
        facets = []
        for j in range(self.n):
            for i in range(self.n):
                a, b, c, d = j * side + i, j * side + i + 1, (j + 1) * side + i, (j + 1) * side + i + 1
                for tri in ((a, b, c), (b, d, c)):
                    facets.append(self._facet(tri, pts, proj, side))
        facets.sort(key=lambda f: f.z)
        return facets

    def _facet(self, tri, pts, proj, side) -> Facet:
        p0, p1, p2 = (pts[k] for k in tri)
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / length, ny / length, nz / length
        back = nz < 0
        if back:
            nx, ny, nz = -nx, -ny, -nz
        lit = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]
        shade = max(-0.5, min(0.32, (lit - LIGHT[2]) * 0.85 + 0.04))
        src = [((k % side) / self.n * self.w, (k // side) / self.n * self.h) for k in tri]
        return Facet(src, [proj[k] for k in tri], shade, back, (p0[2] + p1[2] + p2[2]) / 3)
