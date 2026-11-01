# VTOL Plane — Design Review Report

Custom clean-sheet tilt-rotor tricopter: 2 front tilt motors + 1 fixed
rear motor, V-tail, Pixhawk 6C + PX4. LW-PLA vase-mode airframe,
PETG structural parts, carbon spars and boom. Two printers: Anycubic
Kobra S1 (250³ mm, enclosed) + Kobra X (260³ mm).

This file is the record of every review. The current state is at the
top; older rounds follow, newest first. "Fixed" means the CAD, slicing
and paperwork no longer contain that defect. It is not a promise that
the plane flies. That needs the physical checks listed under "Open".

## Current status (v0.2, Oct 31, 2026)

**Ready to print, starting with the test prints.** Print `wing_tip_r`
(flow) and `rib_tip_r` (fit) first, then the rest (`tracker.md`).

- Verification gate: `python scripts/check_parts.py` passes **76/76**.
  It covers mesh integrity, mirrored L/R parts, bed fit, every spigot,
  coupler and frame fit, spar, joiner, boom and wire paths, motor holes
  and hex-key room, the tilt sweep, prop clearances, thrust split, CG and
  static margin, and overhangs judged on the geometry (no part needs
  supports). It also checks the G-code: present, sliced from the current
  STL (hash stamp), and one vase speed band.
- 46 G-code files, no supports anywhere. S1 LW-PLA 124 g / 23.7 h,
  X LW-PLA 105 g / 20.2 h, S1 PETG 448 g / 20.2 h.
- AUW ~1.91 kg, CG 431 mm from the nose (27 % MAC), hover split
  38/38/23 %, static margin ~20 %.
- Docs match the files: `DESIGN.md` (design and assembly), `BOM.md`,
  `PX4_GUIDE.md`, `SLICING.md`, `tracker.md`.

**Open, can only be closed by building and flying** (in order):

1. LW-PLA flow and spigot fit: the two test prints above.
2. Tilt servo dimensions against the pod bay, before printing pods and
   yokes.
3. Real masses: weigh the parts and re-run `mass_balance.py`.
4. CG: balance at 431 mm, then glide-test.
5. Bench: motor order and direction, tilt calibration (−20…90°),
   surface directions, ruddervator mixing, props off.
6. First hover: vibration and compass interference in the logs.
7. Transition tuning: at altitude, into wind, back-transition ready.

## Round 5 — final pre-print audit and premortem (v0.2, Oct 31, 2026)

Premise: every part is printed, the build is attempted, and the
project fails. What killed it? Method: the 62-check gate passed, so
this round looked where the gate did not.

- Support extrusions were mapped from the G-code back onto each part,
  after registering the slicer's arrange rotation.
- Overhangs were scanned in print orientation, and wall speed was
  measured in every vase file.
- Assembly was walked step by step against the geometry.
- The PX4 parameter meanings were checked in the PX4 source.

Every fix was rebuilt, re-sliced (all 46 files) and re-checked; the
new checks are in the gate. An independent code review of the round's
changes then found five more (5.18–5.22), and a second review pass
found three gaps in those fixes. All are fixed the same way and are in
the table.

