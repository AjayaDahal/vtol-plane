"""Slice every print-ready part with Anycubic Slicer Next (OrcaSlicer CLI works the same).

Set VTOL_SLICER to the slicer executable if it is not at the default Windows install path.
Output: gcode/<printer>_<lwpla|petg>/<part>.gcode, one copy per file (print `qty` copies).
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

import geom as G
from make_print_ready import PARTS

SLICER = os.environ.get("VTOL_SLICER", r"C:\Program Files\AnycubicSlicerNext\AnycubicSlicerNext.exe")
PROFILES = os.path.join(G.ROOT, "slicer_profiles")
MACHINE = {"s1": "machine_kobra_s1.json", "x": "machine_kobra_x.json"}
PROCESS = {("s1", "lwpla_vase"): "process_lwpla_vase.json", ("x", "lwpla_vase"): "process_lwpla_vase_x.json",
           ("s1", "petg"): "process_petg.json", ("s1", "petg_support"): "process_petg_support.json"}
FILAMENT = {"lwpla_vase": "filament_lwpla.json", "petg": "filament_petg.json", "petg_support": "filament_petg.json"}


def out_path(name):
    spec = PARTS[name]
    folder = f"{spec['printer']}_{'lwpla' if spec['material'].startswith('lwpla') else 'petg'}"
    return os.path.join(G.ROOT, "gcode", folder, name + ".gcode")


def slice_part(name):
    spec = PARTS[name]
    settings = [os.path.join(PROFILES, MACHINE[spec["printer"]]),
                os.path.join(PROFILES, PROCESS[(spec["printer"], spec["material"])])]
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [SLICER, "--slice", "0", "--arrange", "1", "--orient", "0", "--ensure-on-bed",
               "--datadir", os.path.join(tmp, "cfg"),
               "--load-settings", ";".join(settings),
               "--load-filaments", os.path.join(PROFILES, FILAMENT[spec["material"]]),
               "--outputdir", tmp, os.path.join(G.PRINT, name + ".stl")]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        found = glob.glob(os.path.join(tmp, "*.gcode"))
        if not found:
            tail = (run.stdout + run.stderr)[-1500:]
            raise RuntimeError(f"{name}: slicer produced no G-code (exit {run.returncode})\n{tail}")
        dst = out_path(name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(found[0], dst)
    return dst


def main(names=None):
    names = names or sorted(PARTS)
    failed = []
    for name in names:
        try:
            dst = slice_part(name)
            print(f"sliced {name:18s} -> {os.path.relpath(dst, G.ROOT)} ({os.path.getsize(dst) // 1024} KB)")
        except Exception as exc:  # report every failure, keep slicing the rest
            failed.append(name)
            print(f"FAILED {name}: {exc}")
    if failed:
        print(f"{len(failed)} parts failed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
