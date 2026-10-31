"""Shared geometry: airfoils, fuselage cross-sections, 2-D offsets, mesh/STL helpers."""
import math
import os
import struct

import numpy as np
from scipy.interpolate import PchipInterpolator

import params as P

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ASSEMBLY = os.path.join(ROOT, "parts", "assembly")
PRINT = os.path.join(ROOT, "parts", "print_ready")

# Clark Y ordinates, percent chord (flat bottom from 30 % aft).
_CY_X = [0, 1.25, 2.5, 5, 7.5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]
_CY_U = [3.50, 5.45, 6.50, 7.90, 8.85, 9.60, 10.68, 11.36, 11.70, 11.40, 10.52,
         9.15, 7.35, 5.22, 2.80, 1.49, 0.12]
_CY_L = [3.50, 1.93, 1.47, 0.93, 0.63, 0.42, 0.15, 0.03, 0, 0, 0, 0, 0, 0, 0, 0, 0]
# Interpolating in sqrt(x) keeps the round leading edge smooth.
_S = np.sqrt(np.array(_CY_X) / 100.0)
_CY_UP = PchipInterpolator(_S, np.array(_CY_U) / 100.0)
_CY_LO = PchipInterpolator(_S, np.array(_CY_L) / 100.0)


def clarky_upper(x):
    return _CY_UP(np.sqrt(np.clip(x, 0.0, 1.0)))


def clarky_lower(x):
    return _CY_LO(np.sqrt(np.clip(x, 0.0, 1.0)))


def naca0012_half(x):
    x = np.clip(x, 0.0, 1.0)
    return 0.6 * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2
                  + 0.2843 * x ** 3 - 0.1036 * x ** 4)


SECTIONS = {
    "clarky": (clarky_upper, clarky_lower),
    "naca0012": (naca0012_half, lambda x: -naca0012_half(x)),
}


def _cos_space(a, b, n):
    t = 0.5 * (1.0 - np.cos(np.linspace(0.0, math.pi, n + 1)))
    return a + (b - a) * t


def _dedupe(loop, tol=1e-9):
    keep = [p for i, p in enumerate(loop) if np.hypot(*(p - loop[i - 1])) > tol]
    return np.array(keep)


def airfoil_loop(section, n=48, hinge=None, part="main", bevel_deg=None, gap_n=0.0):
    """Closed CCW loop (chord 1, LE at x=0) for a full, hinge-truncated or control-surface profile.

    part="main": airfoil ahead of the hinge, closed by a vertical hinge face.
    part="surface": control surface aft of the hinge, front face bevelled underneath
    so a top-surface tape hinge can deflect both ways.
    """
    up, lo = SECTIONS[section]
    if hinge is None:
        xs = _cos_space(0.0, 1.0, n)
        upper = [(x, float(up(x))) for x in xs[::-1]]
        lower = [(x, float(lo(x))) for x in xs[1:]]
        return _dedupe(np.array(upper + lower))
    if part == "main":
        xs = _cos_space(0.0, hinge, n)
        upper = [(x, float(up(x))) for x in xs[::-1]]
        lower = [(x, float(lo(x))) for x in xs[1:]]
        return _dedupe(np.array(upper + lower))
    xt = hinge + gap_n
    t_h = float(up(xt) - lo(xt))
    xb = xt + t_h * math.tan(math.radians(bevel_deg))
    upper = [(x, float(up(x))) for x in np.linspace(1.0, xt, n + 1)]
    lower = [(x, float(lo(x))) for x in np.linspace(xb, 1.0, n + 1)]
    return _dedupe(np.array(upper + lower))


def offset_loop(loop, d):
    """Offset a CCW polygon inward by d (vertex-normal offset with a mitre limit).

    Where d exceeds the local radius (thin leading or trailing edges) the raw offset
    crosses itself; those swallowtail loops are cut out so the result stays simple.
    """
    pts = np.asarray(loop, float)
    prev = np.roll(pts, 1, axis=0)
    nxt = np.roll(pts, -1, axis=0)
    t1 = pts - prev
    t2 = nxt - pts
    t1 /= np.linalg.norm(t1, axis=1, keepdims=True) + 1e-12
    t2 /= np.linalg.norm(t2, axis=1, keepdims=True) + 1e-12
    n1 = np.stack([-t1[:, 1], t1[:, 0]], axis=1)
    n2 = np.stack([-t2[:, 1], t2[:, 0]], axis=1)
    nb = n1 + n2
    nb /= np.linalg.norm(nb, axis=1, keepdims=True) + 1e-12
    cosang = np.clip(np.sum(nb * n1, axis=1), 0.33, 1.0)
    return _remove_loops(pts + nb * (d / cosang)[:, None])


