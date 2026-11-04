"""Complete slicer projects: every print job of a printer in one Anycubic Slicer Next project, one
named plate per job, in print order (open one, pick a plate, slice it, send it):

- 3mf/complete_project_kobra_x_lwpla.3mf: the Kobra X with every LW-PLA skin, one vase part per
  plate (a vase print holds one object per bed), the test prints first.
- 3mf/complete_project_kobra_s1_petg.3mf: the Kobra S1 with the seven PETG plates (plates.py).

A slicer project holds one printer, so there is one per printer. Each is assembled from the jobs'
own 3MF projects (slice_all.py), whose G-code the gate checks: their objects, placements and
settings are copied unchanged, each job onto its own plate, and the gate checks that the projects
are what this script builds from them. The slicer's CLI cannot assemble such a project itself
(--load-assemble-list crashed Anycubic Slicer Next 1.3.3.3), and any plate name crashes its CLI
(1.3.3.3 and 2.0.0.3; the GUI writes and reads them). `--verify` therefore slices a copy with the
names blanked, plate by plate as the GUI does, and checks that each plate prints what its job's
G-code in gcode/ prints.

Run: python scripts/make_projects.py [--verify]
"""
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from xml.sax.saxutils import escape

import numpy as np

import geom as G
import make_tracker
import plates as PT
import slice_all as SA
from make_print_ready import PARTS

PROJECTS = {"x": ("complete_project_kobra_x_lwpla.3mf", "lwpla_vase"),
            "s1": ("complete_project_kobra_s1_petg.3mf", "petg")}
META = "vtol_jobs_sha256"
# Plates waiting for the 3S build (PLAN_3S.md, tracker.md): named so they are not printed early.
# Empty this when the plan is built in.
HOLD = {"petg_6_fuselage_tail", "petg_7_pods_yokes"}
TESTS = {"wing_tip_r": "flow test", "tip_fairing_r": "closing-tip test", "wing_mid_r": "web check"}
GAP = 0.2            # the slicer lays plates out 1.2 bed widths apart (PartPlateList)
DATE = (2026, 1, 1, 0, 0, 0)


def project_path(printer):
    return os.path.join(G.ROOT, "3mf", PROJECTS[printer][0])


def jobs(printer):
    """[(plate name, job name, G-code path, stamp, object names)] in print order. The plate name is
    what the slicer shows on the plate."""
    out = []
    if printer == "x":
        first = [n for n in make_tracker.FIRST if n in PARTS]
        names = [n for n in sorted(PARTS, key=lambda n: (n not in first, first.index(n) if n in first else 0, n))
                 if PARTS[n]["printer"] == "x"]
        for name in names:
            qty = PARTS[name]["qty"]
            for k in range(1, qty + 1):
                notes = ([TESTS[name]] if name in TESTS else []) + ([f"{k} of {qty}"] if qty > 1 else [])
                label = f"LW-PLA {len(out) + 1:02d} - {name}" + (f" ({', '.join(notes)})" if notes else "")
                out.append((label, name, SA.out_path(name), SA.stl_hash(name), [name + ".stl"]))
    else:
        for i, (plate, items) in enumerate(PT.PLATES.items(), start=1):
            copies = dict(items)
            objs = [PT.stl_name(n, k, copies[n]) + ".stl" for n, k, _, _, _ in PT.layout(plate)]
            theme = re.sub(r"^petg_\d+_", "", plate).replace("_", " ")
            label = f"PETG {i} - {theme} ({len(objs)} parts)" + (" - ON HOLD (3S plan)" if plate in HOLD else "")
            out.append((label, plate, PT.gcode_path(plate), PT.plate_hash(plate), objs))
    return out


