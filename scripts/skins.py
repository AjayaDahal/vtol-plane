"""LW-PLA vase-mode skins in the aircraft frame: wing sections, ailerons, V-tail, fuselage.

Vase mode keeps only each layer's outer contour, so these are closed outer surfaces;
all internal structure is PETG (structure.py). Writes parts/assembly/*.stl.
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
    out["wing_root_r"] = wing_skin(*P.Y_ROOT_SEC)
    out["wing_mid_r"] = wing_skin(*P.Y_MID_SEC, hinge=h)
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
