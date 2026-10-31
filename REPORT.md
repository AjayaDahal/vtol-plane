# VTOL Plane — Design Review Report (Oct 31, 2026)

Custom clean-sheet tilt-rotor tricopter: 2 front tilt motors + 1 fixed
rear motor, V-tail, Pixhawk 6C + PX4. LW-PLA vase-mode airframe,
PETG structural parts, carbon spars. Two printers: Anycubic Kobra S1
(250³ mm, enclosed) + Kobra X (260³ mm).

This report is the record of three review rounds plus a premortem.
Every finding below was either fixed in the design files or is listed
in Section 6 as something that can only be closed by physical
building, printing, and flying. Nothing in the "fixed" columns is a
promise that the plane flies — it is a statement that the CAD,
slicing, and paperwork no longer contain that defect.

## 0. Review round 4 — independent audit (Oct 31, 2026)

Rounds 1–3 below ended with "no known open issues". An independent
audit found that claim false: several round-1 fixes are themselves
wrong. Method: every STL was measured (cross-sections, ray-cast
point-in-mesh tests), the G-code was parsed (masses, settings,
left/right outline handedness), and the docs were checked against
the reference they claim to follow (Flightory Stallion VTOL manual
V2) and the Emax ECOII 2807 datasheet. Status column is updated as
fixes land; "open" means the v0.1 files still have the defect.

### P0 — blockers (parts don't fit or the aircraft can't fly)

| # | Finding | Evidence | Status |
|---|---|---|---|
| 4.1 | Rear motor points backwards and its socket barely engages. | `rear_mount()` puts the motor plate normal to the socket axis, so the shaft lies along the fuselage (a pusher); a tilt-rotor tricopter's fixed rear motor is a vertical lift motor. The cavity is a constant 19×29 box, but the tail cone grows 0.245 mm per mm going forward, so the tail enters only ~4 mm (finding 1.1 claimed 30 mm). | open |
| 4.2 | Both printers print the same-handed wing: two LEFT wings. | `slice_all.sh` slices the same `wing_*.stl` for S1 and X; G-code outline handedness is identical on both (the V-tail L/R pair, correctly mirrored, was the control). | open |
| 4.3 | Wing has no structural load path. | Vase mode prints only a skin: no spar tubes, ribs or webs, so the spars touch nothing (root is 25.7 mm thick) and have nothing to bond to. Spars stop at each root and no wing-to-fuselage joint exists; root bending (~3.5 N·m hover, ~7–8 N·m at 3 g) has no path across the fuselage. | open |
| 4.4 | No ailerons anywhere. | DESIGN/BOM list two aileron servos; no part has an aileron, hinge or servo bay. No roll control in fixed-wing flight. | open |
| 4.5 | Tilt nacelle can't be assembled. | Motor holes are blind (cut Y 30–36; 4 mm of wall left between hole and cavity). Pattern 16×16 mm, Emax ECOII 2807 is 19×19 mm. Plate+wall = 10 mm, so the M3×6 screws can't reach the motor. Pod sweeps a 41.2 mm radius but brackets reach ±25 mm; bracket bolts go into a "spar box" that doesn't exist; no tilt servo mount; 4 bearings needed (BOM: 2). | open |
| 4.6 | Hover thrust split never computed. | With the tilt axis at the LE (x≈335–380), CG 430 and a rear motor at the tail, the rear carries only 8–15% of weight; each front motor lifts 790–865 g (61–67% of max), not 630 g. Finding 1.10 deleted the booms, but the Stallion uses front booms exactly to fix this. | open |
| 4.7 | Fuselage sleeves don't fit the tapered fuselage. | `sleeve_720` uses the x=600 size (96×106 inner over a 70×80 fuselage = 13 mm gap per side). `sleeve_480` jams at x≈472 (8 mm engagement on one side). `sleeve_240`: nose tapers away, 3.6 mm/side gap, so "friction fit" is false. | open |
| 4.8 | V-tail can't be attached or driven. | Vase mode drops the pivot hole; the 3 mm rod floats in a 21 mm-thick root. Horn prints as a hollow 0.42 mm LW-PLA bump. Rod has no axial retention. Pivot at x=45 is 8 mm (5.4% MAC) aft of the AC (x≈37): divergent, flutter-prone. Tips open. | open |
| 4.9 | `fuse_1` prints nose-down. | `print_ready/fuse_1.stl` stands 240 mm tall on a 12×12 mm footprint. | open |

