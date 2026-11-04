# Slicing (v0.2)

Slicer: **Anycubic Slicer Next 2.0.0.3** (OrcaSlicer based), driven from the command line. Every
file was re-sliced with it on Nov 3, 2026, when it replaced 1.3.3.3 (`REPORT.md`, round 11).
Printers, one material each: **X** = Anycubic Kobra X (260 x 260 x 260 mm, open frame) prints
every LW-PLA skin, from one spool with one flow calibration (22 jobs, about 49 h). **S1** =
Anycubic Kobra S1 (250 x 250 x 250 mm, enclosed) prints every PETG part as seven plates (about
16 h): PETG warps on the open X. `tracker.md` lists each part and plate with its printer, mass
and print time.

## Pipeline

```
python scripts/build_all.py        # everything below in order (--no-slice to skip slicing)
python scripts/skins.py            # LW-PLA skins     -> parts/assembly/*.stl
python scripts/structure.py        # PETG structure   -> parts/assembly/*.stl
python scripts/make_print_ready.py # rotates into print orientation -> parts/print_ready/*.stl
python scripts/slice_all.py        # -> 3mf/<s1|x>_<lwpla|petg>/<part>.3mf and 3mf/s1_petg_plates/<plate>.3mf (projects),
                                   #    sliced to gcode/<s1|x>_<lwpla|petg>/<part>.gcode and gcode/s1_petg_plates/<plate>.gcode
                                   #    (one file: slice_all.py fuse_1, or a plate's name)
python scripts/make_projects.py    # the two complete projects, a plate per job -> 3mf/complete_project_*.3mf
                                   #    (--verify: slice every plate again and compare it with its job's G-code)
python scripts/make_viewer.py      # 3-D viewer manifest, with each file's sliced mass and time -> viewer/manifest.json;
                                   #    the exterior model for GitHub's 3-D viewer -> renders/vtol_plane.stl
python scripts/make_tracker.py     # print tables and totals in tracker.md, and the queue chart renders/print_schedule.svg
python scripts/mass_balance.py     # mass, CG, battery position (reads masses from the G-code)
python scripts/check_parts.py      # the gate: geometry, fits, flush joints, mechanism, balance, overhangs, G-code
python scripts/audit_print.py      # not in the build: what the slicer itself would support, and how tall and
                                   #    narrow each part stands (needs the slicer, so CI cannot run it)
```

`slice_all.py` run on its own also runs `make_viewer.py`, `make_tracker.py` and
`make_projects.py` when it is done; `build_all.py` runs `make_projects.py --verify`.
A full run (no names) also deletes any G-code or 3MF file that no current part or plate
produces, so a part that moves printer leaves no old file behind.

## 3MF projects: sending a job from the slicer

**Start with the complete projects**, one per printer:

| Project | Printer | Plates, in print order |
|---|---|---|
| `3mf/complete_project_kobra_x_lwpla.3mf` | Kobra X, LW-PLA | 22, one skin each (a vase print holds one object per bed): `LW-PLA 01 - wing_tip_r (flow test)`, `LW-PLA 02 - tip_fairing_r (closing-tip test)`, `LW-PLA 03 - wing_mid_r (web check)`, then the other skins |
| `3mf/complete_project_kobra_s1_petg.3mf` | Kobra S1, PETG | the seven plates below, `PETG 1 - fit tests (4 parts)` to `PETG 7 - pods yokes (4 parts) - ON HOLD (3S plan)` |

Open one in Anycubic Slicer Next, pick a plate, slice it, check the preview and send it. A
slicer project holds one printer, hence one project per printer, each with one material. The
order is `tracker.md`'s, and each project's description lists every plate with what is on it.

Every print job is also a project of its own in `3mf/`, in the same folders and under the same
names as its G-code (`3mf/x_lwpla/wing_tip_r.3mf`, `3mf/s1_petg_plates/petg_1_fit_tests.3mf`,
and each PETG part alone for reprints). Or print the G-code from `gcode/` directly.

- **What is in a project:** the parts where they print, already turned and placed, and every
  setting: the printer (Anycubic Kobra X or Kobra S1 0.4 nozzle), the process (`LW-PLA vase mode
  @VTOL (X)`, `PETG structural @VTOL`), the filament (`LW-PLA foaming @VTOL`, `PETG @VTOL`) and
  the brim of each PETG part that gets one, set on that part (see "Brims" below). The slicer may
  ask whether to keep the project's presets: keep them.
- **Do not change the settings or move the parts.** The wing webs depend on the vase settings
  (see below), and a plate's layout keeps 15 mm at the bed's edge. Leave auto-arrange and
  auto-orient off.
