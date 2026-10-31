#!/usr/bin/env python3
"""Generate fuselage sections for the custom VTOL plane.

The fuselage is a loft of elliptical cross-sections along the X axis
(nose at x=0, tail at x=950). Each section STL covers one span of the
station list, capped flat at both ends, so sections glue together.

Usage: python3 fuselage.py <x0> <x1> <output.stl>
"""
import math
import struct
import sys

# (x, width, height) in mm — nose to tail
STATIONS = [
    (0, 12, 12),
    (60, 60, 70),
    (120, 95, 115),
    (240, 120, 140),
    (360, 120, 135),
    (480, 110, 120),
    (600, 95, 105),
    (720, 70, 80),
    (840, 45, 55),
    (950, 18, 28),
]

N_RING = 28


def interp(x):
    """Linear interpolation of (width, height) at station x."""
    if x <= STATIONS[0][0]:
        return STATIONS[0][1], STATIONS[0][2]
    if x >= STATIONS[-1][0]:
        return STATIONS[-1][1], STATIONS[-1][2]
    for (x0, w0, h0), (x1, w1, h1) in zip(STATIONS, STATIONS[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return w0 + t * (w1 - w0), h0 + t * (h1 - h0)
    raise ValueError(x)


def ring(x):
    w, h = interp(x)
    return [(x, (w / 2) * math.cos(2 * math.pi * i / N_RING),
             (h / 2) * math.sin(2 * math.pi * i / N_RING))
            for i in range(N_RING)]


def loft(rings):
    tris = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(N_RING):
            j = (i + 1) % N_RING
            tris.append((r0[i], r1[i], r1[j]))
            tris.append((r0[i], r1[j], r0[j]))
    return tris


def cap(r, flip):
    cx = sum(p[0] for p in r) / len(r)
    cy = sum(p[1] for p in r) / len(r)
    cz = sum(p[2] for p in r) / len(r)
    c = (cx, cy, cz)
    tris = []
    for i in range(len(r)):
        j = (i + 1) % len(r)
        tris.append((c, r[j], r[i]) if flip else (c, r[i], r[j]))
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
    x0, x1, out = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    xs = [x0] + [x for x, _, _ in STATIONS if x0 < x < x1] + [x1]
    rings = [ring(x) for x in xs]
    tris = loft(rings) + cap(rings[0], flip=True) + cap(rings[-1], flip=False)
    write_stl(out, tris)
    ax = [v[0] for t in tris for v in t]
    ay = [v[1] for t in tris for v in t]
    az = [v[2] for t in tris for v in t]
    print(f"wrote {out}: {len(tris)} triangles, "
          f"x {min(ax):.0f}..{max(ax):.0f}  "
          f"y {min(ay):.0f}..{max(ay):.0f}  "
          f"z {min(az):.0f}..{max(az):.0f} mm")


if __name__ == "__main__":
    main()
