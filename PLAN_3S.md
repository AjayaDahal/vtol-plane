# 3S build plan: flying the parts you already own

> **Status: plan, not built in yet.** The design files still describe the 4S build
> (`DESIGN.md`, `BOM.md`, the G-code). Nothing below is in the CAD until step 3 of
> [Order of work](#order-of-work). Written from the owner's photos of his parts (in
> `gitignore_me/`, not in git) and the repo's own mass balance and gate checks, run on each
> option with the new parts patched in.

## The short answer

- **Keep and use:** the Zeee 3S 8000 mAh hard-case pack (main) and the IPO 3S 6200 (second
  pack), the Cube Black, the Hex Power Brick Mini, the 3DR uBlox GPS + compass and the
  Readytosky 40 A ESCs.
- **Buy:** three SunnySky X2814 **900KV** motors ($29.99 each at SunnySky USA, against $49.99
  for the T-Motor AT2814) and APC 12 × 6 props (see [Motor](#motor)). Also XT60 plugs for the
  Zeee pack and a DF13 → JST-GH cable for the GPS. The whole list, your parts against what to
  buy: [`BOM_3S.csv`](BOM_3S.csv).
- **Leave out:** the Emax 2807 1700KV motors the 4S design calls for; your RS2212 920KV
  motors (too weak) and your 4108 380KV (made for 15 in props on 4–6S); the blue PDB (a
  wiring harness is lighter); the bare PX4FMU v2.4.8 board. The cased Pixhawk 1 is the spare
  flight controller.
- **Printing:** only PETG plates 6 and 7 change: the two yokes and the rear motor mount get the
  new motor's holes, and `fc_shelf` steps down 13 mm under the Cube. **Print everything else
  now** (`tracker.md`).
- **Result (modelled):** an all-up weight of ~2.29 kg. The front motors hover at 48 % of
  their near-empty thrust (the 4S design: 59 %; the limit is 60 %), or ~50–51 % with the
  bigger props' wash on the wing counted. On the Zeee pack that is about 18 min of pure hover
  (the 4S design: 7), drawing 22 A, inside the Power Brick Mini's 30 A rating. Every check that
  was run passes. The margin rests on SunnySky's thrust table, so one motor's thrust is
  measured before anything is built in ([Order of work](#order-of-work), step 2).

## Why the motors have to change

Thrust goes with the square of the voltage. On 3S the 4S design's Emax 2807 1700KV would need
~99 % of its near-empty thrust to hover. Each front motor lifts ~835 g in hover, and the gate
allows at most 60 % of a motor's maximum on a near-empty pack (10.6 V on 3S, under load). So
each motor needs at least ~1.4 kg at 10.6 V, and ~1.5 kg once a 12 in prop's wash on the wing
is counted (risk 1). The prop can be at most
12 in: a 12 in prop passes every clearance check, while a 13 in prop leaves only 9.9 mm
around the rear prop even 50 mm above its mount (the gate wants 10).

None of the motors you have can do it:

| Motor | On 3S |
|---|---|
| Emax ECOII 2807 1700KV (the 4S design's) | would need ~99 % of its near-empty thrust to hover |
| Readytosky RS2212 920KV (you have two) | about 1 kg at most each, barely one front motor's 835 g hover share |
| 4108 380KV (you have one) | made for 15 in props on 4–6S. A 15 in prop does not fit, and on 3S it turns a 12 in prop at only ~4000 rpm: about 0.45 kg |

## Motor

**Buy the SunnySky X2814 900KV**, the standard version: **$29.99** at SunnySky USA
(<https://sunnyskyusa.com/products/sunnysky-x2814-brushless-motors>, in stock in Nov 2026). The
V3 costs $39.99, and the T-Motor AT2814 KV900 $49.99 direct from T-Motor (more from Amazon
resellers). It is the same size as the AT2814: 28 × 14 mm stator, 108 g, 4 mm shaft. It runs
the same APC 12 × 6 prop. On SunnySky's own test table it is slightly stronger than the
AT2814: 1880 g at 11.0 V and 26.4 A on a 12 × 6, against 1720 g at 11.05 V and 27.0 A.

- **It must be the 900KV winding.** On a 12 × 6 the 1000KV draws 35 A at 11 V and the
  1100KV 44 A, so ~42 and ~52 A on a full pack (12.0 V): too much for the 40 A ESCs. The 900KV
  draws ~31 A there.
- **If the table is optimistic.** The table is SunnySky's own (2014), not an independent test.
  With 15 % less thrust than it claims, the front motors would hover at 56 % of their
  near-empty maximum, and at about the 60 % limit once the propwash on the wing (risk 1) is
  counted: where the 4S design is today. So test one motor's thrust as soon as it arrives
  ([Order of work](#order-of-work), step 2). To risk less money, buy one first and test it
  before ordering the rest.
- **In the box** (from the listing's photos): an X-mount, a prop adapter with its nut, and
  screws. The hole pattern is not published, so the yokes and the rear mount get the motor's
  own base holes, measured.
- **Prop height:** with a 12 in prop the disc must sit at least **38 mm** above the motor's
  mounting face. That leaves 10.4 mm around the rear prop; the gate wants 10. At 42 mm the
  clearances are 15.8 mm at the front and 14.4 mm at the rear. If the motor with its prop
  adapter comes out lower, the mount plates move up (`YOKE_PLATE_Z0`, `REAR_PLATE_Z`).
- **The reverse-rotation motor:** the front right motor spins clockwise seen from above, which
  tends to undo the prop adapter's right-hand nut. Use a nyloc nut or medium thread-lock there,
  and check all three nuts before every flight.

All the motors compared, each run through the same model and checks with the Cube Black, the
Readytosky ESCs and the Zeee pack. Currents are scaled by V² to a full pack (12.0 V) and
compared with the 40 A ESCs:

| Motor | Price each | Mass | Prop | Thrust data (source) | Full-throttle current, full pack | Front motor at hover (limit 60 %) | Pure hover | Hover current | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **SunnySky X2814 900KV** | $29.99 | 108 g | APC 12 × 6 | 1880 g at 11.0 V, 26.4 A (SunnySky) | ~31 A | **47.9 %** | **17.8 min** | **21.6 A** | **buy** |
| T-Motor AT2814 KV900 | $49.99 | 108 g | APC 12 × 6 | 1720 g at 11.05 V, 27.0 A (T-Motor) | ~32 A | 52.7 % | 16.4 min | 23.4 A | works, costs more |
| Racerstar BR3536 950KV | $16 | 115 g | APC 10 × 6 | 1580 g at 11.1 V, 35 A (seller) | ~41 A | 58.1 % | 10.4 min | 36.8 A | over the ESCs, no hover margin |
| Propdrive v2 3536 1400KV | ~$31–37 | 121 g | 8 × 6 | 1470 g at ~10.5 V, 30 A (maker) | ~39 A | 55.7 % | 11.6 min | 33.2 A | no better, often out of stock |
| Turnigy 2836 1000KV | ? | 80 g | 10 × 4.7 | 1643 g at 11.6 V, 36 A (independent test) | ~39 A | 58.3 % | 11.5 min | 33.5 A | availability unconfirmed |
| SunnySky X2814 1000 / 1100KV | $29.99 | 108–113 g | 12 × 6 | 2100 / 2300 g at 11 V (SunnySky) | ~42 / ~52 A | – | – | – | over the ESCs |

The Racerstar BR3536 is the cheapest, at $16, but it fails twice. On a full pack it draws
~41 A, over the 40 A ESCs. On its seller's figures it also leaves no hover margin: 58 %
against the 60 % limit before the propwash on the wing (risk 1 below) is counted, and over it
if its table is optimistic. In hover it draws ~37 A, above the Power Brick Mini's 30 A rating,
and it hovers for 10 min instead of 18. It would save ~$42 over three X2814s. Not worth it.

## Results

With the SunnySky X2814 900KV, APC 12 × 6 props, the Cube Black (on a stepped shelf), the
Readytosky ESCs, the Power Brick Mini and the 3DR GPS:

| | 4S design (now) | 3S, Zeee 8000 | 3S, IPO 6200 (estimated) |
|---|---|---|---|
| All-up weight | 2.00 kg | 2.29 kg | 2.25 kg |
| Battery stop pin, CG | x = 380, 29.3 % MAC | x = 380, 29.5 % MAC | x = 370, 29.1 % MAC |
| Front motor at hover, near-empty pack (limit 60 %) | 58.9 % | **47.9 %** | 47.1 % |
| The same with the propwash on the wing (risk 1) | ~59 % | ~50–51 % | ~49–50 % |
| Hover throttle | ~69 % | ~61 % | ~61 % |
| Hover current | ~33 A | 21.6 A | 21.1 A |
| Pure hover time (80 % of the pack) | ~7.3 min | **~17.8 min** | ~14.1 min |
| Static margin | ~18 % | ~18 % | ~18 % |
| PX4 stall / min / transition airspeed | 13 / 16 / 18 m/s | 13 / 17 / 19 m/s | 13 / 16 / 18 m/s |

The 4S column is from the Nov 3 re-slice in Anycubic Slicer Next 2.0.0.3 (`REPORT.md`, round
11). The 3S columns were modelled on the earlier slice, whose PETG weighed ~10 g more, mostly
brims (trimmed off before flight anyway), so they are slightly pessimistic.

The model scales each maker's thrust test by V² to 12.0 V (a full pack under load) and
10.6 V (near empty). Hover power is fitted through the test point nearest hover. The checks
run are the gate's balance, equipment-fit, battery-strap and prop-clearance checks. The IPO
pack's size and mass are estimates (150 × 45 × 32 mm, 450 g); measure it. Each pack has its
own stop-pin hole: the lighter IPO pack sits 10 mm further forward (x = 370) to keep the CG
in the band. Move the pin when you swap packs; `mass_balance.py` gives the hole for the
measured pack.

## What changes in the design

### Printed parts: four, all PETG on plates 6 and 7

| Part | Plate | Change | Why |
|---|---|---|---|
| `yoke_l`, `yoke_r` | `petg_7_pods_yokes` | the new motor's hole pattern (measured); a larger plate if its base needs it | new motor |
| `rear_motor_mount` | `petg_6_fuselage_tail` | the same | new motor |
| `fc_shelf` | `petg_6_fuselage_tail` | its front part, under the Cube, steps down from z = 32 to 19; the aft part, which carries the ESC block, stays at 32 | the Cube's module stands 22.5 mm on its 18 mm carrier. With the shelf at z = 32 the module's top is ~9.5 mm too high for the fuselage's roof on the centreline (~13 mm at its corners), keeping the gate's 2 mm from the skin. At z = 19, on 1 mm foam tape (the Cube isolates its own IMUs), its corners have 1–2 mm to spare, most with the module at the carrier's front. Lowering the whole shelf would bring the ESC block down to 5.5 mm above the battery (18.5 mm now), so the aft part stays put |

With the Pixhawk 1 instead of the Cube, `fc_shelf` stays as it is. The rest of plate 6
(`battery_tray`, `gps_mount`, `pod_collar`, `tail_block`) does not change. If you want those
four early, print them now from their single files in `gcode/s1_petg/` and mark them printed in
`tracker.md`. When the plan is built in, the changed parts get a plate of their own and the
four keep theirs, which you then skip (the gate needs every PETG part on exactly one plate).
The pods (`boom_pod_l/r`) wait with plate 7: a bigger motor plate on the yoke may need more
room in the pod's tilt sweep. The 3DR GPS (38 mm square) sits on the 52 mm saddle, and the
Zeee pack (138 × 47 × 36 mm) fits the tray and its straps as they are.

### The pitot moves outboard (no printed part changes)

The front motors sit at y = ±280 mm. A 12 in disc reaches y = 432, so the pitot at y = 400
would sit in the propwash: it would read high during the front transition and end it early,
a stall at low height. It moves into the tip section at **y ≈ 505**, 73 mm outside the disc
(the 4S design keeps it 31 mm outside its 7 in disc): between the end of the mid/tip rib's
spigot (y = 500) and the tip aileron servo (from y = 518). The tip section has no webs, so
the hole is drilled there by hand instead of in `wing_mid_r`. The gap at y = 392–408 in
`wing_mid_r`'s webs stays, unused, so `wing_mid_r` prints as it is now. The tubing joins the
wire line at x = 457 and runs inboard with the tip aileron's lead.

The gate does not check the pitot against the prop discs today. A new check will keep it at
least 30 mm outside them.

### Scripts (when it is built in)

- `params.py`:
  - `MOTOR_HOLE_SQ` becomes a rectangular pattern (two spacings), read by `yoke()` and
    `rear_motor_mount()`;
  - `MOTOR_BASE_TO_PROP` (measured), `PROP_D` 304.8;
  - the shelf's step: the front part's top at z = 19, under the Cube and the four boards hung
    beneath it (Power Brick Mini, servo BEC, airspeed sensor, receiver; underside z = 16.5).
    Only the aft part and the ESC block keep `FC_SHELF_Z` 32 (`fc_shelf()`, and `UNDER_SHELF`
    and `esc_z()` in `payload.py`, split accordingly);
  - `PITOT_Y` 505, with `PITOT_GAP` kept.
- `payload.py`:
  - the battery at 138 × 47 × 36 mm;
  - the Cube as two boxes: carrier 95 × 45 × 18 mm, module 38.5 × 38.5 × 22.5 mm (where the
    module sits on the carrier, measured), on 1 mm foam (`FC_FOAM`);
  - the ESCs at their measured size;
  - the Power Brick Mini at 65 × 18 × 14 mm, moved to x = 268 (at x = 272 it touches the
    servo BEC);
  - a 38 mm GPS puck.
- `mass_balance.py`:
  - the new masses;
  - the motor's thrust at full and near-empty voltage, and the hover-power fit through its
    test table;
  - `V_PACK` 11.1, `PACK_AH` 8.
- `check_parts.py`: the pitot-to-prop-disc check, and the pitot route through `wing_tip_r`.
- `make_viewer.py`: the motor and prop models.
- `plates.py`: the plate split above.

### Electronics and wiring

- **Battery:** re-terminate the Zeee from EC5 to XT60 (the Power Brick Mini has XT60s).
- **Power Brick Mini:** hover (~22 A) is inside its 30 A continuous rating. Full throttle on
  all three motors (~94 A on a full pack) is inside its 100 A burst rating only, so keep
  full-power climbs short. For more margin later, fit a 60 A+ module.
- **ESCs:** the Readytosky 40 A cover a motor's full-throttle current (~31 A on a full pack).
  They take PWM only (no DShot): calibrate their throttle range in QGC with the props off.
  Pull the red wire out of all three signal plugs, because the servo rail has its own BEC. You
  need three, plus a spare. Three lighter 35–45 A DShot ESCs would save ~69 g.
- **No PDB:** a 1-to-3 harness from the Power Brick Mini's output to the ESC block is lighter
  and fits where the ESCs already are.
- **GPS:** the 3DR LEA-6H + HMC5883L has two DF13 plugs: 6-pin for the GPS, 4-pin for the
  compass's I2C. The Cube takes JST-GH plugs: one adapter cable joins both into its 8-pin GPS1
  port, or two cables run them to GPS1 and an I2C port. It is an old GPS-only receiver: fine to
  start with. A u-blox M10 holds position better later.
- **Cube Black:**
  - its POWER1 port takes the Power Brick Mini's cable directly;
  - PX4 firmware `px4_fmu-v3_default`; its v1.15.4 board config includes VTOL, control
    allocation, the airspeed selector and DShot;
  - disable its internal compasses (the ESC block sits next to it) and use the GPS's.
- **Pixhawk 1 (spare):** it fits on either shelf. Use it only if QGC reports 2 MB of flash,
  which means it runs the same fmu-v3 firmware. Its plugs are DF13 throughout: the GPS plugs
  straight in, and the Power Brick Mini needs an adapter.

### PX4 changes (`PX4_GUIDE.md`, when it is built in)

- **Firmware:** QGC flashes the Cube Black's fmu-v3 build.
- **Outputs:** the same table, but AUX1–3 run **PWM 400 Hz** instead of DShot600. AUX4 shares
  their timer, so it stays unused.
- **Battery:** `BAT1_N_CELLS` 3, `BAT1_CAPACITY` 8000 (6200 for the IPO), `BAT1_V_EMPTY` 3.5.
  Set the voltage and current scales in QGC's Power setup against a multimeter; the Power
  Brick Mini has no published PX4 values.
- **Airspeeds:** the plane is ~14 % heavier, so it stalls ~7 % faster: 12.9 m/s with the 10 %
  mass margin, up from 12.05. `FW_AIRSPD_STALL` stays 13. `FW_AIRSPD_MIN` goes from 16 to
  **17**, and `VT_ARSP_TRANS` and `FW_AIRSPD_TRIM` from 18 to **19**, so the transition still
  ends at the cruise speed. Use these with either pack.
- **Geometry:** the hover CG moves with the new masses, so `CA_ROTORn_PX` changes. Take the
  values from `mass_balance.py` once the plan is built in.
- **Hover throttle:** about 61 %; the hover-thrust estimator learns it.
- **Safety switch:** the 3DR GPS has none, so leave safety off (the default up to PX4 v1.15).

### Risks checked, and what is left

1. **Propwash on the wing in hover.** The slipstream narrows below the prop, to ~0.8 of the
   disc's radius where it meets the wing. From a 12 in prop it still covers the wing's first
   ~60 mm behind the leading edge, about a fifth of the slipstream. That costs an estimated
   5–8 % of the front thrust. About 80 % of the load falls on the front motors, so their real
   hover load is ~2–3 points above the modelled 48 %: ~50–51 %. The 4S design's 7 in
   slipstream (~69 mm radius at the wing, from an axis 65 mm ahead of the leading edge) barely
   reaches the wing, so the gate's figures stand for it. The gate does not model this; the
   first hover's throttle shows it.
2. **Tilt servos.** The motor and prop weigh 137 g instead of 58 g, and the prop is much
   bigger. That means ~3 kg·cm of gyroscopic torque in a brisk roll (3 rad/s) in hover, plus
   ~1.4 kg·cm from the motor's weight at 2 g in forward flight. The KM1203MD (~9 kg·cm) still
   has about twice that. Keep them.
3. **Strength.** A front motor's full thrust rises from ~1.55 kg to ~2.2 kg, and the motor and
   prop weigh more than twice as much as the 4S ones. The gate has no strength check. Before
   flying, support the wing and pull each yoke's motor plate along the motor's axis with
   4.5 kg (twice full thrust; a luggage scale works). Look for cracks or creep in the yoke
   arms, the pod and the tongue.
4. **Still to measure** before plates 6 and 7 are re-made:
   - the motor's hole pattern, its base-to-prop height (at least 38 mm, see [Motor](#motor))
     and its mass;
   - the Cube and carrier's mass and size;
   - the IPO pack's size and mass;
   - the Readytosky ESC's size, and how many you have;
   - the Pixhawk 1's flash size, if you use it.

## Order of work

1. **Now:** print everything except plates 6 and 7 (`tracker.md`, the `wing_tip_r` flow test
   first, on active-foaming LW-PLA). Order the motors, props, XT60 plugs and the GPS cable.
2. **When the parts arrive:**
   - **Thrust-test one motor** before anything else. Use a 12 × 6 prop, a freshly charged
     Zeee pack and a watt meter in line, on a thrust stand or a kitchen-scale rig. Nothing may
     sit in the prop's wash: air blowing onto the scale reads low. Clamp the motor down, run
     full throttle for a few seconds, and stay out of the prop's plane.
   - Multiply the thrust by (10.6 / V)², with V the pack voltage under load. The result must be
     at least **1.5 kg**: the 60 % limit with the upper propwash estimate (risk 1). SunnySky's
     table gives ~1.75 kg. If it falls short, stop and re-plan before printing anything for the
     motor.
   - Measure and weigh the items under risk 4.
3. **Build it in:**
   - tag the current `main` as `v0.2-4s`, so the 4S design can be restored;
   - on a branch `build-3s`, make the script changes above and run
     `python scripts/build_all.py`;
   - update the docs (`BOM.md`, `DESIGN.md`, `PX4_GUIDE.md`, `README.md`, `REPORT.md` as round
     10, `tracker.md`) and the renders;
   - open a pull request, let the CI gate run and merge it, so `main` stays the plane you are
     building.
4. **Print** the new plates 6 and 7.
5. **Load-test** the yokes (risk 3), then do the bench tests and the first hover
   (`PX4_GUIDE.md`).

## What to buy

The items the 3S build adds or changes. The complete list, every item marked as one of your
parts or to buy, is [`BOM_3S.csv`](BOM_3S.csv) (opens in Excel).

| Item | Qty | About | Notes |
|---|---|---|---|
| SunnySky X2814 **900KV**, standard version | 3 + 1 spare | $29.99 each (SunnySky USA) | not the 1000 or 1100KV (see [Motor](#motor)); comes with an X-mount and a prop adapter |
| APC 12x6E (LP12060E) | 2 + 4 spares | $4.87 each | front left and rear: counter-clockwise seen from above |
| APC 12x6EP (LP12060EP), reverse rotation | 1 + 2 spares | $4.87 each | front right: clockwise seen from above. Use the APC adapter ring that fits the motor's prop adapter |
| XT60 plugs | 2 pairs | | re-terminate the Zeee pack (it ships with EC5) |
| DF13 → JST-GH GPS adapter (6-pin GPS + 4-pin I2C into the Cube's 8-pin GPS1) | 1 | | the 3DR GPS to the Cube; check the pinout against the Cube's carrier before plugging in |
| Nyloc nut for the prop adapter's thread, or medium thread-lock | 1 | | the front right motor |
| Optional: three 35–45 A DShot ESCs | 3 | | 69 g lighter than the Readytosky 40 A |

Everything else in `BOM.md` (airspeed sensor and pitot, servos, servo BEC, receiver, carbon,
hardware, filament) is unchanged.
