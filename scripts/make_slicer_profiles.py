#!/usr/bin/env python3
"""Build self-contained OrcaSlicer settings files for the VTOL project.

Why: the stock presets use `inherits` chains (fdm_machine_common,
fdm_process_common, fdm_filament_pla...). The OrcaSlicer CLI rejected the
stock files with "setup params error" — possibly because it cannot resolve
those chains in CLI mode. These merged files have no `inherits` key, so the
CLI gets every value in one file.

Outputs (in ../slicer_profiles/):
  machine_kobra_s1.json, machine_kobra_x.json
  process_standard.json, process_lwpla_vase.json, process_lwpla_vase_x.json
  process_petg.json, process_petg_support.json (tree supports, build plate only)
  filament_lwpla.json, filament_petg.json

The process and filament bases need the OrcaSlicer Anycubic presets (set ORCA_PRESETS). The two
printers come from the installed Anycubic Slicer Next's own presets when they are there (set
ANYCUBIC_PRESETS), so the printer files follow the slicer the parts are sliced with. The PETG
variants are always re-derived from the committed process_standard.json.
"""
import json
import os
import sys

PRESETS = os.environ.get("ORCA_PRESETS", "/home/hatch/workspace/tools/squashfs-root/resources/profiles/Anycubic")
# Anycubic Slicer Next 2.0.0.3's S1 preset primes the nozzle with a purge line beside the bed before
# the first layer, which the older preset these files came from lacked (the start G-code is only
# the printer's G9111 macro, and the profiles print no skirt).
SLICER_PRESETS = os.environ.get("ANYCUBIC_PRESETS",
                                r"C:\Program Files\AnycubicSlicerNext\resources\profiles\Anycubic")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "slicer_profiles")

# LW-PLA foams more the slower it is extruded, so one flow calibration only holds over a
# narrow speed band. The wall speed cap and a 4 s minimum layer time keep every vase part
# between ~17 and 30 mm/s (with the stock 200 mm/s and 8 s, speed followed the perimeter:
# 10 mm/s on the ailerons, 55 mm/s on the wing roots). A single foamed 0.5 mm wall under
# full fan cools well inside 4 s.
VASE_SPEED = {"outer_wall_speed": "30"}
LWPLA_COOLING = {"slow_down_layer_time": ["4"]}
# The wing skins' internal webs are 0.06 mm slots that the vase wall runs into (skins.py). The
# stock 0.049 mm closing radius fills them in, and thin-wall detection (on in the stock S1
# preset, off in the X preset) cuts the section into islands at the 0.6 mm necks, so both
# printers use these values.
VASE_WEBS = {"slice_closing_radius": "0.01", "detect_thin_wall": "0"}
# Bed temperature, the same on every plate type the slicer offers: the plate type picks which of a
# filament's temperatures applies. The 1.3.3.3 CLI set every project to the cool plate, which the
# stock presets heat to 35 C for PLA and 60 C for PETG; 2.0.0.3 sets the textured PEI plate, and two
# of its six types (textured cool, supertack) stay at 35-40 C in every stock preset. LW-PLA makers
# ask for 50-60 C (colorFabb), and a single-wall skin up to 240 mm tall on a 10-120 mm footprint
# needs the grip; PETG gets 75 C, as in Anycubic's own Kobra S1 PETG preset for the textured PEI
# and smooth (hot) plates. check_parts.py reads every plate type's value back from the G-code.
PLATE_TYPES = ("cool", "eng", "hot", "textured", "textured_cool", "supertack")
LWPLA_BED_C, PETG_BED_C = 55, 75


def bed_temp(t):
    return {f"{plate}_plate_temp{layer}": [str(t)] for plate in PLATE_TYPES
            for layer in ("", "_initial_layer")}


LWPLA_BED = bed_temp(LWPLA_BED_C)
PETG_BED = bed_temp(PETG_BED_C)


def load(folder, name, root=None):
    with open(os.path.join(root or PRESETS, folder, name), encoding="utf-8") as f:
        return json.load(f)


def merged(folder, name, root=None):
    """Recursively resolve `inherits` (single string or list)."""
    data = load(folder, name, root)
    base = {}
    inh = data.get("inherits")
    if inh:
        parents = [inh] if isinstance(inh, str) else inh
        for p in parents:
            base.update(merged(folder, p + ".json", root))
    base.update({k: v for k, v in data.items() if k != "inherits"})
    return base


def write(name, data):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="\n") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {path} ({len(data)} keys)")