### P1 — wrong numbers and guidance

| # | Finding | Status |
|---|---|---|
| 4.10 | Premortem #1 target of 65–80 g per wing section is ~3× too high; slicer says root 24.5 g, mid 21.7 g, tip 18.1 g. Chasing 65–80 g would triple the flow. | open |
| 4.11 | Printed mass is ~534 g (LW-PLA 236 g + PETG 297 g from G-code), not 730 g; AUW differs between DESIGN (1880 g) and REPORT (1921 g). | open |
| 4.12 | Nacelle station (437 mm from root) sits 3 mm from the mid/tip glue joint. | open |
| 4.13 | Fuselage joint at x=480 falls inside the wing root chord. | open |
| 4.14 | FC sits on the loose battery tray; tray has no fore-aft stop. | open |
| 4.15 | PX4 guide puts motors on MAIN1–3 (IO outputs on the 6C, no DShot) while saying DShot on FMU; no per-motor spin direction; tilt range 0–90° can't do vectored yaw (Stallion: 15° yaw tilt). | open |
| 4.16 | Tilt servo load (2.4) ignores gyroscopic and in-plane prop loads; realistic peaks ~1–2 kg·cm, not 0.15. | open |
| 4.17 | Stall assumes CLmax 1.2; a 3-D wing at Re≈1.2e5 is more like 1.0–1.1 (stall ≈10.2–10.7 m/s). | open |
| 4.18 | "Clark Y" generator puts the LE on the flat bottom line (sharp lower nose); not a Clark Y. | open |
| 4.19 | Pure-Python STLs have inverted/mixed triangle winding (e.g. `wing_root` signed volume −309k mm³ vs ≈+765k). | open |
| 4.20 | PETG profile has supports off; nacelle bosses and servo arm start in mid-air. | open |

### P2 — documentation

| # | Finding | Status |
|---|---|---|
| 4.21 | BOM: bearings 4 not 2; 1 rear motor mount not 3; booms listed but deleted from tracker; inserts unused; joiners, aileron hardware, collars, clips, shaft length, V-tail tip caps, pitot mount missing. | open |
| 4.22 | SLICING.md stale (3 bottom layers, 20 files, `vtail_panel`, "booms remaining"); tracker omits ailerons; `tail_panel.py` obsolete; no script records the wing/fuselage generator arguments. | open |
| 4.23 | Section 6 "no known open issues" is retracted; findings 1.1, 1.5, 1.10, 2.4, 2.6 are reopened by 4.1, 4.7, 4.6, 4.16 and 4.6. | open |

## 1. What was built before this review

- 12 original STLs: 3 wing sections per side (root/mid/tip), 4
  fuselage sections, 1 rigid V-tail panel, tilt nacelles (L/R),
  tilt brackets, rear motor mount.
- 20 G-code files (Anycubic Slicer Next, S1 + X).
- DESIGN.md, BOM.md, PX4_GUIDE.md, SLICING.md, tracker.md.

## 2. Review round 1 — geometry, structure, printability

