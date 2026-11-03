# VTOL Plane — Design Review Report

Custom clean-sheet tilt-rotor tricopter: 2 front tilt motors + 1 fixed
rear motor, V-tail, Pixhawk 6C + PX4. LW-PLA vase-mode airframe,
PETG structural parts, carbon spars and boom. Two printers: Anycubic
Kobra S1 (250³ mm, enclosed) + Kobra X (260³ mm).

This file is the record of every review. The current state is at the
top; older rounds follow, newest first. "Fixed" means the CAD, slicing
and paperwork no longer contain that defect. It is not a promise that
the plane flies. That needs the physical checks listed under "Open".

## Current status (v0.2, Nov 2, 2026)

**Ready to print, starting with the test prints.** Print `wing_tip_r`
(flow) and PETG plate `petg_1_fit_tests` (tip ring, one servo hatch, two
hatch blocks), then `tip_fairing_r` (closing tip) and `wing_mid_r` (web
check), then the rest on both printers at once (`tracker.md`).

- Verification gate: `python scripts/check_parts.py` passes **114/114**.
  It covers mesh integrity, mirrored L/R parts, bed fit, every spigot,
  coupler and frame fit, flush glued skin joints (wing, V-tail and
  fuselage) with crease-free rib flanges, spar, joiner, boom and wire paths, motor holes
  and hex-key room, the tilt sweep, prop clearances, thrust split, CG and
  static margin, overhangs judged on the geometry (no part needs
  supports), and mirror symmetry of every part printed from one file for
  both sides. Since round 6 it also checks that no two fuselage inserts
  overlap, that the equipment fits (clear of the skin, the inserts and each
  other) and the battery slides out through the nose, the GPS saddle, and
  the wing webs (clear of the spars and wires along the whole span). Since
  round 7 it checks the servo hatches (flat seat, room inside the skin,
  clear of webs, spars, spigots and pins, ahead of the hinges, screws in
  line, the servo comes out past the ledges), the tilt servos' plug
  pockets and the battery straps' path. Since round 8 it checks the tip
  rings and fairings (fit, flush, taper, root closed behind the hinge,
  control-surface end gaps, the closing edge), the rear motor's clamp and
  lead hole, and that the viewer's manifest and `tracker.md` show each
  file's sliced mass and time. Since round 9 it checks the PETG plates
  (every PETG print on exactly one plate, the layouts' spacing), that in
  every file each part is its own object with its outline where the script
  placed it, that no stray G-code is left behind, and that every extrusion
  stays at least 1 mm inside the bed's edge (no brim cut off). It
  also checks the G-code: present, sliced from the current STL (hash
  stamp), inside the printer's height, one vase speed band, and every wing
  web printed fused to the skin.
- 58 G-code files: 51 single parts and 7 PETG plates, no supports
  anywhere. The S1 prints the right wing and the PETG as plates (13 jobs,
  33.0 h), the X the left wing, the fuselage and the V-tail (16 jobs,
  35.4 h): about 35 h with both running, 29 jobs in all.
- AUW ~2.01 kg, CG target 433 mm from the nose (28.5 % MAC; the stop pin
  at x = 380 gives 434.6 mm, 29.2 %), hover split 37/37/26 %, front motors
  at 59.2 % of their near-empty maximum (limit 60 %: the margin is thin),
  static margin ~18 %.
- Span 1478 mm: the wing and V-tail tips close in vase-mode fairings over
  hidden rings, with no flat end or spar end showing (`DESIGN.md`, "Tips").
- Serviceable: battery out through the nose in a minute; every aileron and
  ruddervator servo on a screwed hatch; tilt servos and front motors come
  out with the yoke (`DESIGN.md`, "Servicing").
- Docs match the files: `DESIGN.md` (design and assembly), `BOM.md`,
  `PX4_GUIDE.md`, `SLICING.md`, `tracker.md`.
- Renders of the whole aircraft, every wing joint, the burst view, cuts
  through the fuselage and wing, the service view, the tip fairings,
  every print file and the PETG plates on their beds are in `renders/`
  (3-D viewer: `DESIGN.md`, "Renders and the 3-D viewer").

**Open, can only be closed by building and flying** (in order):

1. LW-PLA flow, spigot fit, closing tips, web fusion and servo-hatch fit:
   the test prints above.
2. Tilt servo dimensions against the pod bay, before printing pods and
   yokes.
3. Real masses: weigh the parts and re-run `mass_balance.py`. The hover
   margin is thin; if the real AUW comes out above ~2.03 kg, the front
   motors exceed 60 % of their near-empty thrust.
4. CG: balance at 433 mm, then glide-test.
5. Bench: motor order and direction, tilt calibration (−20…90°),
   surface directions, ruddervator mixing, props off.
6. First hover: vibration and compass interference in the logs, and
   the temperature of the ESC block and battery afterwards.
7. Transition tuning: at altitude, into wind, back-transition ready.

## Round 9 — print plates and the printer split (v0.2, Nov 2, 2026)

Question: can several parts be sliced onto one plate, so the set is done sooner? Method: the
slicer's handling of several objects was tried on both materials, with its own arrange and with
a layout it is told to keep (`--arrange 0`, verified by the object outlines it writes); the
plates were sliced and timed, and the work was totalled per printer. A code review then
measured the brims and the placement check. Result: the PETG prints as seven plates
(`scripts/plates.py`, `gcode/s1_petg_plates/`), the LW-PLA skins cannot be plated, and four
LW-PLA parts moved to the X so both printers finish together (renders 47 and 35–38).

| # | Severity | Finding | Fix | Status |
|---|---|---|---|---|
| 9.1 | P2 process | **Every PETG part was its own print job:** 53 prints from 30 files, 22.6 h, each started, levelled and cleared on its own. Small parts were also held back by the minimum layer time: the 21 hatch parts take 3 h 53 min as single files and 1 h 13 min sharing one bed. | Seven plates in build order, 474 g and 17.5 h: `petg_1_fit_tests` (tip ring, one servo hatch, two blocks) goes with the LW-PLA test prints, and `petg_7_pods_yokes` waits until the tilt servos are measured. `plates.py` lays them out (print orientation kept, turned about z only, 6 mm apart, 15 mm inside the bed; deterministic), and `slice_all.py` slices each with `--arrange 0`, every placed copy as its own STL: each part keeps its own brim and stays its own object, which the S1's Klipper firmware can cancel alone. The single-part files stay for reprints. New checks: every PETG print on exactly one plate (53 on 7); layouts ≥ 4.5 mm apart (5.0 at the tightest) and 15 mm in. | fixed, gated |
| 9.2 | P2 process | **LW-PLA cannot share a bed.** In vase mode the slicer takes several objects only one after another, and then every object but the last has to pass under the print head's gantry: 48 mm on the S1, 30 mm on the X. The skins are 130–240 mm tall; only the 20–32 mm tip fairings would fit under, and pairing one with a skin saves a single 17–30 min job. | The skins stay one per job; `SLICING.md` says why. | by design |
| 9.3 | P1 schedule | **The S1 had twice the X's work:** 26.8 h of LW-PLA plus 22.6 h of PETG, against 24.0 h on the X. With both running, the X would stand idle for a day. | `fuse_1`, `fuse_3`, `vtail_r` and `ruddervator_r` print on the X. The S1 now prints the right wing and the PETG plates (13 jobs, 33.0 h), the X the left wing, the fuselage and the V-tail (16 jobs, 35.4 h): about 35 h for the whole set instead of 49, in 29 jobs instead of 75. Every 240 mm part now prints on the X (260 mm), which also retires 5.24's lid question; the S1's tallest is 217 mm. | fixed, gated |
| 9.4 | P2 process | **A part that moves printer would leave its old G-code behind,** ready to be printed by mistake (this round: four files in `gcode/s1_lwpla/`), and the gate never checked the G-code's X and Y. | A full `slice_all.py` deletes G-code no current part or plate produces. New checks: no stray G-code files; every extrusion at least 1 mm inside the bed's edge (closest now 2.3 mm). | fixed, gated |
| 9.5 | P1 print | **Brims cut off at the bed's edge** (found in review). The first plate layout kept 8 mm from the edge, sized for a ~7 mm brim, but the PETG profile's auto brim reaches 13.6 mm on the fuselage couplers, 10 mm on the boom ribs. On the rings plate the slicer cut both couplers' brims off at the edge, where the tall thin rings need them most. The single `boom_rib_l` file had the same: the slicer's own arrange had turned the 45° rib along x, 4.7 mm from the edge. The "on the bed" check could not see either, since the slicer trims a brim to the bed. | Plate margin 15 mm; the V-tail ribs and tip rings moved to the boom-rib plate to make room on `petg_6`. Single parts are now centred by `slice_all.py` and sliced with `--arrange 0` too, so the slicer no longer turns them. The edge check now asks for 1 mm of clearance, which a trimmed brim (0.2 mm) fails. Neighbours' brims may still meet and print joined: cut them apart. | fixed, gated |
| 9.6 | P2 gate | **The placement check compared only object centres** (found in review), which a part turned 90° or 180°, or turned the wrong way, keeps. | Each object's outline (`EXCLUDE_OBJECT_DEFINE` polygon) is compared with the footprint where the script placed it, in every file, plates and single parts: 104 objects in 58 files, within 0.001 mm. | fixed, gated |
| 9.7 | P1 flight | **The stop-pin hole hinged on a fraction of a gram.** Re-slicing moved three PETG masses by 0.2–0.3 g (the slicer is not repeatable even at a fixed position: `boom_pod_r` came out at 27.66 and 27.94 g), the battery's target crossed the midpoint between two holes, and the "nearest hole" rule flipped the pin from x = 370 to 380, changing the documented CG, hover load and PX4 values. | The pin goes in the aftmost hole that keeps the CG within 29.5 % MAC (`CG_PIN_MAX`), 0.5 % inside the band, which also gives the front motors the most margin: x = 380, CG 434.6 mm (29.2 %), front motors 59.2 % (59.7 % at 370, 60.1 % at 360), static margin 18 %. The rule has 0.6 mm of CG to spare against the noise. PX4: hover CG 437 mm, `CA_ROTOR2_PX` −0.34. | fixed, gated |

## Round 8 — wing and V-tail tips (v0.2, Nov 2, 2026)

Question: is a part missing at the wing tip, and should it be smoothed out or pointed? Method:
the tip was measured on the model and compared with the reference (a Flightory Stallion, whose
tips are faired). Nothing structural was missing, but the wing ended in a flat PETG plate with
the spar ends showing and a notch behind the aileron, and the V-tail in a flat flange. Both
tips now close in LW-PLA vase fairings over hidden PETG rings, the way the fuselage sections
join (`DESIGN.md`, "Tips"; renders 43–46 and `00_tips`). The extra mass pushed the hover
margin past its limit, so the rear motor moved forward 10 mm. All parts were rebuilt and
re-sliced (51 files).

| # | Severity | Finding | Fix | Status |
|---|---|---|---|---|
| 8.1 | P2 finish, drag | **The wing ended flat.** `rib_tip` was a solid 3 mm PETG plate cut at the hinge line (y 707–710), with both carbon spar ends showing in it and a 5 mm notch behind the hinge between the aileron's end (y = 705) and the plate. A square end also sheds the tip vortex right at the skin's end. | A Hoerner-style vase fairing (`tip_fairing_l/r`, 2.6 g) butts against `wing_tip`'s end over a hidden ring (`rib_tip`, now 7.1 g): straight for 6 mm, then the upper surface curves down to the flat bottom at a sharp edge 32 mm out, with the LE pulled back 18 mm and the TE 8 mm. The fairing is full chord and the ring is solid behind the hinge, so the notch is closed too; the spar ends sit in the ring's bosses. Span 1420 → 1478 mm. New checks: the ring fits both skins (0.82–0.83 mm), the seam is flush (0.04 mm) and keeps the taper (0.01 mm), the ring closes the fairing's root behind the hinge (0 of 25 points open), the aileron stops 2.0 mm short of the fairing, and the fairing closes to 0.34 mm. Its walls lean at most 41.4° from vertical (vase limit 45°). | fixed, gated |
| 8.2 | P2 finish | **The V-tail tips were flat too:** a 1.5 mm flange on `vtail_tip_cap`, square to the panel. | The same build: a symmetric fairing (`vtail_tip_fairing` ×2, one file, 1.3 g) closing onto the chord plane 20 mm out over a hidden ring (`vtail_tip_cap`, now 2.7 g). The ruddervators run 2 mm further out (s = 238) and stop 2.0 mm short of the fairing, as the ailerons do. Checks as for the wing: fits 0.84–0.85 mm, flush 0.03 mm, taper 0.00 mm, root closed, 0.25 mm at the end, walls ≤ 37.6°, and the shared file is mirror-symmetric to 0.01 mm. | fixed, gated |
| 8.3 | P1 flight | **The hover margin, again.** The tip parts add 5 g net, 2 g of it on the V-tail, 540 mm behind the CG. That moved the battery's target about 2.4 mm forward, past the midpoint between two stop-pin holes, so the pin moved from x = 380 to 370 (CG 2.6 mm further forward), and the front motors needed 60.1 % of their near-empty thrust (limit 60 %). | Rear motor forward 10 mm, x = 790 → 780: for the same CG it takes more of the load. Its clamp (x 762–798) stays 2 mm behind the fuselage's tail cone, and the boom's lead hole moves behind the clamp to x = 803 (`BOOM_LEAD_X`). The rear prop clears the fuselage by 33.3 mm and the V-tail by 66.7 mm. New check: the clamp clears the tail cone and the lead hole is in open boom. Result: AUW ~2.01 kg, CG 432.1 mm (27.8 % MAC) with the pin at x = 370, front motors 746 g = 59.7 %, static margin 19 %. PX4: hover CG 435 mm, `CA_ROTOR2_PX` still −0.35 after rounding, airspeeds unchanged (conservative stall 12.05 m/s). | fixed, gated (margin thin) |
| 8.4 | P2 process | **The viewer's masses and times lagged the G-code.** `build_all.py` wrote the viewer manifest before slicing, so the print panel, and any tracker made from it, showed the previous build's slice. After this round's second build the manifest disagreed with the G-code on three PETG parts (`battery_tray`, `frame_main`, `tail_block`) by 0.1–0.2 g, though their STLs had not changed: the slicer is not run-to-run repeatable (`frame_main` came out at 20.1 g in one build and 20.26 g in the next three slices; `battery_tray`'s toolpath order changed at the same mass). Separately, `SLICING.md`'s totals (PETG 467 g / 21.0 h) disagreed with the tracker's (478 g / 22.7 h). | The manifest is now written after slicing (also when a part fails to slice, and by `slice_all.py` run on its own), and the tracker's print table and totals are generated from it (`make_tracker.py`, which keeps the hand-edited Status column). Two new checks: the manifest lists exactly the print table's files, with their printer, material, copies and each file's sliced mass and time; and the tracker matches the manifest. PETG now 476 g / 22.6 h everywhere. Masses are good to ~0.2 g a part (`SLICING.md`). | fixed, gated |