def machines(root):
    """Both printer files from the presets under `root`."""
    os.makedirs(OUT, exist_ok=True)
    for fname, preset in (("machine_kobra_s1.json", "Anycubic Kobra S1 0.4 nozzle.json"),
                          ("machine_kobra_x.json", "Anycubic Kobra X 0.4 nozzle.json")):
        m = merged("machine", preset, root)
        # The stock presets have 0 here; Anycubic Slicer Next 1.3.3.3 (Windows) rejects any
        # value outside 10-18 even with long retraction on cut disabled.
        m["retraction_distances_when_cut"] = ["18"]
        write(fname, m)


def main():
    machines(PRESETS)

    # Process: standard baseline, then variants. Process presets carry a
    # compatible_printers field, so each printer needs variants derived
    # from its OWN stock preset — an S1-derived process is rejected by
    # the Kobra X ("process not compatible with printer").
    std = merged("process", "0.20mm Standard @Anycubic Kobra S1 0.4 nozzle.json")
    std_x = merged("process", "0.20mm Standard @Anycubic Kobra X 0.4 nozzle.json")
    write("process_standard.json", std)

    # Open ends (bottom 0) so spars pass through the wing and equipment
    # reaches the fuselage; a wide outer brim holds the single-wall
    # outline to the bed on layer 1.
    vase_overrides = {
        "spiral_mode": "1",
        "wall_loops": "1",
        "sparse_infill_density": "0%",
        "top_shell_layers": "0",
        "bottom_shell_layers": "0",
        "brim_type": "outer_only",
        "brim_width": "8",
        **VASE_SPEED,
        **VASE_WEBS,
    }
    vase = dict(std)
    vase.update(vase_overrides)
    vase["name"] = "LW-PLA vase mode @VTOL (S1)"
    write("process_lwpla_vase.json", vase)
    vase_x = dict(std_x)
    vase_x.update(vase_overrides)
    vase_x["name"] = "LW-PLA vase mode @VTOL (X)"
    write("process_lwpla_vase_x.json", vase_x)

    # Filaments
    pla = merged("filament", "Anycubic Generic PLA.json")
    lwpla = dict(pla)
    lwpla.update({
        "name": "LW-PLA foaming @VTOL",
        "nozzle_temperature": ["235"],
        "filament_flow_ratio": ["0.55"],
        **LWPLA_COOLING,
    })
    write("filament_lwpla.json", lwpla)

    try:
        petg_fil = merged("filament", "Anycubic Generic PETG.json")
    except FileNotFoundError:
        print("no Anycubic Generic PETG.json; skipping filament_petg.json")
        return
    petg_fil["name"] = "PETG @VTOL"
    write("filament_petg.json", petg_fil)


def petg_variants():
    with open(os.path.join(OUT, "process_standard.json")) as f:
        std = json.load(f)
    petg = dict(std)
    # No brim, rather than the preset's auto brim, which follows the plate type and the slicer:
    # Anycubic Slicer Next 1.3.3.3's CLI took the Cool Plate and put brims on 17 parts, 2.0.0.3 takes
    # a textured PEI plate and put one on a single part. Parts that need one get it from the print
    # table (make_print_ready.py, `brim`), so every plate type and slicer prints the same. Holes in
    # bridged ceilings keep the stock handling here; the parts that need more get it from the print
    # table too (`slicer`; REPORT 11.9). Overhang walls keep their own label: the gate's over-air
    # check finds the walls it measures by it (check_parts.check_air).
    petg.update({"name": "PETG structural @VTOL", "wall_loops": "3", "sparse_infill_density": "15%",
                 "brim_type": "no_brim", "counterbore_hole_bridging": "none", "detect_overhang_wall": "1"})
    write("process_petg.json", petg)
    sup = dict(petg)
    sup.update({"name": "PETG structural + supports @VTOL", "enable_support": "1",
                "support_type": "tree(auto)", "support_on_build_plate_only": "1"})
    write("process_petg_support.json", sup)


def lwpla_tuning():
    """Apply the LW-PLA speed/cooling/web settings and both bed temperatures to the committed
    profiles (idempotent)."""
    vase = {**VASE_SPEED, **VASE_WEBS}
    for name, extra in (("process_lwpla_vase.json", vase), ("process_lwpla_vase_x.json", vase),
                        ("filament_lwpla.json", {**LWPLA_COOLING, **LWPLA_BED}),
                        ("filament_petg.json", PETG_BED)):
        path = os.path.join(OUT, name)
        with open(path) as f:
            data = json.load(f)
        data.update(extra)
        write(name, data)


if __name__ == "__main__":
    if os.path.isdir(PRESETS):
        main()
    else:
        print(f"Orca presets not found at {PRESETS}; keeping the committed base profiles")
    if os.path.isdir(SLICER_PRESETS):
        machines(SLICER_PRESETS)
    else:
        print(f"Anycubic Slicer Next presets not found at {SLICER_PRESETS}; keeping the committed printer files")
    lwpla_tuning()
    petg_variants()