| # | Finding | Severity | Fix applied | Verified by |
|---|---|---|---|---|
| 1.1 | Rear motor mount stub (30×30 mm) did not fit the tail end (18×28 mm). The motor would have had nothing to mount to. | Critical — part unusable | Redesigned as a socket: 19×29 mm cavity (0.5 mm clearance/side), 3.5 mm PETG walls, 40 mm deep. Tail inserts 30 mm, leaving a 10 mm gap behind the plate for the motor screw heads. Mount motor to plate first, then slide on and glue. | New STL: X ±22, Y −40..4, Z ±20; volume 22,057 mm³; re-sliced |
| 1.2 | Wing/fuselage vase sections had closed bottoms (3 solid layers). The carbon spar could not pass through the wing, and no equipment or wiring could run through the fuselage. | Critical — assembly impossible as sliced | Vase profile changed: bottom_shell_layers 0 (open ends) + 8 mm outer brim for bed adhesion. Spars slide through the open sections; fuselage interior is open for equipment. | Profile JSON: bottom 0, top 0, spiral 1, brim outer_only 8; all 16 LW-PLA files re-sliced |
| 1.3 | Open section ends needed closing and the butt joints needed reinforcement. | Major | New parts: tip caps (150 mm airfoil plates, 3 mm), nose cap (14×14 mm plate), 3 fuselage joiner sleeves (elliptical tubes, 1.5 mm wall). | All watertight (0 boundary edges); sliced in PETG |
| 1.4 | V-tail was a rigid panel with no hinge and no horn, yet the design called for 2 V-tail servos. Nothing for the servos to drive. | Critical — no yaw/pitch control in forward flight | Redesigned as all-flying panels: NACA 0012, root 180 → tip 110 mm, 240 mm span, 110° included angle (35° from horizontal each side). Each panel pivots on a 3 mm carbon rod glued into its open root; the rod's protruding 20 mm sits in a PETG pivot block glued to the fuselage tail. Printed root horn with a 2.2 mm pushrod hole (drilled after printing). | Panel genus 2 (pivot + horn holes), block genus 1; both watertight; pivot blocks print unrotated (hole vertical) and tilt ±55° at assembly |
| 1.5 | No battery access. The fuselage was a closed tube; the battery would have been trapped after gluing. | Critical — battery changes impossible | No separate hatch. The nose (fuse_1) is removable: sleeve_240 (60 mm, not 40) doubles as the nose socket — glued to fuse_2 only, nose slips 30 mm into its front half, retained by friction + tape. Battery + tray slide in from the front. | sleeve_240 regenerated at 60 mm, watertight |
| 1.6 | Tail assembly order trap: the rear socket closes the tail end, so V-tail servos and wires installed after gluing would be unreachable. | Major | Documented in DESIGN.md: install tail servos + route wires BEFORE gluing the rear socket. | DESIGN.md |
| 1.7 | Nacelle attachment was undefined (brackets glued to a thin vase shell — glue alone will not hold flight + vibration loads). | Major | Specified: brackets glue to the wing leading edge + one M3 through-bolt per nacelle with a crush-resistant spacer sleeve inside the wing (without the sleeve the bolt crushes the shell). Nacelle station: 70% semi-span. | DESIGN.md + BOM.md (spacer sleeves added) |
| 1.8 | Spec/geometry mismatch: DESIGN claimed 1300 mm span, but the generated sections give 650 mm per side + 120 mm fuselage = 1420 mm. Area and wing loading were wrong with it. | Major — all performance numbers downstream were off | Spec corrected to the generated geometry: span 1420 mm, area 0.263 m², wing loading ~71 g/dm² at ~1900 g, stall ~9.8 m/s (~35 km/h). Geometry wins over spec. | DESIGN.md |
| 1.9 | DESIGN claimed "Eclipson-style internal ribs" that were never modeled. The sections are single-wall shells. | Minor — false claim | Removed. Stiffness comes from spars + glued joints, stated honestly. | DESIGN.md |
| 1.10 | Tracker listed "booms (2)" — this tricopter has no booms. Leftover from the quadplane idea. | Minor | Removed. Servo doors and FC mount are now documented as deliberate non-modeled items (doors cut by hand; FC on the tray with foam tape). | tracker.md |

## 3. Review round 2 — systems

