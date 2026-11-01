# PX4 Setup Guide — Custom Tilt-Rotor VTOL (v0.1)

Starting points for QGroundControl setup on a Pixhawk 6C. Verify every
parameter's units in QGC before first flight — tilt parameter conventions
have changed across PX4 versions.

## Airframe

- In QGC, select **Generic VTOL Tiltrotor** (SYS_AUTOSTART 13100)
  and restart. This is the stock PX4 tilt-rotor airframe; our geometry
  is close enough to start from it, then tune.
- VT_TYPE = 1 (Tiltrotor). 0 = Tailsitter, 2 = Standard quadplane —
  do not use those for this airframe.

## Output mapping (starting point, adapt in Actuator Configuration)

Adapted from PX4's Convergence tilt-rotor layout:

| Output | Function |
|---|---|
| MAIN1 | Front right motor (tilt) |
| MAIN2 | Front left motor (tilt) |
| MAIN3 | Rear motor (fixed) |
| MAIN5 | Right tilt servo |
| MAIN6 | Left tilt servo |
| AUX | V-tail ruddervators (assign as V-tail in Actuator Configuration) |
| AUX | Ailerons |

DShot on the FMU outputs for the three motors (same rule as the
multicopter build: AUX bus on dual-bus Pixhawks, MAIN otherwise).

## Transition parameters (starting points, tune in the field)

- VT_F_TRANS_DUR: 5–15 s (front transition duration)
- VT_B_TRANS_DUR: 8–15 s (back transition duration)
- VT_ARSP_TRANS: 13 m/s starting point (stall is ~9.8 m/s, so
  transition must complete ABOVE stall with margin — the old 10–20
  range was wrong at the bottom end: 10 m/s is barely above stall
  and a gust during transition would drop a wing)
- VT_TILT_MC / VT_TILT_TRANS / VT_TILT_FW: tilt angles for hover /
  transition / forward flight. Example values from a similar tricopter
  build: 0.08 / 0.5 / 0.9 — check the units QGC shows for your PX4
  version before copying these.
- Assign an RC switch to the multicopter ↔ fixed-wing transition
  before any flight.

## First-flight sequence

1. Bench: actuator test with props OFF — verify each motor, tilt
   servo direction, and V-tail/aileron directions.
2. CG check: target 25–30% mean chord to start; glide-test
   (unpowered, hand toss over grass) before any powered hover.
3. First hover: multicopter mode only, low altitude, over open
   ground. Confirm hover throttle near 45–55% and solid yaw
   authority (differential tilt).
4. First transition: at safe altitude (30 m+), switch to fixed-wing
   mode, watch airspeed build and tilt go fully forward. If the
   nose drops or it wallows, switch back — back-transition is the
   safety net.
5. Only after clean transitions both ways: missions, then (phase 2)
   the phone-over-4G MAVLink link from the drone project.

- FW_AIRSPD_MIN: 12 m/s (above the 9.8 m/s stall, below the 13 m/s
  transition speed — the wing must never be asked to fly at stall).
- V-tail mixer: ruddervators. In QGroundControl, assign the two V-tail
  servos as ruddervator pair (pitch + yaw mixing); verify on the
  bench that elevator input moves both panels together and rudder
  input moves them oppositely. A reversed ruddervator is a
  first-flight crash — check it twice, props OFF.

## Preflight checklist (props OFF first, then ON — every flying day)

1. Balance: fingertips under the wing at 430 mm aft of the nose tip
   (27% MAC). Battery slides on its tray to trim: battery center
   267–301 mm from the nose (nominal 282) holds CG in the 25–30% band. If it will
   not balance there, DO NOT FLY — move equipment, do not add dead
   weight to the tail.
2. Motor order + direction (props OFF, then brief spin-up): confirm
   each motor matches the PX4 tilt-rotor output map and spins the
   correct direction for its prop. A wrong-direction front motor
   flips the aircraft on the first hover.
3. Tilt servos: full travel 0–90 deg, both sides symmetric, no
   binding at either end. A binding tilt servo stalls, overheats,
   and fails mid-transition.
4. V-tail: elevator together, rudder opposite (see mixer note above).
   Ailerons: correct direction.
5. Nose retention: nose seated 30 mm into sleeve_240 + tape intact.
   If the nose departs in flight, CG jumps aft and drag spikes.
6. Motor screws: M3x6, verified by hand that no screw touches the
   motor windings (too-long screws short the motor).
7. Wires: no wire touches a carbon spar (carbon is conductive — a
   chafed wire shorts). Heat-shrink or braid anywhere wires cross
   spars. Battery lead cannot reach the props.
8. First transitions: altitude 30 m+, into wind, transition switch
   in hand for an instant back-transition. If the nose drops or a
   wing wallows, switch back immediately — do not ride it out.

## Failsafes (set before first transition)

- Datalink-loss and RC-loss actions: Return or Land (never
  "continue mission" on a first build).
- Geofence: radius + altitude ceiling for the test field.
- Battery failsafe: land at low voltage, not just warn.
- Part 107: VLOS only unless a BVLOS waiver is in hand.
