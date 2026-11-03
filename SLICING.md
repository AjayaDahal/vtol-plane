# Slicing (v0.2)

Slicer: **Anycubic Slicer Next 1.3.3.3** (OrcaSlicer based), driven from the command line.
Printers, one material each: **X** = Anycubic Kobra X (260 x 260 x 260 mm, open frame) prints
every LW-PLA skin, from one spool with one flow calibration (22 jobs, about 51 h). **S1** =
Anycubic Kobra S1 (250 x 250 x 250 mm, enclosed) prints every PETG part as seven plates (about
18 h): PETG warps on the open X. `tracker.md` lists each part and plate with its printer, mass
and print time.

## Pipeline

```
python scripts/build_all.py        # everything below in order (--no-slice to skip slicing)
python scripts/skins.py            # LW-PLA skins     -> parts/assembly/*.stl
python scripts/structure.py        # PETG structure   -> parts/assembly/*.stl
python scripts/make_print_ready.py # rotates into print orientation -> parts/print_ready/*.stl
python scripts/slice_all.py        # -> gcode/<s1|x>_<lwpla|petg>/<part>.gcode and gcode/s1_petg_plates/<plate>.gcode
                                   #    (one file: slice_all.py fuse_1, or a plate's name)
python scripts/make_viewer.py      # 3-D viewer manifest, with each file's sliced mass and time -> viewer/manifest.json;
                                   #    the exterior model for GitHub's 3-D viewer -> renders/vtol_plane.stl
python scripts/make_tracker.py     # print tables and totals in tracker.md, and the queue chart renders/print_schedule.svg
python scripts/mass_balance.py     # mass, CG, battery position (reads masses from the G-code)
python scripts/check_parts.py      # the gate: geometry, fits, flush joints, mechanism, balance, overhangs, G-code
```

`slice_all.py` run on its own also runs `make_viewer.py` and `make_tracker.py` when it is done.
A full run (no names) also deletes any G-code file that no current part or plate produces, so a
part that moves printer leaves no old file behind.