## Round 7 — serviceability: battery, servos, motors (v0.2, Nov 2, 2026)

Questions: how does the battery come out, is there a hatch that opens and closes, how easy is a
bad servo to replace, and is the nose removable? Method: every service job was walked through
on the geometry, part by part and screw by screw, and every way in was proven with ray and
clearance checks in the gate. The answer is the new "Servicing" table in `DESIGN.md`. The nose
was already removable (one M3 nylon screw) and is the fuselage's only hatch; everything
behind it was reachable. The servos and the battery straps were not. The viewer gained a
"Service" animation and the six servo hatches placed in the model (renders 39–40). All parts
were rebuilt and re-sliced (48 files).

| # | Severity | Finding | Fix | Status |
|---|---|---|---|---|
| 7.1 | P0 build | **The battery could not be strapped down.** The tray's strap slots (x = 280/330, \|y\| < 12) sat under the battery, and the rails at y = ±24 ran unbroken, so no strap could pass under the plate. | Strap slots beside the battery (\|y\| 25–27.8) and a gap in both rails under the plate at each strap station. The straps are threaded before the tray is glued in (`DESIGN.md` step 3.8, and a reminder in `tracker.md`). New check: down both slots and under the plate through the rail gaps nothing is crossed; the strap clears the battery by 1.0 mm and the skin by 4.4 mm. | fixed, gated |
| 7.2 | P1 service | **The aileron and ruddervator servos were glued in.** Each sat in a `servo_cage` epoxied inside the skin, so a stripped servo meant cutting the skin open. | Removable `servo_hatch` (×6): the servo screws to its posts and the cover sits flush in an opening cut to its outline, held by two M2×6 screws in `hatch_block`s (×12) glued inside the skin. The pushrods unhook at a clevis on the horn. The V-tail hatch plane is a minimax fit to the curved skin, so the cover is never proud of it. The mid hatch moved to y = 325 to clear the boom rib's spigot, and the block ledges start at \|b\| = 15.5 so the horn (to 14.5) clears them. New checks: skin within −0.01…+0.45 mm of every cover and block; contents fit inside the skin; ≥ 2.65 mm from the webs, spars, spigots and V-tail pins, opening 1.7 mm from the nearest web; 29.5 mm ahead of the hinge cuts; 6.6 mm over the mid servos for the leads; screws in line and ledges seating the cover; servo, posts and horn come out past the ledges. | fixed, gated |
| 7.3 | P1 service | **A tilt servo could not be changed.** Its lead ran through a Ø6 hole, the Ø7 channel and the 5 × 7 tongue groove into the closed wing, and its plug fits none of them. | A plug pocket under each pod's servo bay, open on the inboard face and joined to the wire channel: 27.5 × 11.5 × 10.5 mm for a 25 × 7.6 × 4 mm plug pair. The servo's lead drops straight into it; a 600 mm extension runs from the pocket to the fuselage. A first version, a slot through a 2 mm floor under the bay, would have printed a 19 × 12.5 mm unsupported plate, so the pocket now rises to the bay. New checks: the pocket opens on the face, the lead drops in from the bay, the route to the channel is clear; walls ≥ 2.0 mm to the pod's skin. | fixed, gated |
| 7.4 | P0 build | **The yoke could not be fitted as documented.** `DESIGN.md` said to screw the horn to the yoke and then slide the yoke onto the spline, but the yoke clears the pod and axle boss by 0.5 mm, far too little to push a horn onto its spline, and spreading the arms ~3 mm risks cracking the PETG. | New order (steps 2.4–2.6): the disc horn goes on the spline first, the yoke is lowered on from above, then the axle screw and shim, then two screws drilled through the inboard arm into the disc horn (with a depth stop). The Ø7 hole on the axis reaches the horn's centre screw later. | fixed (procedure) |
| 7.5 | P2 service | **Motor-lead joints had no defined place** and could end up inside a pod or the boom, out of reach. | The joints sit in the flex loop outside each pod and outside the boom, between the rear motor and its lead hole: soldered, or 3.5 mm bullets (~7 g more). Front motors come off with the yoke; the rear motor's screws are reached in place. | fixed (procedure) |
| 7.6 | P1 flight | **The hover margin with every gram counted.** The hatches weigh 14.5 g more than the cages, and the straps, M2 screws, pushrods and clevises, never in the mass list, add ~16 g. The AUW went from 1974 to 2006 g, and with the stop pin at 370 the front motors needed 60.2 % of their near-empty thrust (limit 60 %). | CG target 28.5 % MAC (was 27 %), and the stop pin goes in the hole nearest the target (380): CG 434.4 mm (29.0 % MAC), static margin 18 % (was 20 %), front motors 59.6 %. The static margin is now computed at the CG the pin gives, not at the target. PX4: hover CG 437 mm, `CA_ROTOR2_PX` −0.35. The conservative stall (AUW +10 %, 35 °C, CL 1.0) is now 12.03 m/s, so the rounded-up airspeeds rose one step: STALL 13, MIN 16, TRANS 18 m/s. Round 5's claim (5.7) that they don't shift with small estimate changes was wrong at a rounding boundary. | fixed, gated (margin thin) |
| 7.7 | P2 doc | **"Every panel ≤ 37 mm" was not true.** The mid section's servo bay is 46 mm wide: a web ahead of the rear spar would run through the hatch opening. | Measured: the mid section's top skin sees a third of the root's strain (0.17 × 10⁻³ at 1 g at its inboard end), so the 46 mm panel reaches a flat panel's wrinkling strain only near 3 g, where the root's 37 mm panels are already past theirs. `DESIGN.md` corrected. | verified |

