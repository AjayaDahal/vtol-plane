# VTOL Plane — Print Tracker (v0.2)

Two printers: **S1** = Anycubic Kobra S1 (250³ mm, enclosed),
**X** = Anycubic Kobra X (260³ mm, open frame).
Rule: LW-PLA skins are split by hand (right-hand set + `fuse_1`/`fuse_3` on the S1,
left-hand set + `fuse_2`/`fuse_4` on the X). All PETG parts go on the S1. No part needs supports.

G-code is in `gcode/<printer>_<lwpla|petg>/<part>.gcode`. Mass and time are the
slicer's estimates (Anycubic Slicer Next 1.3.3.3). One file = one copy: print `Qty` copies.
Weigh every part as it comes off the bed. An LW-PLA part more than ~15 % off the mass below
means the flow is wrong; recalibrate before printing more. Where each part goes: `DESIGN.md`.

## Reminders for print time (agents: raise these with the user when printing starts)

- [ ] **Print quality is unverified.** G-code checks cannot show it. The LW-PLA flow of 0.55 and
  the vase-mode walls need a real test print, such as `wing_tip_r` (target 14.7 g), before the
  full set is printed. All vase parts print at 17–30 mm/s, so one calibration covers them all.
- [ ] **Spigot fit.** Print `rib_tip_r` and slide it into that `wing_tip_r` before printing the
  other ribs and couplers. It should go in with light hand force; sand the ring if it is tight.
- [ ] **Tilt servo size.** Measure the tilt servos against the pod bay (24 × 13 mm body, 21 mm
  deep, tab holes 28 mm apart, spline 6 mm from the front) before printing the pods and yokes.
  If they differ, change `SERVO_*` in `scripts/params.py` and rebuild.
- [ ] **Axle shims.** Have two 0.5 mm M3 shim washers (OD ≤ 5 mm) before assembling the yokes;
  without them the yoke binds against the pod.
- [x] ~~Boom-rib supports: watch the tree supports on the `boom_rib_l/r` parts on their first
  print.~~ No longer applies: the boom rib now prints flat with no supports. Its inboard ring
  is the separate `boom_cup`.

Tick a box once the user confirms it is done.

Suggested order: `wing_tip_r` (flow test), then `rib_tip_r` (fit test), then the rest.

