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

With --render it also draws renders/51_support_audit_petg.png: every part the slicer would
support, see-through, with that support in magenta, and what it sits under (WHY).

Run: python scripts/audit_print.py [--render] [part ...]
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
import preview_slices as PS
import slice_all as SA
from make_print_ready import PARTS

RENDER = "51_support_audit_petg.png"
# What each part's would-be support sits under, as RENDER shows it, and how the print copes
# without it (check_parts.check_air() measures every bridge and wall over air in the real G-code).
_POD = "the servo bay's ceiling (a 24 mm bridge), the narrow slot beside it and the axle boss: bridged"
_RIB = "under the plate, inside the spigot ring: a 16 mm bridge; its wire hole stands on a boss"
WHY = {
    "boom_pod_l": _POD, "boom_pod_r": _POD,
    "boom_rib_l": "a 7 mm-wide step at z 5 mm: a 7 mm bridge",
    "boom_rib_r": "a 7 mm-wide step at z 5 mm: a 7 mm bridge",
    "coupler_240": "a small lug inside the ring: a short ledge",
    "frame_main": "inside the horizontal bore along its strut",
    "frame_rear": "inside the horizontal bore along its strut",
    "rear_motor_mount": "inside a horizontal screw hole in its flange",
    "rib_midtip_l": _RIB, "rib_midtip_r": _RIB,
    "tail_block": "a 6 mm slot near the top, and the tops of the pin and wire holes",
    "yoke_l": "inside the axle holes at the top of its arms",
    "yoke_r": "inside the axle holes at the top of its arms",
}

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


def slice_with_supports(name, keep=False):
    """(support grams, support z range, the toolpaths if keep else None) for the part sliced with
    the audit's settings."""
    spec = PARTS[name]
    printer, material = spec["printer"], spec["material"]
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(SA.PROFILES, SA.PROCESS[(printer, material)])) as f:
            proc = json.load(f)
        proc.update(AUDIT[material])
        proc.update(spec["slicer"])
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
        return (*support_grams(found[0], DENSITY[material]), PS.parse(found[0]) if keep else None)


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


def main(names=None, render=False):
    names = names or sorted(PARTS, key=lambda n: (PARTS[n]["material"], n))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        sup = dict(zip(names, pool.map(lambda n: slice_with_supports(n, keep=render), names)))
    print(f"{'part':22s} {'material':10s} {'support (g)':>11s} {'support z (mm)':>16s} {'height':>7s} "
          f"{'base w':>7s} {'h/w':>6s} {'h/(w+brim)':>10s}")
    needs = []
    for name in names:
        grams, zr, _ = sup[name]
        h, w, r, rb = stability(name)
        zt = f"{zr[0]:.1f}-{zr[1]:.1f}" if zr else "-"
        print(f"{name:22s} {PARTS[name]['material']:10s} {grams:11.2f} {zt:>16s} {h:7.1f} {w:7.1f} {r:6.1f} {rb:10.1f}")
        if grams > 0.05:
            needs.append(name)
    print(f"\nparts the slicer would support: {', '.join(needs) or 'none'}")
    if render:
        render_supports(needs, sup)
    return needs


def render_supports(needs, sup):
    """renders/51_support_audit_petg.png: each part the slicer would support, drawn see-through,
    with the supports it would add drawn over it in magenta. The printer's purge line is left
    out, so each picture is framed to its part."""
    purge = PS.NAMES.index("Custom")
    cells, used = [], set()
    for name in needs:
        grams, zr, (segs, kinds) = sup[name]
        part = kinds != purge
        img = PS.draw(segs[part], kinds[part], (420, 380), az=-35.0, el=30.0, xray=True, width=0.8)
        used.update(PS.NAMES[k] for k in np.unique(kinds) if k in PS.SUPPORT)
        cells.append((img, f"{name}: {grams:.1f} g of support, z {zr[0]:.1f}-{zr[1]:.1f} mm", WHY.get(name, "")))
    title = "Where the slicer would add supports, if they were allowed (none print)"
    note = ("Tree supports allowed anywhere, 30 deg threshold, bridges not supported (audit_print.py). Each part is drawn "
            "see-through; magenta is the support it would add. All of it sits inside holes or under bridged spans.")
    img = PS.sheet(cells, 4, title, note, used, extra=[("The part, see-through", (226, 226, 226))])
    path = os.path.join(G.ROOT, "renders", RENDER)
    img.save(path, optimize=True)
    print(f"wrote {os.path.relpath(path, G.ROOT)} ({os.path.getsize(path) // 1024} KB)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--render"]
    main(args or None, render="--render" in sys.argv[1:])
