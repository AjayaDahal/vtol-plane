#!/usr/bin/env python3
"""Small closure/joining parts for the VTOL airframe (pure Python STLs).

Why these exist (review round 1): the wing and fuselage sections print
in vase mode with OPEN ends (bottom_shell_layers=0) so the carbon spars
can pass through the wing and equipment/wiring can run through the
fuselage. Open ends need closing and the section joints need help:

  tip_cap.stl       : flat plate shaped like the tip airfoil (150 mm
                      chord), 3 mm thick, glued over the open wingtip.
  nose_cap.stl      : elliptical plate 14x14 mm, 3 mm thick, glued over
                      the open nose tip (12x12 mm opening).
  sleeve_240/480/720.stl : elliptical tube sleeves (40 mm long) that
                      slide OVER each fuselage section joint and are
                      glued in place, reinforcing the butt joint.
                      Inner dims = joint station + 1 mm clearance,
                      wall 1.5 mm.

Sleeves are annular solids (outer ring + inner ring + end annuli),
so they print as normal PETG parts (no vase mode needed).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wing_section import airfoil_loop, write_stl  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "parts")


def ellipse_loop(rx, ry, n=48):
    return [(rx * math.cos(2 * math.pi * i / n),
             ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def plate(loop_pts, thickness):
    """Flat plate: loop extruded by `thickness` in Z, capped both ends."""
    tris = []
    m = len(loop_pts)
    a = [(x, y, 0.0) for (x, y) in loop_pts]
    b = [(x, y, thickness) for (x, y) in loop_pts]
    for i in range(m):
        j = (i + 1) % m
        tris.append((a[i], b[i], b[j]))
        tris.append((a[i], b[j], a[j]))
    for cap_z, flip in ((0.0, True), (thickness, False)):
        cx = sum(p[0] for p in loop_pts) / m
        cy = sum(p[1] for p in loop_pts) / m
        c = (cx, cy, cap_z)
        for i in range(m):
            j = (i + 1) % m
            p1 = (loop_pts[i][0], loop_pts[i][1], cap_z)
            p2 = (loop_pts[j][0], loop_pts[j][1], cap_z)
            tris.append((c, p2, p1) if flip else (c, p1, p2))
    return tris


def tube(inner, outer, length):
    """Annular tube: outer ring + inner ring, `length` in Z, with end annuli."""
    tris = []
    m = len(inner)
    assert len(outer) == m
    for z0, z1 in ((0.0, length),):
        o0 = [(x, y, z0) for (x, y) in outer]
        o1 = [(x, y, z1) for (x, y) in outer]
        i0 = [(x, y, z0) for (x, y) in inner]
        i1 = [(x, y, z1) for (x, y) in inner]
        for i in range(m):
            j = (i + 1) % m
            # Outer wall.
            tris.append((o0[i], o1[i], o1[j]))
            tris.append((o0[i], o1[j], o0[j]))
            # Inner wall (reversed winding so normals point inward).
            tris.append((i0[i], i1[j], i1[i]))
            tris.append((i0[i], i0[j], i1[j]))
        # End annuli at z0 and z1. Quad (a[i], a[j], b[j], b[i]) split
        # along the a[i]-b[j] diagonal; flip reverses winding at z1.
        for (a, b, flip) in ((o0, i0, False), (o1, i1, True)):
            for i in range(m):
                j = (i + 1) % m
                if flip:
                    tris.append((a[i], b[j], a[j]))
                    tris.append((a[i], b[i], b[j]))
                else:
                    tris.append((a[i], a[j], b[j]))
                    tris.append((a[i], b[j], b[i]))
    return tris


def main():
    os.makedirs(OUT, exist_ok=True)
    # Tip cap: tip airfoil, 150 mm chord, 3 mm thick.
    write_stl(os.path.join(OUT, "tip_cap.stl"), plate(airfoil_loop(150.0), 3.0))
    print("tip_cap.stl: 150 mm chord airfoil plate, 3 mm")
    # Nose cap: 14x14 mm ellipse plate, 3 mm thick.
    write_stl(os.path.join(OUT, "nose_cap.stl"), plate(ellipse_loop(7.0, 7.0), 3.0))
    print("nose_cap.stl: 14x14 mm ellipse plate, 3 mm")
    # Joiner sleeves at the three fuselage joints (width x height at station).
    # sleeve_240 is 60 mm, not 40: it doubles as the nose socket. Glue it
    # to fuse_2 ONLY; the nose (fuse_1) slips 30 mm into its front half
    # and is retained by friction + tape, so the battery stays accessible
    # without a separate hatch. The other sleeves are glued both sides.
    for station, (w, h), length in ((240, (120, 140), 60.0),
                                    (480, (110, 120), 40.0),
                                    (720, (95, 105), 40.0)):
        inner = ellipse_loop(w / 2 + 0.5, h / 2 + 0.5)
        outer = ellipse_loop(w / 2 + 2.0, h / 2 + 2.0)
        name = f"sleeve_{station}.stl"
        write_stl(os.path.join(OUT, name), tube(inner, outer, length))
        print(f"{name}: inner {w+1}x{h+1} mm, wall 1.5 mm, {length:.0f} mm long")


if __name__ == "__main__":
    main()
