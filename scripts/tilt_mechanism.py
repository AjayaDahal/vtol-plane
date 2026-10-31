#!/usr/bin/env python3
"""Tilt mechanism for the VTOL tricopter (build123d, PETG).

Coordinates: X = spanwise (pivot axis), Y = forward (motor axis),
Z = up. Motor center at origin; pivot shaft passes through origin.

Parts:
  tilt_nacelle_r/l.stl : pod + front motor plate (4x M3 on 16 mm square
                         + 9 mm center hole) + pivot bosses with 8 mm
                         bearing pockets + 3.2 mm shaft hole + servo arm
                         with 2.2 mm pushrod hole. Print x2 (one per side).
  tilt_bracket.stl     : cheek plate holding the pivot shaft. Print x4
                         (2 per nacelle, straddling the bosses).
  motor_mount_rear.stl : fixed rear motor plate + glue-in stub. Print x1.

Motor pattern: 2807 class, 16x16 mm M3. Bearings: 3x8x4 mm flanged.
Shaft: 3 mm steel rod. All holes are cut as real CSG cylinders.
"""
import os
import struct
import sys

from build123d import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "parts")


def cyl_x(radius, length, x, y, z):
    """Cylinder with axis along X, centered at (x, y, z)."""
    return Pos(x, y, z) * Rot(0, 90, 0) * Cylinder(radius, length)


def cyl_y(radius, length, x, y, z):
    """Cylinder with axis along Y, centered at (x, y, z)."""
    return Pos(x, y, z) * Rot(90, 0, 0) * Cylinder(radius, length)


def motor_holes(part, y0, y1):
    """4x M3 holes on a 16 mm square + 9 mm center hole, axis along Y."""
    for sx in (-8, 8):
        for sz in (-8, 8):
            part -= cyl_y(1.6, y1 - y0, sx, (y0 + y1) / 2, sz)
    part -= cyl_y(4.5, y1 - y0, 0, (y0 + y1) / 2, 0)
    return part


def nacelle(arm_side):
    # Main pod: 46 wide (X), 64 long (Y), 42 tall (Z); front face Y=+32.
    part = Box(46, 64, 42)
    # Rear-open cavity: 3 mm walls, 6 mm front wall.
    part -= Pos(0, -3, 0) * Box(40, 58, 36)
    # Front motor plate, 4 mm thick, fused to the front face.
    part += Pos(0, 34, 0) * Box(44, 4, 40)
    part = motor_holes(part, 30, 38)
    # Pivot bosses: 14 mm dia, 6 mm long, both sides, axis X at origin.
    for sx in (-1, 1):
        part += cyl_x(7, 6, sx * 26, 0, 0)
        # 8 mm bearing pocket, 4.2 mm deep from the boss outer face.
        part -= cyl_x(4, 4.2, sx * 27, 0, 0)
    # 3.2 mm shaft through-hole, axis X.
    part -= cyl_x(1.6, 62, 0, 0, 0)
    # Servo arm on one side, extending down, with pushrod hole.
    ax = arm_side * 26
    part += Pos(ax, 0, -18) * Box(6, 10, 24)
    part -= cyl_x(1.1, 10, ax, 0, -27)
    return part


def bracket():
    # Cheek plate: 6 thick (X), 50 fore-aft (Y), 44 tall (Z).
    part = Box(6, 50, 44)
    # Shaft hole.
    part -= cyl_x(1.6, 10, 0, 0, 0)
    # 2x M3 mounting holes near the bottom, for the wing spar box.
    for sy in (-16, 16):
        part -= cyl_x(1.6, 10, 0, sy, -16)
    return part


def rear_mount():
    # Motor plate + socket that slides OVER the fuselage tail end.
    # Tail end cross-section is 18 wide x 28 tall, so the socket cavity
    # is 19 x 29 (0.5 mm clearance per side) with 3.5 mm PETG walls.
    # The tail inserts 30 mm into the 40 mm cavity, leaving a 10 mm gap
    # behind the plate for the motor screw heads: mount the motor to the
    # plate first, then slide the socket over the tail and glue the sides.
    part = Pos(0, 2, 0) * Box(44, 4, 40)
    part += Pos(0, -20, 0) * Box(26, 40, 36)
    part -= Pos(0, -20, 0) * Box(19, 40, 29)
    part = motor_holes(part, 0, 4)
    return part


def stl_stats(path):
    """Triangle count + bounding box of an ASCII or binary STL."""
    with open(path, "rb") as f:
        data = f.read()
    xs, ys, zs = [], [], []
    if data[:5] == b"solid" and b"facet" in data[:5000]:
        # ASCII STL (what build123d writes by default).
        n = 0
        for line in data.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if line.startswith("vertex "):
                _, x, y, z = line.split()
                xs.append(float(x))
                ys.append(float(y))
                zs.append(float(z))
            elif line.startswith("facet "):
                n += 1
        return n, (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))
    # Binary STL: 80-byte header, 4-byte count at offset 80, then triangles.
    n = struct.unpack("<I", data[80:84])[0]
    off = 84
    for _ in range(n):
        vals = struct.unpack("<12fH", data[off:off + 50])
        for i in range(3):
            xs.append(vals[3 + i * 3])
            ys.append(vals[4 + i * 3])
            zs.append(vals[5 + i * 3])
        off += 50
    return n, (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = [
        ("tilt_nacelle_r.stl", nacelle(+1)),
        ("tilt_nacelle_l.stl", nacelle(-1)),
        ("tilt_bracket.stl", bracket()),
        ("motor_mount_rear.stl", rear_mount()),
    ]
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
