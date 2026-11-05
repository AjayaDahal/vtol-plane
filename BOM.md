# VTOL Plane — Bill of Materials (v0.2)

Quantities for one airframe. Prices intentionally left out — verify at
purchase time; nothing here is ordered yet. Every printed part is listed
with its printer, mass, print time and status in `tracker.md`; where each
part goes and how it is assembled is in `DESIGN.md`. This list is for the
4S design. For the planned 3S build with the owner's parts (`PLAN_3S.md`),
`BOM_3S.csv` lists every item, from his parts or to buy.

## Printed parts

| Part | Qty | Material | Notes |
|---|---|---|---|
| Fuselage sections `fuse_1`..`fuse_4` | 1 each | LW-PLA vase | `fuse_1` is the removable nose |
| Wing sections root / mid / tip | 1 L + 1 R each | LW-PLA vase | L and R are mirror images (different files); root and mid carry internal webs |
| Ailerons mid / tip | 1 L + 1 R each | LW-PLA vase | one servo per aileron |
| V-tail panels | 1 L + 1 R | LW-PLA vase | fixed panels |
| Ruddervators | 1 L + 1 R | LW-PLA vase | |
| Wing ribs root / mid-tip | 1 L + 1 R each | PETG | spigots slide into the skins, spar bosses |
| Wing tip ring (`rib_tip`) | 1 L + 1 R | PETG | hidden under the joint between the tip skin and the tip fairing; the spar ends sit in its bosses |
| Wing tip fairings | 1 L + 1 R | LW-PLA vase | close the wing tips (Hoerner-style); L and R are mirror images |
| Boom rib + boom cup | 1 L + 1 R each | PETG | the cup is the rib's inboard spigot ring, glued on (prints flat, no supports) |
| Boom pod | 1 L + 1 R | PETG | tilt-servo bay, plug pocket under it, axle boss |
| Tilt yoke (motor mount) | 1 L + 1 R | PETG | 19×19 mm motor pattern |
| Couplers 240 / 370 / 610 | 1 each | PETG | 610 carries the tail-boom web |
| Frames main / rear | 1 each | PETG | joiner sleeves at the spar stations |
| FC shelf, battery tray, pod collar | 1 each | PETG | the shelf also carries the ESC block underneath |
| GPS mount | 1 | PETG | saddle glued on top of `fuse_3`; the GPS lives outside |
| Rear motor mount | 1 | PETG | clamps the tail boom, vertical thrust |
| Tail block | 1 | PETG | carries both V-tail panels |
| V-tail root rib, V-tail tip ring (`vtail_tip_cap`) | 2 each | PETG | one file for both sides: the parts are mirror-symmetric, so either copy fits either side |
| V-tail tip fairing | 2 | LW-PLA vase | one file for both sides (symmetric) |
| Servo hatch | 6 | PETG | one per aileron and ruddervator servo: the servo screws to it, two M2 screws hold it in the skin; one file, mirror-symmetric |
| Hatch block | 12 | PETG | two per hatch, epoxied inside the skin; the hatch screws go into them |
| Control horn | 6 | PETG | 4 ailerons + 2 ruddervators |

## Filament

| Filament | Printer | Needed (from the G-code) | Buy |
|---|---|---|---|
| LW-PLA, **active-foaming**, 1.75 mm | Kobra X: every skin | 266 g | one spool: SainSmart LW-PLA 1 kg (free delivery on Amazon), Bambu Lab PLA Aero 1 kg or colorFabb LW-PLA 750 g |
| PETG, 1.75 mm | Kobra S1: every PETG part, as plates | 464 g | one 1 kg spool, any brand |

One spool of each covers the parts, the test prints and a few reprints: each printer runs
one material. No part needs supports.

**Pick a light colour** (natural, white or yellow) and keep the plane in the shade between
flights. LW-PLA, like any PLA, softens at 55–60 °C (Polymaker's data sheet: heat deflection
54 °C), and dark skins in summer sun get that hot.

**The LW-PLA must be the kind that foams in the nozzle.** It swells in the hot nozzle
(colorFabb: nearly 3× at 250 °C, where it prints at 45 % flow), so the profile feeds 55 % at
235 °C and the walls come out at ~0.68 g/cm³. The flow test print (`wing_tip_r`, 14.7 g)
tunes the flow for the spool you have. Checked against the profile (Nov 2026, US prices):