| # | Severity | Finding | Fix | Status |
|---|---|---|---|---|
| 5.1 | P0 print | **Boom pods:** tree supports filled the 6.3 mm tongue slot, the servo bay, both M3 bolt holes, the axle insert hole and the wire channels. The pod could not go onto the tongue without digging PETG out of a 6 mm slot. | 45° gusset under the axle boss, 45° chamfer under the nose. Printed upright with no supports; the slot, bay and holes bridge. A test slice with supports on adds them only inside those bridgeable cavities. | fixed |
| 5.2 | P0 print | **Boom ribs:** supports filled the inboard spigot ring (13–16 g per rib) and both wire channels. | Inboard ring split off as `boom_cup` (ring + 1.5 mm glue plate, aligned by the spars). The rib prints flat on its inboard face. Its wire channel is now a groove with a 1 mm bridge, closed by the cup. | fixed |
| 5.3 | P0 build | **Rear motor mount:** supports filled the 16.3 mm boom bore, the clamp slit and the bolt hole. Also, the motor screw heads sat ~10 mm above the clamp ring, too little for a hex key, so the motor could not be fitted. | One 36 mm constant section that prints on end, bore vertical, no supports. Plate raised 15 mm (25.6 mm key room). 2 clamp bolts. New check: hex-key room ≥ 23 mm under every motor screw. | fixed |
| 5.4 | P0 build | **No wire path through the boom rib:** the aileron leads and pitot tubing go through holes at x = 457 in the root and mid/tip ribs, but the boom rib between them was solid there. | Ø10 hole at (457, 5) in the boom rib and Ø12 in the cup, in line with the others. New check: a straight wire path through every rib. | fixed |
| 5.5 | P0 flight | **PX4 tilt normalization:** `VT_TILT_*` runs over the tilt servo range `CA_SV_TL*_MINA..MAXA` (−20…90°). The guide's `VT_TILT_MC` 0.08 means motors 11° back in hover. | `PX4_GUIDE.md`: MINA −20, MAXA 90, `VT_TILT_MC` 0.18, TRANS 0.55, FW 1.0, a servo calibration procedure and a bench check. | fixed |
| 5.6 | P0 flight | **PX4 outputs:** motors on MAIN (IO) cannot run DShot on the 6C; no rotor geometry or spin directions were given. | Motors on AUX1–3 (FMU) DShot600, servos on MAIN1–8; `CA_ROTOR*` positions, KM signs and tilt assignment. | fixed |
| 5.7 | P0 flight | **Airspeeds** in `PX4_GUIDE.md` were from v0.1 (stall 9.8, MIN 12, TRANS 13 m/s): transition-stall risk. | STALL 12, MIN 15, TRANS 17 m/s, from `mass_balance.py` with the stall at CL 1.0, 35 °C and AUW +10 %, so they don't shift with small estimate changes. | fixed |
| 5.8 | P0 build | **`DESIGN.md` described v0.1** (nacelles, sleeves, all-flying tail, 1300KV/45 A, "no ribs"). There was no v0.2 assembly sequence, hole list or order of operations. | Rewritten. It now has a parts map, the assembly sequence, every hand-drilled hole with coordinates, the motor-before-yoke and boom-before-`fuse_4` order, and the glue rules. | fixed |
| 5.9 | P1 print | **LW-PLA speed spread:** the 8 s minimum layer time gave 10–56 mm/s walls. LW-PLA foaming depends on speed, so the `wing_tip_r` calibration would not carry to the ailerons or wing roots. | Wall speed capped at 30 mm/s, minimum layer time 4 s: 17–30 mm/s for every vase part, same total time. New check: max ≤ 2× min. | fixed |
| 5.10 | P1 build | **Axle bearing:** the M3 axle screw clamps the bearing inner race across the 0.5 mm running gap, pulling the yoke against the pod (binding). | BOM: 0.5 mm shim washer (OD ≤ 5 mm) between the inner race and the boss. The assembly step checks free swing with the screw tight. | fixed |
| 5.11 | P1 build | **Pod bolts:** M3×30 through the 28 mm pod leaves no thread for a nyloc nut. | M3×35 in the BOM and guide. | fixed |
| 5.12 | P2 print | **`coupler_240`:** the nose-screw boss started 2 mm above the bed. | Boss starts on the bed. | fixed |
| 5.13 | P1 build | **Tilt servo size:** the pod bay fits a 12 mm mini servo; a different servo means a reprint. | Measure before printing (tracker reminder; `SERVO_*` in `params.py`). | open (physical) |
| 5.14 | P2 build | **ESC heat:** ESCs sit inside closed LW-PLA sections; LW-PLA softens at 55–60 °C. | Rule in `DESIGN.md`: no ESC touches a skin; heat-shrink and tie to the spars with an air gap. | procedure |
| 5.15 | P2 build | **Nominal carbon fits:** an 8.0 joiner in an 8.0 ID spar, and the 16.0 boom in 16.3 printed holes. | Dry-fit, sand or ream; documented. | procedure |
| 5.16 | P2 flight | **Compass:** the rear ESC supply ran past the GPS at x = 560. | Rear ESC moved to x ≈ 400 (5.18), so the battery leads stay ahead of the GPS. The rear motor's phase leads still run in the boom ~70 mm below it: keep them twisted together, and check interference in the first hover log. | fixed + procedure |
| 5.17 | P2 build | **Landing:** no gear; the plane lands on its LW-PLA belly. The nose tip is open (vase mode). | EVA foam belly strip (BOM), land on grass; tape the nose tip. | procedure |
| 5.18 | P0 build | **Tail assembly order impossible** (found by an independent code review of this round). The motor mount is a closed clamp, so it can only go on over the boom's aft end, before the tail block. The rear ESC (x ≈ 700) and its leads were inside `fuse_4`, sealed before they could be connected. A second review pass also found that `frame_rear` and the `coupler_610` web could not be reached for reaming or gluing, and that pull strings left in the holes would be pinched. | Rear ESC moved to the front of `fuse_3` (x ≈ 400). Every boom hole is reamed while the parts are loose. The boom goes into `fuse_3` before `fuse_4`, so all its glue joints can be reached. The mount, then the tail block, go over its aft end; the leads are fished through the boom afterwards. | fixed |
| 5.19 | P1 check | **The supports check could never fail:** supports are off in every profile. It missed a 7.7 mm unsupported ledge on the mid/tip rib flange, and the first gusset (5.1) left the underside at the boss tip unsupported. The first geometric version could itself be fooled in three ways: large faces were under-counted, a sloped face could anchor on itself, and a partial ledge counted as a bridge. | New geometric check on the print-ready meshes. Faces > 60° from vertical must be bridged (≤ 30 mm, with the overhang continuing across the whole span). Flat faces may also be ledges of ≤ 3 mm. Sampling is area-weighted, and the probed face's own plane is ignored. It now fails all four pre-fix parts (pod 237 mm², boom rib 1361, mid/tip rib 43, rear mount 354) and synthetic shelf, wedge and partial-ledge cases, and passes bridges, holes and 45° chamfers. Spigot rings now stop 2 mm ahead of a hinge, not 8; the gusset runs from the boss's lowest point at its tip. The support-move count stays as a profile sanity check. | fixed |
| 5.20 | P1 check | **Stale-G-code check used file times,** which git does not keep. It failed on every fresh clone and passed after restoring old G-code. | `slice_all.py` stamps each G-code file with the SHA-256 of its STL; the gate compares hashes. | fixed |
| 5.21 | P0 flight | **PX4 rotor count:** airframe 13100 defaults to `CA_ROTOR_COUNT` 4, a phantom rotor 1 m out that takes part of every command. | Guide sets `CA_ROTOR_COUNT` = 3. | fixed |
| 5.22 | P0 flight | **PX4 tilt servos are mirror images:** one needs Rev Range. The tilts also sit at the raw Disarmed PWM while disarmed and during spool-up. On the reversed output, the PWM min is the forward end. | Guide: Rev Range on one tilt output, with its end points and hover disarmed value given separately; Disarmed PWM at the hover (0°) position on both. | fixed |