| Part | Material | Printer | Qty | Mass each (g) | Time each | Status |
|---|---|---|---|---|---|---|
| `aileron_mid_r` | LW-PLA vase | S1 | 1 | 5.1 | 1h 12m | sliced |
| `aileron_tip_r` | LW-PLA vase | S1 | 1 | 4.8 | 1h 16m | sliced |
| `fuse_1` (removable nose) | LW-PLA vase | S1 | 1 | 18.2 | 3h 22m | sliced |
| `fuse_3` | LW-PLA vase | S1 | 1 | 22.5 | 4h 04m | sliced |
| `ruddervator_r` | LW-PLA vase | S1 | 1 | 5.4 | 1h 23m | sliced |
| `vtail_r` | LW-PLA vase | S1 | 1 | 13.7 | 2h 31m | sliced |
| `wing_mid_r` | LW-PLA vase | S1 | 1 | 15.8 | 2h 53m | sliced |
| `wing_root_r` | LW-PLA vase | S1 | 1 | 23.8 | 4h 21m | sliced |
| `wing_tip_r` | LW-PLA vase | S1 | 1 | 14.7 | 2h 41m | sliced |
| `aileron_mid_l` | LW-PLA vase | X | 1 | 5.1 | 1h 11m | sliced |
| `aileron_tip_l` | LW-PLA vase | X | 1 | 4.8 | 1h 15m | sliced |
| `fuse_2` | LW-PLA vase | X | 1 | 13.9 | 2h 32m | sliced |
| `fuse_4` | LW-PLA vase | X | 1 | 8.0 | 1h 30m | sliced |
| `ruddervator_l` | LW-PLA vase | X | 1 | 5.4 | 1h 22m | sliced |
| `vtail_l` | LW-PLA vase | X | 1 | 13.7 | 2h 31m | sliced |
| `wing_mid_l` | LW-PLA vase | X | 1 | 15.8 | 2h 53m | sliced |
| `wing_root_l` | LW-PLA vase | X | 1 | 23.8 | 4h 19m | sliced |
| `wing_tip_l` | LW-PLA vase | X | 1 | 14.7 | 2h 41m | sliced |
| `battery_tray` | PETG | S1 | 1 | 19.3 | 0h 47m | sliced |
| `boom_cup_l` | PETG | S1 | 1 | 9.2 | 0h 23m | sliced |
| `boom_cup_r` | PETG | S1 | 1 | 9.2 | 0h 23m | sliced |
| `boom_pod_l` | PETG | S1 | 1 | 28.5 | 1h 03m | sliced |
| `boom_pod_r` | PETG | S1 | 1 | 28.5 | 1h 04m | sliced |
| `boom_rib_l` | PETG | S1 | 1 | 22.7 | 0h 52m | sliced |
| `boom_rib_r` | PETG | S1 | 1 | 22.5 | 0h 51m | sliced |
| `control_horn` | PETG | S1 | 6 | 0.6 | 0h 12m | sliced |
| `coupler_240` | PETG | S1 | 1 | 20.5 | 0h 40m | sliced |
| `coupler_370` | PETG | S1 | 1 | 19.2 | 0h 37m | sliced |
| `coupler_610` | PETG | S1 | 1 | 22.4 | 0h 53m | sliced |
| `fc_shelf` | PETG | S1 | 1 | 15.3 | 0h 35m | sliced |
| `frame_main` | PETG | S1 | 1 | 20.3 | 0h 49m | sliced |
| `frame_rear` | PETG | S1 | 1 | 14.9 | 0h 38m | sliced |
| `pod_collar` | PETG | S1 | 1 | 4.7 | 0h 16m | sliced |
| `rear_motor_mount` | PETG | S1 | 1 | 18.1 | 0h 43m | sliced |
| `rib_midtip_l` | PETG | S1 | 1 | 15.0 | 0h 35m | sliced |
| `rib_midtip_r` | PETG | S1 | 1 | 15.0 | 0h 36m | sliced |
| `rib_root_l` | PETG | S1 | 1 | 16.1 | 0h 37m | sliced |
| `rib_root_r` | PETG | S1 | 1 | 16.1 | 0h 37m | sliced |
| `rib_tip_l` | PETG | S1 | 1 | 8.1 | 0h 21m | sliced |
| `rib_tip_r` | PETG | S1 | 1 | 8.1 | 0h 21m | sliced |
| `servo_cage` | PETG | S1 | 6 | 2.1 | 0h 15m | sliced |
| `tail_block` | PETG | S1 | 1 | 28.2 | 1h 10m | sliced |
| `vtail_root_rib` (one file, both sides) | PETG | S1 | 2 | 9.3 | 0h 23m | sliced |
| `vtail_tip_cap` (one file, both sides) | PETG | S1 | 2 | 2.9 | 0h 12m | sliced |
| `yoke_l` | PETG | S1 | 1 | 12.6 | 0h 44m | sliced |
| `yoke_r` | PETG | S1 | 1 | 12.6 | 0h 44m | sliced |

Totals, quantities included:

| Printer | Material | Mass | Time |
|---|---|---|---|
| S1 | LW-PLA | 124 g | 23.7 h |
| X | LW-PLA | 105 g | 20.2 h |
| S1 | PETG | 448 g | 20.2 h |

Notes:

- **One file for both sides.** `vtail_root_rib`, `vtail_tip_cap`, `servo_cage` and
  `control_horn` are mirror-symmetric, so a mirrored "left" part is the same part turned over.
  Print the quantity shown; any copy fits either side. `check_parts.py` verifies this for every
  shared file.
- **240 mm parts on the S1.** `fuse_1`, `fuse_3` and `vtail_r` are 240 mm tall. The highest move is
  242 mm, the 2 mm lift after the last layer, against the S1's 250 mm printable height. The
  slicer's 240 mm "height to lid" setting only applies to by-object printing, which this
  project does not use. Leave the lid on.

Status values: sliced / printing / printed / fitted / failed. Superseded v0.1 parts and their
G-code (nacelles, brackets, sleeves, pivot blocks, socket rear mount) were deleted; do not
print anything that is not in this table.