- **Plate type.** The projects are set to the textured PEI plate, the slicer's default for these
  printers. The bed temperature is the same on all six of the slicer's plate types (LW-PLA
  55 °C, PETG 75 °C) and the brims are set per part, so the plate setting changes nothing in
  the print. On a sheet other than textured PEI, check its maker's temperature limit. On smooth
  PEI, give PETG a thin film of glue stick as a release: it can bond to bare smooth PEI hard
  enough to tear the sheet.
- **It slices to the checked G-code.** `slice_all.py` writes each job's 3MF from the STLs and
  the profiles, then slices that 3MF on its own, with no other settings loaded: the G-code in
  `gcode/` is what the 3MF gives in Anycubic Slicer Next 2.0.0.3, and the gate checks it.
  `make_projects.py` puts each job's 3MF on a plate of its printer's complete project unchanged
  (objects, places, settings). `build_all.py` then slices every plate of both projects again,
  one at a time as the slicer's window does, and compares each with its job's G-code: the same
  layers with the same extrusion, the same objects, mass and time. The PETG plates agree to
  0.001 mm. A vase layer where an outline closes to a fin can differ by up to 0.17 mm (half the
  0.42 mm line allowed), the same on every run: rounding from the plate's offset in the project.
  Another slicer version may slice a little differently: compare its preview with the G-code
  (vase walls, webs, brims) before printing.
- **Current:** each job's 3MF carries its parts' STL hash as metadata (`vtol_stl_sha256`), like
  its G-code, and each complete project a hash of its plates' jobs (`vtol_jobs_sha256`). The gate
  checks the hashes and the presets, and that both complete projects are what `make_projects.py`
  builds from the jobs' 3MFs, file for file.
- **Plate names** are for the slicer's window. Its command line crashes on any plate name
  (1.3.3.3 and 2.0.0.3), so `make_projects.py --verify` slices a copy with the names blanked;
  nothing else differs.
- **No thumbnails.** The 2.0.0.3 command line writes no preview pictures into the projects or the
  G-code; the slicer's window draws them when it slices a plate. G-code printed straight from
  `gcode/` shows no picture on the printer's screen.

On a PETG plate, each part is its own object, as in the G-code: one that comes loose can be
skipped from the printer's screen while the rest finish.

