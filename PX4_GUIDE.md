# PX4 Setup Guide — Custom Tilt-Rotor VTOL (v0.2)

For PX4 v1.14 or later (control allocation in the Actuators tab of QGroundControl). The
parameter names and meanings below were checked against the PX4 source
(`control_allocator/module.yaml`, `vtol_att_control/tiltrotor_params.yaml`). Airspeeds come
from `scripts/mass_balance.py`. Re-check both if you change the airframe or PX4 version.

## Airframe

- In QGC select **Generic Tiltrotor VTOL** (`SYS_AUTOSTART` 13100) and reboot. That sets
  `VT_TYPE` = 1 (tiltrotor) and `CA_AIRFRAME` = 3 (Tiltrotor VTOL).

## Geometry (Actuators tab)

Positions are relative to the hover CG (437 mm aft of the nose tip), x forward, y right.
Set **`CA_ROTOR_COUNT` = 3**. The 13100 airframe defaults to 4 rotors, with a fourth one 1 m
out that would take part of every command.

| Rotor | Position | `CA_ROTORn_PX` | `CA_ROTORn_PY` | `CA_ROTORn_KM` | `CA_ROTORn_TILT` |
|---|---|---|---|---|---|
| 0 | front right, CW | 0.12 | 0.28 | −0.05 | Tilt 1 |
| 1 | front left, CCW | 0.12 | −0.28 | 0.05 | Tilt 2 |
| 2 | rear, CCW (x = 780) | −0.34 | 0 | 0.05 | None |

`KM` is positive for a CCW rotor and negative for CW (viewed from above in hover).

Tilt servos: `CA_SV_TL_COUNT` = 2. For both: `CA_SV_TLn_MINA` = **−20**, `CA_SV_TLn_MAXA`
= **90**, `CA_SV_TLn_TD` = 0 (towards front), `CA_SV_TLn_CT` = 1 (yaw). An angle of 0 means
thrust straight up. The yokes are built for exactly this −20…90° range.

Control surfaces: `CA_SV_CS_COUNT` = 6 — right aileron ×2 (mid, tip), left aileron ×2, right
V-tail, left V-tail.

## Output mapping

DShot only works on the Pixhawk 6C's FMU outputs (the AUX/"FMU PWM OUT" bank). The IO
(MAIN) bank is PWM only.

| Output | Function | Protocol |
|---|---|---|
| AUX1 | motor 1, front right | DShot600 |
| AUX2 | motor 2, front left | DShot600 |
| AUX3 | motor 3, rear | DShot600 |
| MAIN1 | tilt servo 1, right | PWM 50 Hz |
| MAIN2 | tilt servo 2, left | PWM 50 Hz |
| MAIN3, MAIN4 | right aileron mid, tip | PWM 50 Hz |
| MAIN5, MAIN6 | left aileron mid, tip | PWM 50 Hz |
| MAIN7, MAIN8 | right, left ruddervator | PWM 50 Hz |

QGC shows which AUX outputs share a timer. Leave any output that shares a timer with the
motors unused. The servo rail is powered by the BEC, not by the Pixhawk.

## Compass and safety button

- **Compass:** use the one in the GPS, which sits outside on its saddle on top of the
  fuselage. The ESC block hangs under the shelf just behind the Pixhawk, so the Pixhawk's
  internal compass sees the motor currents. In QGC, Vehicle Setup → Sensors → Compass, set the
  internal compass to Disabled (its `CAL_MAGn_PRIO` becomes 0) and calibrate the GPS one.
  Check the magnetometer log for interference after the first hover anyway.
- **Safety button (optional):** a Holybro M10 GPS carries one. PX4 v1.15 and earlier leave
  safety off by default (`CBRK_IO_SAFETY` = 22027); set `CBRK_IO_SAFETY` = 0 to use the
  button. Newer releases replace that parameter with `COM_SAFETY_MODE` (0 = off, 1 = button or
  ground station). With safety on, the MAIN bank (tilt servos, surfaces) stays still and arming
  is refused until the button is pressed.

## Tilt servo calibration (props off, before anything else)

