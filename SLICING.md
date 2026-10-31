# Slicing Setup — Kobra S1 + Kobra X (v0.2, work in progress)

## Toolchain (installed, in home so it survives VM replacement)

Primary: **Anycubic Slicer Next** — Anycubic's own slicer, built on
OrcaSlicer, with native Kobra S1 / Kobra X profiles. This is the tool
the project asked for; OrcaSlicer below is the fallback.

- Anycubic Slicer Next 2.0.0.5 AppImage:
  `~/workspace/tools/anycubic/AnycubicSlicer.AppImage`
  (extracted to `~/workspace/tools/anycubic/squashfs-root/`,
  binary `bin/AnycubicSlicerNext`).
- Note: Anycubic's official Linux distribution is a .deb (Ubuntu
  24.04 only) from anycubic.com/slicerNextDownload; this AppImage is
  a community repackage of the official 2.0.06 .deb, used here
  because the VM cannot run the .deb installer flow while apt is
  locked. For your own PC, take the .deb from the official page.
- Native presets confirmed inside: "Anycubic Kobra S1" and
  "Anycubic Kobra X" machine models.

Fallback: OrcaSlicer 2.4.2 AppImage:
`~/workspace/tools/OrcaSlicer.AppImage`
(extracted to `~/workspace/tools/squashfs-root/`).
OrcaSlicer also ships Kobra S1 / Kobra X presets, and its settings
system is identical, so all profiles below transfer between the two.

## Host libraries (do NOT survive VM replacement)

OrcaSlicer's AppImage needs host OpenGL/EGL/GStreamer/WebKit libs.
Re-run after any VM reset:

```
bash ~/workspace/tools/setup_orca_libs.sh
```

Note: right after a VM reset the system runs its own package-replay
(`apt-get update` holding the apt lock). If the script fails on the
lock, wait a few minutes and retry — the replay also restores
previously installed packages on its own.

## Part orientation

- Wing sections: already span-vertical (span = Z), chord = X. Print
  as-is, standing.
- Fuselage sections: length = X in the STL. Rotate 90° about Y so
  length becomes vertical (Z) before slicing (vase mode spirals up
  the length).
- V-tail panel: span = Z already. Print as-is, twice, mirrored.

## Profiles (starting points — tune with a test section first)

- LW-PLA airframe (wings, fuselage, tail): vase mode (spiral),
  1 wall, 0.2 mm layers, ~235 °C, flow ~55%, no infill, no top
  layers. Calibrate flow on one wing section before batch printing.
- PETG structural (nacelles, booms, mounts): 3 walls, 20% infill;
  motor mounts 100% infill. PETG/ASA parts go to the enclosed S1.
- Printer split: LW-PLA sections alternate S1/X; PETG parts on S1.

## Profiles (self-contained, in `slicer_profiles/`)

Built by `scripts/make_slicer_profiles.py` from OrcaSlicer's stock
presets with all `inherits` chains merged in, so the CLI gets every
value in one file:

- `machine_kobra_s1.json`, `machine_kobra_x.json`
- `process_standard.json` (0.20 mm baseline)
- `process_lwpla_vase.json` (spiral mode, 1 wall, 0% infill, 0 top
  layers, 3 bottom layers, 0.2 mm)
- `process_petg.json` (3 walls, 20% infill), `process_petg_solid.json`
  (100% infill, motor mounts)
- `filament_lwpla.json` (235 °C, flow 0.55), `filament_petg.json`

## CLI command template (not yet proven — see Status)

```
LD_LIBRARY_PATH=~/workspace/tools/sysroot/usr/lib/x86_64-linux-gnu:~/workspace/tools/anycubic/squashfs-root/usr/lib \
  ~/workspace/tools/anycubic/squashfs-root/bin/AnycubicSlicerNext --slice 0 \
  --datadir /tmp/anycubic_cfg \
  --load-settings "slicer_profiles/machine_kobra_s1.json;slicer_profiles/process_lwpla_vase.json" \
  --load-filaments "slicer_profiles/filament_lwpla.json" \
  --outputdir gcode/ parts/wing_root.stl
```

(Run the binary directly with the sysroot on LD_LIBRARY_PATH instead
of AppRun: AppRun's own OpenGL check fails when the host libs live
only in the sysroot.)

## Status: G-code generated (Oct 31, 2026)

20 files in `gcode/` (run `scripts/slice_all.sh` to regenerate):

- `gcode/s1_lwpla/` (8): wing_root/mid/tip, vtail_panel,
  fuse_1–4 — LW-PLA vase mode, 235 °C (220 °C first layer), bed 45.
- `gcode/x_lwpla/` (8): same parts, Kobra X machine profile.
- `gcode/s1_petg/` (4): tilt_nacelle_r/l, tilt_bracket (3 walls,
  20% infill), motor_mount_rear (100% infill) — PETG 255 °C, bed 45.

Verified in the output: `spiral_mode = 1` in the LW-PLA files,
`G9111 bedTemp=45 extruderTemp=255` (PETG) / `220` first layer then
`M104 S235` (LW-PLA) in the start sections, 1100–1101 layers for
the 220 mm wing sections, and distinct S1 vs X start G-code.
Print the LW-PLA parts from either printer folder; PETG parts only
from the S1 folder (enclosed printer).

## Solved issues (for the record)

- Host libs: solved with the sysroot (`~/workspace/tools/sysroot`,
  built by `~/workspace/tools/build_sysroot.py`). Run the slicer
  binary directly with the sysroot + AppImage lib dirs on
  LD_LIBRARY_PATH (AppRun's own OpenGL check fails when host libs
  live only in the sysroot). The AppImage `lib/` dir (not just
  `usr/lib/`) must be on the path for Anycubic's `libcloud_mqtt.so`.
- "setup params error": solved with self-contained profiles
  (`slicer_profiles/`, no `inherits` chains).
- Settings types: Orca/Anycubic preset JSONs store numbers as
  STRINGS ("1", "0.2", "0%"). Integer overrides were rejected
  with "invalid json type" — all overrides are strings now.
- CLI `--rotate-*` segfaults in this build: orientations are baked
  into `parts/print_ready/` by `scripts/make_print_ready.py`
  instead; `slice_all.sh` slices those with no rotation flags.
- Process presets carry `compatible_printers`: each printer needs
  process variants derived from its own stock preset
  (`process_lwpla_vase.json` for S1, `process_lwpla_vase_x.json`
  for X); an S1-derived process is rejected by the X.

## Remaining

- Booms (2) and servo doors / FC mount have no STL yet, so no
  G-code for them. They are the only parts left to model.
- LW-PLA flow (55%) and vase-mode wall quality need a real test
  print before committing to full parts — G-code correctness is
  verified, print quality is not.
