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
    fit("boom rib spigot in root section", br, w["wing_root_r"], 1, P.Y_BOOM_RIB[0] - 5, lo, hi)
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


def check_paths():
    for n in ("rib_root_r", "boom_rib_r", "rib_midtip_r", "rib_tip_r"):
        t = load(n)
        for s, tag in ((P.MAIN_SPAR, "main"), (P.REAR_SPAR, "rear")):
            clear_path(f"{n} {tag} spar hole", t, (s["x"], 0, s["z"]), (0, 1, 0), 1000)
    for n, s, j in (("frame_main", P.MAIN_SPAR, P.MAIN_JOINER), ("frame_rear", P.REAR_SPAR, P.REAR_JOINER)):
        clear_path(f"{n} joiner sleeve", load(n), (s["x"], -200, s["z"]), (0, 1, 0), 400)
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


def check_balance():
    import mass_balance as M
    r = M.compute(verbose=False)
    check("hover thrust split: each front motor <= 40 % of AUW", r["front_share"] <= 0.40,
          f"front {100 * r['front_share']:.1f} % each, rear {100 * r['rear_share']:.1f} %")
    check("hover thrust per front motor <= 60 % of worst-case max", r["front_frac_max"] <= 0.60,
          f"{100 * r['front_frac_max']:.0f} % of {M.T_MAX_EMPTY:.0f} g")
    check("battery position reachable on the tray", r["battery_ok"], r["battery_note"])
    check("static margin 10-25 % MAC", 0.10 <= r["static_margin"] <= 0.25, f"{100 * r['static_margin']:.0f} %")


if __name__ == "__main__":
    check_meshes()
    check_handedness()
    check_bed()
    check_fits()
    check_paths()
    check_mechanism()
    check_balance()
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    sys.exit(1 if failed else 0)
