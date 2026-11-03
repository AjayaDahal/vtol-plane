# VTOL Plane — Print Tracker (v0.2)

Two printers: **S1** = Anycubic Kobra S1 (250³ mm, enclosed),
**X** = Anycubic Kobra X (260³ mm, open frame).
Rule: the **S1** prints the right wing (skins, ailerons, tip fairing) and all the PETG, as seven
plates; the **X** prints the left wing, the four fuselage sections and the V-tail (panels,
ruddervators, tip fairings). That gives each printer about 35 h, so run both at once. No part
needs supports.

G-code: the PETG plates are in `gcode/s1_petg_plates/<plate>.gcode`, each part on them its own
object (cancel a failed one from the printer's screen and let the rest finish). Every part also
has its own file, `gcode/<printer>_<lwpla|petg>/<part>.gcode`, one copy per file: the LW-PLA
skins print from these (vase mode allows one per bed), and a PETG part that fails on a plate is
reprinted from its own. Mass and time are the slicer's estimates (Anycubic Slicer Next
1.3.3.3). The tables and totals below are written from the sliced files by
`scripts/make_tracker.py`; only the Status column and the notes in brackets are edited by hand.
Weigh every part as it comes off the bed. An LW-PLA part more than ~15 % off the mass below
means the flow is wrong; recalibrate before printing more. Where each part goes: `DESIGN.md`.

## Reminders for print time (agents: raise these with the user when printing starts)

- [ ] **Print quality is unverified.** G-code checks cannot show it. The LW-PLA flow of 0.55 and
  the vase-mode walls need a real test print on each printer before the full set is printed:
  `wing_tip_r` on the S1 and its mirror `wing_tip_l` on the X (target 14.7 g each). The two
  printers' extruders differ, so one printer's result does not prove the other's. All vase parts
  print at 17–30 mm/s, so one test per printer covers all its parts.
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
- [ ] **Tilt servo size.** Measure the tilt servos against the pod bay (24 × 13 mm body, 21 mm
  deep, tab holes 28 mm apart, spline 6 mm from the front) before printing plate
  `petg_7_pods_yokes`. If they differ, change `SERVO_*` in `scripts/params.py` and rebuild.
- [ ] **Axle shims.** Have two 0.5 mm M3 shim washers (OD ≤ 5 mm) before assembling the yokes;
  without them the yoke binds against the pod.
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

Suggested order. S1: `wing_tip_r` (flow test), then plate `petg_1_fit_tests` (tip-ring and
servo-hatch fit) and `tip_fairing_r` (closing-tip test), then `wing_mid_r` (web check), then the
rest of the right wing and PETG plates 2–6; plate 7 (pods and yokes) once the tilt servos have
been measured. X: `wing_tip_l` first (its flow test: weigh it), then the left wing, the
fuselage and the V-tail, in any order. To see every print file and plate on its bed with its mass and time, open the 3D
viewer (`python scripts/serve_viewer.py`) and press "Show the print files", or look at
`renders/35_print_files_all.png` and `renders/47_print_plates_s1_petg.png`. Both printers'
queues in this order, with their sliced times: `renders/print_schedule.svg`.

## Plates (PETG, Kobra S1)

| Plate | Printer | On it | Mass (g) | Time | Status |
|---|---|---|---|---|---|
| `petg_1_fit_tests` | S1 | `rib_tip_r`, `servo_hatch`, `hatch_block` ×2 | 11.7 | 0h 32m | sliced |
| `petg_2_wing` | S1 | `rib_root_l`, `rib_root_r`, `rib_midtip_l`, `rib_midtip_r`, `rib_tip_l`, `boom_cup_l`, `boom_cup_r`, `servo_hatch` ×5, `hatch_block` ×10, `control_horn` ×6 | 113.6 | 4h 18m | sliced |
| `petg_3_boom_vtail_ribs` | S1 | `boom_rib_l`, `boom_rib_r`, `vtail_root_rib` ×2, `vtail_tip_cap` ×2 | 68.0 | 2h 26m | sliced |
| `petg_4_fuselage_rings` | S1 | `coupler_240`, `coupler_370` | 39.4 | 1h 15m | sliced |
| `petg_5_fuselage_frames` | S1 | `coupler_610`, `frame_main`, `frame_rear` | 57.4 | 2h 09m | sliced |
| `petg_6_fuselage_tail` | S1 | `fc_shelf`, `battery_tray`, `gps_mount`, `pod_collar`, `tail_block`, `rear_motor_mount` | 102.6 | 3h 49m | sliced |
| `petg_7_pods_yokes` | S1 | `boom_pod_l`, `boom_pod_r`, `yoke_l`, `yoke_r` | 81.1 | 3h 03m | sliced |