## Round 6 — access, internal structure and the electronics bay (v0.2, Nov 2, 2026)

Questions: is there an opening in the fuselage for the FC, battery and the rest, from every
angle? Do the wings, and anything else, have the ribs they need? Method: every service point
was measured from the nose opening; the skins were checked for strength by hand calculation;
the webs were proven in the slicer on both printers; and the electronics were placed as
envelopes (`scripts/payload.py`) that the gate checks against the printed parts. The result
is in `DESIGN.md` ("Inside the wing", "Access and openings") and in the viewer, which gained
a burst view, a nose-open animation, equipment and cable models, section cuts and a gallery
of every print file (renders 27–38). All parts were rebuilt and re-sliced (47 files). This
round supersedes 5.14 (ESCs tied to the spars), 5.16 (rear ESC at x ≈ 400) and 5.17 (nose tip
taped).

| # | Severity | Finding | Fix | Status |
|---|---|---|---|---|
| 6.1 | P1 structure | **The wing skins had no internal structure.** Each spans 204–217 mm between ribs. At the root the top skin is strained to 0.44/0.87/1.31 × 10⁻³ at 1/2/3 g, while a wide, gently curved 0.5 mm panel wrinkles at about 0.5–0.9 × 10⁻³. In hover the root bends the other way: the flat bottom is compressed to ~1 × 10⁻⁴, above flat-plate buckling (~4 × 10⁻⁵ for 150 mm panels), so it would oil-can in steady hover. | Spanwise webs in the root (6) and mid (4) sections, top skin to bottom skin, cutting every panel to ≤ 37 mm (except the mid section's 46 mm servo bay, see 7.7). Each is a 0.06 mm slot that the single vase wall runs into and out of, so it prints as a fused double wall with no extra moves (`webbed_wing_skin`). The tip needs none (0.25 × 10⁻³ at 3 g). +30 g. New checks: spars and wire hole clear of the webs at 159 stations (min 1.62 mm); the boom-cup motor leads and the pitot tubing cross no web; and every web is fused in the G-code (turn-backs within 0.22 mm of the skin line). | fixed, gated |
| 6.2 | P1 print | **The two vase profiles differed,** and neither could print the webs. The S1 had thin-wall detection on, which splits a section at a neck of up to ~0.8 mm, and both had the preset 0.049 mm closing radius, which erases a 0.06 mm slot. | Both profiles: `slice_closing_radius` 0.01 and `detect_thin_wall` 0, set by `make_slicer_profiles.py`. A sweep in the slicer showed one continuous path (0.96–1.02× the outline) with every web fused on both printers. `SLICING.md` explains why the values must stay. | fixed, gated |
| 6.3 | P1 build | **Inserts ran into the coupler rings.** The battery tray's rail feet sat 0.46–1.05 mm inside `coupler_240` and `coupler_370`, and the FC shelf's edges 0.15–0.44 mm inside them. Neither part would have gone in. | Inserts are cut to the fuselage interior, or to the coupler ring where there is one, plus clearance (`inner_envelope` in `structure.py`). New check "fuselage inserts do not overlap": it reports those depths on the old parts and 0.00 mm now. | fixed, gated |
| 6.4 | P0 build | **The GPS could never be fitted or serviced.** It was to sit inside `fuse_3` at x = 560, but that bay is sealed when `fuse_4` goes on (step 3.7), and it was installed in step 5. | External PETG saddle (`gps_mount`) glued on top of `fuse_3`, with a Ø16 cable hole that passes the 10-pin plug. The cable, or a pull cord, is laid in during step 3.3. New checks: the skirt follows the skin with a 0.15–0.20 mm glue gap all round, the 50 mm puck fits the pad, and the cable hole is open. | fixed, gated |
| 6.5 | P1 build | **No way to take a wing off.** The wing connectors were undefined, at the wing root ~240 mm from the opening. | Wing plugs at x ≈ 330 (3.5 mm bullets and servo plugs), 90 mm from the nose opening. Procedure in "Access and openings"; extension lengths and bullets in the BOM. | fixed (procedure) |
| 6.6 | P1 build | **The front ESCs had no home.** "Between the spars" in the root bay is where the Ø10 wire bundle runs. With webs the ESCs could not be tied to the spars, and they needed 40–50 cm DShot leads. | All three ESCs taped into one block, hung under the FC shelf's aft part (x 360–410) above the battery. It sits > 10 mm from any skin, its DShot leads are short, and the rear motor's leads arrive from the boom right behind it. The shelf now runs x 255–415. (A deck on the tray behind the battery was tried first; it blocked the battery from its CG target, see 6.8.) New checks: equipment clears the skin, is not cut by any insert, and keeps ≥ 0.5 mm from other equipment. | fixed, gated |
| 6.7 | P1 access | **Access audit.** The nose is the only opening (115 × 135 mm). | Battery, Pixhawk, boards, wing plugs and the ESC block are 25–180 mm in; nothing serviceable lives aft of x ≈ 450. New check: the battery slides out through `coupler_240` (10.4 mm to spare each side). | verified, gated |
| 6.8 | P0 flight | **Hover margin.** The webs, the GPS saddle, the longer tray and the servo BEC (12 g, missing from the mass list) raised the AUW from 1909 to 1998 g. With the ESC block on the tray deck the battery could not reach the CG target either, so the front motors needed 61–62 % of their near-empty thrust (limit 60 %). | Tip webs and the main spar's front web dropped (−17 g); wiring estimate corrected; tray shortened; saddle lightened. The ESC block moved under the shelf, so the battery reaches the target. The rear motor moved forward from x = 820 to 790: its clearance improves (35.4 → 37.5 mm), PX4 `CA_ROTOR2_PX` −0.36. The thrust split is now computed at the CG the stop pin actually gives. Result: AUW 1974 g, front motors 743 g = 59 % of near-empty maximum, CG 429.4 mm (26.4 % MAC). | fixed, gated |
| 6.9 | P2 build | **Cooling.** Three ESCs, the power module, the BEC and the LiPo sit in a closed LW-PLA fuselage (softens at 55–60 °C), and the nose-tip opening was taped. | The nose tip stays open as an air inlet (mesh optional); two Ø10 outlets in the belly at x = 445. In `DESIGN.md`, the holes table and the preflight list. | procedure (check after the first long hover) |
| 6.10 | P2 flight | **PX4 sensors.** The Pixhawk's internal compass now sits next to the ESC block, and the guide said nothing about the GPS's safety button. | `PX4_GUIDE.md`: disable the internal compass (`CAL_MAGn_PRIO` 0) and use the GPS one. The safety button is optional: PX4 v1.15 defaults `CBRK_IO_SAFETY` to 22027 (safety off); set 0 to use it, or `COM_SAFETY_MODE` = 1 on newer releases. | documented |
| 6.11 | P2 structure | **V-tail and fuselage.** Do they need spars or webs? | No. The V-tail skin is ~12× stiffer in bending than a 4 mm spar would be, and sees ~0.56 × 10⁻³ at CL 0.5 and 25 m/s: fine for normal flight. The fuselage shell has a 4–15× buckling margin. `DESIGN.md`: never lift the plane by the V-tail. | verified |
| 6.12 | P2 check | **Equipment positions were scattered.** The mass list held only x positions, the BEC was missing, and the docs disagreed with them. | `scripts/payload.py` is the single source for every item's envelope and position. The mass balance, the gate and the viewer all read it. | fixed |

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
| 5.14 | P2 build | **ESC heat:** ESCs sit inside closed LW-PLA sections; LW-PLA softens at 55–60 °C. | Rule in `DESIGN.md`: no ESC touches a skin; heat-shrink and tie to the spars with an air gap. | superseded by 6.6 (ESC block under the FC shelf) and 6.9 (cooling) |
| 5.15 | P2 build | **Nominal carbon fits:** an 8.0 joiner in an 8.0 ID spar, and the 16.0 boom in 16.3 printed holes. | Dry-fit, sand or ream; documented. | procedure |
| 5.16 | P2 flight | **Compass:** the rear ESC supply ran past the GPS at x = 560. | Rear ESC moved to x ≈ 400 (5.18), so the battery leads stay ahead of the GPS. The rear motor's phase leads still run in the boom ~70 mm below it: keep them twisted together, and check interference in the first hover log. | superseded by 6.4 (GPS outside), 6.6 and 6.10 (GPS compass only) |
| 5.17 | P2 build | **Landing:** no gear; the plane lands on its LW-PLA belly. The nose tip is open (vase mode). | EVA foam belly strip (BOM), land on grass; tape the nose tip. | belly strip: procedure; nose tip superseded by 6.9 (now the air inlet) |
| 5.18 | P0 build | **Tail assembly order impossible** (found by an independent code review of this round). The motor mount is a closed clamp, so it can only go on over the boom's aft end, before the tail block. The rear ESC (x ≈ 700) and its leads were inside `fuse_4`, sealed before they could be connected. A second review pass also found that `frame_rear` and the `coupler_610` web could not be reached for reaming or gluing, and that pull strings left in the holes would be pinched. | Rear ESC moved to the front of `fuse_3` (x ≈ 400). Every boom hole is reamed while the parts are loose. The boom goes into `fuse_3` before `fuse_4`, so all its glue joints can be reached. The mount, then the tail block, go over its aft end; the leads are fished through the boom afterwards. | fixed |
| 5.19 | P1 check | **The supports check could never fail:** supports are off in every profile. It missed a 7.7 mm unsupported ledge on the mid/tip rib flange, and the first gusset (5.1) left the underside at the boss tip unsupported. The first geometric version could itself be fooled in three ways: large faces were under-counted, a sloped face could anchor on itself, and a partial ledge counted as a bridge. | New geometric check on the print-ready meshes. Faces > 60° from vertical must be bridged (≤ 30 mm, with the overhang continuing across the whole span). Flat faces may also be ledges of ≤ 3 mm. Sampling is area-weighted, and the probed face's own plane is ignored. It now fails all four pre-fix parts (pod 237 mm², boom rib 1361, mid/tip rib 43, rear mount 354) and synthetic shelf, wedge and partial-ledge cases, and passes bridges, holes and 45° chamfers. Spigot rings now stop 2 mm ahead of a hinge, not 8; the gusset runs from the boss's lowest point at its tip. The support-move count stays as a profile sanity check. | fixed |
| 5.20 | P1 check | **Stale-G-code check used file times,** which git does not keep. It failed on every fresh clone and passed after restoring old G-code. | `slice_all.py` stamps each G-code file with the SHA-256 of its STL; the gate compares hashes. | fixed |
| 5.21 | P0 flight | **PX4 rotor count:** airframe 13100 defaults to `CA_ROTOR_COUNT` 4, a phantom rotor 1 m out that takes part of every command. | Guide sets `CA_ROTOR_COUNT` = 3. | fixed |
| 5.22 | P0 flight | **PX4 tilt servos are mirror images:** one needs Rev Range. The tilts also sit at the raw Disarmed PWM while disarmed and during spool-up. On the reversed output, the PWM min is the forward end. | Guide: Rev Range on one tilt output, with its end points and hover disarmed value given separately; Disarmed PWM at the hover (0°) position on both. | fixed |

### External review of the pushed files (Oct 31, 2026)

Three further claims were checked against the files. Two are not defects, but each now has a
gate check so the fact stays verified.

| # | Claim | Finding | Status |
|---|---|---|---|
| 5.23 | The left V-tail root rib and tip cap have no print file. "Same file L and R" is wrong, so printing two gives two right parts. | Not a defect. Both parts are mirror-symmetric about their own chord plane: mirroring deviates 0.00 mm and the volumes are equal. The mirrored left part is therefore the right part turned over, and either copy fits either side. The same holds for `servo_cage` and `control_horn`. New check: every part printed from one shared file must be mirror-symmetric (it fails the pod and boom rib, ~12 mm). Tracker and BOM wording clarified. | verified, gated |
| 5.24 | `fuse_1`, `fuse_3` and `vtail_r` print to Z 242, but the S1 lid clearance is 240. | Not a defect. The top layer is 240.0 mm. 242 is the end-of-print lift (last layer + 2 mm, capped at the printable height). The S1's printable height is 250 mm. The 240 mm `extruder_clearance_height_to_lid` is OrcaSlicer's by-object collision setting ("Used for collision avoidance in by-object printing"), which this project does not use. New check: every G-code move is inside the printer's height. | verified, gated |
| 5.25 | `DESIGN.md` and `PX4_GUIDE.md` are still v0.1: 13 m/s, nose tape, M3×6, MAIN plus DShot. | Already fixed in `6d1b24a` (5.5–5.8). Both docs are v0.2 on `origin/main`: 17 m/s, nylon nose screw, M3×8, motors on AUX1–3 with DShot. The claim was based on the earlier files. | fixed earlier |

### Appearance review: renders and joint flushness (Nov 2, 2026)

Question: once glued, do the wing sections look like one piece? Method:
- **Renders:** the full assembly was rendered from every side (`renders/`, `viewer/`).
- **Profile comparison:** the skin and rib outlines were measured on either side of every glued
  rib face.
- **Reflection stripes:** a stripe render checks surface continuity.

An independent code review then ran two passes over the changes. It found 5.29, 5.30, 5.33
and 5.34, and all four are fixed or documented.

| # | Finding | Result | Status |
|---|---|---|---|
| 5.26 | Are the glued skin joints flush? | Yes. At every rib face the two outlines match within 0.02 mm on top and bottom, after 5.31 (0.08 mm before). That covers the wing (root, boom, mid/tip and tip ribs) and the V-tail (root rib, tip cap). The fuselage rings meet within 0.02 mm at x = 240, 370 and 610. The aileron top surface continues the wing exactly at the hinge line, and the reflection stripes run unbroken from root to tip. New check "glued skin joints are flush" (≤ 0.15 mm). It fails a skin offset by 0.3 mm (0.30–0.38 mm), a fuselage section offset by 0.2 mm, and a tip rib 1 % oversize (0.79 mm). The 0.25 mm-per-side spigot and coupler slip can still make a step in the build. `DESIGN.md` steps 1.4, 3.4, 3.7 and 4.2 now say to line the skins up before the glue sets. | verified, gated |
| 5.27 | What still breaks the one-piece look | Four things, all by design: PETG rib bands if their colour differs; the pod fairing (the boom-rib tongue, up to 18 mm above the wing ahead of x ≈ 422); the control-surface end gaps (y 283–286, 485–492, 705–710); and the open spar ends in the tip ribs. `DESIGN.md` "Finish" covers each one: same-colour PETG or paint, light sanding, filler for the tips, re-balance after painting. | documented |
| 5.28 | `slice_points` in `check_parts.py` threw an IndexError when the plane missed the mesh. A `fit` check would then have crashed instead of failing. | It now returns an empty section, and the flush check reports that as a failure. | fixed |
| 5.29 | Found by the independent review. The flush check compared only the common chord and the LE, so a rib that stops short of (or runs past) the skin's trailing edge or hinge face would pass. One such step existed: the mid/tip rib flange was a prism of the y = 490 section across 487–490, so its inboard face stopped 0.25 mm short of the mid skin's hinge face. | The mid/tip rib flange is now ruled between its two faces, as the boom rib already was. The check now also compares where both outlines end aft. The one exception is the boom rib's outboard face, where the full-chord rib is meant to run past the mid skin's hinge face (the aileron bay end). `rib_midtip_l/r` were re-sliced: 15.0 g and 35 min, as before. | fixed, gated |
| 5.30 | Found by the independent review. The viewer's local server served the whole repo (`.git` included) to any Host header, and accepted captures from any web page. | It now serves only the viewer page, its manifest and the assembly STLs, and answers only to 127.0.0.1/localhost. Captures need the page's own Origin and are capped at 32 MB. 17 request probes behave as intended. | fixed |
| 5.31 | The rib flange profiles used 40 points (36 on the V-tail), while the skins use 48. Between points, the flanges therefore missed their skins by up to 0.08 mm. | Flange profiles now use the skins' exact point distribution (`airfoil_xz` and `vt_section_local` in `structure.py`), so every seam measures 0.00–0.02 mm. The 10 affected PETG files were re-sliced; each changed by ≤ 0.05 g and ≤ 30 s, and the totals are unchanged. | fixed, gated |
| 5.32 | The viewer smoothed shading one part at a time. That drew small jogs in the reflection stripes at every rib band, even where the surfaces match. | Normals are now smoothed across all parts at once, weighted by face area, so a glued seam renders as one surface. Smoothing like this would also hide a real crease, so the gate now checks the flange taper as well (5.33). | fixed |
| 5.33 | Found by the second review pass. Four flanges were prisms of one section against tapered skins: the root rib, tip rib, V-tail root rib and tip cap. They met their skins at small creases: 0.5–1.7° on the surfaces and 4.6–11.5° at the trailing edge or hinge face. | Each flange is now ruled between the sections at its two faces (`ruled_y` in `structure.py`), so it continues the taper. The root rib now spans exactly the 220 mm root chord at y = 60. New check "rib flanges keep the skin taper": each free flange face must match the skin's section continued to that station. The prisms failed it at 0.24–0.60 mm; the ruled flanges measure 0.00 mm. Six PETG files were re-sliced; each changed by ≤ 0.03 g and ≤ 15 s, and the totals are unchanged. | fixed, gated |
| 5.34 | Found by the second review pass. "Point for point" was not true at the boom rib's outboard face: the full-chord rib meets the hinge-cut mid skin, so the two outlines use different points. | Documented as the one exception in `DESIGN.md` and in `airfoil_xz`. The shapes still agree within 0.02 mm. | documented |

## Round 4 — independent audit of v0.1 (statuses as of v0.2)

The v0.1 files these findings describe were deleted. The v0.2 design
(parametric `scripts/`) was rebuilt to fix them, and round 5 closed the
rest. "Check" names the `check_parts.py` test that guards each fix.

### P0 — blockers

| # | Finding | Status |
|---|---|---|
| 4.1 | Rear motor pointed backwards; its socket barely engaged. | **Fixed (v0.2):** vertical lift motor on a boom clamp at x = 820, x = 790 since 6.8, x = 780 since 8.3 (round 5 made it printable and serviceable). Check: rear prop disc clearance, motor holes, hex-key room. |
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
| 4.11 | Printed mass and AUW inconsistent between docs. | **Fixed:** `mass_balance.py` reads the G-code; all docs quote it (1909 g then, 1974 g since round 6). |
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
