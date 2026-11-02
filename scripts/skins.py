"""LW-PLA vase-mode skins in the aircraft frame: wing sections, ailerons, V-tail, fuselage.

Vase mode keeps only each layer's outer contour, so these are closed outer surfaces. The root
and mid wing sections also carry spanwise internal webs, made as thin slots that the single
vase wall runs into and back out of (webbed_wing_skin). All other internal structure is PETG
(structure.py). Writes parts/assembly/*.stl.
"""
import math
import os

import numpy as np

import geom as G
import params as P


def wing_loop(y, hinge=None, part="main"):
    c = P.chord(y)
    gap_n = P.AIL_GAP / c
    lp = G.airfoil_loop("clarky", hinge=hinge, part=part, bevel_deg=P.AIL_BEVEL_DEG, gap_n=gap_n)
    return np.stack([P.X_LE + c * lp[:, 0], np.full(len(lp), y), P.Z_WING + c * lp[:, 1]], axis=1)


def wing_skin(y0, y1, hinge=None, part="main"):
    return G.loft([wing_loop(y0, hinge, part), wing_loop(y1, hinge, part)])


_NOTCH_MIN = 0.02           # slot depth where a section has no web: keeps every station's point count


def _web_full(x, y):
    """Full web depth at chord station x, span y: from the bottom surface to WEB_NECK under the top."""
    c = P.chord(y)
    up, lo = G.SECTIONS["clarky"]
    f = (x - P.X_LE) / c
    return c * (float(up(f)) - float(lo(f))) - P.WEB_NECK


def web_spans(sec, y0, y1, x):
    """Spanwise extents (ya, yb) of the web at chord station x: clear of the spigot rings at both
    ends, and (mid section, ahead of the wire hole) open around the pitot tube."""
    ya, yb = y0 + P.WEB_END_CLEAR, y1 - P.WEB_END_CLEAR
    if sec == "mid" and x < P.RIB_WIRE_X:
        return [(ya, P.PITOT_GAP[0]), (P.PITOT_GAP[1], yb)]
    return [(ya, yb)]


def webbed_wing_skin(sec, y0, y1, hinge=None):
    """Wing section skin with spanwise internal webs (P.WING_WEBS).

    Each web is a WEB_SLOT-wide slot cut up from the bottom surface to WEB_NECK under the top
    surface. In vase mode the single wall runs up one side of the slot and back down the other,
    printing a double-line web joined to both skins. The slot depth ramps in at WEB_RAMP (under
    45 deg) at each end of a web, so the web never starts with an overhang, and it stops
    WEB_END_CLEAR short of the section ends where the rib spigots slide in. Every station has the
    same points, so the loft is valid; where there is no web the slot is _NOTCH_MIN deep.
    """
    xs_web = sorted(P.WING_WEBS[sec])
    spans = {x: web_spans(sec, y0, y1, x) for x in xs_web}

    def depth(x, y):
        d = _NOTCH_MIN
        for ya, yb in spans[x]:
            if ya <= y <= yb:
                d = max(d, min(_web_full(x, y), P.WEB_RAMP * (y - ya), P.WEB_RAMP * (yb - y)))
        return d

    # Stations: section ends, each web's ramp start and end, and at most 30 mm apart between.
    # A ramp meets the full depth where RAMP * (y - ya) equals the full depth at that same y,
    # and the full depth changes with the chord, so solve for that station (fixed point).
    def kink(x, y_end, sgn):
        y = y_end + sgn * _web_full(x, y_end) / P.WEB_RAMP
        for _ in range(8):
            y = y_end + sgn * _web_full(x, y) / P.WEB_RAMP
        return y

    keys = {y0, y1}
    for x, sp in spans.items():
        for ya, yb in sp:
            keys |= {ya, yb, kink(x, ya, +1), kink(x, yb, -1)}
    keys = sorted(k for k in keys if y0 <= k <= y1)
    ys = []
    for a, b in zip(keys, keys[1:]):
        ys += list(np.linspace(a, b, max(1, int(math.ceil((b - a) / 30.0))) + 1)[:-1])
    ys = [y for i, y in enumerate(ys) if i == 0 or y - ys[i - 1] > 0.05] + [y1]

    # Lower-surface points between slots: the plain loop's spacing, frozen at mid-section so
    # every station gets the same count.
    f_end = 1.0 if hinge is None else hinge
    base = G._cos_space(0.0, f_end, 48)[1:]
    c_ref = P.chord((y0 + y1) / 2)
    bounds = [0.0] + [(x - P.X_LE) / c_ref for x in xs_web] + [f_end]
    seg_t = [sorted({(f - a) / (b - a) for f in base if a < f < b} | {1.0}) for a, b in zip(bounds, bounds[1:])]

    up, lo = G.SECTIONS["clarky"]
    loops = []
    for y in ys:
        c = P.chord(y)
        X = lambda f: P.X_LE + c * f
        zu = lambda f: P.Z_WING + c * float(up(f))
        zl = lambda f: P.Z_WING + c * float(lo(f))
        pts = [(X(f), zu(f)) for f in G._cos_space(0.0, f_end, 48)[::-1]]
        h = P.WEB_SLOT / 2 / c
        fw = [(x - P.X_LE) / c for x in xs_web]
        starts, ends = [0.0] + [f + h for f in fw], [f - h for f in fw] + [f_end]
        for k, (a, b) in enumerate(zip(starts, ends)):
            pts += [(X(a + (b - a) * t), zl(a + (b - a) * t)) for t in seg_t[k]]
            if k < len(fw):
                z_end = zl(fw[k]) + depth(xs_web[k], y)
                pts += [(X(fw[k] - h), z_end), (X(fw[k] + h), z_end), (X(fw[k] + h), zl(fw[k] + h))]
        pts = np.array(pts)
        loops.append(np.column_stack([pts[:, 0], np.full(len(pts), y), pts[:, 1]]))
    assert len({len(lp) for lp in loops}) == 1, "webbed skin stations must share one point count"
    return G.loft(loops)


