# Custom VTOL RC Plane — Design Spec (v0.1)

Designed from scratch, 2026-10-31. No licensed files: every part is generated
by the scripts in `scripts/`. Defaults below are the design baseline — Ajaya
can override any of them.

## Configuration

- **Layout:** tilt-rotor tricopter — two front tilt motors + one fixed rear
  motor, V-tail. Same proven architecture as the Flightory Stallion, but
  sized and sectioned for our printers. Two tilt servos only; no tail-sitter
  landing gymnastics, no quadplane dead weight in cruise.
- **Flight controller:** Pixhawk 6C running PX4 (tilt-rotor VTOL airframe).
  ArduPilot is the fallback if PX4 tilt tuning proves painful — the
  hardware is identical either way.
- **Manual backup link:** ELRS receiver (as on the 4G drone project).
  The phone-over-4G MAVLink link can be added later as phase 2.

## Dimensions and weights (targets)

- Wingspan: 1420 mm (650 mm panels each side + 120 mm fuselage width).
  Length: ~950 mm. (An earlier 1300 mm figure was wrong: it did not
  count the fuselage width between the panels. The generated geometry
  rules, so the spec was corrected to match it.)
- Wing: Clark Y airfoil (flat bottom, forgiving, easy to build), root chord
  220 mm, tip chord 150 mm, mean chord ~185 mm, wing area ~0.263 m².
- Wing loading at 1923 g AUW: ~72 g/dm². Estimated stall speed
  ~9.8 m/s (~35 km/h) at Clmax 1.2 (estimate, not a guarantee — first
  flights will confirm).
- AUW budget (`scripts/mass_balance.py`, printed parts from the sliced
  G-code): printed airframe ~690 g, 4S battery ~520 g, everything else
  (motors, ESCs, servos, FC, carbon, wiring, hardware) ~710 g → ~1923 g.

## Power system (sized from the Stallion's proven setup)

- Motors: 3× 2807 1300KV class (Emax ECOII 2807 1300KV or T-Motor F90).
- Props: 7×4.5 (two CCW, one CW), 7×4 / 7×5 / 7×6 acceptable.
- ESCs: 3× 45A BLHeli_S (individual, not 4-in-1 — easier placement).
- Battery: 4S 5000 mAh LiPo baseline (4S Li-ion up to 4S3P possible
  for endurance builds).
- Hover math: 3 motors × ~1.3 kg max thrust ≈ 3.9 kg → T/W ≈ 2.1 at
  full throttle, hover around 45–50% throttle. Comfortable margin for
  control authority in hover and transition.

## Servos and tilt mechanism

- Tilt: 2× metal-gear servos, Kingmax 1203MD / GDW DS041MG class,
  driving printed PETG nacelles that pivot on 3×8×4 mm flanged bearings
  with a 3 mm shaft.
- Control surfaces: 2× 9 g metal-gear aileron servos, 2× 9 g metal-gear
  V-tail (ruddervator) servos. 6 servos total.
- Yaw in hover: differential tilt of the front motors (vectored yaw),
  same as the Stallion.

## Structure and materials

- Airframe: LW-PLA (active foaming) for wings, fuselage, tail — light,
  sandable, glueable. Print in vase mode (single wall, open ends,
  8 mm outer brim). Correction: there are NO internal ribs — the
  original spec claimed Eclipson-style ribs that were never modeled.
  Stiffness comes from the carbon spars + glued section joints.
- Wing spars: 8 mm OD main + 6 mm OD rear, 2× 650 mm each (one per
  panel, not a full-span spar through the fuselage). The spars slide
  through the open-ended vase sections and are glued at each section
  joint; wing section butt joints get a wrap of tape over the glue.
- Fuselage sections: open-ended vase tubes, glued butt joints
  reinforced by PETG joiner sleeves slid over each joint. No battery
  hatch: the nose section (fuse_1) is REMOVABLE and the battery +
  tray slide in from the front. The nose joint uses the 60 mm
  sleeve_240 as a socket: glue the sleeve to fuse_2 ONLY, and let
  the nose slip 30 mm into its front half, retained by friction +
  tape. The other sleeves (480, 720) are glued both sides.