## Every part, one per file

Print the LW-PLA skins from these. The PETG rows are the masses to weigh against and the files
for reprinting one part.

| Part | Material | Printer | Qty | Mass each (g) | Time each | Status |
|---|---|---|---|---|---|---|
| `aileron_mid_r` | LW-PLA vase | S1 | 1 | 5.1 | 1h 11m | sliced |
| `aileron_tip_r` | LW-PLA vase | S1 | 1 | 4.8 | 1h 16m | sliced |
| `tip_fairing_r` | LW-PLA vase | S1 | 1 | 2.6 | 0h 30m | sliced |
| `wing_mid_r` | LW-PLA vase | S1 | 1 | 20.7 | 3h 46m | sliced |
| `wing_root_r` | LW-PLA vase | S1 | 1 | 33.5 | 6h 05m | sliced |
| `wing_tip_r` | LW-PLA vase | S1 | 1 | 14.7 | 2h 41m | sliced |
| `aileron_mid_l` | LW-PLA vase | X | 1 | 5.1 | 1h 11m | sliced |
| `aileron_tip_l` | LW-PLA vase | X | 1 | 4.8 | 1h 16m | sliced |
| `fuse_1` (removable nose) | LW-PLA vase | X | 1 | 18.2 | 3h 22m | sliced |
| `fuse_2` | LW-PLA vase | X | 1 | 13.9 | 2h 32m | sliced |
| `fuse_3` | LW-PLA vase | X | 1 | 22.5 | 4h 04m | sliced |
| `fuse_4` | LW-PLA vase | X | 1 | 8.0 | 1h 30m | sliced |
| `ruddervator_l` | LW-PLA vase | X | 1 | 5.4 | 1h 23m | sliced |
| `ruddervator_r` | LW-PLA vase | X | 1 | 5.4 | 1h 23m | sliced |
| `tip_fairing_l` | LW-PLA vase | X | 1 | 2.6 | 0h 30m | sliced |
| `vtail_l` | LW-PLA vase | X | 1 | 13.7 | 2h 31m | sliced |
| `vtail_r` | LW-PLA vase | X | 1 | 13.7 | 2h 31m | sliced |
| `vtail_tip_fairing` (one file, both sides) | LW-PLA vase | X | 2 | 1.3 | 0h 16m | sliced |
| `wing_mid_l` | LW-PLA vase | X | 1 | 20.7 | 3h 48m | sliced |
| `wing_root_l` | LW-PLA vase | X | 1 | 33.5 | 6h 06m | sliced |
| `wing_tip_l` | LW-PLA vase | X | 1 | 14.7 | 2h 42m | sliced |
| `battery_tray` | PETG | S1 | 1 | 20.4 | 0h 55m | sliced |
| `boom_cup_l` | PETG | S1 | 1 | 9.2 | 0h 23m | sliced |
| `boom_cup_r` | PETG | S1 | 1 | 9.2 | 0h 23m | sliced |
| `boom_pod_l` | PETG | S1 | 1 | 27.9 | 1h 03m | sliced |
| `boom_pod_r` | PETG | S1 | 1 | 27.7 | 1h 02m | sliced |
| `boom_rib_l` | PETG | S1 | 1 | 22.4 | 0h 51m | sliced |
| `boom_rib_r` | PETG | S1 | 1 | 22.4 | 0h 51m | sliced |
| `control_horn` | PETG | S1 | 6 | 0.6 | 0h 12m | sliced |
| `coupler_240` | PETG | S1 | 1 | 20.5 | 0h 40m | sliced |
| `coupler_370` | PETG | S1 | 1 | 19.2 | 0h 37m | sliced |
| `coupler_610` | PETG | S1 | 1 | 22.4 | 0h 53m | sliced |
| `fc_shelf` | PETG | S1 | 1 | 24.2 | 0h 53m | sliced |
| `frame_main` | PETG | S1 | 1 | 20.3 | 0h 50m | sliced |
| `frame_rear` | PETG | S1 | 1 | 14.9 | 0h 38m | sliced |
| `gps_mount` | PETG | S1 | 1 | 7.0 | 0h 20m | sliced |
| `hatch_block` (two per hatch) | PETG | S1 | 12 | 0.8 | 0h 08m | sliced |
| `pod_collar` | PETG | S1 | 1 | 4.7 | 0h 16m | sliced |
| `rear_motor_mount` | PETG | S1 | 1 | 18.1 | 0h 43m | sliced |
| `rib_midtip_l` | PETG | S1 | 1 | 15.0 | 0h 36m | sliced |
| `rib_midtip_r` | PETG | S1 | 1 | 15.0 | 0h 36m | sliced |
| `rib_root_l` | PETG | S1 | 1 | 16.1 | 0h 37m | sliced |
| `rib_root_r` | PETG | S1 | 1 | 16.1 | 0h 37m | sliced |
| `rib_tip_l` (hidden tip ring) | PETG | S1 | 1 | 7.1 | 0h 20m | sliced |
| `rib_tip_r` (hidden tip ring) | PETG | S1 | 1 | 7.1 | 0h 20m | sliced |
| `servo_hatch` (one file for all six) | PETG | S1 | 6 | 3.0 | 0h 17m | sliced |
| `tail_block` | PETG | S1 | 1 | 27.9 | 1h 10m | sliced |
| `vtail_root_rib` (one file, both sides) | PETG | S1 | 2 | 9.3 | 0h 24m | sliced |
| `vtail_tip_cap` (tip ring; one file, both sides) | PETG | S1 | 2 | 2.7 | 0h 12m | sliced |
| `yoke_l` | PETG | S1 | 1 | 12.6 | 0h 44m | sliced |
| `yoke_r` | PETG | S1 | 1 | 12.6 | 0h 44m | sliced |

