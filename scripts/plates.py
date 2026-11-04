"""Print plates: the PETG parts grouped onto shared Kobra S1 beds, so the PETG prints run as a few
jobs instead of one file per part.

Only PETG is plated. An LW-PLA vase skin is one continuous spiral wall: the slicer puts several
vase objects on one plate only by printing them one after another, and then every object but the
last has to pass under the print head's gantry (40 mm on the S1, 30 mm on the X). The skins are
130-240 mm tall; on the X, which prints them all, only the 20 mm V-tail tip fairing would fit
under, and pairing it with a skin would save a single 12 min job.

Layout: each part keeps its print orientation (make_print_ready.py) and only turns about Z. Its
footprint is the convex hull of its print-ready mesh, laid out on a 1 mm grid, GAP mm from every
other footprint and MARGIN mm inside the bed. MARGIN was sized for the widest brim the 1.3.3.3
slicer's auto brim made (13.6 mm, on the fuselage couplers); the 5 mm brims the print table sets
now (make_print_ready.py, `brim`) leave room to spare, so no brim is cut off at the bed's edge.
Neighbours' brims may meet and print joined. Parts go on largest first, each at the lowest free spot, then
the leftmost (bottom-left fill), trying its minimum-area orientation, that turned 90 deg, then
the two diagonals; the finished layout is centred on the bed. The
layout is deterministic, so the gate and the viewer recompute it. slice_all.py writes every
placed copy as its own STL and slices the plate with --arrange 0: the slicer keeps the
positions, and each part stays its own object, with its own brim if it has one, and can be
cancelled on its own on the printer (Klipper exclude_object).
"""
import hashlib
import json
import os
from functools import lru_cache

import numpy as np

import geom as G
from make_print_ready import PARTS

PRINTER = "s1"
BED = 250.0
MARGIN = 15.0
GAP = 6.0
RES = 1.0

# In print order. Copies of one part may be split between plates; check_parts.py checks that the
# plates hold every PETG print exactly once.
PLATES = {
    # With the LW-PLA test prints: the tip ring's fit in wing_tip_r, a servo in its hatch.
    "petg_1_fit_tests": [("rib_tip_r", 1), ("servo_hatch", 1), ("hatch_block", 2)],
    # Everything for the wing panels but the boom ribs.
    "petg_2_wing": [("rib_root_l", 1), ("rib_root_r", 1), ("rib_midtip_l", 1), ("rib_midtip_r", 1),
                    ("rib_tip_l", 1), ("boom_cup_l", 1), ("boom_cup_r", 1),
                    ("servo_hatch", 5), ("hatch_block", 10), ("control_horn", 6)],
    "petg_3_boom_vtail_ribs": [("boom_rib_l", 1), ("boom_rib_r", 1), ("vtail_root_rib", 2), ("vtail_tip_cap", 2)],
    "petg_4_fuselage_rings": [("coupler_240", 1), ("coupler_370", 1)],
    "petg_5_fuselage_frames": [("coupler_610", 1), ("frame_main", 1), ("frame_rear", 1)],
    "petg_6_fuselage_tail": [("fc_shelf", 1), ("battery_tray", 1), ("gps_mount", 1), ("pod_collar", 1),
                             ("tail_block", 1), ("rear_motor_mount", 1)],
    # Only after the tilt servos have been measured against the pod bay (tracker.md).
    "petg_7_pods_yokes": [("boom_pod_l", 1), ("boom_pod_r", 1), ("yoke_l", 1), ("yoke_r", 1)],
}


def _hull(pts):
    """Convex hull, counter-clockwise (monotone chain)."""
    pts = np.unique(np.round(np.asarray(pts, float), 4), axis=0)
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) -
                                     (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]
    return np.array(half(pts) + half(pts[::-1]))


