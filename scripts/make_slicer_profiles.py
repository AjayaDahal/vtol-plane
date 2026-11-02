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

The base files need the OrcaSlicer Anycubic presets (set ORCA_PRESETS); the PETG
variants are always re-derived from the committed process_standard.json.
"""
import json
import os
import sys

PRESETS = os.environ.get("ORCA_PRESETS", "/home/hatch/workspace/tools/squashfs-root/resources/profiles/Anycubic")
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


def load(folder, name):
    with open(os.path.join(PRESETS, folder, name)) as f:
        return json.load(f)


def merged(folder, name, seen=None):
    """Recursively resolve `inherits` (single string or list)."""
    data = load(folder, name)
    base = {}
    inh = data.get("inherits")
    if inh:
        parents = [inh] if isinstance(inh, str) else inh
        for p in parents:
            base.update(merged(folder, p + ".json"))
    base.update({k: v for k, v in data.items() if k != "inherits"})
    return base


def write(name, data):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="\n") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {path} ({len(data)} keys)")


def main():
    os.makedirs(OUT, exist_ok=True)

    # Machines
    write("machine_kobra_s1.json",
          merged("machine", "Anycubic Kobra S1 0.4 nozzle.json"))
    # The stock X preset has 0 here; Anycubic Slicer Next 1.3.3.3 (Windows) rejects any
    # value outside 10-18 even with long retraction on cut disabled.
    mx = merged("machine", "Anycubic Kobra X 0.4 nozzle.json")
    mx["retraction_distances_when_cut"] = ["18"]
    write("machine_kobra_x.json", mx)

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
    petg.update({"name": "PETG structural @VTOL", "wall_loops": "3", "sparse_infill_density": "15%"})
    write("process_petg.json", petg)
    sup = dict(petg)
    sup.update({"name": "PETG structural + supports @VTOL", "enable_support": "1",
                "support_type": "tree(auto)", "support_on_build_plate_only": "1"})
    write("process_petg_support.json", sup)


def lwpla_tuning():
    """Apply the LW-PLA speed/cooling/web settings to the committed profiles (idempotent)."""
    vase = {**VASE_SPEED, **VASE_WEBS}
    for name, extra in (("process_lwpla_vase.json", vase), ("process_lwpla_vase_x.json", vase),
                        ("filament_lwpla.json", LWPLA_COOLING)):
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
    lwpla_tuning()
    petg_variants()
