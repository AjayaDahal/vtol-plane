"""Slice every print-ready part, and every PETG plate, with Anycubic Slicer Next (OrcaSlicer CLI
works the same).

Set VTOL_SLICER to the slicer executable if it is not at the default Windows install path.
Each print job is first laid out as a project 3MF, which is then sliced on its own:
- 3mf/<printer>_<lwpla|petg>/<part>.3mf and 3mf/s1_petg_plates/<plate>.3mf: open one in the
  slicer to send the job to the printer. It carries the parts where they print and every
  setting (printer, process, filament), so it slices to the G-code below.
- gcode/<printer>_<lwpla|petg>/<part>.gcode, one copy per file (print `qty` copies), and
  gcode/s1_petg_plates/<plate>.gcode, the PETG parts laid out on shared beds (plates.py).
Each G-code file ends with a `; vtol_stl_sha256 = ...` comment naming the STL it was sliced from
(for a plate, a hash of its parts' STLs and places), and its 3MF carries the same hash as
metadata, so check_parts.py can tell stale files from current (git does not keep file times).
Run on its own (`python slice_all.py [part or plate ...]`), it then refreshes
viewer/manifest.json and tracker.md, which carry each file's sliced mass and time, and the two
complete projects (make_projects.py).
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

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
META_3MF = "vtol_stl_sha256"


def stl_hash(name):
    with open(os.path.join(G.PRINT, name + ".stl"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def out_path(name):
    spec = PARTS[name]
    folder = f"{spec['printer']}_{'lwpla' if spec['material'].startswith('lwpla') else 'petg'}"
    return os.path.join(G.ROOT, "gcode", folder, name + ".gcode")


def path_3mf(gcode):
    """The project 3MF a G-code file is sliced from: 3mf/<same folder>/<same name>.3mf."""
    folder = os.path.basename(os.path.dirname(gcode))
    return os.path.join(G.ROOT, "3mf", folder, os.path.splitext(os.path.basename(gcode))[0] + ".3mf")


def preset_names(printer, material):
    """The printer, process and filament preset names a job's 3MF carries."""
    names = []
    for fname in (MACHINE[printer], PROCESS[(printer, material)], FILAMENT[material]):
        with open(os.path.join(PROFILES, fname)) as f:
            names.append(json.load(f)["name"])
    return tuple(names)


def _run(cmd, what):
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    return run, f"{what} (exit {run.returncode})\n{(run.stdout + run.stderr)[-1500:]}"