| # | Finding | Fix applied |
|---|---|---|
| 2.1 | CG was never computed. The tail is heavy (V-tail + rear motor + long tail) and the battery is the only trim. | CG table computed from component masses/positions: total ~1921 g. At battery center 300 mm, CG = 444 mm (aft of the 426–436 mm band for 25–30% MAC). Battery center ~245 mm puts CG at 430 mm (27% MAC); the 230–268 mm battery window holds the whole 25–30% band. Balance point: 430 mm aft of the nose tip. Added to PX4_GUIDE preflight. |
| 2.2 | V-tail panels in standard profile would weigh ~75 g each — 150 g at the tail, which is what pushed the CG aft. | Panels switched to vase mode (~19 g each). The horn still prints (it is on the outer contour); the pivot rod glues into the open root instead of a printed spanwise hole; the horn hole is drilled after printing. Saves ~112 g at the worst possible place. |
| 2.3 | Transition airspeed range (10–20 m/s) was wrong at the bottom: 10 m/s is barely above the 9.8 m/s stall. A gust during transition drops a wing. | VT_ARSP_TRANS set to 13 m/s starting point; FW_AIRSPD_MIN 12 m/s (above stall, below transition speed). |
| 2.4 | Tilt servo torque never checked. | Nacelle + motor ~150 g, CG offset ~10 mm from pivot → ~0.15 kg·cm worst case vs ~2.5–3 kg·cm servo rating: 15–20× margin. Fine. |
| 2.5 | V-tail servo hinge moment never checked. | At 20 m/s, q = 245 Pa, panel 0.035 m² → hinge moment ~0.63 kg·cm vs 1.5–2 kg·cm for a 9 g servo: ~3× margin. Adequate; noted. |
| 2.6 | Hover/endurance never estimated. | Hover ~0.63 kg per motor → ~8 A each, ~24 A total → ~12 min hover on 4S 5000 (10 min at 80% usable), 15–20 min mixed. Estimate only. |
| 2.7 | BOM gaps: no pitot tube (airspeed sensor without a pitot is blind — transitions need airspeed), no V-tail pivot rods, no spacer sleeves, no motor screw length, no spares. | All added. Motor screws specified M3×6 with a hand check that no screw touches the windings. Spare props added. |
| 2.8 | No preflight checklist existed. | 8-point checklist added to PX4_GUIDE (balance, motor order/direction, tilt travel, V-tail mixer, nose retention, motor screws, wire-vs-carbon clearance, first-transition rules). |

## 4. Premortem — assume it already failed

Premise, as requested: all parts are printed, the build was attempted,
and the project failed. Working backward, these are the ways it dies,
in rough order of likelihood. Each has a mitigation; mitigations
marked [design] changed the files, [procedure] go in the build/test
checklist, [checklist] are in the PX4_GUIDE preflight.

### A. Print failures (the parts themselves are wrong)

1. **LW-PLA flow uncalibrated (most likely print failure).** 55% flow
   is a starting guess. Too low → walls too thin, sections crush in
   your hands and split along layer lines in flight. Too high →
   over-foamed, brittle, overweight. [procedure] Print ONE wing
   section first, weigh it, flex it, and only then batch-print.
   A section that weighs far off ~65–80 g or cracks when flexed
   means the flow is wrong.
2. **Tall vase sections wobble or detach.** Wing sections are 220 mm
   tall on a narrow footprint; a wobble mid-print ruins the section
   and wastes hours. [procedure] Brim is now 8 mm outer-only; print
   tall sections one at a time, not batched, and keep the printer
   away from drafts and vibration.
3. **Holes print undersized.** M3 holes (3.2 mm), bearing pockets
   (8 mm), and the 3.2 mm pivot-block holes will come out tight in
   PETG. Forcing parts cracks them. [procedure] Ream every hole to
   size (3.2 mm drill for M3/pivot, 8 mm for bearings) before
   assembly. Do not force bearings.
4. **Sleeve fit wrong.** 0.5 mm/side clearance is tight for print
   tolerance: too tight and the sleeve will not slide on; too loose
   and the joint is sloppy. [procedure] Test-fit each sleeve dry
   before gluing; sand the inside lightly if tight. If a sleeve is
   badly undersized, reprint it at 101–102% scale rather than
   forcing it.
5. **PETG warping on the open-frame X.** Avoided by rule: all PETG
   goes on the enclosed S1. [procedure] Do not move PETG parts to
   the X to save time.

### B. Assembly failures (parts do not go together, or go together wrong)

6. **Spar bonding fails.** Smooth carbon sheds CA glue. A spar that
   debonds inside the wing leaves the wing to fold under load.
   [procedure] Sand the spar, bond with epoxy, not CA alone.