Totals, quantities included, printed as above (LW-PLA one part per job, PETG as plates):

| Printer | What | Jobs | Mass | Time |
|---|---|---|---|---|
| S1 | LW-PLA vase, one part per job | 6 | 81 g | 15.5 h |
| S1 | PETG, 7 plates | 7 | 474 g | 17.5 h |
| S1 | total | 13 | 555 g | 33.0 h |
| X | LW-PLA vase, one part per job | 16 | 185 g | 35.4 h |
| S1 | for comparison: the same PETG as single files (reprints) | 53 | 475 g | 22.6 h |

Notes:

- **One file for both sides.** `vtail_root_rib`, `vtail_tip_cap`, `vtail_tip_fairing`,
  `servo_hatch`, `hatch_block` and `control_horn` are mirror-symmetric, so a mirrored "left" part
  is the same part turned over. Print the quantity shown (the plates already hold every copy);
  any copy fits either side. `check_parts.py` verifies this for every shared file. The wing tip
  fairings are not symmetric (the Clark Y is cambered): print `tip_fairing_l` and
  `tip_fairing_r`.
- **Plates.** Each copy on a plate is its own object, named after its part (`hatch_block_3`), so
  the printer can cancel one that comes loose and finish the rest; reprint it from its own
  file. The parts keep 6 mm apart (at least 4.5 mm on the layout grid), close enough that
  neighbours' brims may print joined (cut them apart), and 15 mm from the bed's edge, room for
  the widest auto brim (13.6 mm, on the fuselage couplers). `check_parts.py` checks that the
  plates hold every PETG print exactly once, that the G-code puts each part where the layout
  does, and that no brim is cut off at the bed's edge.
- **240 mm parts on the X.** `fuse_1`, `fuse_3` and both V-tail panels are 240 mm tall; they
  print on the X (260 mm). Nothing on the S1 is taller than 217 mm.

Status values: not sliced / sliced / printing / printed / fitted / failed. Superseded v0.1 parts and their
G-code (nacelles, brackets, sleeves, pivot blocks, socket rear mount) were deleted; do not
print anything that is not in these tables.
