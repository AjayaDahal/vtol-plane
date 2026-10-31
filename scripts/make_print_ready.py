#!/usr/bin/env python3
"""Rotate design-orientation STLs into print orientation.

Why: Anycubic Slicer Next's CLI segfaults on --rotate-* flags in this
build, so rotation is baked into the mesh instead. Design STLs in
parts/ stay untouched; rotated copies go to parts/print_ready/ and
are what slice_all.sh slices.

Rotations (right-handed):
  fuselage sections : rotate-y -90  (length X -> up Z)
  tilt nacelles     : rotate-x -90  (motor plate +Y -> down on bed)
  tilt bracket      : rotate-y  90  (plate thickness X -> vertical)
  rear motor mount  : rotate-x -90  (motor plate +Y -> down on bed)
After rotation, min Z is translated to 0 (sits on the bed).
Wing sections and the V-tail panel already print as-is.
"""
import os
import struct

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "parts")
DST = os.path.join(SRC, "print_ready")

JOBS = {
    "fuse_1.stl": "ry-90",
    "fuse_2.stl": "ry-90",
    "fuse_3.stl": "ry-90",
    "fuse_4.stl": "ry-90",
    "tilt_nacelle_r.stl": "rx-90",
    "tilt_nacelle_l.stl": "rx-90",
    "tilt_bracket.stl": "ry90",
    "motor_mount_rear.stl": "rx-90",
}


def read_stl(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:5] == b"solid" and b"facet" in data[:5000]:
        tris = []
        cur = []
        for line in data.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if line.startswith("vertex "):
                cur.append(tuple(float(v) for v in line.split()[1:4]))
                if len(cur) == 3:
                    tris.append(tuple(cur))
                    cur = []
        return tris
    n = struct.unpack("<I", data[80:84])[0]
    tris = []
    off = 84
    for _ in range(n):
        vals = struct.unpack("<12fH", data[off:off + 50])
        off += 50
        tris.append(tuple(
            (vals[3 + i * 3], vals[4 + i * 3], vals[5 + i * 3])
            for i in range(3)))
    return tris


def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"VTOL print-ready STL".ljust(80, b"\x00"))
        f.write(struct.pack("<I", len(tris)))
        for tri in tris:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
            ux, uy, uz = bx - ax, by - ay, bz - az
            vx, vy, vz = cx - ax, cy - ay, cz - az
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            norm = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
            f.write(struct.pack("<12fH",
                                nx / norm, ny / norm, nz / norm,
                                ax, ay, az, bx, by, bz, cx, cy, cz, 0))


def rot(kind, p):
    x, y, z = p
    if kind == "ry-90":   # (x,y,z) -> (-z, y, x)
        return (-z, y, x)
    if kind == "ry90":    # (x,y,z) -> (z, y, -x)
        return (z, y, -x)
    if kind == "rx-90":   # (x,y,z) -> (x, z, -y)
        return (x, z, -y)
    raise ValueError(kind)


def main():
    os.makedirs(DST, exist_ok=True)
    for name, kind in JOBS.items():
        tris = read_stl(os.path.join(SRC, name))
        tris = [tuple(rot(kind, v) for v in tri) for tri in tris]
        min_z = min(v[2] for tri in tris for v in tri)
        tris = [tuple((x, y, z - min_z) for (x, y, z) in tri)
                for tri in tris]
        xs = [v[0] for tri in tris for v in tri]
        ys = [v[1] for tri in tris for v in tri]
        zs = [v[2] for tri in tris for v in tri]
        out = os.path.join(DST, name)
        write_stl(out, tris)
        print(f"{name}: {kind} -> X {min(xs):.1f}..{max(xs):.1f}, "
              f"Y {min(ys):.1f}..{max(ys):.1f}, "
              f"Z {min(zs):.1f}..{max(zs):.1f}")


if __name__ == "__main__":
    main()