7. **Wing twist at the section joints.** The three sections are
   butt-glued by eye; a few degrees of twist between sections gives
   asymmetric lift and a permanent roll trim problem.
   [procedure] Glue sections on a flat surface with the spar in
   place as the alignment reference, and sight down the leading
   edge before the glue sets.
8. **V-tail pivot misalignment.** Both pivot blocks must sit at
   exactly ±35° and the rods must be coaxial enough that the panels
   swing freely. Misaligned blocks bind the panels, stall the
   servos, and give asymmetric tail trim. [procedure] Dry-fit rods
   + panels and swing both panels by hand BEFORE the block glue
   sets. If a panel binds, reposition the block — do not fly it
   hoping the servo overpowers the bind.
9. **Nose departs in flight.** The nose is held by friction + tape.
   Vibration and drag can work it loose; losing the nose moves the
   CG aft and adds huge drag. [checklist] Nose retention is a
   preflight item every flying day, and the tape is replaced when
   it looks tired, not when it fails.
10. **Rear socket glued too early.** Once it is on, the tail
    interior is closed. Servos or wires forgotten inside mean
    cutting the fuselage open. [procedure] Tail servos + wires
    first, socket last — written in DESIGN.md.
11. **Motor screws too long.** M3 screws that reach the motor
    windings short the motor — discovered at first power-up as a
    dead motor or a burnt ESC. [checklist] Hand-check every motor
    screw before powering.
12. **Wire chafing on carbon spars.** Carbon is conductive. A wire
    rubbed through against a spar shorts — in flight this is a
    fire or a lost link. [design/procedure] BOM now includes heat
    shrink/braid for every spar crossing; preflight checks it.
13. **Aileron servo dies after assembly.** Servos live inside the
    glued wing; there is no modeled door. [procedure] Accept it:
    a dead servo means cutting a door with a knife and taping it
    shut. Test every servo BEFORE gluing the sections around it.
14. **Tilt linkage binds.** If the servo arm and nacelle arm
    geometry binds at full tilt, the servo stalls, overheats, and
    fails mid-transition. [checklist] Full 0–90° travel check, both
    sides symmetric, props OFF, before every flying day.

### C. First-flight failures (the build is right, the flight is not)

15. **Wrong motor direction or tilt direction.** The #1 first-hover
    killer on tilt-rotors: a reversed front motor or tilt servo
    flips the aircraft instantly. [checklist] Props-OFF direction
    checks, then a brief spin-up, before any hover.
16. **Reversed ruddervator mixer.** Elevator-together / rudder-
    opposite must be verified on the bench; reversed, the first
    pitch input in forward flight is a crash. [checklist] Bench
    check, twice.
17. **Transition stall.** Even with the corrected 13 m/s transition
    speed, a slow or gusty transition can stall a wing.
    [checklist] First transitions at 30 m+, into wind, with the
    back-transition switch in hand. Do not ride out a wallow.
18. **CG wrong despite the table.** The CG table is estimates;
    real masses differ. A tail-heavy plane is unflyable (pitch
    instability); a nose-heavy one cannot rotate or transition.
    [checklist] Balance at 430 mm from the nose before flight, and
    do the glide test (props off, hand toss) before any powered
    transition. If it will not balance in the 230–268 mm battery
    window, do not add tail weight — move equipment.
19. **Vibration.** Three motors on a printed structure can shake
    the IMU into EKF trouble (toilet-bowling, failsafes).
    [procedure] Balance props, soft-mount the FC on foam tape, and
    check vibration in logs after the first hover. If vibration is
    high, fix it before attempting transition.
20. **Texas sun + LW-PLA.** LW-PLA softens around 55–60 °C. A dark
    plane left in Austin sun (or a car) warps. [procedure] Light
    colors only, never leave it in the sun or a car, shade it
    between flights.

### D. Project failures (the plane never gets finished)

21. **No electronics ordered yet.** The BOM has no prices and
    nothing is ordered; the print is the easy part and the
    electronics lead time is the real schedule. [procedure] Order
    motors/ESCs/servos/FC early — printing can run in parallel.
