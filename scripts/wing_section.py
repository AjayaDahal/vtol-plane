#!/usr/bin/env python3
"""Generate a Clark-Y wing section STL for the custom VTOL plane.

Pure Python, no CAD kernel: lofts a flat-bottom Clark-Y airfoil between two
spanwise stations and writes a binary STL. The section is a closed solid,
meant to be printed in vase mode (single wall) in LW-PLA, Eclipson-style.

Usage: python3 wing_section.py [output.stl]
Defaults: root chord 220 mm, tip chord 208 mm, section length 200 mm.
"""
import math
import struct
import sys


def clark_y_upper(x, t=0.117):
    """Upper surface of a Clark-Y-ish airfoil, x in [0, 1]."""
    return 5 * t * (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x * x
        + 0.2843 * x * x * x
        - 0.1036 * x * x * x * x
    )


def airfoil_loop(chord, n=48):
    """Closed airfoil polygon: TE -> upper -> LE -> flat bottom -> TE.

    Returns list of (x, y) in mm. Flat bottom (Clark Y) keeps y=0 on the
    lower surface; the upper formula already closes to 0 at TE and LE.
    """
    pts = []
    # Upper surface: x from 1 down to 0. The NACA formula returns the
    # HALF-thickness, so double it: Clark Y is flat-bottomed, meaning the
    # full 11.7% thickness sits above the bottom line.
    for i in range(n + 1):
        x = 1.0 - i / n
        pts.append((x * chord, 2 * clark_y_upper(x) * chord))
    # Lower surface: x from 0 up to 1 (flat bottom, skip duplicate LE/TE)
    for i in range(1, n):
        x = i / n
        pts.append((x * chord, 0.0))
    return pts


def loft(section_a, section_b, z_a, z_b):
    """Triangulate the side walls between two equal-length airfoil loops."""
    tris = []
    m = len(section_a)
    for i in range(m):
        j = (i + 1) % m
        a1 = (section_a[i][0], section_a[i][1], z_a)
        a2 = (section_a[j][0], section_a[j][1], z_a)
        b1 = (section_b[i][0], section_b[i][1], z_b)
        b2 = (section_b[j][0], section_b[j][1], z_b)
        tris.append((a1, b1, b2))
        tris.append((a1, b2, a2))
    return tris


def cap(loop_pts, z, flip):
    """Fan-triangulate an end cap around the loop centroid."""
    cx = sum(p[0] for p in loop_pts) / len(loop_pts)
    cy = sum(p[1] for p in loop_pts) / len(loop_pts)
    c = (cx, cy, z)
    tris = []
    m = len(loop_pts)
    for i in range(m):
        j = (i + 1) % m
        p1 = (loop_pts[i][0], loop_pts[i][1], z)
        p2 = (loop_pts[j][0], loop_pts[j][1], z)
        tris.append((c, p2, p1) if flip else (c, p1, p2))
    return tris


def normal(tri):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / ln, ny / ln, nz / ln)


def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(tris)))
        for tri in tris:
            nx, ny, nz = normal(tri)
            f.write(struct.pack("<12fH", nx, ny, nz,
                                *[c for v in tri for c in v], 0))


def main():
    # Usage: wing_section.py out.stl root_chord tip_chord length
    out = sys.argv[1] if len(sys.argv) > 1 else "wing_section_root.stl"
    root_chord = float(sys.argv[2]) if len(sys.argv) > 2 else 220.0
    tip_chord = float(sys.argv[3]) if len(sys.argv) > 3 else 208.0
    length = float(sys.argv[4]) if len(sys.argv) > 4 else 200.0
    root = airfoil_loop(root_chord)
    tip = airfoil_loop(tip_chord)
    tris = loft(root, tip, 0.0, length)
    tris += cap(root, 0.0, flip=True)
    tris += cap(tip, length, flip=False)
    write_stl(out, tris)
    xs = [v[0] for t in tris for v in t]
    ys = [v[1] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    print(f"wrote {out}: {len(tris)} triangles")
    print(f"bbox x {min(xs):.1f}..{max(xs):.1f}  "
          f"y {min(ys):.1f}..{max(ys):.1f}  "
          f"z {min(zs):.1f}..{max(zs):.1f} mm")


if __name__ == "__main__":
    main()
