"""Verification gate: every check prints PASS/FAIL; exit code 1 if anything fails.

Checks the exported STLs (integrity, handedness, bed fit, fits between mating parts,
hole paths) and the mechanism (tilt sweep, prop-disc clearances) from the same params.
"""
import math
import os
import sys

import numpy as np

import geom as G
import params as P
from make_print_ready import PARTS

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def load(name, folder=None):
    return G.read_stl(os.path.join(folder or G.ASSEMBLY, name + ".stl"))


# --- mesh helpers -----------------------------------------------------------------
def mesh_integrity(tris):
    v = np.round(tris.reshape(-1, 3), 3)
    _, inv = np.unique(v, axis=0, return_inverse=True)
    f = inv.reshape(-1, 3)
    area = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    f = f[area > 1e-9]
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    _, cnt = np.unique(np.sort(e, axis=1), axis=0, return_counts=True)
    _, dcnt = np.unique(e, axis=0, return_counts=True)
    return int(np.sum(cnt == 1)), int(np.sum(cnt > 2)), int(np.sum(dcnt > 1)), G.signed_volume(tris)


def slice_points(tris, axis, value):
    """Intersection segments of a mesh with the plane coord[axis] = value -> (k, 2, 3)."""
    d = tris[:, :, axis] - value
    segs = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        di, dj = d[:, i], d[:, j]
        m = (di < 0) != (dj < 0)
        t = (di[m] / (di[m] - dj[m]))[:, None]
        segs.append((np.nonzero(m)[0], tris[m, i] + t * (tris[m, j] - tris[m, i])))
    idx = np.concatenate([s[0] for s in segs])
    pts = np.concatenate([s[1] for s in segs])
    if len(idx) == 0:
        return np.empty((0, 2, 3))
    order = np.argsort(idx, kind="stable")
    idx, pts = idx[order], pts[order]
    keep = np.r_[idx[1:] == idx[:-1], False]
    return np.stack([pts[keep], pts[np.r_[False, keep[:-1]]]], axis=1)


def inside_2d(pts, segs):
    """Crossing-number point-in-polygon against a segment soup (2-D arrays)."""
    a, b = segs[:, 0], segs[:, 1]
    res = np.zeros(len(pts), bool)
    for k, p in enumerate(pts):
        cond = (a[:, 1] > p[1]) != (b[:, 1] > p[1])
        xi = a[cond, 0] + (p[1] - a[cond, 1]) * (b[cond, 0] - a[cond, 0]) / (b[cond, 1] - a[cond, 1])
        res[k] = np.sum(xi > p[0]) % 2 == 1
    return res


def dist_2d(pts, segs):
    a, b = segs[:, 0], segs[:, 1]
    ab = b - a
    out = np.empty(len(pts))
    for k, p in enumerate(pts):
        t = np.clip(np.einsum("ij,ij->i", p - a, ab) / (np.einsum("ij,ij->i", ab, ab) + 1e-12), 0, 1)
        out[k] = np.min(np.linalg.norm(a + ab * t[:, None] - p, axis=1))
    return out


def fit(name, inner, outer, axis, value, lo, hi, plane=(0, 2)):
    """All of `inner`'s section points lie inside `outer`'s section with a gap in [lo, hi]."""
    si = slice_points(inner, axis, value)
    so = slice_points(outer, axis, value)
    if len(si) == 0 or len(so) == 0:
        check(name, False, f"empty slice at {value}")
        return
    pi = si.reshape(-1, 3)[:, plane]
    so2 = so[:, :, plane]
    inside = inside_2d(pi[::3], so2)
    gap = dist_2d(pi, so2).min()
    check(name, inside.all() and lo <= gap <= hi,
          f"min gap {gap:.2f} mm (want {lo}-{hi}), {np.sum(~inside)} points outside")


def ray_hits(tris, origin, direction):
    o, d = np.asarray(origin, float), np.asarray(direction, float)
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    t = o - v0
    u = np.einsum("ij,ij->i", t, p) * inv
    q = np.cross(t, e1)
    v = np.einsum("j,ij->i", d, q) * inv
    s = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (s > 0)
    return s[hit]


def clear_path(name, tris, origin, direction, length):
    hits = ray_hits(tris, origin, direction)
    hits = hits[hits < length]
    check(name, len(hits) == 0, f"{len(hits)} surface crossings along the hole axis")


# --- analytic envelopes for clearance checks ----------------------------------------
_CY = G.airfoil_loop("clarky", n=80)


def wing_clearance(p):
    y = abs(p[1])
    if not (P.Y_ROOT <= y <= P.Y_TIP):
        return np.inf
    c = P.chord(y)
    loop = np.stack([P.X_LE + c * _CY[:, 0], P.Z_WING + c * _CY[:, 1]], axis=1)
    segs = np.stack([loop, np.roll(loop, -1, axis=0)], axis=1)
    q = np.array([[p[0], p[2]]])
    d = dist_2d(q, segs)[0]
    return -d if inside_2d(q, segs)[0] else d


def vt_clearance(p, half):
    from skins import vt_chord, vt_frame
    origin, e_s, e_t = vt_frame()
    q = np.array(p, float)
    if half < 0:
        q[1] = -q[1]
    rel = q - origin
    u, s, t = rel[0], rel @ e_s, rel @ e_t
    if not (0 <= s <= P.VT_SPAN):
        return np.inf
    c = vt_chord(s)
    lp = G.airfoil_loop("naca0012", n=60)
    loop = lp * c
    segs = np.stack([loop, np.roll(loop, -1, axis=0)], axis=1)
    d = dist_2d(np.array([[u, t]]), segs)[0]
    return -d if inside_2d(np.array([[u, t]]), segs)[0] else d


