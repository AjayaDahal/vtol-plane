"""Slice every print-ready part, and every PETG plate, with Anycubic Slicer Next (OrcaSlicer CLI
works the same).

Set VTOL_SLICER to the slicer executable if it is not at the default Windows install path.
Output: gcode/<printer>_<lwpla|petg>/<part>.gcode, one copy per file (print `qty` copies), and
gcode/s1_petg_plates/<plate>.gcode, the PETG parts laid out on shared beds (plates.py).
Each file ends with a `; vtol_stl_sha256 = ...` comment naming the STL it was sliced from (for a
plate, a hash of its parts' STLs and places), so check_parts.py can tell stale G-code from
current (git does not keep file times).
Run on its own (`python slice_all.py [part or plate ...]`), it then refreshes
viewer/manifest.json and tracker.md, which carry each file's sliced mass and time.
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import geom as G
import plates as PT
from make_print_ready import PARTS

SLICER = os.environ.get("VTOL_SLICER", r"C:\Program Files\AnycubicSlicerNext\AnycubicSlicerNext.exe")
PROFILES = os.path.join(G.ROOT, "slicer_profiles")
MACHINE = {"s1": "machine_kobra_s1.json", "x": "machine_kobra_x.json"}
PROCESS = {("s1", "lwpla_vase"): "process_lwpla_vase.json", ("x", "lwpla_vase"): "process_lwpla_vase_x.json",
           ("s1", "petg"): "process_petg.json", ("s1", "petg_support"): "process_petg_support.json"}
FILAMENT = {"lwpla_vase": "filament_lwpla.json", "petg": "filament_petg.json", "petg_support": "filament_petg.json"}
STAMP = "; vtol_stl_sha256 = "


def stl_hash(name):
    with open(os.path.join(G.PRINT, name + ".stl"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def out_path(name):
    spec = PARTS[name]
    folder = f"{spec['printer']}_{'lwpla' if spec['material'].startswith('lwpla') else 'petg'}"
    return os.path.join(G.ROOT, "gcode", folder, name + ".gcode")


def _slice(stls, printer, material, dst, stamp, arrange):
    """Slice `stls` onto one bed; --arrange 0 keeps each STL where it is."""
    settings = [os.path.join(PROFILES, MACHINE[printer]), os.path.join(PROFILES, PROCESS[(printer, material)])]
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [SLICER, "--slice", "0", "--arrange", str(arrange), "--orient", "0", "--ensure-on-bed",
               "--datadir", os.path.join(tmp, "cfg"),
               "--load-settings", ";".join(settings),
               "--load-filaments", os.path.join(PROFILES, FILAMENT[material]),
               "--outputdir", tmp, *stls]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        found = glob.glob(os.path.join(tmp, "*.gcode"))
        if len(found) != 1:
            tail = (run.stdout + run.stderr)[-1500:]
            raise RuntimeError(f"{os.path.basename(dst)}: slicer produced {len(found)} G-code files "
                               f"(exit {run.returncode})\n{tail}")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(found[0], dst)
    with open(dst, "a", newline="\n") as f:
        f.write(f"{STAMP}{stamp}\n")
    return dst


def bed_centre(printer):
    """Centre of the printer's printable area (machine profile)."""
    with open(os.path.join(PROFILES, MACHINE[printer])) as f:
        corners = [[float(c) for c in corner.split("x")] for corner in json.load(f)["printable_area"]]
    xs, ys = zip(*corners)
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def slice_part(name):
    """The part centred on the bed and sliced with --arrange 0: the slicer's arrange would turn
    some parts about z (it laid the 45 deg boom rib along x and cut its brim at the bed edge)."""
    spec = PARTS[name]
    cx, cy = bed_centre(spec["printer"])
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, name + ".stl")
        G.write_stl(path, G.transform(G.read_stl(os.path.join(G.PRINT, name + ".stl")), None, (cx, cy, 0.0)))
        return _slice([path], spec["printer"], spec["material"], out_path(name), stl_hash(name), arrange=0)


def slice_plate(plate):
    """Every placed copy as its own STL, so each stays its own object (own brim, cancellable)."""
    copies = dict(PT.PLATES[plate])
    with tempfile.TemporaryDirectory() as tmp:
        stls = []
        for name, k, x, y, angle in PT.layout(plate):
            path = os.path.join(tmp, PT.stl_name(name, k, copies[name]) + ".stl")
            G.write_stl(path, PT.placed_mesh(name, x, y, angle))
            stls.append(path)
        return _slice(stls, PT.PRINTER, "petg", PT.gcode_path(plate), PT.plate_hash(plate), arrange=0)


def expected_gcode():
    """Every G-code file the current print table and plates produce."""
    paths = [out_path(n) for n in PARTS] + [PT.gcode_path(p) for p in PT.PLATES]
    return {os.path.normcase(os.path.abspath(p)) for p in paths}


def main(names=None):
    full = not names
    names = names or sorted(PARTS) + list(PT.PLATES)
    failed = []
    for name in names:
        try:
            dst = slice_plate(name) if name in PT.PLATES else slice_part(name)
            print(f"sliced {name:22s} -> {os.path.relpath(dst, G.ROOT)} ({os.path.getsize(dst) // 1024} KB)")
        except Exception as exc:  # report every failure, keep slicing the rest
            failed.append(name)
            print(f"FAILED {name}: {exc}")
    if full:
        # A part that moved printer, or a dropped plate, would leave an old file behind to be printed.
        keep = expected_gcode()
        for path in glob.glob(os.path.join(G.ROOT, "gcode", "*", "*.gcode")):
            if os.path.normcase(os.path.abspath(path)) not in keep:
                os.remove(path)
                print(f"removed stray {os.path.relpath(path, G.ROOT)}")
    if failed:
        print(f"{len(failed)} files failed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        # The viewer manifest and tracker.md carry each file's sliced mass and time.
        import make_tracker
        import make_viewer
        make_viewer.main()
        make_tracker.main()