def _seg_hit(p, r, q, s):
    """Intersection parameter t along p->p+r with segment q->q+s, or None."""
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return None
    w = q - p
    t = (w[0] * s[1] - w[1] * s[0]) / den
    u = (w[0] * r[1] - w[1] * r[0]) / den
    return t if (0.0 < t < 1.0 and 0.0 < u < 1.0) else None


def _remove_loops(pts):
    """Cut the shorter side off at every self-crossing until the polygon is simple."""
    pts = [np.asarray(p, float) for p in pts]
    changed = True
    while changed and len(pts) > 3:
        changed = False
        n = len(pts)
        for i in range(n):
            p, r = pts[i], pts[(i + 1) % n] - pts[i]
            for j in range(i + 2, n):
                if (j + 1) % n == i:
                    continue
                t = _seg_hit(p, r, pts[j], pts[(j + 1) % n] - pts[j])
                if t is None:
                    continue
                x = p + t * r
                inner = j - i            # vertices i+1..j form one side of the crossing
                if inner <= n - inner:
                    pts = pts[:i + 1] + [x] + pts[j + 1:]
                else:
                    pts = [x] + pts[i + 1:j + 1]
                changed = True
                break
            if changed:
                break
    return _dedupe(np.array(pts), 1e-6)


def clip_x(loop, x_max):
    """Keep the part of a closed polygon with x <= x_max (Sutherland-Hodgman)."""
    out = []
    pts = list(map(tuple, loop))
    for i, cur in enumerate(pts):
        prev = pts[i - 1]
        cin, pin = cur[0] <= x_max, prev[0] <= x_max
        if cin != pin:
            t = (x_max - prev[0]) / (cur[0] - prev[0])
            out.append((x_max, prev[1] + t * (cur[1] - prev[1])))
        if cin:
            out.append(cur)
    return np.array(out)


def polygon_area(loop):
    x, y = loop[:, 0], loop[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


# --- fuselage ---------------------------------------------------------------
_FS = np.array(P.FUSE_STATIONS, float)
_FW = PchipInterpolator(_FS[:, 0], _FS[:, 1])
_FH = PchipInterpolator(_FS[:, 0], _FS[:, 2])
_FZ = PchipInterpolator(_FS[:, 0], _FS[:, 3])


def fuse_dims(x):
    """(width, height, centre z) of the fuselage outer surface at station x."""
    x = float(np.clip(x, _FS[0, 0], _FS[-1, 0]))
    return float(_FW(x)), float(_FH(x)), float(_FZ(x))


def fuse_ring(x, inset=0.0, n=96):
    """3-D ring (n, 3) of the fuselage surface at x, shrunk by `inset` per side."""
    w, h, zc = fuse_dims(x)
    a, b = w / 2 - inset, h / 2 - inset
    t = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    return np.stack([np.full(n, x), a * np.cos(t), zc + b * np.sin(t)], axis=1)


def fuse_half_width(x, z, inset=0.0):
    w, h, zc = fuse_dims(x)
    a, b = w / 2 - inset, h / 2 - inset
    r = 1.0 - ((z - zc) / b) ** 2
    return a * math.sqrt(r) if r > 0 else 0.0


# --- meshes -----------------------------------------------------------------
def loft(loops, caps=True):
    """Triangulate a closed skin through same-length 3-D loops; normals point outward."""
    loops = [np.asarray(lp, float) for lp in loops]
    n = len(loops[0])
    tris = []
    for a, b in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            tris.append((a[i], a[j], b[j]))
            tris.append((a[i], b[j], b[i]))
    if caps:
        for lp, flip in ((loops[0], True), (loops[-1], False)):
            c = lp.mean(axis=0)
            for i in range(n):
                j = (i + 1) % n
                tris.append((c, lp[j], lp[i]) if flip else (c, lp[i], lp[j]))
    tris = np.array(tris)
    if signed_volume(tris) < 0:
        tris = tris[:, ::-1]
    return tris


def signed_volume(tris):
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    return float(np.sum(np.einsum("ij,ij->i", a, np.cross(b, c))) / 6.0)


def mirror_y(tris):
    m = tris.copy()
    m[..., 1] *= -1.0
    return m[:, ::-1]


def rotation(axis, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def transform(tris, R=None, t=(0, 0, 0)):
    out = tris if R is None else tris @ np.asarray(R).T
    return out + np.asarray(t, float)


def write_stl(path, tris):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tris = np.asarray(tris, np.float64)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-20
    rec = np.zeros(len(tris), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = nrm
    rec["v"] = tris
    with open(path, "wb") as f:
        f.write(os.path.basename(path).encode()[:80].ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        f.write(rec.tobytes())


def read_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        verts = [list(map(float, ln.split()[1:4])) for ln in data.decode("utf-8", "replace").splitlines()
                 if ln.strip().startswith("vertex")]
        return np.array(verts, float).reshape(-1, 3, 3)
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:84 + 50 * n], dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return rec["v"].astype(np.float64)
