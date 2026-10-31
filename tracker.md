# VTOL Plane — Print Tracker (v0.2)

Two printers: **S1** = Anycubic Kobra S1 (250³ mm, enclosed),
**X** = Anycubic Kobra X (260³ mm, open frame).
Rule: LW-PLA skins are split by hand (right-hand set + `fuse_1`/`fuse_3` on the S1,
left-hand set + `fuse_2`/`fuse_4` on the X). All PETG parts go on the S1.

G-code is in `gcode/<printer>_<lwpla|petg>/<part>.gcode`. Mass and time are the
slicer's estimates (Anycubic Slicer Next 1.3.3.3). One file = one copy: print `Qty` copies.
Weigh every part as it comes off the bed. An LW-PLA part more than ~15 % off the mass below
means the flow is wrong; recalibrate before printing more.

| Part | Material | Printer | Qty | Mass each (g) | Time each | Status |
|---|---|---|---|---|---|---|
| `aileron_mid_r` | LW-PLA vase | S1 | 1 | 5.1 | 2h 17m | sliced |
| `aileron_tip_r` | LW-PLA vase | S1 | 1 | 4.8 | 2h 27m | sliced |
| `fuse_1` (removable nose) | LW-PLA vase | S1 | 1 | 18.2 | 2h 43m | sliced |
| `fuse_3` | LW-PLA vase | S1 | 1 | 22.5 | 2h 46m | sliced |
| `ruddervator_r` | LW-PLA vase | S1 | 1 | 5.4 | 2h 36m | sliced |
| `vtail_r` | LW-PLA vase | S1 | 1 | 13.7 | 2h 45m | sliced |
| `wing_mid_r` | LW-PLA vase | S1 | 1 | 15.8 | 2h 22m | sliced |
| `wing_root_r` | LW-PLA vase | S1 | 1 | 23.8 | 2h 31m | sliced |
| `wing_tip_r` | LW-PLA vase | S1 | 1 | 14.7 | 2h 30m | sliced |
| `aileron_mid_l` | LW-PLA vase | X | 1 | 5.1 | 2h 16m | sliced |
| `aileron_tip_l` | LW-PLA vase | X | 1 | 4.8 | 2h 25m | sliced |
| `fuse_2` | LW-PLA vase | X | 1 | 13.9 | 1h 33m | sliced |
| `fuse_4` | LW-PLA vase | X | 1 | 8.0 | 1h 45m | sliced |
| `ruddervator_l` | LW-PLA vase | X | 1 | 5.4 | 2h 34m | sliced |
| `vtail_l` | LW-PLA vase | X | 1 | 13.7 | 2h 46m | sliced |
| `wing_mid_l` | LW-PLA vase | X | 1 | 15.8 | 2h 21m | sliced |
| `wing_root_l` | LW-PLA vase | X | 1 | 23.8 | 2h 29m | sliced |
| `wing_tip_l` | LW-PLA vase | X | 1 | 14.7 | 2h 29m | sliced |
| `battery_tray` | PETG | S1 | 1 | 19.3 | 0h 47m | sliced |
| `boom_pod_l` | PETG + supports | S1 | 1 | 31.9 | 1h 25m | sliced |
| `boom_pod_r` | PETG + supports | S1 | 1 | 31.9 | 1h 25m | sliced |
| `boom_rib_l` | PETG + supports | S1 | 1 | 38.0 | 2h 03m | sliced |
| `boom_rib_r` | PETG + supports | S1 | 1 | 38.4 | 2h 05m | sliced |
| `control_horn` | PETG | S1 | 6 | 0.6 | 0h 11m | sliced |
| `coupler_240` | PETG | S1 | 1 | 20.4 | 0h 40m | sliced |
| `coupler_370` | PETG | S1 | 1 | 19.2 | 0h 37m | sliced |
| `coupler_610` | PETG | S1 | 1 | 22.4 | 0h 52m | sliced |
| `fc_shelf` | PETG | S1 | 1 | 15.3 | 0h 34m | sliced |
| `frame_main` | PETG | S1 | 1 | 20.1 | 0h 49m | sliced |
| `frame_rear` | PETG | S1 | 1 | 14.9 | 0h 37m | sliced |
| `pod_collar` | PETG | S1 | 1 | 4.7 | 0h 16m | sliced |
| `rear_motor_mount` | PETG + supports | S1 | 1 | 14.2 | 0h 52m | sliced |
| `rib_midtip_l` | PETG | S1 | 1 | 14.7 | 0h 35m | sliced |
| `rib_midtip_r` | PETG | S1 | 1 | 14.7 | 0h 35m | sliced |
| `rib_root_l` | PETG | S1 | 1 | 16.1 | 0h 36m | sliced |
| `rib_root_r` | PETG | S1 | 1 | 16.1 | 0h 37m | sliced |
| `rib_tip_l` | PETG | S1 | 1 | 7.9 | 0h 21m | sliced |
| `rib_tip_r` | PETG | S1 | 1 | 7.9 | 0h 21m | sliced |
| `servo_cage` | PETG | S1 | 6 | 2.1 | 0h 14m | sliced |
| `tail_block` | PETG | S1 | 1 | 28.2 | 1h 09m | sliced |
| `vtail_root_rib` (same file L and R) | PETG | S1 | 2 | 9.2 | 0h 23m | sliced |
| `vtail_tip_cap` (same file L and R) | PETG | S1 | 2 | 2.8 | 0h 11m | sliced |
| `yoke_l` | PETG | S1 | 1 | 12.6 | 0h 44m | sliced |
| `yoke_r` | PETG | S1 | 1 | 12.6 | 0h 44m | sliced |

Totals, quantities included:

| Printer | Material | Mass | Time |
|---|---|---|---|
| S1 | LW-PLA | 124 g | 23.0 h |
| X | LW-PLA | 105 g | 20.7 h |
| S1 | PETG (incl. supports) | 462 g | 22.7 h |

Suggested order: one `wing_tip_r` first as the LW-PLA flow test (target 14.7 g); then the
PETG ribs, so each spigot can be test-fitted in its skin before the full set is printed.

Status values: sliced / printing / printed / fitted / failed. Superseded v0.1 parts and their
G-code (nacelles, brackets, sleeves, pivot blocks, socket rear mount) were deleted; do not
print anything that is not in this table.