The two tilt servos are mirror images (each sits in its pod's inboard face), so the same PWM
change turns the two yokes opposite ways. PX4 sends both the same tilt command.

1. In the Actuators tab, move each tilt servo with its slider. Tick **Rev Range** on whichever
   tilt output moves the wrong way, so that both yokes tilt forward as the value rises.
2. Set the end points. PX4 keeps min below max and reverses by flipping the command, so the
   ends swap on the reversed output:

   | Output | PWM minimum | PWM maximum | Disarmed (hover, 0°) |
   |---|---|---|---|
   | normal | 20° back | straight forward | min + 0.18 × (max − min) |
   | Rev Range | straight forward | 20° back | max − 0.18 × (max − min) |

   The servo must reach both ends without buzzing against its own stop. If it cannot cover
   110°, widen the range within PX4's limits (min 800–1400 µs, max 1600–2200 µs) and what the
   servo allows.
3. Set each tilt output's **Disarmed** PWM to the value in the table, then confirm by eye that
   the motor points straight up. PX4 sends this raw value, unreversed, while disarmed and during
   spool-up in hover.
4. Check that both sides match at both ends, at the midpoint (35° forward of vertical) and at
   the disarmed position.

## Tilt and transition parameters

PX4 normalizes the tilt over the servo range set above: angle = −20° + 110° × value.

| Parameter | Value | Meaning |
|---|---|---|
| `VT_TILT_MC` | **0.18** | 0°: thrust straight up in hover |
| `VT_TILT_TRANS` | 0.55 | ~40° during the front transition |
| `VT_TILT_FW` | 1.0 | 90°: thrust forward |
| `FW_AIRSPD_STALL` | 13 m/s | stall at CL 1.0, 35 °C, AUW +10 % (12.05 m/s, rounded up) |
| `FW_AIRSPD_MIN` | 16 m/s | 1.25 × that stall |
| `FW_AIRSPD_TRIM` | 18 m/s | cruise; CL ≈ 0.37 there |
| `FW_AIRSPD_MAX` | 25 m/s | |
| `VT_ARSP_TRANS` | 18 m/s | transition ends 2 m/s above `FW_AIRSPD_MIN`, at the cruise speed |
| `VT_F_TRANS_DUR` | 5–15 s | front transition |
| `VT_B_TRANS_DUR` | 8–15 s | back transition |

Do not copy tilt values from other builds. A value of 0.08, for example, would mean the
motors lean 11° back in hover with this servo range. On the bench (props off), arm in
multicopter mode and confirm the motors point straight up. If they don't, correct
`VT_TILT_MC`, not the servo horn. Assign an RC switch to the transition before any flight.

## First-flight sequence

1. Bench, props off: actuator test for every motor (order and spin direction), both tilt
   servos, all four ailerons and both ruddervators.
2. CG: balance at 433 mm aft of the nose tip with the motors tilted forward. Glide-test
   (unpowered hand toss over grass) before any powered hover.
3. First hover: multicopter mode only, low, over open ground. Hover throttle should be around
   70 %. Check yaw authority (differential tilt) and the vibration and compass logs before
   flying again.
4. First transition at 30 m+, into wind, with the transition switch in hand. If the nose drops
   or a wing wallows, switch back. Back-transition is the safety net.
5. Only after clean transitions both ways: missions, then the phone-over-4G MAVLink link.

## Preflight checklist (props off first, then on — every flying day)

1. Balance: motors tilted forward, fingertips 433 mm aft of the nose tip. The battery centre
   should be at 271–306 mm (the stop pin in the tray hole at x = 380 holds it at 301). If it
   will not balance there, do not fly. Move equipment; do not add tail weight.
2. Motor order and direction match the table above (props off, then a brief spin-up). A
   wrong-direction front motor flips the aircraft on the first hover.
3. Tilt: both yokes swing −20…90° freely with the axle screws tight, and match at the ends.
   A binding tilt stalls the servo mid-transition.
4. Surfaces: ailerons the right way; ruddervators move together for elevator and opposite
   for rudder. A reversed ruddervator is a first-flight crash; check it twice.
5. Nose: M3 nylon screw in, nose seated on its coupler. If the nose departs, the CG jumps aft.
   Battery straps tight; every servo hatch has both M2 screws in and its pushrod clevis
   clipped.
6. Motor screws: M3×8 in 4 mm plates, checked by hand that none touches the windings.
7. Wires: nothing chafes on carbon (it conducts) and no ESC touches an LW-PLA skin. The
   battery lead cannot reach a prop. The nose-tip air inlet and the two belly outlets are open.
8. Wings: both lock pins in, joiners fully home.

## Failsafes (set before the first transition)

- Datalink and RC loss: Return or Land, never "continue mission" on a first build.
- Geofence: radius and altitude ceiling for the field.
- Battery failsafe: land at low voltage, not just warn.
- Part 107: VLOS only unless a BVLOS waiver is in hand.