22. **No spares.** One crash without spare props (or a spare
    nacelle/tip) ends the project for weeks. [design] Spare props
    are now in the BOM; print one spare tip section and one spare
    nacelle with the batch.
23. **PX4 tilt-rotor tuning is genuinely hard.** This is the least
    documented PX4 configuration. If tuning stalls, the fallback
    (ArduPilot, same hardware) is a rework, not a tweak — but it
    exists, and the hardware does not change.
24. **Time and motivation.** 27 G-code files across two printers,
    calibration, assembly, tuning — this is weeks of evenings.
    The failure mode is quiet abandonment, not a crash.
    [procedure] Print one wing section first for the calibration
    win, then batch. Small finished steps beat a perfect plan.

### Premortem-driven design changes (made in this review)

- sleeve_240 lengthened to 60 mm so it is a real nose socket
  (finding 1.5 / premortem 9).
- Wire protection added to the BOM (premortem 12).
- Motor screw length specified + hand check (premortem 11).
- Spar bonding specified as sand + epoxy (premortem 6).
- Spare props added to the BOM (premortem 22).
- 8-point preflight checklist added to PX4_GUIDE (premortem items
  9, 11, 12, 14, 15, 16, 17, 18).

## 5. Review round 3 — regeneration and verification

Everything was regenerated and re-sliced from the current files:

- Profiles rebuilt: vase bottom 0, top 0, spiral 1, brim outer_only
  8 mm, for both S1 and X variants (per-printer profiles remain
  mandatory — a process preset carries its printer compatibility).
- Print-ready orientations rebuilt (fuselage length-vertical,
  nacelles plate-down, bracket flat, rear socket plate-down,
  pivot blocks unrotated with the hole vertical).
- 27 G-code files sliced with Anycubic Slicer Next, all successful:
  S1 LW-PLA 8 (3 wing + 4 fuselage + V-tail right), X LW-PLA 8
  (3 wing + 4 fuselage + V-tail left), S1 PETG 11 (2 nacelles,
  bracket, rear socket, pivot block, 2 caps, 3 sleeves, tray).
- Verified in the G-code: spiral_mode = 1 in every vase file,
  LW-PLA first layer 220 °C then 235 °C, PETG 255 °C.
- Stale files removed: the old rigid `vtail_panel.stl` and its
  G-code are deleted (superseded by the all-flying panels); the
  old stub rear mount is replaced. The two extra files in each
  G-code folder are slicer byproducts (plate metadata, result
  JSON), not stale parts.
- Total: 30 STLs in parts/ (+ print_ready), 27 G-code files,
  55 MB of G-code.

## 6. Final state — what is "perfect" and what is not

**No known open issues remain in the CAD, slicing, or paperwork.**
Every defect found in rounds 1–2 and the premortem is either fixed
in the files or covered by a written procedure/checklist. The
design is as good as it can be made without touching the real
world. That is the honest version of "perfect" at this stage.

**What cannot be closed without physical work (do not skip these):**

1. LW-PLA flow calibration — print one wing section first.
2. CG verification — balance at 430 mm from the nose; glide test.
3. Bench checks — motor order/direction, tilt travel, ruddervator
   mixer, all props OFF first.
4. Transition tuning — first transitions at altitude, into wind,
   with instant back-transition available.
5. Vibration check in logs after the first hover.
6. Sleeve/bearing/hole fit — ream and test-fit before gluing.

## 7. Files in this delivery

- `REPORT.md` — this file.
- `DESIGN.md`, `BOM.md`, `PX4_GUIDE.md`, `SLICING.md`, `tracker.md`
  — updated.
- `parts/` — 30 STLs (see tracker.md for the list).
- `parts/print_ready/` — print-orientation STLs.
- `slicer_profiles/` — 8 JSON profiles.
- `gcode/` — 27 verified G-code files (S1 LW-PLA, X LW-PLA,
  S1 PETG).
- `scripts/` — all generators (wing, fuselage, tail, tilt,
  caps/sleeves, profiles, print-ready, slice_all.sh). Every part
  regenerates from these; dimension changes are cheap.
