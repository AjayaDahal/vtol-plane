#!/usr/bin/env python3
"""Generate one V-tail panel for the custom VTOL plane.

Symmetric NACA-style section (half-thickness formula on both sides),
tapered loft, capped at both ends. Print twice, mirrored, for the V-tail.

Usage: python3 tail_panel.py <output.stl>
Defaults: root chord 180 mm, tip chord 110 mm, length 240 mm.
"""
import math
import struct
import sys


def half_thickness(x, t=0.12):
    return 5 * t * (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x * x
        + 0.2843 * x * x * x
        - 0.1036 * x * x * x * x
    )


def airfoil_loop(chord, n=40):
    pts = []
    for i in range(n + 1):  # upper, TE -> LE
        x = 1.0 - i / n
        pts.append((x * chord, half_thickness(x) * chord))
    for i in range(1, n):  # lower, LE -> TE
        x = i / n
        pts.append((x * chord, -half_thickness(x) * chord))
    return pts


def loft(a, b, z_a, z_b):
    tris = []
    for i in range(len(a)):
        j = (i + 1) % len(a)
        a1 = (a[i][0], a[i][1], z_a)
        a2 = (a[j][0], a[j][1], z_a)
        b1 = (b[i][0], b[i][1], z_b)
        b2 = (b[j][0], b[j][1], z_b)
        tris.append((a1, b1, b2))
        tris.append((a1, b2, a2))
    return tris


def cap(loop_pts, z, flip):
    cx = sum(p[0] for p in loop_pts) / len(loop_pts)
    cy = sum(p[1] for p in loop_pts) / len(loop_pts)
    c = (cx, cy, z)
    tris = []
    for i in range(len(loop_pts)):
        j = (i + 1) % len(loop_pts)
        p1 = (loop_pts[i][0], loop_pts[i][1], z)
        p2 = (loop_pts[j][0], loop_pts[j][1], z)
        tris.append((c, p2, p1) if flip else (c, p1, p2))
    return tris


def normal(tri):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
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
    out = sys.argv[1] if len(sys.argv) > 1 else "vtail_panel.stl"
    root = airfoil_loop(180.0)
    tip = airfoil_loop(110.0)
    tris = loft(root, tip, 0.0, 240.0)
    tris += cap(root, 0.0, flip=True)
    tris += cap(tip, 240.0, flip=False)
    write_stl(out, tris)
    xs = [v[0] for t in tris for v in t]
    ys = [v[1] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    print(f"wrote {out}: {len(tris)} triangles, "
          f"x {min(xs):.1f}..{max(xs):.1f}  "
          f"y {min(ys):.1f}..{max(ys):.1f}  "
          f"z {min(zs):.1f}..{max(zs):.1f} mm")


if __name__ == "__main__":
    main()