def _set_brims(project, brims):
    """Give each object named in `brims` ({STL name: mm}) its own outer brim in the project 3MF, as
    per-object settings: the slicer applies them on any plate and shows them on the object."""
    with zipfile.ZipFile(project) as z:
        files = [(info, z.read(info.filename)) for info in z.infolist()]
    with zipfile.ZipFile(project, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in files:
            if info.filename == "Metadata/model_settings.config":
                text = data.decode()
                for stl, width in brims.items():
                    head = (r'(<object id="\d+">\s*<metadata key="name" value="' + re.escape(stl) +
                            r'"/>\s*<metadata key="extruder" value="\d+"/>)')
                    text, n = re.subn(head, r'\1\n    <metadata key="brim_type" value="outer_only"/>'
                                      rf'\n    <metadata key="brim_width" value="{width:g}"/>', text, count=1)
                    if n != 1:
                        raise RuntimeError(f"{stl}: no such object in {os.path.basename(project)}")
                data = text.encode()
            z.writestr(info, data)


def _slice(stls, printer, material, dst, stamp, arrange, brims=None):
    """Lay `stls` out on one bed as a project 3MF (--arrange 0 keeps each STL where it is), give the
    parts in `brims` their brim, then slice that 3MF on its own, with a fresh settings folder: the
    G-code is what opening the 3MF in the slicer and slicing it gives, and the 3MF must carry every
    setting itself."""
    settings = [os.path.join(PROFILES, MACHINE[printer]), os.path.join(PROFILES, PROCESS[(printer, material)])]
    project = path_3mf(dst)
    with tempfile.TemporaryDirectory() as tmp:
        name3 = os.path.basename(project)   # the slicer writes it into --outputdir
        _, log = _run([SLICER, "--arrange", str(arrange), "--orient", "0", "--ensure-on-bed",
                       "--datadir", os.path.join(tmp, "cfg"),
                       "--load-settings", ";".join(settings),
                       "--load-filaments", os.path.join(PROFILES, FILAMENT[material]),
                       "--metadata-name", META_3MF, "--metadata-value", stamp,
                       "--export-3mf", name3, "--outputdir", tmp, *stls], f"{name3}: no 3MF written")
        made = os.path.join(tmp, name3)
        if not os.path.exists(made):
            raise RuntimeError(log)
        if brims:
            _set_brims(made, brims)
        sliced = os.path.join(tmp, "sliced")
        os.makedirs(sliced)
        _, log = _run([SLICER, "--slice", "0", "--arrange", "0", "--orient", "0",
                       "--datadir", os.path.join(tmp, "cfg_3mf"), "--outputdir", sliced, made],
                      f"{os.path.basename(dst)}: slicing the 3MF")
        found = glob.glob(os.path.join(sliced, "*.gcode"))
        if len(found) != 1:
            raise RuntimeError(f"{len(found)} G-code files from {log}")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(found[0], dst)
        os.makedirs(os.path.dirname(project), exist_ok=True)
        shutil.move(made, project)
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
        brims = {name + ".stl": spec["brim"]} if spec["brim"] else None
        return _slice([path], spec["printer"], spec["material"], out_path(name), stl_hash(name), arrange=0,
                      brims=brims)


def slice_plate(plate):
    """Every placed copy as its own STL, so each stays its own object (own brim, cancellable)."""
    copies = dict(PT.PLATES[plate])
    with tempfile.TemporaryDirectory() as tmp:
        stls, brims = [], {}
        for name, k, x, y, angle in PT.layout(plate):
            path = os.path.join(tmp, PT.stl_name(name, k, copies[name]) + ".stl")
            G.write_stl(path, PT.placed_mesh(name, x, y, angle))
            stls.append(path)
            if PARTS[name]["brim"]:
                brims[os.path.basename(path)] = PARTS[name]["brim"]
        return _slice(stls, PT.PRINTER, "petg", PT.gcode_path(plate), PT.plate_hash(plate), arrange=0, brims=brims)


def expected_gcode():
    """Every G-code file the current print table and plates produce."""
    paths = [out_path(n) for n in PARTS] + [PT.gcode_path(p) for p in PT.PLATES]
    return {os.path.normcase(os.path.abspath(p)) for p in paths}


def expected_3mf():
    """Every 3MF project the current print table and plates produce."""
    paths = [out_path(n) for n in PARTS] + [PT.gcode_path(p) for p in PT.PLATES]
    return {os.path.normcase(os.path.abspath(path_3mf(p))) for p in paths}


def main(names=None):
    full = not names
    names = names or sorted(PARTS) + list(PT.PLATES)
    failed = []
    for name in names:
        try:
            dst = slice_plate(name) if name in PT.PLATES else slice_part(name)
            print(f"sliced {name:22s} -> {os.path.relpath(dst, G.ROOT)} ({os.path.getsize(dst) // 1024} KB) "
                  f"and {os.path.relpath(path_3mf(dst), G.ROOT)}")
        except Exception as exc:  # report every failure, keep slicing the rest
            failed.append(name)
            print(f"FAILED {name}: {exc}")
    if full:
        # A part that moved printer, or a dropped plate, would leave an old file behind to be printed.
        for keep, pattern in ((expected_gcode(), ("gcode", "*", "*.gcode")), (expected_3mf(), ("3mf", "*", "*.3mf"))):
            for path in glob.glob(os.path.join(G.ROOT, *pattern)):
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
        # The viewer manifest and tracker.md carry each file's sliced mass and time, and the
        # complete projects are assembled from the job 3MFs.
        import make_projects
        import make_tracker
        import make_viewer
        make_viewer.main()
        make_tracker.main()
        try:
            make_projects.main()
        except Exception as exc:  # e.g. a job 3MF missing after a failed slice; the gate reports it
            print(f"complete projects not rebuilt: {exc}")
