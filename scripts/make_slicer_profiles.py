#!/usr/bin/env python3
"""Build self-contained OrcaSlicer settings files for the VTOL project.

Why: the stock presets use `inherits` chains (fdm_machine_common,
fdm_process_common, fdm_filament_pla...). The OrcaSlicer CLI rejected the
stock files with "setup params error" — possibly because it cannot resolve
those chains in CLI mode. These merged files have no `inherits` key, so the
CLI gets every value in one file.

Outputs (in ../slicer_profiles/):
  machine_kobra_s1.json, machine_kobra_x.json
  process_standard.json, process_lwpla_vase.json
  process_petg.json, process_petg_solid.json (100% infill, motor mounts)
  filament_lwpla.json, filament_petg.json
"""
import json
import os
import sys

PRESETS = "/home/hatch/workspace/tools/squashfs-root/resources/profiles/Anycubic"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "slicer_profiles")


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
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {path} ({len(data)} keys)")


def main():
    os.makedirs(OUT, exist_ok=True)

    # Machines
    write("machine_kobra_s1.json",
          merged("machine", "Anycubic Kobra S1 0.4 nozzle.json"))
    write("machine_kobra_x.json",
          merged("machine", "Anycubic Kobra X 0.4 nozzle.json"))

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
    }
    vase = dict(std)
    vase.update(vase_overrides)
    vase["name"] = "LW-PLA vase mode @VTOL (S1)"
    write("process_lwpla_vase.json", vase)
    vase_x = dict(std_x)
    vase_x.update(vase_overrides)
    vase_x["name"] = "LW-PLA vase mode @VTOL (X)"
    write("process_lwpla_vase_x.json", vase_x)

    petg = dict(std)
    petg.update({
        "name": "PETG structural @VTOL",
        "wall_loops": "3",
        "sparse_infill_density": "20%",
    })
    write("process_petg.json", petg)

    solid = dict(petg)
    solid.update({
        "name": "PETG solid @VTOL (motor mounts)",
        "sparse_infill_density": "100%",
    })
    write("process_petg_solid.json", solid)

    # Filaments
    pla = merged("filament", "Anycubic Generic PLA.json")
    lwpla = dict(pla)
    lwpla.update({
        "name": "LW-PLA foaming @VTOL",
        "nozzle_temperature": ["235"],
        "filament_flow_ratio": ["0.55"],
    })
    write("filament_lwpla.json", lwpla)

    try:
        petg_fil = merged("filament", "Anycubic Generic PETG.json")
    except FileNotFoundError:
        print("no Anycubic Generic PETG.json; skipping filament_petg.json")
        return
    petg_fil["name"] = "PETG @VTOL"
    write("filament_petg.json", petg_fil)


if __name__ == "__main__":
    main()