def _area(poly):
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _rot(pts, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return pts @ np.array([[c, s], [-s, c]])


@lru_cache(maxsize=None)
def _footprint(name):
    """Convex hull of the print-ready mesh seen from above, and the angle that lays its
    minimum-area rectangle along the axes with the long side along x. A part whose rectangle
    square to the bed is within 2 % of that minimum stays square (0 or 90 deg)."""
    v = G.read_stl(os.path.join(G.PRINT, name + ".stl")).reshape(-1, 3)
    hull = _hull(v[:, :2])
    best = None
    for p, q in zip(hull, np.roll(hull, -1, axis=0)):
        ang = -np.degrees(np.arctan2(q[1] - p[1], q[0] - p[0]))
        r = _rot(hull, ang)
        w, h = r.max(0) - r.min(0)
        area = round(w * h, 6)
        if best is None or area < best[0]:
            best = (area, (ang + (90.0 if h > w else 0.0)) % 180.0)
    w0, h0 = hull.max(0) - hull.min(0)
    if w0 * h0 <= 1.02 * best[0]:
        return hull, 0.0 if w0 >= h0 else 90.0
    return hull, best[1]


def _inside(poly, cx, cy, grow=0.0):
    """Grid points (cx, cy) within `grow` of the convex polygon (mitred corners: conservative)."""
    d = np.full(cx.shape, -np.inf)
    for p, q in zip(poly, np.roll(poly, -1, axis=0)):
        e = q - p
        n = np.array([e[1], -e[0]]) / np.hypot(*e)
        d = np.maximum(d, (cx - p[0]) * n[0] + (cy - p[1]) * n[1])
    return d <= grow


def placed_hull(name, x, y, angle):
    return _rot(_footprint(name)[0], angle) + (x, y)


def _to_edges(pts, poly):
    """Distance from each point to the nearest edge of the polygon (zero-length edges ignored)."""
    a, b = poly, np.roll(poly, -1, axis=0)
    ab = b - a
    keep = (ab * ab).sum(-1) > 1e-12
    a, ab = a[keep], ab[keep]
    t = np.clip(((pts[:, None, :] - a) * ab).sum(-1) / (ab * ab).sum(-1), 0.0, 1.0)
    return np.linalg.norm(pts[:, None, :] - (a + t[..., None] * ab), axis=-1).min(1)


def hull_gap(P, Q):
    """Shortest distance between two convex polygons; 0 if they touch or overlap."""
    for A, B in ((P, Q), (Q, P)):
        for p, q in zip(A, np.roll(A, -1, axis=0)):
            n = np.array([q[1] - p[1], p[0] - q[0]])
            if ((B - p) @ n).min() > 0:   # every vertex of B outside this edge of A: separated
                break
        else:
            continue
        break
    else:
        return 0.0
    return float(min(_to_edges(P, Q).min(), _to_edges(Q, P).min()))


def outline_dev(P, Q):
    """Largest distance from either polygon's corners to the other's outline: 0 for one outline."""
    return float(max(_to_edges(P, Q).max(), _to_edges(Q, P).max()))


def convex_hull(pts):
    """Convex hull of 2-D points, counter-clockwise."""
    return _hull(pts)


def outside_dist(pts, poly):
    """Distance from each point to the convex counter-clockwise polygon `poly`: 0 inside it."""
    pts = np.asarray(pts, float)
    a, b = poly, np.roll(poly, -1, axis=0)
    cross = (b[:, 0] - a[:, 0]) * (pts[:, None, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (pts[:, None, 0] - a[:, 0])
    return np.where((cross >= -1e-9).all(1), 0.0, _to_edges(pts, poly))


def placed_mesh(name, x, y, angle):
    """The print-ready mesh turned `angle` deg about z and moved to (x, y) on the bed."""
    tris = G.read_stl(os.path.join(G.PRINT, name + ".stl"))
    return G.transform(tris, G.rotation("z", angle), (x, y, 0.0))


@lru_cache(maxsize=None)
def layout(plate):
    """Placements on the bed: (part, copy, x, y, angle), copy counting from 1."""
    n = int(round(BED / RES))
    centres = (np.arange(n) + 0.5) * RES
    gx, gy = np.meshgrid(centres, centres)
    blocked = np.zeros((n, n), bool)
    size = 2 * n
    items = [(name, k) for name, copies in PLATES[plate] for k in range(1, copies + 1)]
    area = {name: _area(_footprint(name)[0]) for name, _ in PLATES[plate]}
    items.sort(key=lambda it: (-area[it[0]], it[0], it[1]))
    placed = []
    for name, k in items:
        hull, base = _footprint(name)
        best = None
        for pref, turn in enumerate((0.0, 90.0, 45.0, 135.0)):
            angle = round((base + turn) % 360.0, 6)
            poly = _rot(hull, angle)
            lo, hi = poly.min(0), poly.max(0)
            f0 = np.floor(lo / RES).astype(int)
            w, h = (np.ceil(hi / RES).astype(int) - f0)
            if w > n or h > n:
                continue
            lx, ly = np.meshgrid((np.arange(w) + 0.5 + f0[0]) * RES, (np.arange(h) + 0.5 + f0[1]) * RES)
            mask = _inside(poly, lx, ly).astype(float)
            # overlap[oy, ox]: blocked cells under the part when its first cell sits on (ox, oy)
            overlap = np.fft.irfft2(np.fft.rfft2(blocked.astype(float), (size, size)) *
                                    np.conj(np.fft.rfft2(mask, (size, size))), (size, size))[:n, :n]
            ox, oy = np.meshgrid(np.arange(n), np.arange(n))
            tx, ty = (ox - f0[0]) * RES, (oy - f0[1]) * RES
            ok = (overlap < 0.5) & (lo[0] + tx >= MARGIN) & (hi[0] + tx <= BED - MARGIN) & \
                 (lo[1] + ty >= MARGIN) & (hi[1] + ty <= BED - MARGIN)
            if not ok.any():
                continue
            top = np.where(ok, hi[1] + ty, np.inf)
            j = np.lexsort((tx.ravel(), top.ravel()))[0]
            cand = (top.ravel()[j], pref, tx.ravel()[j], angle, tx.ravel()[j], ty.ravel()[j], poly)
            if best is None or cand[:3] < best[:3]:
                best = cand
        if best is None:
            raise ValueError(f"plate {plate}: no room for {name} copy {k}")
        _, _, _, angle, tx, ty, poly = best
        blocked |= _inside(poly + (tx, ty), gx, gy, GAP)
        placed.append((name, k, float(tx), float(ty), float(angle)))
    hulls = [placed_hull(name, x, y, a) for name, _, x, y, a in placed]
    lo, hi = np.min([p.min(0) for p in hulls], 0), np.max([p.max(0) for p in hulls], 0)
    sx, sy = (BED - lo - hi) / 2
    out = sorted((name, k, round(x + sx, 3), round(y + sy, 3), a) for name, k, x, y, a in placed)
    return tuple(out)


def stl_name(name, k, copies):
    """The file name a placed copy is sliced from: it names the object on the printer."""
    return f"{name}_{k}" if copies > 1 else name


def gcode_path(plate):
    return os.path.join(G.ROOT, "gcode", f"{PRINTER}_petg_plates", plate + ".gcode")


def plate_hash(plate):
    """Hash of everything a plate's G-code depends on: each part's print-ready STL and its place."""
    h = hashlib.sha256()
    for name, k, x, y, a in layout(plate):
        with open(os.path.join(G.PRINT, name + ".stl"), "rb") as f:
            h.update(hashlib.sha256(f.read()).digest())
        h.update(json.dumps([name, k, x, y, a]).encode())
    return h.hexdigest()


if __name__ == "__main__":
    for plate, items in PLATES.items():
        lay = layout(plate)
        hulls = [placed_hull(n, x, y, a) for n, _, x, y, a in lay]
        lo, hi = np.min([p.min(0) for p in hulls], 0), np.max([p.max(0) for p in hulls], 0)
        gaps = [hull_gap(hulls[i], hulls[j]) for i in range(len(hulls)) for j in range(i + 1, len(hulls))]
        fill = sum(_area(h) for h in hulls) / BED ** 2
        print(f"{plate}: {len(lay)} prints, footprints x {lo[0]:.1f}..{hi[0]:.1f}, y {lo[1]:.1f}..{hi[1]:.1f}, "
              f"closest {min(gaps) if gaps else float('nan'):.2f} mm apart, {100 * fill:.0f} % of the bed")
        for n, k, x, y, a in lay:
            print(f"   {n:18s} {k:2d}  x {x:6.1f}  y {y:6.1f}  turned {a:6.1f} deg")
