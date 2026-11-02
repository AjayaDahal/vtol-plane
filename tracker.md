# VTOL Plane — Print Tracker (v0.2)

Two printers: **S1** = Anycubic Kobra S1 (250³ mm, enclosed),
**X** = Anycubic Kobra X (260³ mm, open frame).
Rule: LW-PLA skins are split by hand (right-hand set + `fuse_1`/`fuse_3` on the S1,
left-hand set + `fuse_2`/`fuse_4` and both V-tail tip fairings on the X). All PETG parts go on
the S1. No part needs supports.

G-code is in `gcode/<printer>_<lwpla|petg>/<part>.gcode`. Mass and time are the
slicer's estimates (Anycubic Slicer Next 1.3.3.3). One file = one copy: print `Qty` copies.
The print table and totals are written from the sliced files by `scripts/make_tracker.py`;
only the Status column and the notes in brackets are edited by hand.
Weigh every part as it comes off the bed. An LW-PLA part more than ~15 % off the mass below
means the flow is wrong; recalibrate before printing more. Where each part goes: `DESIGN.md`.

## Reminders for print time (agents: raise these with the user when printing starts)

- [ ] **Print quality is unverified.** G-code checks cannot show it. The LW-PLA flow of 0.55 and
  the vase-mode walls need a real test print, such as `wing_tip_r` (target 14.7 g), before the
  full set is printed. All vase parts print at 17–30 mm/s, so one calibration covers them all.
- [ ] **Spigot fit.** Print `rib_tip_r` (the hidden tip ring) and slide its inboard half into
  that `wing_tip_r` before printing the other ribs and couplers. It should go in with light hand
  force; sand the ring if it is tight.
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
  deep, tab holes 28 mm apart, spline 6 mm from the front) before printing the pods and yokes.
  If they differ, change `SERVO_*` in `scripts/params.py` and rebuild.
- [ ] **Axle shims.** Have two 0.5 mm M3 shim washers (OD ≤ 5 mm) before assembling the yokes;
  without them the yoke binds against the pod.
- [ ] **Servo hatch fit.** Print one `servo_hatch` and two `hatch_block`s before the other five.
  The 9 g servo's tabs must screw to the posts (holes 28 mm apart) with its body (up to 23 ×
  12.2 mm) between them, and its horn must stay within 15 mm of the cover's centre.
- [ ] **Battery straps before the tray is glued.** The two Velcro straps thread through the
  `battery_tray` (down a slot, under the plate through the rail gaps, up the other slot); once
  the tray is epoxied in they cannot be fitted (`DESIGN.md` step 3.8).
- [x] ~~Boom-rib supports: watch the tree supports on the `boom_rib_l/r` parts on their first
  print.~~ No longer applies: the boom rib now prints flat with no supports. Its inboard ring
  is the separate `boom_cup`.

Tick a box once the user confirms it is done.

Suggested order: `wing_tip_r` (flow test), then `rib_tip_r` (fit test) and `tip_fairing_r`
(closing-tip test), then `wing_mid_r` (web check), one `servo_hatch` with two `hatch_block`s
(servo fit), then the rest. To see every print
file on its bed with its mass and time, open the 3D viewer (`python scripts/serve_viewer.py`)
and press "Show the print files", or look at `renders/35_print_files_all.png`.