| LW-PLA | Spool | Price | Shipping | Notes |
|---|---|---|---|---|
| SainSmart LW-PLA, white | 1 kg | $47.49, Amazon | free, no Prime needed | foams above 210 °C, down to 0.54 g/cm³ |
| Bambu Lab PLA Aero, white or light grey | 1 kg with spool | $26.99, Bambu US store | $6.99 under $59; free over $59 or with 4 filaments | Bambu's foaming table gives a minimum flow of ~0.53 at 235 °C, against the profile's 0.55: the walls fill at ~0.67 g/cm³. Order the PETG with it |
| colorFabb LW-PLA | 750 g | $40.50, Amazon | $11 | the reference: up to ~3× at 250 °C |
| eSUN PLA-LW | 1 kg | | | foams up to 2.2× |
| Creality Lightweight PLA | 1 kg | $51.43, Amazon | free | foams less (about 0.8 g/cm³ in Creality's own figures), so heavier skins: not recommended |

**Pre-foamed lightweight PLA does not fit these files.** Polymaker PolyLite LW-PLA (0.9 g/cm³),
SUNLU LW-PLA and Overture Air PLA come foamed on the spool and print like normal PLA, at full
flow and 190–210 °C. Printed from these files they get about half the plastic they need: thin,
weak walls. With a profile of their own they would print well, but the skins come out ~85 g
heavier. The 4S design's hover margin cannot carry that, and the 3S plan would lose its
margin in its pessimistic case (`REPORT.md` 10.1).

**Use normal PETG.** A foaming PETG exists (eSUN PETG-LW: 40–60 % flow at 240–270 °C), but the
PETG parts carry the loads: the motor yokes and mounts, the ribs around the spars, the couplers
and frames, the screws and heat-set inserts. Their fits are sized for solid PETG. Foamed walls
are weaker and their size varies with the foaming.

## Electronics

| Item | Qty | Notes |
|---|---|---|
| Flight controller, Pixhawk 6C | 1 | PX4 tilt-rotor VTOL |
| GPS + compass module (M10 class, ≤ 50 mm round) | 1 | on the external saddle on top of `fuse_3`; a Holybro M10 also carries the safety button, LED and buzzer |
| Digital airspeed sensor (MS4525DO class) | 1 | PX4 transitions use airspeed |
| Pitot tube for airspeed sensor | 1 | right wing mid-section LE at y≈400 mm, outside the prop disc (tip section at y≈505 for the 3S build's 12 in props, `PLAN_3S.md`) |
| Motor, Emax ECOII 2807 **1700KV** | 3 | Emax's 4S winding, 19×19 mm M3. The 1300KV version is the 6S winding: on 4S it gives only ~1.35 kg, too little margin at ~2.0 kg AUW. Use 1300KV only with a 6S pack |
| ESC, 50 A, DShot (BLHeli_32 or BLHeli_S) | 3 | 1700KV + 7 in pulls ~46 A at full throttle, so 45 A is too small. Body ≤ 50 × 28 × 12 mm with heat-shrink: the three are taped into one block under the FC shelf |
| Propeller 7×4.5 | 1 CW + 2 CCW + spares | front right CW, front left CCW, rear CCW (Stallion order) |
| Tilt servo, Kingmax KM1203MD (12 mm mini, 20 g, ~9 kg·cm, metal gear) | 2 | bay fits 24×13 mm bodies with 28 mm tab pitch; tab-to-spline ≈ 11 mm; use its round (disc) horn |
| Servo, 9 g metal gear (ailerons) | 4 | one per aileron; body ≤ 23 × 12.2 mm, tab holes 28 mm apart (it screws to its hatch's posts) |
| Servo, 9 g metal gear (ruddervators) | 2 | as the aileron servos |
| ELRS 2.4 GHz receiver | 1 | manual backup link |
| Battery, 4S 5000 mAh LiPo (≥ 50C) | 1 + spare | XT60; ~155×48×37 mm |
| Power module | 1 | FC power + V/I sensing; rated ≥ 40 A continuous, ≥ 140 A peak — check the rating of the one you buy |
| Servo BEC, 5–6 V, ≥ 5 A | 1 | the Pixhawk does not power the servo rail; 8 servos incl. two 20 g tilt servos |

## Hardware and consumables

| Item | Qty | Notes |
|---|---|---|
| Carbon tube 10×8 mm (main spar) | 2 × 650 mm | one per panel; sand + epoxy into every rib (smooth carbon sheds CA) |
| Carbon tube 6×4 mm (rear spar) | 2 × 650 mm | |
| Carbon tube 8×6 mm (main joiner) | 1 × 420 mm | slides 150 mm into both main spars, through the main frame sleeve |
| Carbon rod 4 mm (rear joiner) | 1 × 320 mm | inside both rear spars, through the rear frame sleeve |
| Carbon tube 16×14 mm (tail boom) | 1 × 630 mm | x = 420 to 1050; motor and servo wires run inside it |
| Carbon rod 4 mm (V-tail pins) | 2 × 20 mm | 8 mm into the tail block, 12 mm into the V-tail root rib |
| Carbon rod 3 mm (battery stop pin) | 1 × 25 mm | tray pin holes every 10 mm |
| Flanged bearing 3×8×4 mm (F693ZZ) | 2 | one per tilt yoke (the servo horn is the other pivot) |
| M3 shim washer, 0.5 mm thick, OD ≤ 5 mm | 2 + spares | between each bearing's inner race and the axle boss; without it the axle screw pulls the yoke against the pod and it binds |
| M3 heat-set inserts | 4 | 2 tilt axles, 1 nose screw, 1 spare |
| M3×12 socket screw + washer (tilt axle) | 2 | through the bearing and shim into the axle-boss insert |
| M3×35 bolt + nyloc nut | 4 | boom pod to boom-rib tongue (with epoxy); the pod is 28 mm wide |
| M3×8 screws (motors) | 12 | 4 mm plates: 4 mm of thread; check by hand that none touches the windings |
| M3×16 bolt + nut + washer (rear motor clamp) | 2 | |
| M3×12 nylon screw + 12 mm nylon washer | 1 + spare | holds the removable nose; an M3 nylon thumb screw makes battery changes tool-free |
| M2.5 nylon screw or pin | 2 | locks each rear spar to the rear joiner (drill guide in the root rib) |
| M2×6 screws | 12 + spares | two per servo hatch, into its hatch blocks |
| M2×6 self-tapping screws | 4 | two per tilt yoke, through the inboard arm into the servo's disc horn |
| Pushrods 1.2 mm steel, snap clevis or EZ connector | 6 | ailerons and ruddervators: Z-bend in the servo arm, clevis at the horn (sets the neutral, and unhooks so a hatch can come out) |
| Hinge tape (Blenderm or similar) | 1 roll | top-surface hinges |
| Servo extension leads | set | 500 mm ×2 (mid ailerons), 600 mm ×2 (tilt servos, from the pod's plug pocket), 800 mm ×2 (tip ailerons): to the plugs at x ≈ 330 in the fuselage; 650 mm ×2 (ruddervators, pulled through the boom). Each servo's own plug meets its extension where a hatch or the plug pocket reaches it |
| Silicone wire 16 AWG, 3 colours | ~5 m | motor phase leads: front motors extended ~550 mm to the plugs at x ≈ 330, rear motor ~450 mm (inside the boom), plus pigtails to the ESC block. The joints to the motors' own leads sit outside the pods and the boom |
| 3.5 mm bullet connectors | 6 pairs + spares | the wing motor-lead plugs, reachable through the nose; 9 more pairs if you want the motors themselves to unplug (~7 g, see `DESIGN.md`) |
| Fish tape or 1 mm stiff wire | ~1 m | pulls the leads through the boom once the motor mount and tail block are on |
| Pull cord (thin nylon) | ~1 m | lays the GPS cable through `fuse_3` before `fuse_4` goes on |
| Epoxy (30 min) + microballoons, CA | — | epoxy for all carbon bonds |
| Heat shrink / braid for wire protection | — | anywhere wires cross carbon — carbon is conductive |
| Velcro one-wrap strap, 20 mm | 2 × 300 mm + 2 × 200 mm | two hold the battery (threaded through the tray before it is glued in), two hang the ESC block |
| XT60 connectors | 2 | battery lead |
| Foam: 3 mm sheet, double-sided foam tape | small | between the ESCs, under the Pixhawk and the GPS |
| Nylon mesh (optional) | scrap | inside the nose-tip air inlet, keeps grass out |
| EVA foam strip 5–10 mm | ~250 × 40 mm | belly landing pad (the plane lands on its LW-PLA belly) |
| Spare propellers, 7×4.5 | 2 sets | a crash without spares ends the project for weeks |

## Already owned / to confirm

- Anycubic Kobra S1 + Kobra X (printers)
- Radio transmitter (ELRS-compatible — confirm model)
- Charger for 4S LiPo (confirm)
- LW-PLA and PETG filament stock (confirm colors/quantities on hand)
