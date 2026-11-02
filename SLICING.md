# Slicing (v0.2)

Slicer: **Anycubic Slicer Next 1.3.3.3** (OrcaSlicer based), driven from the command line.
Printers: **S1** = Anycubic Kobra S1 (250 x 250 x 250 mm, enclosed), **X** = Anycubic Kobra X
(260 x 260 x 260 mm, open frame). LW-PLA skins are split between the two; every PETG part goes
on the S1. `tracker.md` lists each part with its printer, mass and print time.

## Pipeline

```
python scripts/build_all.py        # everything below in order (--no-slice to skip slicing)
python scripts/skins.py            # LW-PLA skins     -> parts/assembly/*.stl
python scripts/structure.py        # PETG structure   -> parts/assembly/*.stl
python scripts/make_print_ready.py # rotates into print orientation -> parts/print_ready/*.stl
python scripts/make_viewer.py      # 3-D viewer manifest -> viewer/manifest.json (serve_viewer.py, DESIGN.md)
python scripts/slice_all.py        # -> gcode/<s1|x>_<lwpla|petg>/<part>.gcode  (one part: slice_all.py fuse_1)
python scripts/mass_balance.py     # mass, CG, battery position (reads masses from the G-code)
python scripts/check_parts.py      # the gate: geometry, fits, flush joints, mechanism, balance, overhangs, G-code (80 checks)
```

`scripts/make_print_ready.py` holds the print table: printer, material, slicer process,
orientation and copy count per part. Set `VTOL_SLICER` if the slicer is not at
`C:\Program Files\AnycubicSlicerNext\AnycubicSlicerNext.exe`.
Orientations are baked into the STLs (the CLI `--rotate-*` options crash this build), and the
slicer is called with `--orient 0 --arrange 1 --ensure-on-bed`.

## Profiles (`slicer_profiles/`, self-contained, built by `scripts/make_slicer_profiles.py`)

| File | Use |
|---|---|
| `machine_kobra_s1.json`, `machine_kobra_x.json` | printer definitions |
| `process_lwpla_vase.json` (S1), `process_lwpla_vase_x.json` (X) | spiral mode, 1 wall, 0.2 mm, 8 mm outer brim, wall speed capped at 30 mm/s, `slice_closing_radius` 0.01, `detect_thin_wall` 0. Each printer needs its own variant: a process derived from one printer is rejected by the other |
| `process_petg.json` | 3 walls, 15 % crosshatch infill, 5 top / 3 bottom layers, 5 mm auto brim, no supports. Every PETG part uses it |
| `process_petg_support.json` | same, with tree supports. No part uses it any more; kept for one-off prints |
| `filament_lwpla.json` | 235 C (220 C first layer), flow 0.55, fan 100 %, 4 s minimum layer time |
| `filament_petg.json` | 255 C, flow 0.95, fan 40 % |

Numbers in the preset JSONs are strings ("1", "0.2", "0%"); integer overrides are rejected.

LW-PLA foams more the slower it is extruded. The stock settings (200 mm/s walls, 8 s minimum
layer time) made every vase layer take 8 s, so wall speed followed the perimeter: 10 mm/s on the
ailerons, 55 mm/s on the wing roots. No single flow setting suits that range. With the 30 mm/s
cap and a 4 s minimum, every vase part prints at 17–30 mm/s, so the `wing_tip_r` calibration
carries over to the rest. Total time is about the same.

The root and mid wing skins carry internal webs: 0.06 mm slots cut up from the bottom surface,
which the single vase wall runs into and back out of (`DESIGN.md`, "Inside the wing"). Two
settings in both vase profiles make that work, and must not go back to the presets' values:

- `slice_closing_radius` 0.01 (preset 0.049). The preset radius closes a 0.06 mm slot, and
  the web disappears from the G-code.
- `detect_thin_wall` 0 (on in the S1 preset, off in the X one). With it on, the outer wall
  splits a section at a neck of up to ~0.8 mm into islands, and spiral mode then prints only
  one of them. With it off the limit is one line width (0.42 mm), and the webs' 0.6 mm neck to
  the top skin sits inside the window where the wall stays whole and the web still fuses to the
  skin (it stops touching above ~0.84 mm). Both printers were checked in the slicer.

`make_slicer_profiles.py` writes these. The G-code stamp is the STL's hash only, so after any
profile change re-slice every part (`build_all.py` does) rather than only the changed STLs.

## G-code check (Nov 2, 2026)

`check_parts.py` checks the print-ready meshes and parses all 48 files in `gcode/` on every run:

- Every file is present and was sliced from the current STL. `slice_all.py` ends each file with a
  `; vtol_stl_sha256 = ...` stamp, and the gate compares it with the STL's hash; file times are
  not used, because git does not keep them.
- Every move stays inside the printer's printable height, the end-of-print lift included (S1
  250 mm, X 260 mm). The tallest parts reach 242 mm: a 240 mm top layer plus the 2 mm lift. The
  S1 profile's 240 mm `extruder_clearance_height_to_lid` only applies to by-object printing,
  which is not used.
- Parts printed from one file for both sides (`vtail_root_rib`, `vtail_tip_cap`, `servo_hatch`,
  `hatch_block`, `control_horn`) are checked to be mirror-symmetric, so either copy fits either
  side.
- No part needs supports, judged on the geometry: every PETG face more than 60° from vertical is
  bridged (span ≤ 30 mm, e.g. the top of a hole), and flat faces may also be ledges of ≤ 3 mm.
  Vase skins lean ≤ 45°. The pods print upright (45° gusset under the axle boss, 45° nose
  chamfer; the slot, the servo bay and the plug pocket under it are bridges or short ledges).
  The servo hatches print cover-down and the hatch blocks upside down, both flat. The boom rib
  prints flat, its inboard ring being the separate `boom_cup`. The rear motor mount stands on
  one end, bore vertical. As a sanity check on the profiles, no G-code file contains a support
  extrusion.
- LW-PLA walls print at 17 mm/s (ruddervator tips) to 30 mm/s.
- The wing webs print: in a layer where all of a skin's webs are at full depth, the vase path
  turns back once per web and each turn lands within 0.22 mm of the top-skin line (it fuses
  below one line width, 0.42 mm). Checked on all four webbed skins, left and right.
- Every part fits its bed, brim included. The largest is `wing_root`, 234 x 40 mm on the
  250 mm S1 bed; the tallest are `fuse_1`/`fuse_3`/`vtail_r` at 240 mm against 250 mm.
- LW-PLA files: `spiral_mode = 1`, 235 C, bed 35 C. PETG files: 255 C, bed 60 C, 3 walls.
- Masses and times in `tracker.md` equal the slicer's footer (`total filament used [g]`,
  `print_time`). Totals: S1 LW-PLA 139 g / 26.3 h, X LW-PLA 120 g / 22.9 h, S1 PETG 467 g / 21.0 h.

Not checked: print quality. The LW-PLA flow (0.55) and vase-mode wall quality need a real test print
(one `wing_tip_r`) before the full set is printed; see the reminders in `tracker.md`.