## Round 4 — independent audit of v0.1 (statuses as of v0.2)

The v0.1 files these findings describe were deleted. The v0.2 design
(parametric `scripts/`) was rebuilt to fix them, and round 5 closed the
rest. "Check" names the `check_parts.py` test that guards each fix.

### P0 — blockers

| # | Finding | Status |
|---|---|---|
| 4.1 | Rear motor pointed backwards; its socket barely engaged. | **Fixed (v0.2):** vertical lift motor on a boom clamp at x = 820 (round 5 made it printable and serviceable). Check: rear prop disc clearance, motor holes, hex-key room. |
| 4.2 | Both printers printed the same-handed wing. | **Fixed (v0.2):** separate mirrored `_r` (S1) and `_l` (X) files. Check: "left/right parts are mirror images". |
| 4.3 | Wing had no structural load path. | **Fixed (v0.2):** PETG ribs with spar bosses on 10×8 / 6×4 spars, joiners through two fuselage frames. Checks: spar paths, spigot fits, joiner sleeves. |
| 4.4 | No ailerons. | **Fixed (v0.2):** two ailerons per side, tape hinge, servo cages and horns. |
| 4.5 | Tilt nacelle could not be assembled. | **Fixed (v0.2):** boom pod + yoke, 19×19 pattern, bearing + direct-drive servo (round 5 added the shim). Checks: motor holes, tilt sweep, bearing gap. |
| 4.6 | Hover thrust split never computed (front motors overloaded). | **Fixed (v0.2):** tilt axis 65 mm ahead of the LE; 38/38/23 % split. Check: thrust split, % of max. |
| 4.7 | Fuselage sleeves did not fit the tapered fuselage. | **Fixed (v0.2):** internal couplers lofted to the skin. Check: coupler fits (0.8 mm gap). |
| 4.8 | V-tail could not be attached or driven. | **Fixed (v0.2):** fixed V-tail with ruddervators, tail block on the boom, 4 mm pins. Check: V-tail rib fits. |
| 4.9 | `fuse_1` printed nose-down on a 12 mm footprint. | **Fixed (v0.2):** prints wide end down. Check: "no part stands on a tiny footprint". |