- Order of assembly matters at the tail: the V-tail servos live in
  fuse_4 and the rear motor socket is glued over the tail end, so
  install the tail servos and route their wires BEFORE gluing the
  socket on. Once the socket is glued, the tail interior is closed.
- Structural parts: PETG for booms, motor mounts, tilt nacelles
  (motor mounts 100% infill). Carbon tubes for spars: 8 mm OD main,
  6 mm OD rear.
- Fasteners: M2/M3 screws, brass inserts where parts come apart
  repeatedly (servo doors, FC mount). CA glue for section joints.
- V-tail: all-flying panels (NACA 0012, root 180 mm, tip 110 mm,
  240 mm span each), included angle 110 degrees (each panel 35
  degrees from horizontal). Each panel pivots on a 3 mm carbon rod
  glued into its spanwise pivot hole; the rod protrudes 20 mm from
  the root into a PETG pivot block glued to the fuselage tail. The
  9 g V-tail servos drive the panels via pushrods to the root horns.
- Nacelle station: 70% semi-span (mid-section region). Attachment:
  bracket cheek plates glue to the wing leading edge + one M3
  through-bolt per nacelle with a crush-resistant spacer sleeve
  inside the wing (the vase shell alone would crush under a bolt).

## Print plan (dual printer)

- Every part sectioned to fit BOTH beds: Kobra S1 250×250×250 mm,
  Kobra X 260×260×260 mm. Wing: 3 sections per side, each under
  250 mm long. Fuselage: 4–5 sections under 250 mm.
- Printer assignment rule of thumb: LW-PLA airframe sections split
  evenly across both printers; PETG/ASA structural parts go to the
  enclosed S1 (better for warp-prone materials).
- Slicer: Anycubic Slicer Next (primary — native Kobra S1/X profiles),
  OrcaSlicer as fallback. See `SLICING.md` for setup status.
- LW-PLA profile starting point: ~235 °C, flow ~55%, 0.2 mm layers,
  vase mode for skins. To be tuned with a calibration cube/section
  before committing to full parts.

## Tilt mechanism (PETG, generated with build123d)

- Nacelle pod: 46 wide × 64 long × 42 tall, rear-open cavity
  (3 mm walls, 6 mm front wall), front motor plate 44×40×4 mm.
- Motor pattern: 2807 class, 4× M3 clearance holes on a 16 mm
  square + 9 mm center hole, cut through plate + front wall so
  screws enter from inside the pod.
- Pivot: 3 mm steel shaft on the X axis through the pod center.
  Each side has a 14 mm dia × 6 mm boss with an 8 mm × 4.2 mm
  bearing pocket for a 3×8×4 mm flanged bearing.
- Servo arm on one side per nacelle (mirror pair L/R), extending
  30 mm below the pivot axis, with a 2.2 mm pushrod hole.
- Bracket: 6×50×44 mm cheek plate per side (print 4), with a
  3.2 mm shaft hole + 2× M3 spar-mount holes; plates straddle the
  nacelle bosses.
- Rear motor mount: 44×40×4 mm plate (same motor pattern, cut
  through the whole mount) + 30×30×24 mm glue-in stub for the
  fuselage tail.

## File layout

- `scripts/` — parametric generators. Wing/fuselage/tail are pure
  Python STL writers; the tilt mechanism uses build123d
  (venv at `~/workspace/tools/vtol-venv/`).
- `parts/` — generated STLs, one per printable section.
- `tracker.md` — print tracker: part, printer, status.
- `BOM.md` — full bill of materials.
- `SLICING.md` — slicer setup, profiles, and open issues.

## Open questions / to confirm in flight test

- Exact CG position (target: ~25–30% mean chord to start, verify by
  glide test before first powered VTOL hover).
- Transition tuning: PX4 tilt-rotor params (tilt angle schedule,
  transition airspeed) need bench + field tuning.
- V-tail vs conventional tail: V-tail chosen for fewer parts and
  cleaner rear-motor airflow; revisit if yaw authority is weak.