| Part | Material | Printer | Qty | Mass each (g) | Time each | Status |
|---|---|---|---|---|---|---|
| `aileron_mid_r` | LW-PLA vase | S1 | 1 | 5.1 | 1h 11m | sliced |
| `aileron_tip_r` | LW-PLA vase | S1 | 1 | 4.8 | 1h 16m | sliced |
| `fuse_1` (removable nose) | LW-PLA vase | S1 | 1 | 18.2 | 3h 22m | sliced |
| `fuse_3` | LW-PLA vase | S1 | 1 | 22.5 | 4h 04m | sliced |
| `ruddervator_r` | LW-PLA vase | S1 | 1 | 5.4 | 1h 22m | sliced |
| `tip_fairing_r` | LW-PLA vase | S1 | 1 | 2.6 | 0h 30m | sliced |
| `vtail_r` | LW-PLA vase | S1 | 1 | 13.7 | 2h 31m | sliced |
| `wing_mid_r` | LW-PLA vase | S1 | 1 | 20.7 | 3h 46m | sliced |
| `wing_root_r` | LW-PLA vase | S1 | 1 | 33.5 | 6h 05m | sliced |
| `wing_tip_r` | LW-PLA vase | S1 | 1 | 14.7 | 2h 41m | sliced |
| `aileron_mid_l` | LW-PLA vase | X | 1 | 5.1 | 1h 11m | sliced |
| `aileron_tip_l` | LW-PLA vase | X | 1 | 4.8 | 1h 15m | sliced |
| `fuse_2` | LW-PLA vase | X | 1 | 13.9 | 2h 32m | sliced |
| `fuse_4` | LW-PLA vase | X | 1 | 8.0 | 1h 30m | sliced |
| `ruddervator_l` | LW-PLA vase | X | 1 | 5.4 | 1h 23m | sliced |
| `tip_fairing_l` | LW-PLA vase | X | 1 | 2.6 | 0h 30m | sliced |
| `vtail_l` | LW-PLA vase | X | 1 | 13.7 | 2h 31m | sliced |
| `vtail_tip_fairing` (one file, both sides) | LW-PLA vase | X | 2 | 1.3 | 0h 16m | sliced |
| `wing_mid_l` | LW-PLA vase | X | 1 | 20.7 | 3h 48m | sliced |
| `wing_root_l` | LW-PLA vase | X | 1 | 33.5 | 6h 06m | sliced |
| `wing_tip_l` | LW-PLA vase | X | 1 | 14.7 | 2h 42m | sliced |
| `battery_tray` | PETG | S1 | 1 | 20.4 | 0h 55m | sliced |
| `boom_cup_l` | PETG | S1 | 1 | 9.2 | 0h 23m | sliced |
| `boom_cup_r` | PETG | S1 | 1 | 9.2 | 0h 23m | sliced |
| `boom_pod_l` | PETG | S1 | 1 | 27.9 | 1h 03m | sliced |
| `boom_pod_r` | PETG | S1 | 1 | 27.9 | 1h 03m | sliced |
| `boom_rib_l` | PETG | S1 | 1 | 22.6 | 0h 52m | sliced |
| `boom_rib_r` | PETG | S1 | 1 | 22.4 | 0h 51m | sliced |
| `control_horn` | PETG | S1 | 6 | 0.6 | 0h 12m | sliced |
| `coupler_240` | PETG | S1 | 1 | 20.5 | 0h 40m | sliced |
| `coupler_370` | PETG | S1 | 1 | 19.2 | 0h 37m | sliced |
| `coupler_610` | PETG | S1 | 1 | 22.4 | 0h 53m | sliced |
| `fc_shelf` | PETG | S1 | 1 | 24.3 | 0h 53m | sliced |
| `frame_main` | PETG | S1 | 1 | 20.3 | 0h 49m | sliced |
| `frame_rear` | PETG | S1 | 1 | 14.9 | 0h 38m | sliced |
| `gps_mount` | PETG | S1 | 1 | 7.0 | 0h 20m | sliced |
| `hatch_block` (two per hatch) | PETG | S1 | 12 | 0.8 | 0h 08m | sliced |
| `pod_collar` | PETG | S1 | 1 | 4.7 | 0h 16m | sliced |
| `rear_motor_mount` | PETG | S1 | 1 | 18.1 | 0h 43m | sliced |
| `rib_midtip_l` | PETG | S1 | 1 | 15.0 | 0h 35m | sliced |
| `rib_midtip_r` | PETG | S1 | 1 | 15.0 | 0h 36m | sliced |
| `rib_root_l` | PETG | S1 | 1 | 16.1 | 0h 37m | sliced |
| `rib_root_r` | PETG | S1 | 1 | 16.1 | 0h 37m | sliced |
| `rib_tip_l` (hidden tip ring) | PETG | S1 | 1 | 7.1 | 0h 20m | sliced |
| `rib_tip_r` (hidden tip ring) | PETG | S1 | 1 | 7.1 | 0h 20m | sliced |
| `servo_hatch` (one file for all six) | PETG | S1 | 6 | 3.0 | 0h 17m | sliced |
| `tail_block` | PETG | S1 | 1 | 28.2 | 1h 10m | sliced |
| `vtail_root_rib` (one file, both sides) | PETG | S1 | 2 | 9.3 | 0h 23m | sliced |
| `vtail_tip_cap` (tip ring; one file, both sides) | PETG | S1 | 2 | 2.7 | 0h 12m | sliced |
| `yoke_l` | PETG | S1 | 1 | 12.6 | 0h 44m | sliced |
| `yoke_r` | PETG | S1 | 1 | 12.6 | 0h 44m | sliced |

Totals, quantities included:

| Printer | Material | Mass | Time |
|---|---|---|---|
| S1 | LW-PLA | 141 g | 26.8 h |
| X | LW-PLA | 125 g | 24.0 h |
| S1 | PETG | 476 g | 22.6 h |

Notes:

- **One file for both sides.** `vtail_root_rib`, `vtail_tip_cap`, `vtail_tip_fairing`,
  `servo_hatch`, `hatch_block` and `control_horn` are mirror-symmetric, so a mirrored "left" part
  is the same part turned over. Print the quantity shown; any copy fits either side.
  `check_parts.py` verifies this for every shared file. The wing tip fairings are not
  symmetric (the Clark Y is cambered): print `tip_fairing_l` and `tip_fairing_r`.
- **240 mm parts on the S1.** `fuse_1`, `fuse_3` and `vtail_r` are 240 mm tall. The highest move is
  242 mm, the 2 mm lift after the last layer, against the S1's 250 mm printable height. The
  slicer's 240 mm "height to lid" setting only applies to by-object printing, which this
  project does not use. Leave the lid on.

Status values: not sliced / sliced / printing / printed / fitted / failed. Superseded v0.1 parts and their
G-code (nacelles, brackets, sleeves, pivot blocks, socket rear mount) were deleted; do not
print anything that is not in this table.