def project_stamp(printer):
    lines = [f"{label}:{stamp}" for label, _, _, stamp, _ in jobs(printer)]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def describe(printer, plan):
    """The project's title and description: the plates in print order and what is on each."""
    what = "Kobra X, LW-PLA vase skins" if printer == "x" else "Kobra S1, PETG plates"
    title = f"VTOL plane - {what} ({len(plan)} plates)"
    if printer == "x":
        body = "; ".join(label for label, *_ in plan)
    else:
        body = "; ".join(f"{label}: " + ", ".join(n if c == 1 else f"{c}x {n}" for n, c in PT.PLATES[job])
                         for label, job, *_ in plan)
    return title, (f"One plate per print job, in print order (tracker.md): {body}. "
                   "Slice a plate, check the preview, send it (SLICING.md).")


def plate_grid(printer, count):
    """Each plate's origin in the project, as the slicer lays plates out: in rows of
    round(sqrt(n)) columns (one more if sqrt(n) rounds down), 1.2 bed sizes apart."""
    with open(os.path.join(SA.PROFILES, SA.MACHINE[printer])) as f:
        area = [[float(c) for c in p.split("x")] for p in json.load(f)["printable_area"]]
    w = max(p[0] for p in area) - min(p[0] for p in area)
    d = max(p[1] for p in area) - min(p[1] for p in area)
    root = math.sqrt(count)
    cols = int(round(root)) + (1 if root > round(root) else 0)
    return [((i % cols) * w * (1 + GAP), -(i // cols) * d * (1 + GAP)) for i in range(count)], (w, d)


def _read(path):
    """A job's 3MF: [(object name, mesh file text, component transform, item transform,
    model_settings block)], the zip's other files we reuse, and its project settings."""
    with zipfile.ZipFile(path) as z:
        model = z.read("3D/3dmodel.model").decode()
        ms = z.read("Metadata/model_settings.config").decode()
        items = dict(re.findall(r'<item objectid="(\d+)"[^>]*?transform="([^"]+)"', model))
        blocks = {m.group(1): m.group(0) for m in re.finditer(r'<object id="(\d+)">.*?</object>', ms, re.S)}
        objs = []
        for oid, comp in re.findall(r'<object id="(\d+)"[^>]*type="model">\s*<components>(.*?)</components>',
                                    model, re.S):
            path3, sub_id, transform = re.search(
                r'p:path="([^"]+)" objectid="(\d+)"[^>]*?transform="([^"]+)"', comp).groups()
            name = re.search(r'<metadata key="name" value="([^"]+)"', blocks[oid]).group(1)
            objs.append(dict(name=name, mesh=z.read(path3.lstrip("/")).decode(), sub_id=sub_id,
                             component=transform, item=items[oid], block=blocks[oid]))
        files = {n: z.read(n) for n in z.namelist() if n.startswith("Metadata/") and n.endswith(".png")}
        shared = {n: z.read(n) for n in ("[Content_Types].xml", "_rels/.rels", "Metadata/slice_info.config")}
        header = model[:model.index("<resources>")]
        settings = z.read("Metadata/project_settings.config")
    return objs, files, shared, header, settings


def _shift(transform, dx, dy):
    v = transform.split()
    v[9], v[10] = repr(float(v[9]) + dx), repr(float(v[10]) + dy)
    return " ".join(v)


def entries(printer):
    """One complete project's files, {name: bytes}, in the order they are written."""
    plan = jobs(printer)
    origins, _ = plate_grid(printer, len(plan))
    entries, rels, resources, items, blocks, plates = {}, [], [], [], [], []
    shared = header = settings = None
    k = 0
    for p, ((label, job, gcode, _, _), (ox, oy)) in enumerate(zip(plan, origins), start=1):
        objs, files, sh, hd, st = _read(SA.path_3mf(gcode))
        if settings is None:
            shared, header, settings = sh, hd, st
        elif st != settings:
            raise RuntimeError(f"{job}: its 3MF's settings differ from the project's first job")
        # The job's thumbnails, if its 3MF has any (Anycubic Slicer Next 2.0's CLI writes none; the
        # GUI draws them when it slices).
        thumbs = []
        for key, png in (("thumbnail_file", "plate_{}.png"), (None, "plate_{}_small.png"),
                         ("thumbnail_no_light_file", "plate_no_light_{}.png"), ("top_file", "top_{}.png"),
                         ("pick_file", "pick_{}.png")):
            data = files.get("Metadata/" + png.format(1))
            if data:
                entries["Metadata/" + png.format(p)] = data
                if key:
                    thumbs.append(f'    <metadata key="{key}" value="Metadata/{png.format(p)}"/>\n')
        instances = []
        for o in objs:
            k += 1
            top, sub = 2 * k, 2 * k - 1
            path3 = f"/3D/Objects/{o['name']}_{k}.model"
            mesh = re.sub(r'<object id="\d+" p:UUID="[^"]+"',
                          f'<object id="{sub}" p:UUID="{k:04x}0000-81cb-4c03-9d28-80fed5dfa1dc"', o["mesh"], count=1)
            entries[path3.lstrip("/")] = mesh.encode()
            rels.append(f' <Relationship Target="{path3}" Id="rel-{k}" '
                        f'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>')
            resources.append(
                f'  <object id="{top}" p:UUID="{k:08x}-61cb-4c03-9d28-80fed5dfa1dc" type="model">\n'
                f'   <components>\n'
                f'    <component p:path="{path3}" objectid="{sub}" p:UUID="{k:04x}0000-b206-40ff-9872-83e8017abed1" '
                f'transform="{o["component"]}"/>\n'
                f'   </components>\n  </object>')
            items.append(f'  <item objectid="{top}" p:UUID="{top:08x}-b1ec-4553-aec9-835e5b724bb4" '
                         f'transform="{_shift(o["item"], ox, oy)}" printable="1"/>')
            block = re.sub(r'<object id="\d+">', f'<object id="{top}">', o["block"], count=1)
            blocks.append("  " + re.sub(r'<part id="\d+"', f'<part id="{sub}"', block, count=1))
            instances.append(f'    <model_instance>\n      <metadata key="object_id" value="{top}"/>\n'
                             f'      <metadata key="instance_id" value="0"/>\n'
                             f'      <metadata key="identify_id" value="{1000 + k}"/>\n    </model_instance>')
        name = escape(label, {'"': "&quot;"})
        plates.append(
            f'  <plate>\n    <metadata key="plater_id" value="{p}"/>\n'
            f'    <metadata key="plater_name" value="{name}"/>\n'
            f'    <metadata key="locked" value="false"/>\n'
            + "".join(thumbs) + "\n".join(instances) + "\n  </plate>")
    header = re.sub(r'\s*<metadata name="vtol_stl_sha256">[^<]*</metadata>', "", header)
    header = header.replace("<resources>", "")
    title, description = describe(printer, plan)
    header = re.sub(r'<metadata name="Title">[^<]*</metadata>', f'<metadata name="Title">{escape(title)}</metadata>', header)
    header = re.sub(r'<metadata name="Description">[^<]*</metadata>',
                    f'<metadata name="Description">{escape(description)}</metadata>', header)
    header = header.rstrip() + f'\n <metadata name="{META}">{project_stamp(printer)}</metadata>\n'
    entries["3D/3dmodel.model"] = (header + " <resources>\n" + "\n".join(resources) + "\n </resources>\n"
                                   ' <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">\n' + "\n".join(items) +
                                   "\n </build>\n</model>\n").encode()
    entries["3D/_rels/3dmodel.model.rels"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        + "\n".join(rels) + "\n</Relationships>\n").encode()
    entries["Metadata/model_settings.config"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
                                                 + "\n".join(blocks) + "\n" + "\n".join(plates) +
                                                 "\n  <assemble>\n  </assemble>\n</config>\n").encode()
    entries["Metadata/project_settings.config"] = settings
    entries.update(shared)
    order = (["[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model", "3D/_rels/3dmodel.model.rels"] +
             sorted(n for n in entries if n.startswith("3D/Objects/")) +
             ["Metadata/project_settings.config", "Metadata/model_settings.config", "Metadata/slice_info.config"] +
             sorted(n for n in entries if n.endswith(".png")))
    return {name: entries[name] for name in order}


def build(printer):
    """Write one complete project; return its path."""
    files = entries(printer)
    dst = project_path(printer)
    tmp = dst + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    os.replace(tmp, dst)
    return dst


def _unnamed(src, dst):
    """A copy of a project with its plate names blanked: any plate name crashes the slicer's CLI.
    Nothing else changes."""
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for info in zi.infolist():
            data = zi.read(info.filename)
            if info.filename == "Metadata/model_settings.config":
                data = re.sub(rb'(<metadata key="plater_name" value=")[^"]*"', rb'\1"', data)
            zo.writestr(info, data)


def _profile(path):
    """Per layer: (Z, extruded length, XY box of the extrusions); the objects' outlines by name;
    the filament mass and the estimated time (s)."""
    layers, objs, z, e, box = [], {}, None, 0.0, None
    x = y = 0.0
    mass = secs = None
    obj_re = re.compile(r"EXCLUDE_OBJECT_DEFINE NAME=(\S+) CENTER=\S+ POLYGON=(\[\[.*\]\])")
    with open(path, errors="replace") as f:
        for line in f:
            if line.startswith(";Z:"):
                if z is not None:
                    layers.append((z, e, box))
                z, e, box = float(line[3:]), 0.0, None
            elif line.startswith("; total filament used [g] ="):
                mass = float(line.split("=")[1])
            elif line.startswith("; estimated printing time (normal mode) ="):
                t = line.split("=")[1]
                secs = sum(int(v) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[u] for v, u in re.findall(r"(\d+)([dhms])", t))
            elif line.startswith("EXCLUDE_OBJECT_DEFINE"):
                m = obj_re.match(line)
                if m:
                    objs[re.sub(r"_id_\d+_copy_\d+$", "", m.group(1))] = json.loads(m.group(2))
            elif line.startswith("G1") or line.startswith("G0"):
                m = dict(re.findall(r"([XYE])(-?[\d.]+)", line))
                nx, ny = float(m.get("X", x)), float(m.get("Y", y))
                if "E" in m and float(m["E"]) > 0 and ("X" in m or "Y" in m):
                    e += float(m["E"])
                    pts = ((x, y), (nx, ny))
                    lo = [min(p[i] for p in pts) for i in (0, 1)]
                    hi = [max(p[i] for p in pts) for i in (0, 1)]
                    box = (lo, hi) if box is None else ([min(box[0][i], lo[i]) for i in (0, 1)],
                                                        [max(box[1][i], hi[i]) for i in (0, 1)])
                x, y = nx, ny
    if z is not None:
        layers.append((z, e, box))
    return layers, objs, mass, secs


TOL_BOX, TOL_E = 0.21, 0.1   # mm: a layer's extents; mm of filament on a layer (or 0.5 %)


def same_print(a, b):
    """(why G-code a does not print what b prints, or None; the worst layer-extent and extrusion
    differences found). The same layers, the same extrusion on every layer inside the same box,
    the same objects and outlines (0.01 mm), and the same filament mass and time. A plate on a
    project is offset from its job's bed: that moves some coordinates by one unit in the last
    digit (0.001 mm), and vase-mode smoothing turns that into up to 0.17 mm (Anycubic Slicer Next
    2.0.0.3, the same on every run) on a layer where an outline closes to a fin: the tip fairings'
    tops, the ruddervators' trailing edges, the top of fuse_1. Half the 0.42 mm line is allowed. A
    misplaced part moves by millimetres, and a changed setting changes every layer by per cent."""
    la, oa, ma, ta = _profile(a)
    lb, ob, mb, tb = _profile(b)
    worst_box = worst_e = 0.0
    if [round(z, 3) for z, _, _ in la] != [round(z, 3) for z, _, _ in lb]:
        return f"{len(la)} layers against {len(lb)}", worst_box, worst_e
    for (z, ea, ba), (_, eb, bb) in zip(la, lb):
        worst_e = max(worst_e, abs(ea - eb))
        if abs(ea - eb) > max(0.005 * eb, TOL_E):
            return f"layer Z{z}: {ea:.2f} mm of filament against {eb:.2f}", worst_box, worst_e
        if (ba is None) != (bb is None):
            return f"layer Z{z}: extrudes on one side only", worst_box, worst_e
        if ba:
            dev = max(abs(u - v) for p, q in zip(ba, bb) for u, v in zip(p, q))
            worst_box = max(worst_box, dev)
            if dev > TOL_BOX:
                return f"layer Z{z}: extrusions in {ba}, against {bb}", worst_box, worst_e
    if sorted(oa) != sorted(ob):
        return f"objects {sorted(oa)} against {sorted(ob)}", worst_box, worst_e
    for name in oa:
        pa, pb = np.array(oa[name]), np.array(ob[name])
        if pa.shape != pb.shape or np.abs(pa - pb).max() > 0.01:
            return f"{name}: outline moved", worst_box, worst_e
    if ma is None or mb is None or abs(ma - mb) > 0.01:
        return f"{ma} g against {mb} g", worst_box, worst_e
    if ta is None or tb is None or abs(ta - tb) > max(0.005 * tb, 2):
        return f"{ta} s against {tb} s", worst_box, worst_e
    return None, worst_box, worst_e


def verify(printer):
    """Slice each plate of the project on its own, as the GUI slices a plate, from a copy with the
    plate names blanked (_unnamed), and check it prints what its job's G-code prints. One run over
    every plate was not repeatable in Anycubic Slicer Next 1.3.3.3 (a few per cent more or less
    infill on some layers from run to run, and once two plates skipped while it reported success);
    one plate per run is repeatable to the byte."""
    plan = jobs(printer)
    bad, same, worst = [], 0, [0.0, 0.0]
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, os.path.basename(project_path(printer)))
        _unnamed(project_path(printer), src)
        for p, (label, job, gcode, _, _) in enumerate(plan, start=1):
            out = os.path.join(tmp, f"p{p}")
            os.makedirs(out)
            run = subprocess.run([SA.SLICER, "--slice", str(p), "--datadir", os.path.join(out, "cfg"),
                                  "--outputdir", out, src], capture_output=True, text=True, timeout=3600)
            found = glob.glob(os.path.join(out, "*.gcode"))
            if len(found) != 1:
                bad.append(f"plate {p} ({label}): {len(found)} G-code files (exit {run.returncode})")
                continue
            why, dev_box, dev_e = same_print(found[0], gcode)
            worst = [max(worst[0], dev_box), max(worst[1], dev_e)]
            if why:
                bad.append(f"plate {p} ({label}) against {os.path.relpath(gcode, G.ROOT)}: {why}")
            else:
                same += 1
    return same, len(plan), bad, worst


def main(check=False):
    failed = []
    for printer in PROJECTS:
        dst = build(printer)
        line = f"wrote {os.path.relpath(dst, G.ROOT)}: {len(jobs(printer))} plates, {os.path.getsize(dst) // 1024} KB"
        if check:
            same, n, bad, worst = verify(printer)
            line += (f"; sliced on its own, {same}/{n} plates print what their jobs' G-code prints "
                     f"(worst layer: extents {worst[0]:.3f} mm, extrusion {worst[1]:.3f} mm of filament)")
            failed += bad
        print(line)
    for b in failed:
        print("FAILED", b)
    return not failed


if __name__ == "__main__":
    sys.exit(0 if main("--verify" in sys.argv[1:]) else 1)
