#!/usr/bin/env python3
"""All-flying V-tail panels + pivot blocks (build123d, PETG/LW-PLA).

Review round 1 finding: the original V-tail was a single rigid panel
per side with no hinge and no control horn, yet the design called for
2x 9 g V-tail servos — there was nothing for the servos to drive.
Fix: each panel pivots as a whole on a 3 mm carbon rod (all-flying
tail). The rod glues into the panel's spanwise pivot hole and
protrudes 20 mm from the root into a pivot block glued to the
fuselage tail.

Geometry: V-tail included angle 110 degrees, i.e. each panel's span
axis tilts 35 degrees from horizontal. Panel coords: X = chord
(0 = LE), Y = thickness, Z = span (0 = root, 240 = tip).
NACA 0012 symmetric section, root chord 180 mm, tip chord 110 mm.
Pivot rod at 25% of root chord (X = 45 mm).
Horn: block behind the pivot (X 60..90) on one side, with a 2.2 mm
pushrod hole. Panels are a mirrored pair (horn on -Y / +Y).
Pivot block: 30x24x24 mm, hole along the rod axis, rotated so the
hole axis matches the panel span direction (+-55 deg about X).
"""
import math
import os
import struct

from build123d import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "parts")


def naca0012_yt(x, t=0.12):
    return 5 * t * (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x * x
        + 0.2843 * x * x * x
        - 0.1036 * x * x * x * x
    )


def airfoil_face(chord):
    pts = []
    for i in range(49):
        x = 1.0 - i / 48
        pts.append((x * chord, naca0012_yt(x) * chord))
    for i in range(1, 48):
        x = i / 48
        pts.append((x * chord, -naca0012_yt(x) * chord))
    return Face(Polyline(*pts, close=True))


def panel(horn_side):
    root = airfoil_face(180.0)
    tip = Pos(0, 0, 240) * airfoil_face(110.0)
    part = loft([root, tip])
    # Spanwise pivot hole, 3.2 mm dia, at 25% root chord.
    part -= Pos(45, 0, 120) * Cylinder(1.6, 250)
    # Horn block behind the pivot, one side, with pushrod hole.
    part += Pos(75, horn_side * 14, 12) * Box(30, 8, 24)
    part -= Pos(75, horn_side * 14, 12) * Rot(90, 0, 0) * Cylinder(1.1, 20)
    return part


def pivot_block(tilt_sign):
    # Box in rod coords (rod = Z), then tilt so the hole axis matches
    # the panel span direction: rotate about X by -55 deg for the +Y
    # panel, +55 deg for the -Y panel.
    blk = Box(30, 24, 24) - Cylinder(1.6, 30)
    return Rot(-55 * tilt_sign, 0, 0) * blk


def stl_stats(path):
    with open(path, "rb") as f:
        data = f.read()
    n = struct.unpack("<I", data[80:84])[0]
    xs, ys, zs = [], [], []
    off = 84
    for _ in range(n):
        vals = struct.unpack("<12fH", data[off:off + 50])
        off += 50
        for i in range(3):
            xs.append(vals[3 + i * 3])
            ys.append(vals[4 + i * 3])
            zs.append(vals[5 + i * 3])
    return n, (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "print_ready"), exist_ok=True)
    jobs = [
        ("vtail_r.stl", panel(-1)),
        ("vtail_l.stl", panel(+1)),
        ("vtail_pivot_block_r.stl", pivot_block(+1)),
        ("vtail_pivot_block_l.stl", pivot_block(-1)),
    ]
    # Print orientation for the pivot blocks is UNROTATED (hole vertical,
    # prints cleanly); the +/-55 deg tilt happens at assembly when the
    # block is glued to the fuselage. One file, printed twice.
    blk = Box(30, 24, 24) - Cylinder(1.6, 30)
    export_stl(blk, os.path.join(OUT, "print_ready", "vtail_pivot_block.stl"))
    print("print_ready/vtail_pivot_block.stl: unrotated, hole vertical")
    for name, part in jobs:
        path = os.path.join(OUT, name)
        export_stl(part, path)
        n, bx, by, bz = stl_stats(path)
        print(f"{name}: vol={part.volume:.0f} mm^3, tris={n}, "
              f"X {bx[0]:.1f}..{bx[1]:.1f}, "
              f"Y {by[0]:.1f}..{by[1]:.1f}, "
              f"Z {bz[0]:.1f}..{bz[1]:.1f}")


if __name__ == "__main__":
    main()
