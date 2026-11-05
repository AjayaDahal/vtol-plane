# VTOL Plane — Print Tracker (v0.2)

Two printers, one material each:
- **X** = Anycubic Kobra X (260³ mm, open frame) prints every LW-PLA skin: both wings, the
  fuselage and the V-tail. One printer means one LW-PLA spool and one flow calibration.
- **S1** = Anycubic Kobra S1 (250³ mm, enclosed) prints all the PETG, as seven plates. PETG
  warps on the open-frame X.

The X has the long queue (about 49 h, against 16 h for the S1). Run both at once when you can.
No part needs supports. Brims: every LW-PLA skin has an 8 mm one; on the PETG only the five
parts that stand tall on a small base (`coupler_240`, `coupler_370`, `rear_motor_mount`,
`tail_block`, `control_horn`), 5 mm. Trim them off before fitting.

**To print from the slicer**, open the printer's complete project in Anycubic Slicer Next:
`3mf/complete_project_kobra_x_lwpla.3mf` on the X (plates `LW-PLA 01` to `LW-PLA 22`) and
`3mf/complete_project_kobra_s1_petg.3mf` on the S1 (`PETG 1` to `PETG 7`). Every job below is a
named plate, in the suggested order. Pick the plate, slice it without changing anything, check
the preview and send it (`SLICING.md`, "3MF projects"). Each job is also a project of its own
under `3mf/` and G-code under `gcode/`, in the same folder and under the same name: the PETG
plates in `gcode/s1_petg_plates/<plate>.gcode`, each part on them its own object (cancel a failed
one from the printer's screen and let the rest finish), and every part in
`gcode/<printer>_<lwpla|petg>/<part>.gcode`, one copy per file. The LW-PLA skins print from these
(vase mode allows one per bed), and a PETG part that fails on a plate is reprinted from its own.
Mass and time are the slicer's estimates (Anycubic Slicer Next 2.0.0.3). The tables and totals
below are written from the sliced files by `scripts/make_tracker.py`; only the Status column and
the notes in brackets are edited by hand.
Weigh every part as it comes off the bed. An LW-PLA part more than ~15 % off the mass below
means the flow is wrong; recalibrate before printing more. One exception: about 27 % light
means a pre-foamed spool (see the reminders), which no flow setting fixes. Where each part goes:
`DESIGN.md`.

## Reminders for print time (agents: raise these with the user when printing starts)

- [ ] **3S build: hold PETG plates 6 and 7.** The owner is switching to his own 3S packs, the
  Cube Black and new motors on 12 in props (`PLAN_3S.md`). That changes `fc_shelf` and
  `rear_motor_mount` (plate `petg_6_fuselage_tail`) and `yoke_l/r` (plate `petg_7_pods_yokes`).
  Print these two plates only once the plan is built in and re-sliced, with the new motors
  measured. Everything else prints as it is now, every LW-PLA part included. Plate 6's
  unchanged parts (`battery_tray`, `gps_mount`, `pod_collar`, `tail_block`) may print early
  from their single files; mark them printed here. **Order one SunnySky X2814 900KV now and
  thrust-test it** (`PLAN_3S.md`, step 2): plates 6 and 7 wait for its measured hole pattern,
  and the premortem found the 4S motors too marginal for the build as it will weigh
  (`REPORT.md`, round 13). If the wings are assembled before the motors arrive, drill the pitot
  at y ≈ 505 in `wing_tip_r`, not at y ≈ 400 (`DESIGN.md`, "Holes and cuts made by hand").
- [ ] **LW-PLA type: active-foaming only.** The LW-PLA files are sliced for filament that
  foams in the hot nozzle (colorFabb-style LW-PLA): it swells to about twice its volume, so the
  profile feeds only 55 % (flow 0.55 at 235 °C). Pre-foamed LW-PLA (Polymaker's, 0.9 g/cm³)
  does not swell. Printed from these files it gets about half the plastic it needs: thin,
  gappy, weak walls. Check what is on the spool before the first print (`BOM.md`, "Filament").
  The flow test also shows it: from a pre-foamed spool `wing_tip_r` weighs ~10.7 g instead of
  14.7 g. Do not raise the flow until it weighs 14.7 g: the part would weigh right with about a
  quarter of the plastic missing from its walls.
- [ ] **Plate and bed.** The files are set up for the textured PEI plate. Every plate type in the
  slicer gets the same bed temperature (LW-PLA 55 °C, PETG 75 °C), so the plate setting changes
  nothing; on another sheet, check its maker's temperature limit. Clean the plate with isopropyl
  alcohol before each print. On smooth PEI, give PETG a thin film of glue stick first: it can
  bond hard enough to tear the sheet.
- [ ] **Print quality is unverified.** G-code checks cannot show it. The LW-PLA flow of 0.55 and
  the vase-mode walls need a real test print before the full set is printed: `wing_tip_r` on
  the X (target 14.7 g, with a closed, even wall: no gaps between the layers, no light through
  it). Every LW-PLA part prints on the X at 17–30 mm/s, so this one test covers them all.
- [ ] **Spigot fit.** Plate `petg_1_fit_tests` carries `rib_tip_r` (the hidden tip ring): slide
  its inboard half into that `wing_tip_r` before printing the other PETG plates. It should go
  in with light hand force; sand the ring if it is tight.
- [ ] **Tip fairing.** Print `tip_fairing_r` (30 min) next and slide it onto the ring's other
  half: its end must meet the skin's end edge to edge, with no step. It stands on its root and
  closes at the top, its walls leaning in by up to 41.4° and merging into one thin fin. A slightly
  rough fin sands smooth. If the loops sag or droop instead, the lean is too much for this
  filament: lengthen `WING_TIP_CLOSE` and `VT_TIP_CLOSE` in `scripts/params.py` (a longer close
  leans less) and rebuild before printing the other three fairings.
- [ ] **Wing webs.** The root and mid skins carry internal webs (`DESIGN.md`, "Inside the wing").
  When the first `wing_mid_r` comes off, look into its open ends: every web must run from the
  bottom skin up to the top skin and be joined to it, with no gap and no blob. If a web stops
  short, raise the flow slightly before printing the root skins.
- [ ] **Slender control surfaces.** The ailerons and ruddervators are the slenderest prints:
  199–233 mm tall on bases 9.5–11.6 mm wide, held by the 8 mm brim. On the first of them, watch
  the brim go down and the first centimetres: if the brim lifts at an end, or the top sways as
  the nozzle passes, stop it, clean the plate and print it again rather than let it run on.
- [ ] **Tilt servo size.** Measure the tilt servos against the pod bay (24 × 13 mm body, 21 mm
  deep, tab holes 28 mm apart, spline 6 mm from the front) before printing plate
  `petg_7_pods_yokes`. If they differ, change `SERVO_*` in `scripts/params.py` and rebuild.
  The bay's ceiling prints as a 24 mm bridge, the longest in the build: if it sags, trim the
  sag off so the servo slides in.
- [ ] **Axle shims.** Have two 0.5 mm M3 shim washers (OD ≤ 5 mm) before assembling the yokes;
  without them the yoke binds against the pod.
- [ ] **Holes and bridges in the PETG.** No part prints with supports (`renders/51` shows where the
  slicer would have put them, and why none are needed), so the top of every horizontal hole
  (bolt, pin, wire, insert and pushrod holes, 1.6–10 mm) is a bridge and may sag a little. Run a
  drill of the hole's size through each before fitting its bolt, pin or insert. Clear any loose
  strands from under the bridged ceilings too: inside the `rib_midtip` rings, the pods' servo
  bays and the slot near the top of `tail_block`.
- [ ] **Servo hatch fit.** Plate `petg_1_fit_tests` also carries one `servo_hatch` and two
  `hatch_block`s; try a servo in them before printing plate `petg_2_wing`, which has the other
  five. The 9 g servo's tabs must screw to the posts (holes 28 mm apart) with its body (up to
  23 × 12.2 mm) between them, and its horn must stay within 15 mm of the cover's centre.
- [ ] **Battery straps before the tray is glued.** The two Velcro straps thread through the
  `battery_tray` (down a slot, under the plate through the rail gaps, up the other slot); once
  the tray is epoxied in they cannot be fitted (`DESIGN.md` step 3.8).
- [x] ~~Boom-rib supports: watch the tree supports on the `boom_rib_l/r` parts on their first
  print.~~ No longer applies: the boom rib now prints flat with no supports. Its inboard ring
  is the separate `boom_cup`.

Tick a box once the user confirms it is done.

Suggested order (the plates of the complete projects follow it):
- **X:** `wing_tip_r` (flow test: weigh it), `tip_fairing_r` (closing-tip test), `wing_mid_r`
  (web check): plates `LW-PLA 01` to `03`. Then the other skins in any order.
- **S1, alongside:** plate `petg_1_fit_tests` (`PETG 1`; tip-ring and servo-hatch fit: try the
  ring in that `wing_tip_r`), then plates 2–5.
- **Held:** plates 6 and 7 wait for the 3S changes (`PLAN_3S.md`). Plate 7 (pods and yokes) also
  waits for the tilt servos to be measured.

To see every print file and plate on its bed with its mass and time, open the 3D
viewer (`python scripts/serve_viewer.py`) and press "Show the print files", or look at
`renders/35_print_files_all.png` and `renders/47_print_plates_s1_petg.png`. Both printers'
queues in this order, with their sliced times: `renders/print_schedule.svg`. Every plate as the
slicer prints it, drawn from the G-code like its preview (walls, infill, bridges, brims, no
supports): `renders/48_sliced_plates_x_lwpla.png`, `renders/49_sliced_plates_s1_petg.png`, and
the PETG first layers from above, `renders/50_first_layers_s1_petg.png`.

## Plates (PETG, Kobra S1)

| Plate | Printer | On it | Mass (g) | Time | Status |
|---|---|---|---|---|---|
| `petg_1_fit_tests` | S1 | `rib_tip_r`, `servo_hatch`, `hatch_block` ×2 | 11.2 | 0h 25m | sliced |
| `petg_2_wing` | S1 | `rib_root_l`, `rib_root_r`, `rib_midtip_l`, `rib_midtip_r`, `rib_tip_l`, `boom_cup_l`, `boom_cup_r`, `servo_hatch` ×5, `hatch_block` ×10, `control_horn` ×6 | 112.6 | 4h 00m | sliced |
| `petg_3_boom_vtail_ribs` | S1 | `boom_rib_l`, `boom_rib_r`, `vtail_root_rib` ×2, `vtail_tip_cap` ×2 | 65.6 | 2h 08m | sliced |
| `petg_4_fuselage_rings` | S1 | `coupler_240`, `coupler_370` | 37.7 | 1h 03m | sliced |
| `petg_5_fuselage_frames` | S1 | `coupler_610`, `frame_main`, `frame_rear` | 55.3 | 1h 54m | sliced |
| `petg_6_fuselage_tail` | S1 | `fc_shelf`, `battery_tray`, `gps_mount`, `pod_collar`, `tail_block`, `rear_motor_mount` | 101.7 | 3h 38m | on hold (3S plan) |
| `petg_7_pods_yokes` | S1 | `boom_pod_l`, `boom_pod_r`, `yoke_l`, `yoke_r` | 79.8 | 2h 51m | on hold (3S plan) |

## Every part, one per file

Print the LW-PLA skins from these. The PETG rows are the masses to weigh against and the files
for reprinting one part.

| Part | Material | Printer | Qty | Mass each (g) | Time each | Status |
|---|---|---|---|---|---|---|
| `aileron_mid_l` | LW-PLA vase | X | 1 | 5.1 | 1h 07m | sliced |
| `aileron_mid_r` | LW-PLA vase | X | 1 | 5.1 | 1h 07m | sliced |
| `aileron_tip_l` | LW-PLA vase | X | 1 | 4.8 | 1h 12m | sliced |
| `aileron_tip_r` | LW-PLA vase | X | 1 | 4.8 | 1h 12m | sliced |
| `fuse_1` (removable nose) | LW-PLA vase | X | 1 | 18.2 | 3h 18m | sliced |
| `fuse_2` | LW-PLA vase | X | 1 | 13.9 | 2h 28m | sliced |
| `fuse_3` | LW-PLA vase | X | 1 | 22.5 | 4h 00m | sliced |
| `fuse_4` | LW-PLA vase | X | 1 | 8.0 | 1h 26m | sliced |
| `ruddervator_l` | LW-PLA vase | X | 1 | 5.4 | 1h 19m | sliced |
| `ruddervator_r` | LW-PLA vase | X | 1 | 5.4 | 1h 19m | sliced |
| `tip_fairing_l` | LW-PLA vase | X | 1 | 2.6 | 0h 26m | sliced |
| `tip_fairing_r` | LW-PLA vase | X | 1 | 2.6 | 0h 26m | sliced |
| `vtail_l` | LW-PLA vase | X | 1 | 13.7 | 2h 27m | sliced |
| `vtail_r` | LW-PLA vase | X | 1 | 13.7 | 2h 27m | sliced |
| `vtail_tip_fairing` (one file, both sides) | LW-PLA vase | X | 2 | 1.3 | 0h 12m | sliced |
| `wing_mid_l` | LW-PLA vase | X | 1 | 20.7 | 3h 44m | sliced |
| `wing_mid_r` | LW-PLA vase | X | 1 | 20.7 | 3h 44m | sliced |
| `wing_root_l` | LW-PLA vase | X | 1 | 33.5 | 6h 02m | sliced |
| `wing_root_r` | LW-PLA vase | X | 1 | 33.5 | 6h 02m | sliced |
| `wing_tip_l` | LW-PLA vase | X | 1 | 14.7 | 2h 37m | sliced |
| `wing_tip_r` | LW-PLA vase | X | 1 | 14.7 | 2h 37m | sliced |
| `battery_tray` | PETG | S1 | 1 | 20.1 | 0h 48m | sliced |
| `boom_cup_l` | PETG | S1 | 1 | 9.2 | 0h 18m | sliced |
| `boom_cup_r` | PETG | S1 | 1 | 9.2 | 0h 18m | sliced |
| `boom_pod_l` | PETG | S1 | 1 | 27.7 | 0h 57m | sliced |
| `boom_pod_r` | PETG | S1 | 1 | 27.7 | 0h 57m | sliced |
| `boom_rib_l` | PETG | S1 | 1 | 20.9 | 0h 41m | sliced |
| `boom_rib_r` | PETG | S1 | 1 | 20.9 | 0h 41m | sliced |
| `control_horn` | PETG | S1 | 6 | 0.7 | 0h 08m | sliced |
| `coupler_240` | PETG | S1 | 1 | 19.5 | 0h 32m | sliced |
| `coupler_370` | PETG | S1 | 1 | 18.2 | 0h 30m | sliced |
| `coupler_610` | PETG | S1 | 1 | 21.3 | 0h 44m | sliced |
| `fc_shelf` | PETG | S1 | 1 | 23.6 | 0h 48m | on hold (3S plan) |
| `frame_main` | PETG | S1 | 1 | 19.5 | 0h 41m | sliced |
| `frame_rear` | PETG | S1 | 1 | 14.7 | 0h 31m | sliced |
| `gps_mount` | PETG | S1 | 1 | 6.9 | 0h 16m | sliced |
| `hatch_block` (two per hatch) | PETG | S1 | 12 | 0.8 | 0h 04m | sliced |
| `pod_collar` | PETG | S1 | 1 | 4.7 | 0h 12m | sliced |
| `rear_motor_mount` | PETG | S1 | 1 | 18.1 | 0h 38m | on hold (3S plan) |
| `rib_midtip_l` | PETG | S1 | 1 | 15.4 | 0h 32m | sliced |
| `rib_midtip_r` | PETG | S1 | 1 | 15.4 | 0h 32m | sliced |
| `rib_root_l` | PETG | S1 | 1 | 15.1 | 0h 29m | sliced |
| `rib_root_r` | PETG | S1 | 1 | 15.1 | 0h 29m | sliced |
| `rib_tip_l` (hidden tip ring) | PETG | S1 | 1 | 6.8 | 0h 14m | sliced |
| `rib_tip_r` (hidden tip ring) | PETG | S1 | 1 | 6.8 | 0h 14m | sliced |
| `servo_hatch` (one file for all six) | PETG | S1 | 6 | 3.0 | 0h 12m | sliced |
| `tail_block` | PETG | S1 | 1 | 28.0 | 1h 05m | sliced |
| `vtail_root_rib` (one file, both sides) | PETG | S1 | 2 | 9.2 | 0h 19m | sliced |
| `vtail_tip_cap` (tip ring; one file, both sides) | PETG | S1 | 2 | 2.7 | 0h 08m | sliced |
| `yoke_l` | PETG | S1 | 1 | 12.2 | 0h 39m | on hold (3S plan) |
| `yoke_r` | PETG | S1 | 1 | 12.2 | 0h 39m | on hold (3S plan) |

Totals, quantities included, printed as above (LW-PLA one part per job, PETG as plates):

| Printer | What | Jobs | Mass | Time |
|---|---|---|---|---|
| S1 | PETG, 7 plates | 7 | 464 g | 16.0 h |
| X | LW-PLA vase, one part per job | 22 | 266 g | 49.4 h |
| S1 | for comparison: the same PETG as single files (reprints) | 53 | 465 g | 18.1 h |

Notes:

- **One file for both sides.** `vtail_root_rib`, `vtail_tip_cap`, `vtail_tip_fairing`,
  `servo_hatch`, `hatch_block` and `control_horn` are mirror-symmetric, so a mirrored "left" part
  is the same part turned over. Print the quantity shown (the plates already hold every copy);
  any copy fits either side. `check_parts.py` verifies this for every shared file. The wing tip
  fairings are not symmetric (the Clark Y is cambered): print `tip_fairing_l` and
  `tip_fairing_r`.
- **Plates.** Each copy on a plate is its own object, named after its part (`hatch_block_3`), so
  the printer can cancel one that comes loose and finish the rest; reprint it from its own
  file. The parts keep 6 mm apart (at least 4.5 mm on the layout grid) and 15 mm from the bed's
  edge. A 5 mm brim (couplers, horns, `tail_block`, `rear_motor_mount`) stops at a
  neighbour, and two brims may meet between parts and print joined: cut them apart.
  `check_parts.py` checks that the plates hold every PETG print exactly once, that the G-code
  puts each part where the layout does, brims only where they belong, and none cut off at the
  bed's edge.
- **240 mm parts on the X.** `fuse_1`, `fuse_3` and both V-tail panels are 240 mm tall; they
  print on the X (260 mm). The S1 prints only PETG, the tallest being `tail_block` (80 mm).

Status values: not sliced / sliced / printing / printed / fitted / failed. Superseded v0.1 parts and their
G-code (nacelles, brackets, sleeves, pivot blocks, socket rear mount) were deleted; do not
print anything that is not in these tables.