### P1 — wrong numbers and guidance

| # | Finding | Status |
|---|---|---|
| 4.10 | Wing-section mass target ~3× too high. | **Fixed:** tracker targets are the slicer's masses. |
| 4.11 | Printed mass and AUW inconsistent between docs. | **Fixed:** `mass_balance.py` reads the G-code; all docs quote it (1909 g). |
| 4.12 | Nacelle station 3 mm from a glue joint. | **Fixed (v0.2):** the boom has its own rib at y = ±280. |
| 4.13 | Fuselage joint inside the wing root chord. | **Fixed (v0.2):** joints at x = 370 and 610, outside the chord (380–600). |
| 4.14 | FC on the loose battery tray; tray had no stop. | **Fixed (v0.2):** separate FC shelf; tray stop-pin holes every 10 mm. |
| 4.15 | PX4 outputs, spin directions and tilt range wrong or missing. | **Fixed (round 5):** see 5.5, 5.6, 5.21 and 5.22. |
| 4.16 | Tilt servo load underestimated. | **Fixed (v0.2):** 9 kg·cm metal-gear servo, direct drive. |
| 4.17 | Stall assumed CLmax 1.2. | **Fixed:** `mass_balance.py` reports CL 1.0–1.2; PX4 airspeeds use CL 1.0 (round 5, 5.7). |
| 4.18 | "Clark Y" had a sharp lower nose. | **Fixed (v0.2):** published Clark Y ordinates, round LE. |
| 4.19 | STLs had inverted or mixed winding. | **Fixed (v0.2):** check "mesh integrity" (closed, manifold, outward). |
| 4.20 | PETG overhangs printed in mid-air. | **Fixed (round 5):** no part needs supports. Check: the geometric overhang check (every face > 60° is bridged or a ≤ 3 mm ledge). |

### P2 — documentation

| # | Finding | Status |
|---|---|---|
| 4.21 | BOM wrong or incomplete. | **Fixed:** v0.2 BOM; round 5 added the shim, M3×35, the second clamp bolt and the belly foam. |
| 4.22 | `SLICING.md` stale; tracker missing ailerons; generator inputs unrecorded. | **Fixed:** `SLICING.md` rewritten, tracker complete, `params.py` holds every input. |
| 4.23 | Section 6's "no known open issues" was false. | **Fixed:** retracted; this file now opens with the real status. |

---

## Rounds 1–3 and the first premortem (v0.1 — superseded)

Kept for the record. These sections describe the v0.1 design (nacelles,
sleeves, all-flying V-tail, `slice_all.sh`). None of those parts or files
exist any more, and round 4 found several of these fixes were themselves
wrong.

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

**Retracted in round 4 (finding 4.23).** The claim that followed was:
"No known open issues remain in the CAD, slicing, or paperwork."
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