`scripts/make_print_ready.py` holds the print table: printer, material, slicer process,
orientation and copy count per part. Set `VTOL_SLICER` if the slicer is not at
`C:\Program Files\AnycubicSlicerNext\AnycubicSlicerNext.exe`.
Orientations are baked into the STLs (the CLI `--rotate-*` options crash this build). Each part
is centred on its bed by `slice_all.py` and sliced with `--orient 0 --arrange 0 --ensure-on-bed`,
so the slicer keeps its orientation: with `--arrange 1` the slicer's own arrange turned some parts
about z (it laid the 45° boom rib along x and cut its brim at the bed's edge).

## Plates (`scripts/plates.py`)

The PETG parts print as seven plates on the S1 instead of 53 single prints: 474 g and 17.5 h
against 22.6 h, because small parts sharing a bed no longer each wait out the minimum layer
time, and 46 fewer jobs to start, level and clear. The plates are grouped in build order:
`petg_1_fit_tests` (tip ring, one servo hatch, two hatch blocks) goes with the LW-PLA test
prints, and `petg_7_pods_yokes` waits until the tilt servos have been measured.

- **Layout.** Each part keeps its print orientation and only turns about z. Its footprint (the
  convex hull of its print-ready mesh) is laid on a 1 mm grid, 6 mm from every other footprint
  (at least 4.5 mm after the grid's rounding) and 15 mm inside the bed. That margin holds the
  widest brim the PETG profile's auto brim makes, 13.6 mm on the fuselage couplers (it is not
  the profile's 5 mm `brim_width`), so no brim is cut off at the bed's edge; neighbours' brims
  may meet and print joined. Largest first, each part goes to the lowest free spot, then the
  leftmost, trying its minimum-area orientation, that turned 90°, then the diagonals; the layout
  is then centred. It is deterministic, so the gate and the viewer recompute it.
- **Slicing.** `slice_all.py` writes every placed copy as its own STL and slices the plate with
  `--arrange 0`, which keeps each STL where it is. Every part stays its own object: it gets its
  own brim, and the S1's Klipper firmware can cancel it (`EXCLUDE_OBJECT`) without stopping the
  rest. A plate's stamp hashes its parts' STLs and their places.
- **LW-PLA is not plated.** A vase skin is one continuous spiral wall, and the slicer only puts
  several vase objects on one bed by printing them one after another (by object). Then every
  object but the last has to pass under the print head's gantry: 48 mm on the S1, 30 mm on the
  X (`extruder_clearance_height_to_rod`). The skins are 130–240 mm tall; only the tip fairings
  (20–32 mm) would fit under, and pairing one with a skin would save a single job of 17–30 min.
- The single-part PETG files stay: weigh against them, and reprint one part from its own file.

## Profiles (`slicer_profiles/`, self-contained, built by `scripts/make_slicer_profiles.py`)

| File | Use |
|---|---|
| `machine_kobra_s1.json`, `machine_kobra_x.json` | printer definitions |
| `process_lwpla_vase.json` (S1), `process_lwpla_vase_x.json` (X) | spiral mode, 1 wall, 0.2 mm, 8 mm outer brim, wall speed capped at 30 mm/s, `slice_closing_radius` 0.01, `detect_thin_wall` 0. Each printer needs its own variant: a process derived from one printer is rejected by the other. Every LW-PLA part prints on the X now; the S1 variant is kept for one-off prints |
| `process_petg.json` | 3 walls, 15 % crosshatch infill, 5 top / 3 bottom layers, 5 mm auto brim, no supports. Every PETG part uses it |
| `process_petg_support.json` | same, with tree supports. No part uses it any more; kept for one-off prints |
| `filament_lwpla.json` | 235 C (220 C first layer), flow 0.55, fan 100 %, 4 s minimum layer time |
| `filament_petg.json` | 255 C, flow 0.95, fan 40 % |

Numbers in the preset JSONs are strings ("1", "0.2", "0%"); integer overrides are rejected.

`filament_lwpla.json` is for **active-foaming** LW-PLA (colorFabb LW-PLA, eSUN PLA-LW), which
swells in the nozzle: hence 55 % flow at 235 °C. Pre-foamed lightweight PLA (Polymaker PolyLite
LW-PLA, SUNLU LW-PLA, Overture Air PLA) does not swell. It needs its own profile at about full
flow and 190–210 °C, and its skins weigh ~32 % more (0.9 against ~0.68 g/cm³), so it also
changes the mass balance (`BOM.md`, "Filament").

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

`check_parts.py` checks the print-ready meshes and parses all 58 files in `gcode/` (51 parts, 7
plates) on every run:

- Every file is present and was sliced from the current STL. `slice_all.py` ends each file with a
  `; vtol_stl_sha256 = ...` stamp, and the gate compares it with the STL's hash (a plate's: its
  parts' STLs and their places); file times are not used, because git does not keep them. No
  other G-code file is in `gcode/`.
- Every move stays inside the printer's printable height, the end-of-print lift included (S1
  250 mm, X 260 mm), and every extrusion, brims included, stays at least 1 mm inside the bed's
  edge, so no brim is cut off there. The tallest parts,
  the 240 mm fuselage sections and V-tail panels, print on the X; its highest move is 240 mm,
  against 260 mm. The S1 prints only PETG, the tallest being `tail_block` at 80 mm.
- Plates: they hold every PETG print exactly once, and their layouts keep parts at least 4.5 mm
  apart and 15 mm inside the bed. In every file, plate or single part, each part is its own
  object (`EXCLUDE_OBJECT_DEFINE`) whose outline matches the footprint where the script placed
  it, turned as it meant (within 0.5 mm), so the slicer neither moved nor turned anything.
- Parts printed from one file for both sides (`vtail_root_rib`, `vtail_tip_cap`,
  `vtail_tip_fairing`, `servo_hatch`, `hatch_block`, `control_horn`) are checked to be
  mirror-symmetric, so either copy fits either side.
- No part needs supports, judged on the geometry: every PETG face more than 60° from vertical is
  bridged (span ≤ 30 mm, e.g. the top of a hole), and flat faces may also be ledges of ≤ 3 mm.
  Vase skins lean ≤ 45°. The pods print upright (45° gusset under the axle boss, 45° nose
  chamfer; the slot, the servo bay and the plug pocket under it are bridges or short ledges).
  The servo hatches print cover-down and the hatch blocks upside down, both flat. The boom rib
  prints flat, its inboard ring being the separate `boom_cup`. The hidden tip rings stand on
  their full-chord fairing end. The rear motor mount stands on one end, bore vertical. The tip
  fairings stand on their root like the skins and close at the top; no wall leans more than
  41.4° (the wing's; the V-tail's 37.6°), and the gate prints the steepest. As a sanity check
  on the profiles, no G-code file contains a support extrusion.
- LW-PLA walls print at 17 mm/s (ruddervator tips) to 30 mm/s.
- The wing webs print: in a layer where all of a skin's webs are at full depth, the vase path
  turns back once per web and each turn lands within 0.22 mm of the top-skin line (it fuses
  below one line width, 0.42 mm). Checked on all four webbed skins, left and right.
- Every part fits its bed, brim included. The largest is `wing_root`, 234 x 40 mm on the
  X's 260 mm bed; the tallest are `fuse_1`/`fuse_3`/`vtail_l`/`vtail_r` at 240 mm against the
  X's 260 mm.
- LW-PLA files: `spiral_mode = 1`, 235 C, bed 35 C. PETG files: 255 C, bed 60 C, 3 walls.
- Masses and times in `tracker.md` and the viewer equal the slicer's footer (`total filament
  used [g]`, `print_time`): `build_all.py` writes the viewer's manifest and the tracker's table
  (`make_tracker.py`) after slicing, and the gate checks both against every file.
  Totals as printed: X 50.9 h of LW-PLA (266 g, 22 jobs); S1 17.5 h of PETG plates (474 g,
  7 jobs). The PETG as single files would take 22.6 h (475 g).
- Re-slicing an unchanged STL does not always give the same file, even at the same place on the
  bed: `boom_pod_r` came out at 27.66 g and 27.94 g in two slices. Treat each mass as good to
  ~0.3 g, and expect a full re-slice to move a few tracker entries by a few tenths. The mass
  balance's stop-pin choice has 0.6 mm of CG to spare against this (`REPORT.md` 9.7).

Not checked: print quality. The LW-PLA flow (0.55) and vase-mode wall quality need a real test print
(one `wing_tip_r`) before the full set is printed; see the reminders in `tracker.md`.
