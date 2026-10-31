# VTOL Plane — Bill of Materials (v0.1)

Quantities for one airframe. Prices intentionally left out — verify at
purchase time; nothing here is ordered yet.

## Printed parts

| Part | Qty | Material | Notes |
|---|---|---|---|
| Wing root section | 2 (L+R mirrored) | LW-PLA | vase mode |
| Wing mid section | 2 (L+R mirrored) | LW-PLA | vase mode |
| Wing tip section | 2 (L+R mirrored) | LW-PLA | vase mode |
| Fuselage sections 1–4 | 1 each | LW-PLA | vase mode |
| V-tail panel | 2 (mirrored) | LW-PLA | vase mode |
| Tilt nacelle | 2 | PETG | 3 walls, 20% infill |
| Motor mount | 3 | PETG | 100% infill |
| Wing boom (tilt) | 2 | PETG | 3 walls, 20% infill |
| Servo doors, FC mount | set | PETG | brass inserts |

Filament estimate (until sliced): LW-PLA ~700–900 g, PETG ~200–300 g.

## Electronics

| Item | Qty | Notes |
|---|---|---|
| Flight controller, Pixhawk 6C | 1 | PX4 tilt-rotor VTOL |
| GPS + compass module (M10 class) | 1 | mount away from power wiring |
| Digital airspeed sensor (MS4525DO class) | 1 | PX4 transitions use airspeed |
| Pitot tube for airspeed sensor | 1 | was missing from the BOM entirely — transitions are blind without it |
| Motor, 2807 1300KV class | 3 | Emax ECOII 2807 / T-Motor F90 |
| ESC, 45A BLHeli_S | 3 | individual, not 4-in-1 |
| Propeller 7×4.5 | 3 + spares | two CCW, one CW |
| Tilt servo, metal gear (Kingmax 1203MD / GDW DS041MG class) | 2 | |
| Servo, 9 g metal gear (aileron) | 2 | |
| Servo, 9 g metal gear (V-tail ruddervator) | 2 | |
| ELRS 2.4 GHz receiver | 1 | manual backup link |
| Battery, 4S 5000 mAh LiPo | 1 + spare | XT60 |
| Power module (PM02 class) | 1 | FC power + voltage/current sensing |

## Hardware and consumables

| Item | Qty | Notes |
|---|---|---|
| Carbon tube, 8 mm OD (main spar) | 2 × 650 mm | one per panel; sand + epoxy, not CA alone (smooth carbon sheds CA) |
| Carbon tube, 6 mm OD (rear spar) | 2 × 650 mm | |
| Carbon rod, 3 mm (V-tail pivots) | 2 × 50 mm | 30 mm glued into the panel root + 20 mm into the pivot block |
| Flanged bearing 3×8×4 mm | 2 | tilt pivots |
| Steel rod, 3 mm (tilt pivot shaft) | 2 | |
| Crush-spacer sleeve, ~5 mm OD tube | 2 × ~25 mm | inside the wing under each nacelle through-bolt — without it the bolt crushes the vase shell |
| Screws M3×6 (motor mount) | 12 | verify by hand: no screw may touch the motor windings |
| Screws M2×8, M3 assortment | set | |
| Brass inserts M2/M3 | set | servo doors, FC mount |
| Control horns, pushrods, linkages | set | V-tail horns are printed; drill their 2.2 mm holes after printing |
| Servo extension leads | set | wing + tail runs |
| CA glue, epoxy (spar + pivot-rod bonding) | — | |
| Heat shrink / braid for wire protection | — | anywhere wires cross carbon spars — carbon is conductive |
| Velcro straps, XT60 connectors | — | |
| Spare propellers, 7×4.5 | 2 sets | a crash without spares ends the project for weeks |

## Already owned / to confirm

- Anycubic Kobra S1 + Kobra X (printers)
- Radio transmitter (ELRS-compatible — confirm model)
- Charger for 4S LiPo (confirm)
- LW-PLA and PETG filament stock (confirm colors/quantities on hand)
