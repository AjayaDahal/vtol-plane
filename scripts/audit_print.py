"""Print audit through the slicer's own eyes. It needs the slicer, so it is not part of the gate
(which runs in CI without one); run it after a geometry or profile change. For every print file:

- Supports: the part sliced with automatic tree supports allowed anywhere (not only from the
  bed) and bridges left unsupported, to see whether the slicer would add any. PETG parts use
  their own process at the usual 30 deg threshold. The LW-PLA skins print in vase mode, which
  cannot print supports, so they are sliced as plain walls with the threshold at 45 deg, the
  vase limit: any support there means a wall leans further than a vase can print.
- Stability: the part's height against the narrowest width of its first layer, with and without
  its brim (the vase profile's 8 mm; a PETG part's own, if the print table gives it one). Tall,
  narrow parts are the ones a nozzle can knock loose or set wobbling. The gate picks the PETG
  parts that get a brim by a related measure, height against the root of the first-layer area.

Run: python scripts/audit_print.py [part ...]
"""
import concurrent.futures
import glob
import json
import math
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

import geom as G
import plates as PT
import slice_all as SA
from make_print_ready import PARTS

AUDIT = {
    "lwpla_vase": {"spiral_mode": "0", "enable_support": "1", "support_type": "tree(auto)",
                   "support_on_build_plate_only": "0", "bridge_no_support": "1",
                   "support_threshold_angle": "45"},
    "petg": {"enable_support": "1", "support_type": "tree(auto)", "support_on_build_plate_only": "0",
             "bridge_no_support": "1", "support_threshold_angle": "30"},
}
VASE_BRIM = 8.0
DENSITY = {"lwpla_vase": 1.24, "petg": 1.27}


def support_grams(path, density):
    """Filament (g) extruded as support, and the z range of the support moves."""
    typ, z, grams, zs = "", 0.0, 0.0, []
    area = math.pi * 0.875 ** 2
    with open(path, errors="ignore") as fh:
        for line in fh:
            if line.startswith(";TYPE:"):
                typ = line[6:].strip()
                continue
            if not line.startswith("G1"):
                continue
            mz = re.search(r"Z(-?[\d.]+)", line)
            if mz:
                z = float(mz.group(1))
            me = re.search(r"E(-?[\d.]+)", line)
            if me and float(me.group(1)) > 0 and "upport" in typ:
                grams += float(me.group(1)) * area * density / 1000.0
                zs.append(z)
    return grams, (min(zs), max(zs)) if zs else None


def slice_with_supports(name):
    spec = PARTS[name]
    printer, material = spec["printer"], spec["material"]
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(SA.PROFILES, SA.PROCESS[(printer, material)])) as f:
            proc = json.load(f)
        proc.update(AUDIT[material])
        proc_path = os.path.join(tmp, "process_audit.json")
        with open(proc_path, "w") as f:
            json.dump(proc, f)
        cx, cy = SA.bed_centre(printer)
        stl = os.path.join(tmp, name + ".stl")
        G.write_stl(stl, G.transform(G.read_stl(os.path.join(G.PRINT, name + ".stl")), None, (cx, cy, 0.0)))
        out = os.path.join(tmp, "out")
        os.makedirs(out)
        cmd = [SA.SLICER, "--slice", "0", "--arrange", "0", "--orient", "0", "--ensure-on-bed",
               "--datadir", os.path.join(tmp, "cfg"),
               "--load-settings", ";".join([os.path.join(SA.PROFILES, SA.MACHINE[printer]), proc_path]),
               "--load-filaments", os.path.join(SA.PROFILES, SA.FILAMENT[material]),
               "--outputdir", out, stl]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        found = glob.glob(os.path.join(out, "*.gcode"))
        if len(found) != 1:
            raise RuntimeError(f"{name}: no G-code (exit {run.returncode})\n{(run.stdout + run.stderr)[-800:]}")
        return support_grams(found[0], DENSITY[material])


def min_width(h):
    """Narrowest width of a convex polygon (rotating calipers over its edges)."""
    best = np.inf
    for i in range(len(h)):
        e = h[(i + 1) % len(h)] - h[i]
        n = np.array([-e[1], e[0]]) / np.hypot(*e)
        d = (h - h[i]) @ n
        best = min(best, d.max() - d.min())
    return best


def stability(name):
    v = G.read_stl(os.path.join(G.PRINT, name + ".stl")).reshape(-1, 3)
    z0 = v[:, 2].min()
    height = v[:, 2].max() - z0
    base = PT.convex_hull(v[v[:, 2] <= z0 + 0.25][:, :2])
    w = min_width(base)
    brim = VASE_BRIM if PARTS[name]["material"] == "lwpla_vase" else PARTS[name]["brim"]
    return height, w, height / w, height / (w + 2 * brim)


def main(names=None):
    names = names or sorted(PARTS, key=lambda n: (PARTS[n]["material"], n))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        sup = dict(zip(names, pool.map(slice_with_supports, names)))
    print(f"{'part':22s} {'material':10s} {'support (g)':>11s} {'support z (mm)':>16s} {'height':>7s} "
          f"{'base w':>7s} {'h/w':>6s} {'h/(w+brim)':>10s}")
    needs = []
    for name in names:
        grams, zr = sup[name]
        h, w, r, rb = stability(name)
        zt = f"{zr[0]:.1f}-{zr[1]:.1f}" if zr else "-"
        print(f"{name:22s} {PARTS[name]['material']:10s} {grams:11.2f} {zt:>16s} {h:7.1f} {w:7.1f} {r:6.1f} {rb:10.1f}")
        if grams > 0.05:
            needs.append(name)
    print(f"\nparts the slicer would support: {', '.join(needs) or 'none'}")
    return needs


if __name__ == "__main__":
    main(sys.argv[1:] or None)