def vt_chord(s):
    return P.VT_ROOT_CHORD + (P.VT_TIP_CHORD - P.VT_ROOT_CHORD) * s / P.VT_SPAN


def vt_frame():
    """Right V-tail panel: origin on the root chord line at the rib face, span and thickness axes."""
    d = math.radians(P.VT_DIHEDRAL)
    origin = np.array([P.VT_X_LE, P.VT_ROOT[0], P.VT_ROOT[1]])
    e_s = np.array([0.0, math.cos(d), math.sin(d)])
    e_t = np.array([0.0, -math.sin(d), math.cos(d)])
    return origin, e_s, e_t


def vt_point(u, s, t):
    origin, e_s, e_t = vt_frame()
    return origin + np.outer(np.atleast_1d(u), [1, 0, 0]) + np.outer(np.atleast_1d(s), e_s) \
        + np.outer(np.atleast_1d(t), e_t)


def vt_loop(s, hinge, part):
    c = vt_chord(s)
    lp = G.airfoil_loop("naca0012", hinge=hinge, part=part, bevel_deg=P.AIL_BEVEL_DEG,
                        gap_n=P.AIL_GAP / c)
    return vt_point(c * lp[:, 0], np.full(len(lp), s), c * lp[:, 1])


def fuse_skin(x0, x1, step=4.0):
    xs = np.linspace(x0, x1, int(math.ceil((x1 - x0) / step)) + 1)
    return G.loft([G.fuse_ring(x) for x in xs])


def build():
    out = {}
    h = P.AIL_HINGE
    out["wing_root_r"] = webbed_wing_skin("root", *P.Y_ROOT_SEC)
    out["wing_mid_r"] = webbed_wing_skin("mid", *P.Y_MID_SEC, hinge=h)
    out["wing_tip_r"] = wing_skin(*P.Y_TIP_SEC, hinge=h)
    out["aileron_mid_r"] = wing_skin(*P.AILERONS["mid"], hinge=h, part="surface")
    out["aileron_tip_r"] = wing_skin(*P.AILERONS["tip"], hinge=h, part="surface")
    out["vtail_r"] = G.loft([vt_loop(0.0, P.VT_HINGE, "main"), vt_loop(P.VT_SPAN, P.VT_HINGE, "main")])
    s0, s1 = P.VT_RUDDERVATOR
    out["ruddervator_r"] = G.loft([vt_loop(s0, P.VT_HINGE, "surface"), vt_loop(s1, P.VT_HINGE, "surface")])
    for name in list(out):
        out[name[:-2] + "_l"] = G.mirror_y(out[name])
    for i, (x0, x1) in enumerate(zip(P.FUSE_SPLITS, P.FUSE_SPLITS[1:]), start=1):
        out[f"fuse_{i}"] = fuse_skin(x0, x1)
    for name, tris in out.items():
        G.write_stl(os.path.join(G.ASSEMBLY, name + ".stl"), tris)
        lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
        print(f"{name:16s} {len(tris):6d} tris  x {lo[0]:7.1f}..{hi[0]:7.1f}  "
              f"y {lo[1]:7.1f}..{hi[1]:7.1f}  z {lo[2]:6.1f}..{hi[2]:6.1f}")
    return out


if __name__ == "__main__":
    build()