def disc_points(center, normal, r, rings=(0.35, 0.7, 1.0), n=72):
    normal = np.asarray(normal, float) / np.linalg.norm(normal)
    a = np.cross(normal, [0, 1, 0] if abs(normal[1]) < 0.9 else [1, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(normal, a)
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pts = [center]
    for k in rings:
        pts += list(center + k * r * (np.outer(np.cos(t), a) + np.outer(np.sin(t), b)))
    return np.array(pts)


# --- checks -----------------------------------------------------------------------
def check_meshes():
    for folder in (G.ASSEMBLY, G.PRINT):
        bad = []
        for f in sorted(os.listdir(folder)):
            if not f.endswith(".stl"):
                continue
            bnd, nm, dup, vol = mesh_integrity(G.read_stl(os.path.join(folder, f)))
            if bnd or nm or dup or vol <= 0:
                bad.append(f"{f}(open {bnd}, nonmanifold {nm}, flipped {dup}, vol {vol:.0f})")
        check(f"mesh integrity {os.path.basename(folder)}", not bad, "; ".join(bad) or "closed, manifold, outward")


def check_handedness():
    names = [f[:-6] for f in os.listdir(G.ASSEMBLY) if f.endswith("_r.stl")]
    bad = []
    for n in sorted(names):
        r, l = load(n + "_r"), load(n + "_l")
        lm = G.mirror_y(l).reshape(-1, 3)
        rv = r.reshape(-1, 3)
        if np.abs(lm.min(0) - rv.min(0)).max() > 0.05 or np.abs(lm.max(0) - rv.max(0)).max() > 0.05 \
                or abs(G.signed_volume(r) - G.signed_volume(l)) > 0.002 * G.signed_volume(r):
            bad.append(n)
        if rv[:, 1].mean() <= 0:
            bad.append(n + " (right part not at +y)")
    check("left/right parts are mirror images", not bad, ", ".join(bad) or f"{len(names)} pairs")


def check_bed():
    bad, small = [], []
    for name, spec in sorted(PARTS.items()):
        v = load(name, G.PRINT).reshape(-1, 3)
        ext = v.max(0) - v.min(0)
        bed, height = (250.0, 250.0) if spec["printer"] == "s1" else (260.0, 260.0)
        margin = 6.0 if spec["material"] == "lwpla_vase" else 4.0
        if ext[0] > bed - 2 * margin or ext[1] > bed - 2 * margin or ext[2] > height:
            bad.append(f"{name} {ext[0]:.0f}x{ext[1]:.0f}x{ext[2]:.0f}")
        base = v[v[:, 2] < 0.3]
        bext = base.max(0) - base.min(0)
        if bext[0] * bext[1] < 0.06 * ext[0] * ext[1]:
            small.append(f"{name} base {bext[0]:.0f}x{bext[1]:.0f} under {ext[0]:.0f}x{ext[1]:.0f}")
    check("print-ready parts fit their printer", not bad, "; ".join(bad) or f"{len(PARTS)} parts")
    check("no part stands on a tiny footprint", not small, "; ".join(small) or "ok")


def check_fits():
    lo, hi = P.INSET - 0.2, P.INSET + 0.6
    w = {n: load(n) for n in ("wing_root_r", "wing_mid_r", "wing_tip_r")}
    fit("root rib spigot in root section", load("rib_root_r"), w["wing_root_r"], 1, P.Y_ROOT_RIB[1] + 5, lo, hi)
    br = load("boom_rib_r")
    fit("boom cup spigot in root section", load("boom_cup_r"), w["wing_root_r"], 1, P.Y_BOOM_RIB[0] - 5, lo, hi)
    fit("boom rib spigot in mid section", br, w["wing_mid_r"], 1, P.Y_BOOM_RIB[1] + 5, lo, hi)
    mt = load("rib_midtip_r")
    fit("mid/tip rib spigot in mid section", mt, w["wing_mid_r"], 1, P.Y_MIDTIP_RIB[0] - 5, lo, hi)
    fit("mid/tip rib spigot in tip section", mt, w["wing_tip_r"], 1, P.Y_MIDTIP_RIB[1] + 5, lo, hi)
    fit("tip rib spigot in tip section", load("rib_tip_r"), w["wing_tip_r"], 1, P.Y_TIP_RIB[0] - 4, lo, hi)
    f = {i: load(f"fuse_{i}") for i in range(1, 5)}
    for xj, (a, b) in zip(P.FUSE_SPLITS[1:-1], ((1, 2), (2, 3), (3, 4))):
        c = load(f"coupler_{int(xj)}")
        fit(f"coupler_{int(xj)} in fuse_{a}", c, f[a], 0, xj - 15, lo, hi, plane=(1, 2))
        fit(f"coupler_{int(xj)} in fuse_{b}", c, f[b], 0, xj + 15, lo, hi, plane=(1, 2))
    for n, xs in (("frame_main", P.MAIN_SPAR["x"] + 4), ("frame_rear", P.REAR_SPAR["x"] + 2.5)):
        fit(f"{n} in fuse_3", load(n), f[3], 0, xs, lo, hi + 0.6, plane=(1, 2))
    fit("fc_shelf in fuse_2", load("fc_shelf"), f[2], 0, 305.0, 0.2, 3.0, plane=(1, 2))
    fit("battery_tray in fuse_2", load("battery_tray"), f[2], 0, 305.0, 0.2, 40.0, plane=(1, 2))
    fit("pod_collar in fuse_4", load("pod_collar"), f[4], 0, 752.0, lo, hi, plane=(1, 2))
    # V-tail ribs: slice in the panel frame.
    from skins import vt_frame
    origin, e_s, e_t = vt_frame()
    R = np.stack([[1, 0, 0], e_s, e_t])
    to_local = lambda t: (t - origin) @ R.T
    vt = to_local(load("vtail_r"))
    fit("V-tail root rib spigot in panel", to_local(load("vtail_root_rib_r")), vt, 1, 5.0, lo, hi, plane=(0, 2))
    fit("V-tail tip cap spigot in panel", to_local(load("vtail_tip_cap_r")), vt, 1, P.VT_SPAN - 3, lo, hi,
        plane=(0, 2))


def outline_z(segs, xs):
    """Highest and lowest z where each vertical x = xs crosses a 2-D section outline."""
    a, b = segs[:, 0][None], segs[:, 1][None]
    x = np.asarray(xs, float)[:, None]
    dx = b[..., 0] - a[..., 0]
    m = ((a[..., 0] - x) * (b[..., 0] - x) <= 0) & (np.abs(dx) > 1e-9)
    t = np.where(m, (x - a[..., 0]) / np.where(m, dx, 1.0), 0.0)
    z = a[..., 1] + t * (b[..., 1] - a[..., 1])
    return np.where(m, z, -np.inf).max(1), np.where(m, z, np.inf).min(1)


FLUSH_TOL = 0.15


def check_flush():
    """Each glued skin joint is flush: either side of a rib face, the two outlines match on
    top and bottom over their common chord, and the fuselage rings match where the sections
    butt, so the glued airframe reads as one surface."""
    from skins import vt_frame
    origin, e_s, e_t = vt_frame()
    R = np.stack([[1, 0, 0], e_s, e_t])
    cache = {}

    def mesh(name, local=False):
        if (name, local) not in cache:
            cache[name, local] = (load(name) - origin) @ R.T if local else load(name)
        return cache[name, local]

    def sec(name, y, local=False):
        return slice_points(mesh(name, local), 1, y)[:, :, [0, 2]]

    def step(a, b, x_from=None, te=True):
        if len(a) == 0 or len(b) == 0:
            return np.inf
        lo = max(a[..., 0].min(), b[..., 0].min(), x_from or -np.inf)
        hi = min(a[..., 0].max(), b[..., 0].max())
        xs = np.arange(lo + 0.5, hi - 0.5, 0.25)
        (ta, ba), (tb, bb) = outline_z(a, xs), outline_z(b, xs)
        le = 0.0 if x_from else abs(a[..., 0].min() - b[..., 0].min())
        # Trailing edge or hinge face: where both outlines end aft.
        end = abs(a[..., 0].max() - b[..., 0].max()) if te else 0.0
        return max(np.abs(tb - ta).max(), np.abs(bb - ba).max(), le, end)

    e = 0.05
    tongue_end = P.TONGUE_FAIR_X[1] + 1.0   # ahead of this the boom-rib tongue is the pod fairing
    # (label, inboard part, outboard part, joint y, compare from x, compare aft ends)
    joints = (("root rib", "rib_root_r", "wing_root_r", P.Y_ROOT_RIB[1], None, True),
              ("boom rib in", "wing_root_r", "boom_rib_r", P.Y_BOOM_RIB[0], tongue_end, True),
              # The full-chord boom rib runs on past the mid skin's hinge face: aileron bay end.
              ("boom rib out", "boom_rib_r", "wing_mid_r", P.Y_BOOM_RIB[1], tongue_end, False),
              ("mid/tip rib in", "wing_mid_r", "rib_midtip_r", P.Y_MIDTIP_RIB[0], None, True),
              ("mid/tip rib out", "rib_midtip_r", "wing_tip_r", P.Y_MIDTIP_RIB[1], None, True),
              ("tip rib", "wing_tip_r", "rib_tip_r", P.Y_TIP_RIB[0], None, True))
    res = [(lbl, step(sec(a, y - e), sec(b, y + e), xf, te)) for lbl, a, b, y, xf, te in joints]
    res.append(("V-tail root rib", step(sec("vtail_root_rib_r", -e, True), sec("vtail_r", e, True))))
    res.append(("V-tail tip cap", step(sec("vtail_r", P.VT_SPAN - e, True),
                                       sec("vtail_tip_cap_r", P.VT_SPAN + e, True))))
    # Fuselage sections butt skin to skin: compare the two rings point to outline both ways.
    for xj, (a, b) in zip(P.FUSE_SPLITS[1:-1], ((1, 2), (2, 3), (3, 4))):
        sa = slice_points(load(f"fuse_{a}"), 0, xj - e)[:, :, [1, 2]]
        sb = slice_points(load(f"fuse_{b}"), 0, xj + e)[:, :, [1, 2]]
        d = np.inf if len(sa) == 0 or len(sb) == 0 else \
            max(dist_2d(sa.reshape(-1, 2), sb).max(), dist_2d(sb.reshape(-1, 2), sa).max())
        res.append((f"fuse x={xj:.0f}", d))
    worst = max(s for _, s in res)
    check("glued skin joints are flush (wing, V-tail, fuselage)", worst <= FLUSH_TOL,
          ", ".join(f"{lbl} {s:.2f}" for lbl, s in res) + f" mm (want <= {FLUSH_TOL})")

    # A rib flange that is a prism of one section meets its tapered skin at a crease (up to 6 deg
    # at the trailing edge). Ruled flanges continue the taper: their free face is the skin's own
    # section continued to that station.
    from skins import vt_loop, wing_loop
    ring = lambda pts: np.stack([pts, np.roll(pts, -1, axis=0)], axis=1)
    to_ut = lambda pts: ((pts - origin) @ R.T)[:, [0, 2]]
    yr, yt = mesh("rib_root_r")[..., 1].min(), mesh("rib_tip_r")[..., 1].max()
    sr = mesh("vtail_root_rib_r", True)[..., 1].min()
    sc = mesh("vtail_tip_cap_r", True)[..., 1].max()
    free = (("root rib, y=60 face", sec("rib_root_r", yr + e), ring(wing_loop(yr + e)[:, [0, 2]])),
            ("tip rib, y=710 face", sec("rib_tip_r", yt - e), ring(wing_loop(yt - e, P.AIL_HINGE)[:, [0, 2]])),
            ("V-tail rib, inner face", sec("vtail_root_rib_r", sr + e, True),
             ring(to_ut(vt_loop(sr + e, P.VT_HINGE, "main")))),
            ("V-tail cap, outer face", sec("vtail_tip_cap_r", sc - e, True),
             ring(to_ut(vt_loop(sc - e, P.VT_HINGE, "main")))))
    res = [(lbl, step(a, b)) for lbl, a, b in free]
    worst = max(s for _, s in res)
    check("rib flanges keep the skin taper (no crease at the seams)", worst <= FLUSH_TOL,
          ", ".join(f"{lbl} {s:.2f}" for lbl, s in res) + f" mm off the continued skin (want <= {FLUSH_TOL})")


def check_paths():
    for n in ("rib_root_r", "boom_cup_r", "boom_rib_r", "rib_midtip_r", "rib_tip_r"):
        t = load(n)
        for s, tag in ((P.MAIN_SPAR, "main"), (P.REAR_SPAR, "rear")):
            clear_path(f"{n} {tag} spar hole", t, (s["x"], 0, s["z"]), (0, 1, 0), 1000)
    for n, s, j in (("frame_main", P.MAIN_SPAR, P.MAIN_JOINER), ("frame_rear", P.REAR_SPAR, P.REAR_JOINER)):
        clear_path(f"{n} joiner sleeve", load(n), (s["x"], -200, s["z"]), (0, 1, 0), 400)
    # Aileron servo leads and pitot tubing run spanwise between the spars through every rib.
    for n in ("rib_root_r", "boom_cup_r", "boom_rib_r", "rib_midtip_r"):
        clear_path(f"{n} wire/pitot hole", load(n), (P.RIB_WIRE_X, 0, P.RIB_WIRE_Z + 1.0), (0, 1, 0), 1000)
    for n in ("frame_main", "frame_rear", "coupler_610", "pod_collar", "rear_motor_mount", "tail_block"):
        clear_path(f"{n} tail-boom bore", load(n), (0, 0, P.BOOM_Z), (1, 0, 0), 2000)
    worst = min(G.fuse_half_width(x, P.BOOM_Z, P.LWPLA_WALL) for x in np.arange(P.BOOM_X[0], 760.0, 5.0))
    check("tail boom stays inside the pod", worst > P.BOOM_OD / 2 + 2, f"min half-width at boom height {worst:.1f} mm")
    # Spars inside every section end with 1 mm margin.
    worst = np.inf
    for n, (y0, y1) in (("wing_root_r", P.Y_ROOT_SEC), ("wing_mid_r", P.Y_MID_SEC), ("wing_tip_r", P.Y_TIP_SEC)):
        t = load(n)
        for y in (y0 + 0.5, y1 - 0.5):
            segs = slice_points(t, 1, y)[:, :, [0, 2]]
            for s in (P.MAIN_SPAR, P.REAR_SPAR):
                ang = np.linspace(0, 2 * math.pi, 24, endpoint=False)
                ring = np.stack([s["x"] + s["od"] / 2 * np.cos(ang), s["z"] + s["od"] / 2 * np.sin(ang)], axis=1)
                worst = min(worst, dist_2d(ring, segs).min() if inside_2d(ring, segs).all() else -1)
    check("spars fit inside every wing section", worst >= P.LWPLA_WALL + 1.0, f"min skin clearance {worst:.2f} mm")
    sq = P.MOTOR_HOLE_SQ / 2
    plates = (("yoke_r", P.X_PIVOT, P.BOOM_Y, P.Z_PIVOT + P.YOKE_PLATE_Z0),
              ("rear_motor_mount", P.X_REAR_MOTOR, 0.0, P.REAR_PLATE_Z))
    for n, cx, cy, z0 in plates:
        t = load(n)
        for dx, dy in ((-sq, -sq), (-sq, sq), (sq, -sq), (sq, sq), (0, 0)):
            # Through the plate, plus 4 mm of head room under the screw heads.
            start = z0 - (0.5 if dx == dy == 0 else 4.5)
            clear_path(f"{n} motor hole ({dx:+.1f},{dy:+.1f})", t, (cx + dx, cy + dy, start), (0, 0, 1), 20)
        # A 2.5 mm hex key's short leg (~21 mm) has to stand under every screw head
        # (fit the motor before the mount goes on the pod or boom).
        worst = min(min(np.r_[ray_hits(t, (cx + dx, cy + dy, z0 - 3.0), (0, 0, -1)), 99.0])
                    for dx in (-sq, sq) for dy in (-sq, sq))
        check(f"{n} hex-key room under the motor screws", worst >= 23.0, f"{worst:.1f} mm (want >= 23)")
    clear_path("yoke bearing pocket", load("yoke_r"), (P.X_PIVOT, P.BOOM_Y, P.Z_PIVOT), (0, 1, 0), 60)
    pod = load("boom_pod_r").reshape(-1, 3)
    yk = load("yoke_r").reshape(-1, 3)
    near = lambda v: np.hypot(v[:, 0] - P.X_PIVOT, v[:, 2] - P.Z_PIVOT) < P.AXLE_BOSS_R + 1
    gap = yk[near(yk) & (yk[:, 1] > P.BOOM_Y), 1].min() - pod[near(pod), 1].max()
    check("axle boss to yoke arm running gap", 0.3 <= gap <= 1.0, f"{gap:.2f} mm")


def check_mechanism():
    from build123d import Axis, Cylinder, Pos, Rot
    import structure as S
    pod, rib, yk, plate = S.boom_pod(), S.boom_rib(), S.yoke(), S.yoke_plate()
    axis = Axis((P.X_PIVOT, P.BOOM_Y, P.Z_PIVOT), (0, 1, 0))
    worst, worst_at, plate_min = np.inf, None, np.inf
    for th in np.arange(P.TILT_MIN_DEG - 5, P.TILT_MAX_DEG + 5.1, 5.0):
        y_rot = yk.rotate(axis, -th)
        d = min(y_rot.distance_to(pod), y_rot.distance_to(rib))
        if d < worst:
            worst, worst_at = d, th
        p_rot = plate.rotate(axis, -th)
        plate_min = min(plate_min, p_rot.distance_to(pod), p_rot.distance_to(rib))
    check("tilt yoke clears pod and boom rib over -25..95 deg", worst >= 0.3,
          f"min {worst:.2f} mm at {worst_at:+.0f} deg (0.5 mm is the bearing running gap)")
    check("motor plate sweep clears the pod by >= 2 mm", plate_min >= 2.0, f"min {plate_min:.1f} mm")
    # Front prop disc vs wing, pod and fuselage.
    z_prop = P.YOKE_PLATE_Z0 + P.YOKE_PLATE_T + P.MOTOR_BASE_TO_PROP
    worst = (np.inf, None)
    for th in np.arange(P.TILT_MIN_DEG, P.TILT_MAX_DEG + 0.1, 5.0):
        rad = math.radians(th)
        n = np.array([-math.sin(rad), 0.0, math.cos(rad)])
        c = np.array([P.X_PIVOT, P.BOOM_Y, P.Z_PIVOT]) + z_prop * n
        disc = Pos(*c) * Rot(0, -th, 0) * Cylinder(P.PROP_D / 2, 1.0)
        d = min(disc.distance_to(pod), disc.distance_to(rib))
        for p in disc_points(c, n, P.PROP_D / 2):
            d = min(d, wing_clearance(p), abs(p[1]) - G.fuse_dims(p[0])[0] / 2)
        if d < worst[0]:
            worst = (d, th)
    check("front prop disc clears wing, pod and fuselage over the tilt range", worst[0] >= 10.0,
          f"min {worst[0]:.1f} mm at {worst[1]:+.0f} deg")
    # Rear prop disc vs V-tail, boom, pod.
    zc = P.REAR_PLATE_Z + 4.0 + P.MOTOR_BASE_TO_PROP
    c = np.array([P.X_REAR_MOTOR, 0.0, zc])
    d = np.inf
    for p in disc_points(c, (0, 0, 1), P.PROP_D / 2):
        w, h, z0 = G.fuse_dims(p[0])
        fus = np.inf if p[0] > P.FUSE_SPLITS[-1] else (p[2] - (z0 + h / 2))
        boom = math.hypot(p[1], p[2] - P.BOOM_Z) - P.BOOM_OD / 2
        d = min(d, vt_clearance(p, 1), vt_clearance(p, -1), fus, boom)
    check("rear prop disc clears V-tail, boom and pod", d >= 10.0, f"min {d:.1f} mm")


def unsupported_area(t, n=600, seed=0):
    """Estimated area (mm2) of overhang in print orientation that would need support, and one
    example point. Faces 60-80 deg from vertical must be bridged; flatter faces may also be
    ledges of <= 3 mm out from a wall. A bridge needs material on two opposite sides (span
    <= 30 mm) AND the overhang must continue over the whole span (a ceiling within 3 mm above
    the probe line all the way across), so a ledge reaching only part-way is not a bridge.
    Hits on the probed face's own plane are ignored, so a flat sloped underside cannot anchor
    on itself."""
    rng = np.random.default_rng(seed)
    nrm = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    un = nrm / (2 * area[:, None] + 1e-12)
    zlo, zhi = t[:, :, 2].min(1), t[:, :, 2].max(1)
    lo_xy, hi_xy = t[:, :, :2].min(1), t[:, :, :2].max(1)
    cen = t.mean(1)
    steep = np.nonzero((-un[:, 2] > math.sin(math.radians(60))) & (zlo > 0.3))[0]
    if not len(steep):
        return 0.0, None
    dirs = [np.array([math.cos(a), math.sin(a), 0.0]) for a in np.radians(np.arange(0, 180, 22.5))]
    pick = rng.choice(steep, size=n, replace=True, p=area[steep] / area[steep].sum())
    w = area[steep].sum() / n
    bad, worst = 0, None
    for k in pick:
        r1, r2 = rng.random(2)
        if r1 + r2 > 1:
            r1, r2 = 1 - r1, 1 - r2
        q = t[k, 0] + r1 * (t[k, 1] - t[k, 0]) + r2 * (t[k, 2] - t[k, 0])
        p = q - [0, 0, 0.3]
        # Ignore the probed face's own plane: a flat sloped underside must not anchor on itself.
        same = (un @ un[k] > math.cos(math.radians(3))) & (np.abs((cen - q) @ un[k]) < 0.5)
        near = ~same & (zlo <= p[2]) & (zhi >= p[2]) & np.all(lo_xy <= p[:2] + 31, 1) & \
            np.all(hi_xy >= p[:2] - 31, 1)
        tn = t[near]
        roof = t[(zhi >= p[2]) & (zlo <= p[2] + 3.0) & np.all(lo_xy <= p[:2] + 31, 1) &
                 np.all(hi_xy >= p[:2] - 31, 1)]
        flat = -un[k, 2] > math.sin(math.radians(80))
        ok = False
        for d in dirs:
            a = ray_hits(tn, p, d)
            b = ray_hits(tn, p, -d)
            a = a.min() if len(a) else np.inf
            b = b.min() if len(b) else np.inf
            if flat and min(a, b) <= 3.0:
                ok = True
                break
            if a + b <= 30.0:
                s = np.arange(-b + 0.5, a - 0.5, 1.5)
                if all(len(h := ray_hits(roof, p + si * d, (0, 0, 1))) and h.min() <= 3.0 for si in s):
                    ok = True
                    break
        if not ok:
            bad += 1
            worst = worst if worst is not None else q
    return bad * w, worst


def check_overhangs():
    """Print-ready parts need no supports, judged on the geometry (the slicer has supports
    switched off, so its output cannot show this). See unsupported_area(). Vase skins must not
    lean more than 45 deg."""
    bad, lean_bad = [], []
    for name, spec in sorted(PARTS.items()):
        t = load(name, G.PRINT)
        if spec["material"].startswith("lwpla"):
            nrm = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
            nz = nrm[:, 2] / (np.linalg.norm(nrm, axis=1) + 1e-12)
            side = (t[:, :, 2].max(1) - t[:, :, 2].min(1)) > 0.3
            lean = np.degrees(np.arcsin(np.clip(np.abs(nz[side]), 0, 1))).max()
            if lean > 45.0:
                lean_bad.append(f"{name} {lean:.0f} deg")
            continue
        a, worst = unsupported_area(t)
        if a > 5.0:
            bad.append(f"{name} ~{a:.0f} mm2 (e.g. print xyz {np.round(worst, 1)})")
    check("PETG overhangs are bridges <= 30 mm or ledges <= 3 mm (no supports needed)", not bad,
          "; ".join(bad) or "all PETG parts")
    check("vase skins lean <= 45 deg", not lean_bad, "; ".join(lean_bad) or "all LW-PLA skins")


def gcode_path(name):
    spec = PARTS[name]
    folder = f"{spec['printer']}_{'lwpla' if spec['material'].startswith('lwpla') else 'petg'}"
    return os.path.join(G.ROOT, "gcode", folder, name + ".gcode")


def check_gcode():
    """The sliced files: present, sliced from the current STL, inside the printer's height
    (end-of-print lift included), no support extrusions, one vase speed band."""
    import json
    import re
    from slice_all import MACHINE, PROFILES, STAMP, stl_hash
    height = {}
    for printer, fname in MACHINE.items():
        with open(os.path.join(PROFILES, fname)) as fh:
            height[printer] = float(json.load(fh)["printable_height"])
    missing, stale, with_support, too_tall, vase = [], [], [], [], {}
    z_top = {}
    for name, spec in sorted(PARTS.items()):
        path = gcode_path(name)
        if not os.path.exists(path):
            missing.append(name)
            continue
        with open(path, "rb") as fh:
            fh.seek(max(0, os.path.getsize(path) - 400))
            tail = fh.read().decode("ascii", "replace")
        stamp = re.search(re.escape(STAMP) + r"([0-9a-f]{64})", tail)
        if not stamp or stamp.group(1) != stl_hash(name):
            stale.append(name)
        typ, f, x, y, z_max = "", 0.0, 0.0, 0.0, 0.0
        n_sup, speeds, lens = 0, [], []
        with open(path, errors="ignore") as fh:
            for line in fh:
                if line.startswith(";TYPE:"):
                    typ = line[6:].strip()
                    continue
                if not (line.startswith("G1") or line.startswith("G0")):
                    continue
                mz = re.search(r"Z(-?[\d.]+)", line)
                if mz:
                    z_max = max(z_max, float(mz.group(1)))
                mf = re.search(r"F([\d.]+)", line)
                if mf:
                    f = float(mf.group(1))
                mx, my, me = re.search(r"X(-?[\d.]+)", line), re.search(r"Y(-?[\d.]+)", line), \
                    re.search(r"E(-?[\d.]+)", line)
                nx = float(mx.group(1)) if mx else x
                ny = float(my.group(1)) if my else y
                if me and float(me.group(1)) > 0 and (mx or my):
                    if "upport" in typ:
                        n_sup += 1
                    elif typ == "Outer wall":
                        speeds.append(f / 60.0)
                        lens.append(math.hypot(nx - x, ny - y))
                x, y = nx, ny
        z_top[name] = z_max
        if z_max > height[spec["printer"]]:
            too_tall.append(f"{name} Z {z_max:.1f} > {height[spec['printer']]:.0f}")
        if n_sup:
            with_support.append(f"{name} ({n_sup} moves)")
        if spec["material"] == "lwpla_vase" and speeds:
            s, w = np.array(speeds), np.array(lens)
            order = np.argsort(s)
            cw = np.cumsum(w[order]) / w.sum()
            vase[name] = (float(np.interp(0.05, cw, s[order])), float(np.interp(0.95, cw, s[order])))
    check("G-code present for every part", not missing, ", ".join(missing) or f"{len(PARTS)} files")
    check("G-code sliced from the current print-ready STL (hash stamp)", not stale,
          ", ".join(stale) or "all current")
    tallest = max(z_top, key=z_top.get) if z_top else None
    check("G-code stays inside the printer's height, end-of-print lift included", not too_tall,
          "; ".join(too_tall) or (f"highest move Z {z_top[tallest]:.1f} ({tallest}); "
                                  + ", ".join(f"{k} {v:.0f} mm" for k, v in height.items())))
    check("G-code has no support extrusions (profile sanity)", not with_support,
          "; ".join(with_support) or "0 support moves")
    if vase:
        lo = min(v[0] for v in vase.values())
        hi = max(v[1] for v in vase.values())
        slow = min(vase, key=lambda k: vase[k][0])
        fast = max(vase, key=lambda k: vase[k][1])
        check("LW-PLA vase walls print in one speed band (one flow calibration)", hi <= 2.0 * lo,
              f"{lo:.0f} mm/s ({slow}) to {hi:.0f} mm/s ({fast}), want max <= 2x min")


def _mesh_dist(pts, tris):
    """Distance from each point to the nearest triangle (projection if it lands inside the
    triangle, else the nearest vertex: exact for points on or near the surface)."""
    a, ab, ac = tris[:, 0], tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    n = np.cross(ab, ac)
    nn = np.einsum("ij,ij->i", n, n) + 1e-18
    out = np.empty(len(pts))
    for i, p in enumerate(pts):
        ap = p - a
        v = np.einsum("ij,ij->i", np.cross(ap, ac), n) / nn
        w = np.einsum("ij,ij->i", np.cross(ab, ap), n) / nn
        inside = (v >= 0) & (w >= 0) & (v + w <= 1)
        dq = np.abs(np.einsum("ij,ij->i", ap, n)) / np.sqrt(nn)
        dv = np.min(np.linalg.norm(tris - p, axis=2), axis=1)
        out[i] = np.min(np.where(inside, dq, dv))
    return out


def check_shared_files():
    """A part printed from one file in several copies for both sides (V-tail ribs and caps,
    servo hatches and their blocks, horns) must be mirror-symmetric, so its mirror image is the
    same part turned over and either copy fits either side."""
    rng = np.random.default_rng(2)
    bad, done = [], []
    for name, spec in sorted(PARTS.items()):
        if spec["qty"] < 2:
            continue
        t = load(spec["src"] or name)
        area = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
        k = rng.choice(len(t), 800, p=area / area.sum())
        r1, r2 = rng.random((2, 800))
        s = r1 + r2 > 1
        r1[s], r2[s] = 1 - r1[s], 1 - r2[s]
        pts = t[k, 0] + r1[:, None] * (t[k, 1] - t[k, 0]) + r2[:, None] * (t[k, 2] - t[k, 0])
        # Candidate mirror planes: principal planes of the exact (area-weighted) surface moments.
        s3 = t.sum(1)
        c = (area[:, None] * s3).sum(0) / (3 * area.sum())
        d0, s0 = t - c, s3 - 3 * c
        cov = (area[:, None, None] / 12 * (np.einsum("tvi,tvj->tij", d0, d0)
                                           + np.einsum("ti,tj->tij", s0, s0))).sum(0)
        _, vecs = np.linalg.eigh(cov)
        best = min(_mesh_dist(pts - 2 * np.outer((pts - c) @ nv, nv), t).max() for nv in vecs.T)
        (done if best <= 0.05 else bad).append(f"{name} ({best:.2f} mm)")
    check("one file for both sides only where the part is mirror-symmetric", not bad,
          "; ".join(bad) or ", ".join(done))


def check_balance():
    import mass_balance as M
    r = M.compute(verbose=False)
    check("hover thrust split: each front motor <= 40 % of AUW", r["front_share"] <= 0.40,
          f"front {100 * r['front_share']:.1f} % each, rear {100 * r['rear_share']:.1f} %")
    check("hover thrust per front motor <= 60 % of worst-case max", r["front_frac_max"] <= 0.60,
          f"{100 * r['front_frac_max']:.1f} % of {M.T_MAX_EMPTY:.0f} g")
    check("battery position reachable on the tray", r["battery_ok"], r["battery_note"])
    check("static margin 10-25 % MAC", 0.10 <= r["static_margin"] <= 0.25, f"{100 * r['static_margin']:.0f} %")


# --- inserts, equipment, GPS saddle --------------------------------------------------
INSERTS = ("coupler_240", "coupler_370", "coupler_610", "frame_main", "frame_rear", "fc_shelf",
           "battery_tray", "pod_collar")
_SKEW = np.array([0.0123, 0.0071, 1.0]) / np.linalg.norm([0.0123, 0.0071, 1.0])


def inside_mesh(pts, tris):
    """Ray-parity point-in-solid test. The ray is skewed off the axes so it misses edges, and
    only triangles whose x-y extent can meet it are tested."""
    lo, hi = tris[:, :, :2].min(1) - 3.0, tris[:, :, :2].max(1) + 3.0
    out = np.zeros(len(pts), bool)
    for i, p in enumerate(pts):
        m = np.all((p[:2] >= lo) & (p[:2] <= hi), axis=1)
        out[i] = len(ray_hits(tris[m], p, _SKEW)) % 2 == 1
    return out


def surface_samples(tris, n=3000, seed=0):
    """Every vertex plus area-weighted random points on the surface."""
    rng = np.random.default_rng(seed)
    area = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    k = rng.choice(len(tris), n, p=area / area.sum())
    r1, r2 = rng.random((2, n))
    s = r1 + r2 > 1
    r1[s], r2[s] = 1 - r1[s], 1 - r2[s]
    pts = tris[k, 0] + r1[:, None] * (tris[k, 1] - tris[k, 0]) + r2[:, None] * (tris[k, 2] - tris[k, 0])
    return np.concatenate([np.unique(tris.reshape(-1, 3).round(4), axis=0), pts])


def penetration(a, b):
    """How deep the surface of mesh a reaches inside closed mesh b (0 if it doesn't)."""
    lo, hi = b.reshape(-1, 3).min(0) - 0.01, b.reshape(-1, 3).max(0) + 0.01
    pts = surface_samples(a)
    pts = pts[np.all((pts >= lo) & (pts <= hi), axis=1)]
    if len(pts) == 0:
        return 0.0
    ins = inside_mesh(pts, b)
    return float(_mesh_dist(pts[ins], b).max()) if ins.any() else 0.0


def check_inserts():
    """No two PETG inserts in the fuselage overlap, e.g. the tray's rails and the shelf's edges
    where they pass through a coupler ring."""
    meshes = {n: load(n) for n in INSERTS}
    box = {n: (t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)) for n, t in meshes.items()}
    worst, pairs = (0.0, ""), 0
    for i, a in enumerate(INSERTS):
        for b in INSERTS[i + 1:]:
            if np.any(box[a][1] < box[b][0] - 0.5) or np.any(box[b][1] < box[a][0] - 0.5):
                continue
            pairs += 1
            for p, q in ((a, b), (b, a)):
                d = penetration(meshes[p], meshes[q])
                if d > worst[0]:
                    worst = (d, f"{p} {d:.2f} mm inside {q}")
    check("fuselage inserts do not overlap each other", worst[0] <= 0.05,
          worst[1] or f"{pairs} touching pairs checked, deepest 0.00 mm")


def box_points(c, size, n=5):
    """A grid of points over the surface of an axis-aligned box."""
    c, h = np.asarray(c, float), np.asarray(size, float) / 2
    g = np.linspace(-1, 1, n)
    u, v = (a.ravel() for a in np.meshgrid(g, g))
    pts = []
    for ax in range(3):
        o = [k for k in range(3) if k != ax]
        for s in (-1.0, 1.0):
            p = np.zeros((len(u), 3))
            p[:, ax], p[:, o[0]], p[:, o[1]] = s, u, v
            pts.append(p)
    return c + np.concatenate(pts) * h


# Room each item needs from the LW-PLA skin: a LiPo swells, and an ESC must never touch the
# skin (LW-PLA softens at 55-60 C).
SKIN_ROOM = {"battery": 3.0, "esc": 5.0}


def check_equipment():
    """The equipment inside the fuselage (payload.py) fits: clear of the skin, not cut by any
    printed part or by each other, and the battery slides out through the nose opening. The
    battery sits where the balance puts its stop pin."""
    import mass_balance as M
    import payload as PL
    items = [e for e in PL.equipment(M.compute(verbose=False)["pin"]) if e["inside"]]
    meshes = {n: load(n) for n in INSERTS}
    skin, cut = [], []
    room_min = (np.inf, "")
    for e in items:
        c, s = np.array(e["pos"]), np.array(e["size"], float)
        need = next((v for k, v in SKIN_ROOM.items() if e["name"].startswith(k)), 2.0)
        pts = box_points(c, s)
        room = min(G.fuse_half_width(x, z, need) - abs(y) for x, y, z in pts)
        if room < 0:
            skin.append(f"{e['name']} short by {-room:.1f} mm")
        if room < room_min[0]:
            room_min = (room, e["name"])
        lo, hi = c - s / 2, c + s / 2
        for n, t in meshes.items():
            v = t.reshape(-1, 3)
            if np.any(np.all((v > lo + 0.05) & (v < hi - 0.05), axis=1)):
                cut.append(f"{n} inside {e['name']}")
            tlo, thi = v.min(0), v.max(0)
            near = pts[np.all((pts >= tlo - 0.01) & (pts <= thi + 0.01), axis=1)]
            if len(near):
                ins = inside_mesh(near, t)
                if ins.any() and _mesh_dist(near[ins], t).max() > 0.05:
                    cut.append(f"{e['name']} inside {n}")
    check("equipment inside the fuselage clears the skin", not skin,
          "; ".join(skin) or f"tightest: {room_min[1]} with {room_min[0]:.1f} mm to spare beyond its "
                             f"required room (battery 3, ESCs 5, others 2 mm)")
    check("equipment is not cut by any printed insert", not cut, "; ".join(cut) or f"{len(items)} items")
    overlap = []
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            ga = np.abs(np.array(a["pos"]) - np.array(b["pos"])) - (np.array(a["size"]) + np.array(b["size"])) / 2
            if np.all(ga < 0.5):
                overlap.append(f"{a['name']}/{b['name']}")
    check("equipment items keep >= 0.5 mm from each other", not overlap, ", ".join(overlap) or "ok")
    # Battery change: the pack slides forward off the tray and out through coupler_240.
    bat = next(e for e in items if e["name"] == "battery")
    c, s = np.array(bat["pos"]), np.array(bat["size"])
    lo = np.array([P.FUSE_SPLITS[1] - P.COUPLER_HALF - 5.0, -s[1] / 2, c[2] - s[2] / 2 + 0.3])
    hi = c + s / 2
    blocked = [n for n in ("coupler_240", "fc_shelf", "battery_tray")
               if np.any(np.all((meshes[n].reshape(-1, 3) > lo) & (meshes[n].reshape(-1, 3) < hi), axis=1))]
    xs = np.arange(lo[0], hi[0], 2.0)
    ring = min(G.fuse_half_width(x, z, P.INSET + P.COUPLER_WALL + 1.0) - s[1] / 2 for x in xs for z in (lo[2], hi[2]))
    check("battery slides out through the nose opening", not blocked and ring > 0,
          ", ".join(blocked) or f"{ring:.1f} mm each side at the tightest point of its path")


def skin_distance(pts):
    """Signed distance from points to the fuselage's outer surface (+ outside), from the
    elliptic stations in params."""
    th = np.linspace(0, 2 * math.pi, 3600, endpoint=False)
    out = np.empty(len(pts))
    for i, (x, y, z) in enumerate(pts):
        w, h, zc = G.fuse_dims(x)
        a, b = w / 2, h / 2
        d = np.min(np.hypot(y - a * np.cos(th), z - zc - b * np.sin(th)))
        out[i] = d if (y / a) ** 2 + ((z - zc) / b) ** 2 > 1 else -d
    return out


def check_gps_mount():
    """The external GPS saddle sits on fuse_3 with a glue gap, takes the puck, and its cable
    hole is open."""
    import payload as PL
    t = load("gps_mount")
    v = np.unique(t.reshape(-1, 3).round(4), axis=0)
    d = skin_distance(v)
    # The skirt's bottom edge: the lowest vertex in each 2 mm stretch of the outer perimeter.
    xc, a = P.GPS_X, P.GPS_PAD / 2
    rim = v[(np.abs(np.abs(v[:, 0] - xc) - a) < 0.01) | (np.abs(np.abs(v[:, 1]) - a) < 0.01)]
    s = np.where(np.abs(np.abs(rim[:, 1]) - a) < 0.01, rim[:, 0] - xc + 4 * a * (rim[:, 1] > 0), rim[:, 1] + 2 * a
                 + 4 * a * (rim[:, 0] > xc))
    edge = np.array([rim[s // 2 == k][np.argmin(rim[s // 2 == k][:, 2])] for k in np.unique(s // 2)])
    de = skin_distance(edge)
    check("GPS saddle follows the skin with a 0.05-0.4 mm glue gap", d.min() >= 0.05 and de.max() <= 0.4,
          f"skirt edge {de.min():.2f}-{de.max():.2f} mm off the skin all round ({len(edge)} points); "
          f"nothing closer than {d.min():.2f} mm")
    top = v[:, 2].max()
    pad = v[np.abs(v[:, 2] - top) < 0.01]
    ext = pad.max(0) - pad.min(0)
    check("GPS puck fits the saddle pad", min(ext[0], ext[1]) >= PL.GPS_D and abs(top - PL.gps_top()) < 0.01,
          f"pad {ext[0]:.0f} x {ext[1]:.0f} mm for a {PL.GPS_D:.0f} mm puck, top z {top:.1f}")
    clear_path("GPS saddle cable hole", t, (P.GPS_X, 0, top + 5), (0, 0, -1), 30)


# --- wing webs ------------------------------------------------------------------------
WEB_SECTIONS = (("wing_root_r", "root", P.Y_ROOT_SEC), ("wing_mid_r", "mid", P.Y_MID_SEC),
                ("wing_tip_r", "tip", P.Y_TIP_SEC))


def check_webs():
    """The spanwise webs in the wing skins leave room for the spars along the whole span, for the
    wire/pitot hole wherever leads run (out to the tip aileron servo), and for the boom's motor
    leads, not just at the section ends."""
    import payload as PL
    from structure import BOOM_WIRE_X_END
    ang = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    rings = [(s["x"], s["z"], s["od"] / 2, np.inf) for s in (P.MAIN_SPAR, P.REAR_SPAR)]
    rings.append((P.RIB_WIRE_X, P.RIB_WIRE_Z, P.RIB_WIRE_R, max(PL.AIL_SERVO_Y) + 15.0))
    worst, where, n = np.inf, "", 0
    for name, sec, (y0, y1) in WEB_SECTIONS:
        t = load(name)
        for y in np.arange(y0 + 1.0, y1 - 0.5, 4.0):
            segs = slice_points(t, 1, y)[:, :, [0, 2]]
            n += 1
            for cx, cz, r, y_max in rings:
                if y > y_max:
                    continue
                ring = np.stack([cx + r * np.cos(ang), cz + r * np.sin(ang)], axis=1)
                d = dist_2d(ring, segs).min() if inside_2d(ring, segs).all() else -1.0
                if d < worst:
                    worst, where = d, f"{name} y={y:.0f}, hole at x={cx:.0f}"
    check("spars and wire hole clear the wing webs along the whole span", worst >= P.LWPLA_WALL + 1.0,
          f"min {worst:.2f} mm over {n} stations ({where})")

    def route_hits(t, pts):
        hits = 0
        for a, b in zip(pts, pts[1:]):
            a, b = np.array(a, float), np.array(b, float)
            h = ray_hits(t, a, (b - a) / np.linalg.norm(b - a))
            hits += int(np.sum(h < np.linalg.norm(b - a)))
        return hits

    # Motor and tilt-servo leads leave the boom cup at x=412 and cross the main spar near the
    # outboard end of the root section, where the webs have run out, then follow the wire hole.
    y1 = P.Y_ROOT_SEC[1]
    leads = [(BOOM_WIRE_X_END, y1 - 3.0, P.Z_WING + 7.0), (P.MAIN_SPAR["x"], y1 - 11.0, 13.0),
             (P.RIB_WIRE_X, y1 - 15.0, P.RIB_WIRE_Z), (P.RIB_WIRE_X, P.Y_ROOT_SEC[0] + 1.0, P.RIB_WIRE_Z)]
    h1 = route_hits(load("wing_root_r"), leads)
    # Pitot tubing: from the tube's end straight back to the wire hole through the pitot gap,
    # then inboard along the wire hole.
    y0m = P.Y_MID_SEC[0]
    pitot = [(P.X_LE + 3.0, P.PITOT_Y, PL.pitot_z()), (PL.PITOT_X[1], P.PITOT_Y, PL.pitot_z()),
             (P.RIB_WIRE_X, P.PITOT_Y, P.RIB_WIRE_Z), (P.RIB_WIRE_X, y0m + 1.0, P.RIB_WIRE_Z)]
    h2 = route_hits(load("wing_mid_r"), pitot)
    check("motor-lead and pitot routes cross no web", h1 == 0 and h2 == 0,
          f"{h1} skin crossings on the boom-cup lead route, {h2} on the pitot route")


def gcode_band(path, z0, dz=0.2):
    """Extruding moves of one layer band [z0, z0+dz) as (n, 2, 2) segments."""
    import re
    x = y = z = 0.0
    segs = []
    with open(path, errors="ignore") as fh:
        for line in fh:
            if not line.startswith(("G1", "G0")):
                continue
            m = dict(re.findall(r"([XYZE])(-?[\d.]+)", line))
            nx, ny, nz = float(m.get("X", x)), float(m.get("Y", y)), float(m.get("Z", z))
            if z0 <= nz < z0 + dz and "E" in m and float(m["E"]) > 0:
                segs.append(((x, y), (nx, ny)))
            if nz > z0 + 3 * dz:
                break
            x, y, z = nx, ny, nz
    return np.array(segs, float).reshape(-1, 2, 2)


def turnarounds(segs, step=0.05, win=1.2):
    """180-degree turns along an extrusion path, and for each the distance from its apex to the
    nearest part of the path more than 4 mm away along it (the line it should fuse with)."""
    pts, s, acc = [], [], 0.0
    for p0, p1 in segs:
        d = float(np.hypot(*(p1 - p0)))
        k = max(1, int(d / step))
        for j in range(k):
            pts.append(p0 + (p1 - p0) * j / k)
            s.append(acc + d * j / k)
        acc += d
    pts, s = np.array(pts), np.array(s)
    tang = np.gradient(pts, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-12
    w = int(win / step)
    gaps, i = [], w
    while i < len(pts) - w:
        if np.dot(tang[i - w], tang[i + w]) < -0.9:
            j = i - w + int(np.argmax(pts[i - w:i + w] @ tang[i - w]))
            far = np.abs(s - s[j]) > 4.0
            gaps.append(float(np.min(np.linalg.norm(pts[far] - pts[j], axis=1))))
            i += 3 * w
        else:
            i += 1
    return gaps


def check_web_gcode():
    """Every web prints: in a layer where all of a section's webs are at full depth, the vase
    path turns back once per web, and each turn lands on the top-skin line (fused)."""
    from skins import _web_full, web_spans
    bad, info = [], []
    for name, sec, (y0, y1) in WEB_SECTIONS:
        if sec not in P.WING_WEBS:
            continue
        # Lowest layer at least 15 % up the part where every web has finished its ramp.
        ready = max(ya + _web_full(x, ya) / P.WEB_RAMP for x in P.WING_WEBS[sec] for ya, _ in web_spans(sec, y0, y1, x)[:1])
        z0 = round(max(ready - y0 + 4.0, 0.15 * (y1 - y0)) / 0.2) * 0.2
        want = len(P.WING_WEBS[sec])
        for side in ("r", "l"):
            part = name[:-1] + side
            path = gcode_path(part)
            if not os.path.exists(path):
                bad.append(f"{part}: no G-code")
                continue
            gaps = turnarounds(gcode_band(path, z0))
            ok = len(gaps) >= want and sorted(gaps)[want - 1] <= P.LINE_W
            info.append(f"{part} z{z0:.1f}: {len(gaps)} turns, worst web gap {sorted(gaps)[min(want, len(gaps)) - 1]:.2f}"
                        if gaps else f"{part} z{z0:.1f}: 0 turns")
            if not ok:
                bad.append(info[-1])
    check("wing webs print as fused double walls (G-code)", not bad,
          "; ".join(bad) or f"{len(info)} skins, every web fused (<= {P.LINE_W} mm): " + "; ".join(info))


# --- servicing: servo hatches, tilt-servo plug pocket, battery straps ---------------------
HATCH_RIBS = {"wing": ("boom_rib", "rib_midtip", "rib_tip"), "vtail": ("vtail_root_rib", "vtail_tip_cap")}


def hatch_world(h, pts):
    """Local hatch coordinates (a chordwise, b spanwise, n into the airfoil) to world points."""
    pts = np.asarray(pts, float).reshape(-1, 3)
    return (np.asarray(h["origin"]) + pts[:, :1] * np.asarray(h["a"]) + pts[:, 1:2] * np.asarray(h["b"])
            + pts[:, 2:] * np.asarray(h["n"]))


def hatch_depth(h, pts):
    """Depth of world points inside the wing's or V-tail's outer surface (negative: outside)."""
    if h["where"] == "wing":
        return np.array([-wing_clearance(p) for p in pts])
    side = 1 if h["origin"][1] > 0 else -1
    return np.array([-vt_clearance(p, side) for p in pts])


def hatch_contents():
    """Local points over what a hatch carries inside the skin, from the cover's inner face up:
    the servo, its two tab posts and both hatch blocks."""
    import payload as PL
    t, top = P.HATCH_T, P.HATCH_BLOCK_TOP
    pa, pb, ph = P.HATCH_POST
    y1 = P.HATCH_B + P.HATCH_CLEAR + P.HATCH_GLUE
    pts = [box_points(PL.SERVO_ON_HATCH, PL.SERVO9)]
    pts += [box_points((x, 0, (t + ph) / 2), (pa, pb, ph - t)) for x in (-P.SERVO9_TAB_PITCH / 2, P.SERVO9_TAB_PITCH / 2)]
    pts += [box_points((0, s * (P.HATCH_MID + y1) / 2, (t + top) / 2), (2 * P.HATCH_BLOCK_A, y1 - P.HATCH_MID, top - t))
            for s in (-1, 1)]
    return np.concatenate(pts)


def check_hatches():
    """The removable servo hatches (wing and V-tail): the skin is flat under each cover and
    block glue face; the servo, posts and blocks fit inside the airfoil clear of the webs,
    spars, rib spigots and V-tail pins; the opening stays ahead of the hinge and clear of the
    webs; the leads have room over the mid servo; the screws line up; the ledges seat the cover;
    and the servo with its horn comes out through the opening past the ledges."""
    import payload as PL
    from skins import vt_chord, vt_frame, web_spans
    a_o, b_o = P.HATCH_A + P.HATCH_CLEAR, P.HATCH_B + P.HATCH_CLEAR
    plane = [(a, b, 0.0) for a in np.linspace(-a_o, a_o, 11) for b in np.linspace(-b_o, b_o, 15)]
    plane += [(a, s * b, 0.0) for a in np.linspace(-P.HATCH_BLOCK_A, P.HATCH_BLOCK_A, 5)
              for b in np.linspace(b_o, b_o + P.HATCH_GLUE, 4) for s in (-1, 1)]
    edge = [(s * a_o, b, 0.0) for b in np.linspace(-b_o, b_o, 15) for s in (-1, 1)]
    local = hatch_contents()
    sv_c, sv = np.array(PL.SERVO_ON_HATCH), np.array(PL.SERVO9)
    sv_top = [(a, b, sv_c[2] + sv[2] / 2) for a in np.linspace(-sv[0] / 2, sv[0] / 2, 7)
              for b in np.linspace(sv_c[1] - sv[1] / 2, sv_c[1] + sv[1] / 2, 7)]
    flat, room, clash, ahead, leads = [], [], [], [], []
    dev = (np.inf, -np.inf)
    room_min, clear_min, hinge_min, lead_min, web_edge_min = np.inf, (np.inf, ""), np.inf, np.inf, np.inf
    half_web = P.WEB_SLOT / 2 + P.LINE_W
    ribs = {}
    for h in PL.servo_hatches():
        side = "r" if h["origin"][1] > 0 else "l"
        d = hatch_depth(h, hatch_world(h, plane))
        # d > 0: the skin bulges past the plane, so the cover sits under it there (and the glue
        # gap under a block is d); d < 0: the cover would stand proud of the skin.
        dev = (min(dev[0], d.min()), max(dev[1], d.max()))
        if d.max() > 0.5 or d.min() < -0.1:
            flat.append(f"{h['name']} {d.min():+.2f}..{d.max():+.2f} mm")
        w = hatch_world(h, local)
        # Clearance to the skin's inner face, except where the servo and blocks rest on the cover.
        dep = hatch_depth(h, w) - P.LWPLA_WALL
        free = local[:, 2] > P.HATCH_T + 0.05
        room_min = min(room_min, dep[free].min())
        if dep.min() < 0.5 or dep[free].min() < 0.5:
            room.append(f"{h['name']} {min(dep.min(), dep[free].min()):.2f} mm")

        def near(what, dist):
            nonlocal clear_min
            if dist < clear_min[0]:
                clear_min = (dist, f"{h['name']} to {what}")
            if dist < 0.5:
                clash.append(f"{h['name']} {dist:.2f} mm from {what}")

        if h["where"] == "wing":
            y = abs(h["origin"][1])
            sec, (y0, y1) = ("mid", P.Y_MID_SEC) if y < P.Y_MID_SEC[1] else ("tip", P.Y_TIP_SEC)
            ew = hatch_world(h, edge)
            for xw in P.WING_WEBS.get(sec, ()):
                for ya, yb in web_spans(sec, y0, y1, xw):
                    m = (np.abs(w[:, 1]) > ya - 0.5) & (np.abs(w[:, 1]) < yb + 0.5)
                    if m.any():
                        near(f"web x={xw}", np.min(np.abs(w[m, 0] - xw)) - half_web)
                    me = (np.abs(ew[:, 1]) > ya - 0.5) & (np.abs(ew[:, 1]) < yb + 0.5)
                    if me.any():
                        web_edge_min = min(web_edge_min, np.min(np.abs(ew[me, 0] - xw)) - half_web)
            for s, tag in ((P.MAIN_SPAR, "main spar"), (P.REAR_SPAR, "rear spar")):
                near(tag, np.min(np.hypot(w[:, 0] - s["x"], w[:, 2] - s["z"])) - s["od"] / 2)
            y_out = y + b_o
            hinge_min = min(hinge_min, P.X_LE + P.AIL_HINGE * P.chord(y_out) - P.AIL_GAP - (h["origin"][0] + a_o))
            if y < P.Y_MID_SEC[1]:
                # The tip servo's lead and the pitot tubing pass over the mid servo.
                up, _ = G.SECTIONS["clarky"]
                for p in hatch_world(h, sv_top):
                    c = P.chord(abs(p[1]))
                    lead_min = min(lead_min, P.Z_WING + c * float(up((p[0] - P.X_LE) / c)) - P.LWPLA_WALL - p[2])
        else:
            o, e_s, e_t = vt_frame()
            if side == "l":
                o, e_s, e_t = o * [1, -1, 1], e_s * [1, -1, 1], e_t * [1, -1, 1]
            s_of = (w - o) @ e_s
            # 4 mm carbon pin: 12 mm into the root rib, on the chord plane at 30 % root chord.
            pin = o + 0.30 * P.VT_ROOT_CHORD * np.array([1.0, 0, 0])
            rel = w - pin
            along = np.clip(rel @ e_s, -P.RIB_T, 12.0)
            near("V-tail pin", np.min(np.linalg.norm(rel - np.outer(along, e_s), axis=1)) - P.VT_PIN_D / 2)
            u_out = ((hatch_world(h, [(a_o, b, 0) for b in (-b_o, b_o)]) - o) @ np.array([1.0, 0, 0]))
            s_ends = (hatch_world(h, [(0, -b_o, 0), (0, b_o, 0)]) - o) @ e_s
            hinge_min = min(hinge_min, min(P.VT_HINGE * vt_chord(s) for s in s_ends) - u_out.max())
            if s_of.min() < 0:
                clash.append(f"{h['name']} reaches past the root rib face")
        for r in HATCH_RIBS[h["where"]]:
            key = f"{r}_{side}"
            if key not in ribs:
                ribs[key] = load(key)
            t = ribs[key]
            lo, hi = t.reshape(-1, 3).min(0) - 1.0, t.reshape(-1, 3).max(0) + 1.0
            m = np.all((w >= lo) & (w <= hi), axis=1)
            if m.any():
                ins = inside_mesh(w[m], t)
                if ins.any():
                    clash.append(f"{h['name']} inside {key}")
                else:
                    near(key, float(_mesh_dist(w[m], t).min()))
    check("servo hatches: skin flat under every cover and block (<= 0.5 mm)", not flat,
          "; ".join(flat) or f"skin {dev[0]:+.2f}..{dev[1]:+.2f} mm from the hatch plane (+: cover sits under the skin)")
    check("servo hatches: servo, posts and blocks fit inside the skin", not room,
          "; ".join(room) or f"{room_min:.2f} mm to the skin's inner face at the tightest point off the cover")
    check("servo hatches clear the webs, spars, rib spigots and V-tail pins", not clash and web_edge_min >= 1.5,
          "; ".join(clash) or f"closest: {clear_min[1]} {clear_min[0]:.2f} mm; opening edge {web_edge_min:.1f} mm "
                              f"from a web (want >= 1.5)")
    check("servo hatch openings stay ahead of the aileron and ruddervator hinge cuts", hinge_min >= 3.0,
          f"{hinge_min:.1f} mm to spare (want >= 3)")
    check("leads and pitot tubing have room over the mid aileron servos", lead_min >= 5.0,
          f"{lead_min:.1f} mm from the servo's top to the top skin (want >= 5)")
    # Screws, ledges and the way out, in the hatch's own frame.
    cover, block = load("servo_hatch"), load("hatch_block")
    both = np.concatenate([cover, block, block * np.array([-1.0, -1.0, 1.0])])
    hits = sum(len(ray_hits(both, (0, s * P.HATCH_SCREW_B, -2.0), (0, 0, 1))) for s in (-1, 1))
    cv, bv = cover.reshape(-1, 3), block.reshape(-1, 3)
    seat = bv[bv[:, 1] < P.HATCH_B, 2].min() - cv[np.abs(cv[:, 1]) > P.HATCH_MID + 0.1, 2].max()
    lap = P.HATCH_B - P.HATCH_MID
    check("hatch screws line up through cover and block; the ledges seat the cover", hits == 0 and abs(seat) < 0.02 and lap >= 4,
          f"{hits} surface crossings on the two screw axes, ledge-to-cover gap {seat:.2f} mm, overlap {lap:.1f} mm")
    post_a = P.SERVO9_TAB_PITCH / 2 + P.HATCH_POST[0] / 2
    horn_b = sv_c[1] + sv[1] / 2 + PL.SERVO9_HORN
    low_b = sv_c[1] - sv[1] / 2
    check("servo, posts and horn come out through the opening past the ledges",
          post_a <= a_o - 0.5 and max(horn_b, -low_b) <= P.HATCH_MID - 0.5,
          f"posts to |a| {post_a:.2f} (opening {a_o:.1f}); servo and horn |b| {low_b:.1f}..{horn_b:.1f} "
          f"(ledges from {P.HATCH_MID:.1f})")


def check_pod_plug():
    """The tilt servo's plug pocket: open on the pod's inboard face, the servo's lead drops into
    it from the bay, it joins the wire channel, it takes a mated plug pair, and it keeps its walls."""
    from structure import pod_profile
    t = load("boom_pod_r")
    (x0, x1), (z0, z1) = P.POD_PLUG_X, P.POD_PLUG_Z
    y0 = P.Y_POD[0]
    bl, bh, bd = P.SERVO_BODY
    bx1 = P.X_PIVOT - P.SERVO_SHAFT_FROM_FRONT - 0.5 + bl
    face = sum(len(ray_hits(t, (x, y0 + d, z), (0, -1, 0))) for x in (x0 + 1.5, (x0 + x1) / 2, x1 - 1.5)
               for z in (z0 + 1.0, (z0 + z1) / 2, z1 - 1.0) for d in (2.0, P.POD_PLUG_DEPTH - 1.0))
    drop = sum(len(h[h < P.Z_PIVOT - z0 - 1.0]) for h in
               (ray_hits(t, (bx1 - dx, y0 + dy, P.Z_PIVOT), (0, 0, -1)) for dx in (2.0, 5.0) for dy in (3.0, 8.0)))
    xh, zc = bx1 - 4.0, P.Z_WING + 7.0
    route = [(xh, y0 + 6.0, z0 + 2.0), (xh, P.BOOM_Y - 1.0, zc), (P.TONGUE_X0 - 0.5, P.BOOM_Y, zc)]
    chan = 0
    for a, b in zip(route, route[1:]):
        a, b = np.array(a, float), np.array(b, float)
        h = ray_hits(t, a, (b - a) / np.linalg.norm(b - a))
        chan += int(np.sum(h < np.linalg.norm(b - a)))
    check("tilt-servo plug pocket: open on the face, lead drops in from the bay, joins the wire channel",
          face == 0 and drop == 0 and chan == 0,
          f"{face} crossings out through the face, {drop} down from the bay, {chan} along the route to the channel")
    plug = (25.0, 7.6, 4.0)
    size = (x1 - x0, P.POD_PLUG_DEPTH, z1 - z0)
    prof = pod_profile()
    segs = np.stack([prof, np.roll(prof, -1, axis=0)], axis=1)
    ring = [(x, z) for x in np.linspace(x0, x1, 12) for z in (z0, z1)] + \
           [(x, z) for x in (x0, x1) for z in np.linspace(z0, z1, 8)]
    ring = np.array(ring)
    wall = dist_2d(ring, segs).min() if inside_2d(ring, segs).all() else -1.0
    check("plug pocket takes a mated plug pair and keeps >= 1.2 mm walls", all(s >= p + 1.0 for s, p in zip(size, plug))
          and wall >= 1.2 and P.TONGUE_X0 - 1.0 - x1 >= 0.8,
          f"pocket {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm for a {plug[0]:.0f} x {plug[1]} x {plug[2]:.0f} pair; "
          f"wall to the pod's skin {wall:.1f} mm, to the tongue slot {P.TONGUE_X0 - 1.0 - x1:.1f} mm")


def check_tray_straps():
    """Battery straps: each goes down a slot beside the battery, under the plate through a gap in
    both rails, and up the other slot, with room to the skin all the way round."""
    import payload as PL
    t = load("battery_tray")
    zt, hs = P.TRAY_Z, P.TRAY_STRAP_W / 2
    ym = sum(P.TRAY_STRAP_Y) / 2
    down = under = 0
    for xs in P.TRAY_STRAP_X:
        for dx in (-hs + 1.5, 0.0, hs - 1.5):
            for s in (-1, 1):
                h = ray_hits(t, (xs + dx, s * ym, zt + 2.0), (0, 0, -1))
                down += int(np.sum(h < 7.5))
            h = ray_hits(t, (xs + dx, -ym, zt - 4.5), (0, 1, 0))
            under += int(np.sum(h < 2 * ym))
    H = PL.BATTERY_SIZE[2]
    skin = min(G.fuse_half_width(xs, z, P.LWPLA_WALL) - P.TRAY_STRAP_Y[1]
               for xs in P.TRAY_STRAP_X for z in np.linspace(zt - 5.0, zt + H, 12))
    beside = P.TRAY_STRAP_Y[0] - PL.BATTERY_SIZE[1] / 2
    check("battery straps loop round the battery through the tray", down == 0 and under == 0 and skin >= 0.5 and beside >= 0.8,
          f"{down} crossings down the slots, {under} under the plate through the rail gaps; "
          f"strap {beside:.1f} mm clear of the battery, {skin:.1f} mm from the skin at the tightest")


if __name__ == "__main__":
    check_meshes()
    check_handedness()
    check_bed()
    check_fits()
    check_flush()
    check_paths()
    check_mechanism()
    check_balance()
    check_overhangs()
    check_shared_files()
    check_inserts()
    check_equipment()
    check_gps_mount()
    check_webs()
    check_hatches()
    check_pod_plug()
    check_tray_straps()
    if "--no-gcode" not in sys.argv:
        check_gcode()
        check_web_gcode()
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    sys.exit(1 if failed else 0)