`scripts/make_print_ready.py` holds the print table: printer, material, slicer process,
orientation and copy count per part. Set `VTOL_SLICER` if the slicer is not at
`C:\Program Files\AnycubicSlicerNext\AnycubicSlicerNext.exe`.
Orientations are baked into the STLs (the CLI `--rotate-*` options crash this build). Each part
is centred on its bed by `slice_all.py` and sliced with `--orient 0 --arrange 0 --ensure-on-bed`,
so the slicer keeps its orientation: with `--arrange 1` the slicer's own arrange turned some parts
about z (it laid the 45° boom rib along x and cut its brim at the bed's edge).

## Plates (`scripts/plates.py`)

The PETG parts print as seven plates on the S1 instead of 53 single prints: 461 g and 15.9 h
against 18.1 h, because small parts sharing a bed no longer each wait out the minimum layer
time, and 46 fewer jobs to start, level and clear. The plates are grouped in build order:
`petg_1_fit_tests` (tip ring, one servo hatch, two hatch blocks) goes with the LW-PLA test
prints, and `petg_7_pods_yokes` waits until the tilt servos have been measured.

- **Layout.** Each part keeps its print orientation and only turns about z. Its footprint (the
  convex hull of its print-ready mesh) is laid on a 1 mm grid, 6 mm from every other footprint
  (at least 4.5 mm after the grid's rounding) and 15 mm inside the bed. The margin was sized for
  the auto brims of the 1.3.3.3 slicer (13.6 mm on the fuselage couplers); the 5 mm brims set now
  (see "Brims") leave room to spare, so no brim is cut off at the bed's edge. A brim stops short
  of a neighbour's footprint, and two brims may meet between parts and print joined: cut them
  apart. Largest first, each part goes to the lowest free spot, then the
  leftmost, trying its minimum-area orientation, that turned 90°, then the diagonals; the layout
  is then centred. It is deterministic, so the gate and the viewer recompute it.
- **Slicing.** `slice_all.py` writes every placed copy as its own STL and slices the plate with
  `--arrange 0`, which keeps each STL where it is. Every part stays its own object: a part with
  a brim gets its own, and the S1's Klipper firmware can cancel any part (`EXCLUDE_OBJECT`)
  without stopping the rest. A plate's stamp hashes its parts' STLs and their places.
- **LW-PLA is not plated.** A vase skin is one continuous spiral wall, and the slicer only puts
  several vase objects on one bed by printing them one after another (by object). Then every
  object but the last has to pass under the print head's gantry: 40 mm on the S1, 30 mm on the
  X (`extruder_clearance_height_to_rod`). The skins are 130–240 mm tall; on the X, which prints
  them all, only the 20 mm V-tail tip fairing would fit under, and pairing it with a skin would
  save a single 12 min job.
- The single-part PETG files stay: weigh against them, and reprint one part from its own file.

## Profiles (`slicer_profiles/`, self-contained, built by `scripts/make_slicer_profiles.py`)

| File | Use |
|---|---|
| `machine_kobra_s1.json`, `machine_kobra_x.json` | printer definitions: Anycubic Slicer Next 2.0.0.3's own presets, which `make_slicer_profiles.py` reads from the installed slicer. The S1's draws a purge line beside the bed (y = 255 mm) before the first layer; its start G-code is only the printer's `G9111` macro, and the profiles print no skirt |
| `process_lwpla_vase.json` (S1), `process_lwpla_vase_x.json` (X) | spiral mode, 1 wall, 0.2 mm, 8 mm outer brim, wall speed capped at 30 mm/s, `slice_closing_radius` 0.01, `detect_thin_wall` 0. Each printer needs its own variant: a process derived from one printer is rejected by the other. Every LW-PLA part prints on the X now; the S1 variant is kept for one-off prints |
| `process_petg.json` | 3 walls, 15 % crosshatch infill, 5 top / 3 bottom layers, no brim (a part that needs one gets its own: "Brims" below), no supports. Every PETG part uses it |
| `process_petg_support.json` | same, with tree supports. No part uses it any more; kept for one-off prints |
| `filament_lwpla.json` | 235 C (220 C first layer), flow 0.55, fan 100 %, 4 s minimum layer time, bed 55 C on every plate type |
| `filament_petg.json` | 255 C, flow 0.95, fan 40 %, bed 75 C on every plate type |

Numbers in the preset JSONs are strings ("1", "0.2", "0%"); integer overrides are rejected.

**Bed temperature.** The plate type picks which of a filament's bed temperatures applies, so each
profile sets the same one on all six types the slicer offers (cool, engineering, smooth "hot",
textured PEI, textured cool, supertack). The 1.3.3.3 command line set every project to the cool
plate, which the stock presets heat to 35 °C for PLA and 60 °C for PETG: too cold for LW-PLA skins
up to 240 mm tall, the ailerons 213 mm on a 9.5 mm base (colorFabb asks for 50–60 °C). 2.0.0.3 sets
the textured PEI plate, and every stock preset keeps its textured cool and supertack plates at
35–40 °C. Now LW-PLA gets 55 °C and PETG 75 °C, as in Anycubic's own Kobra S1 PETG preset for the
textured PEI and smooth plates, whichever plate the slicer is set to. The gate reads every plate
type's value back from every file, so a plate type that a new slicer version adds fails it until
`make_slicer_profiles.py` covers it.

**Brims.** Every LW-PLA skin has the vase profile's 8 mm outer brim. PETG prints without one,
except the parts that stand taller than the square root of their first-layer contact area, a
lever the nozzle can pry off the bed: `tail_block` (height 3.2 times that root), `coupler_370`
(2.0), `coupler_240` (1.8), `rear_motor_mount` (1.3), `control_horn` (1.2) and `rib_midtip_l/r`
(1.04) get a 5 mm brim; the next is the yoke at 0.82. The print table sets it per part
(`make_print_ready.py`, `brim`), and `slice_all.py` writes it into the job's 3MF as that object's
own setting, so the slicer applies it on any plate and shows it on the object. The gate measures
every part's ratio in its G-code and checks the list, and that the brims printed are exactly these.
The stock auto brim is off: it follows the plate type and the slicer version, and put brims on 17
PETG parts with 1.3.3.3 (cool plate) and on one with 2.0.0.3 (textured PEI).

`filament_lwpla.json` is for **active-foaming** LW-PLA (colorFabb LW-PLA, SainSmart LW-PLA, Bambu
Lab PLA Aero, eSUN PLA-LW), which swells in the nozzle: hence 55 % flow at 235 °C. Pre-foamed
lightweight PLA (Polymaker PolyLite LW-PLA, SUNLU LW-PLA, Overture Air PLA) does not swell. It
needs its own profile at about full flow and 190–210 °C, and its skins weigh ~32 % more (0.9
against ~0.68 g/cm³), so it also changes the mass balance (`BOM.md`, "Filament").

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

## G-code check (Nov 3, 2026)

`check_parts.py` checks the print-ready meshes and parses all 58 files in `gcode/` (51 parts, 7
plates) on every run:

- Every file is present and was sliced from the current STL. `slice_all.py` ends each file with a
  `; vtol_stl_sha256 = ...` stamp, and the gate compares it with the STL's hash (a plate's: its
  parts' STLs and their places); file times are not used, because git does not keep them. No
  other G-code file is in `gcode/`.
- Every job's 3MF project is in `3mf/`, carries the same hash as metadata and the right printer,
  process and filament presets, and no other 3MF is there. The G-code is sliced from it. The two
  complete projects are what `make_projects.py` builds from these, file for file.
- Every move stays inside the printer's printable height, the end-of-print lift included (S1
  250 mm, X 260 mm), and every extrusion, brims included, stays at least 1 mm inside the bed's
  edge, so no brim is cut off there. The S1's purge line is the exception: its own preset draws it
  beside the bed, at y = 255 mm. The tallest parts,
  the 240 mm fuselage sections and V-tail panels, print on the X; its highest move is 240 mm,
  against 260 mm. The S1 prints only PETG, the tallest being `tail_block` at 80 mm.
- Plates: they hold every PETG print exactly once, and their layouts keep parts at least 4.5 mm
  apart and 15 mm inside the bed. In every PETG file, plate or single part, each part is its own
  object (`EXCLUDE_OBJECT_DEFINE`) whose outline matches the footprint where the script placed
  it, turned as it meant (within 0.5 mm), so the slicer neither moved nor turned anything. In
  vase mode 2.0.0.3 labels no objects (one part per bed, nothing to cancel), so a skin's
  extrusions, brim left out, must lie inside its placed footprint (within 0.5 mm; they lie inside
  it) and reach within 2.5 mm of its corners: a sharp trailing edge stops short of its tip, up
  to 1.6 mm on the ruddervators, because the line cannot follow a wedge thinner than itself.
- Brims: every vase skin has its 8 mm brim, and on PETG exactly the parts the print table gives
  one, each on its own object (see "Brims" above). The table's list must be the parts standing
  taller than the root of their first-layer contact area, measured in their G-code.
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
  on the profiles, no G-code file contains a support extrusion. The slicer agrees once its
  answer is read: `audit_print.py` (not in the gate) slices every part with tree supports allowed
  anywhere. It adds none to the skins, and on 13 PETG files only under the tops of horizontal
  holes (1.6–10 mm) or under bridges, such as `rib_midtip`'s plate over its spigot ring and the
  pods' cavities. A support inside a hole or a closed cavity could not be taken out and would
  spoil the fit, so none prints; drill the horizontal holes to size before assembly
  (`tracker.md`).
- LW-PLA walls print at 17 mm/s (ruddervator tips) to 30 mm/s.
- The wing webs print: in a layer where all of a skin's webs are at full depth, the vase path
  turns back once per web and each turn lands within 0.22 mm of the top-skin line (it fuses
  below one line width, 0.42 mm). Checked on all four webbed skins, left and right.
- Every part fits its bed, brim included. The largest is `wing_root`, 234 x 40 mm on the
  X's 260 mm bed; the tallest are `fuse_1`/`fuse_3`/`vtail_l`/`vtail_r` at 240 mm against the
  X's 260 mm.
- LW-PLA files: `spiral_mode = 1`, 235 C, bed 55 C. PETG files: 255 C, bed 75 C, 3 walls. The
  bed temperature is the same on every plate type in each file and in the printer's start macro
  (`G9111 bedTemp`); with the vase walls' and webs' settings, the brim type and no supports, the
  gate reads these back from every file.
- Masses and times in `tracker.md` and the viewer equal the slicer's footer (`total filament
  used [g]`, `print_time`): `build_all.py` writes the viewer's manifest and the tracker's table
  (`make_tracker.py`) after slicing, and the gate checks both against every file.
  Totals as printed: X 49.4 h of LW-PLA (266 g, 22 jobs); S1 15.9 h of PETG plates (461 g,
  7 jobs). The PETG as single files would take 18.1 h (462 g).
- Re-slicing an unchanged STL did not always give the same file in 1.3.3.3, even at the same
  place on the bed: `boom_pod_r` came out at 27.66 g and 27.94 g in two slices. Treat each mass
  as good to ~0.3 g, and expect a full re-slice to move a few tracker entries by a few tenths.
  The mass balance's stop-pin choice has 0.4 mm of CG to spare against this (CG 434.8 mm against
  the rule's 435.2 mm; `REPORT.md` 9.7).

Not checked: print quality. The LW-PLA flow (0.55) and vase-mode wall quality need a real test print
(one `wing_tip_r`) before the full set is printed; see the reminders in `tracker.md`.
