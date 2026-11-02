"""Purchased equipment as simple envelopes in the aircraft frame (mm; x aft, y right, z up).

The one place that says where each piece of equipment sits. The viewer draws these,
check_parts.py checks that the ones inside the fuselage fit and clear the printed parts, and
mass_balance.py takes their x positions. Sizes include heat-shrink but not leads.
"""
import math

import numpy as np

import geom as G
import params as P

BATTERY_SIZE = (155.0, 48.0, 37.0)    # 4S 5000 mAh LiPo
ESC_SIZE = (50.0, 12.0, 28.0)         # 50 A ESC standing on edge: length, thickness, height
ESC_GAP = 3.0                         # foam or air between the three ESCs
FC_SIZE = (84.8, 44.0, 12.4)          # Pixhawk 6C
FC_FOAM = 3.0                         # vibration foam under it
FC_X = 305.0
GPS_D, GPS_H = 50.0, 15.0             # M10-class puck
SERVO9 = (23.0, 22.5, 12.2)           # 9 g servo lying on its side: x, along the span, thickness
AIL_SERVO_X = 458.0                   # centred in the bay between the main-spar web and the rear spar
AIL_SERVO_Y = (320.0, 530.0)
UNDER_SHELF = P.FC_SHELF_Z - 2.5      # underside of the FC shelf: small boards hang here on Velcro
PITOT_X = (P.X_LE - 70.0, P.X_LE + 40.0)


def battery_x(pin=None):
    """Battery centre with its rear end against the stop pin (default: the last hole)."""
    pin = float(max(np.arange(*P.TRAY_PIN_X))) if pin is None else pin
    return pin - P.TRAY_PIN_R - BATTERY_SIZE[0] / 2


def esc_y():
    t = ESC_SIZE[1] + ESC_GAP
    return (-t, 0.0, t)


def esc_z():
    """Centre height of the ESC block hung under the FC shelf's aft part."""
    return UNDER_SHELF - ESC_SIZE[2] / 2


def gps_top():
    """Top face of the GPS saddle."""
    w, h, zc = G.fuse_dims(P.GPS_X)
    return zc + h / 2 + 0.2 + P.GPS_PAD_T


def _wing_lower_z(x, y):
    c = P.chord(abs(y))
    _, lo = G.SECTIONS["clarky"]
    return P.Z_WING + c * float(lo((x - P.X_LE) / c))


def pitot_z():
    """Leading-edge height at the pitot station (Clark Y's nose is above its flat bottom)."""
    up, _ = G.SECTIONS["clarky"]
    return P.Z_WING + P.chord(P.PITOT_Y) * float(up(0.0))


def _item(name, label, kind, pos, color, group, inside, **geo):
    return dict(name=name, label=label, kind=kind, pos=[float(v) for v in pos], color=color, group=group,
                inside=inside, **geo)


def equipment(pin=None):
    """Every item: kind 'box' (size along the basis axes) or 'cyl' (r, h along `axis`)."""
    zt = P.TRAY_Z
    L, W, H = BATTERY_SIZE
    items = [_item("battery", "4S 5000 mAh LiPo", "box", (battery_x(pin), 0, zt + H / 2), "#e8b923", "power",
                   True, size=list(BATTERY_SIZE))]
    l, t, h = ESC_SIZE
    for k, (y, who) in enumerate(zip(esc_y(), ("left motor", "rear motor", "right motor"))):
        items.append(_item(f"esc_{k}", f"ESC 50 A ({who})", "box", (sum(P.ESC_BLOCK_X) / 2, y, esc_z()),
                           "#7a3fb0", "power", True, size=[l, t, h]))
    items.append(_item("fc", "Pixhawk 6C", "box", (FC_X, 0, P.FC_SHELF_Z + FC_FOAM + FC_SIZE[2] / 2),
                       "#2b3440", "avionics", True, size=list(FC_SIZE)))
    # Under the shelf, above the battery: power module and BEC on the left, receiver and
    # airspeed sensor on the right, all inside the shelf's solid centre strip (|y| < 24).
    for name, label, size, x, y in (("power_module", "power module", (40, 22, 10), 272, -12),
                                    ("bec", "servo BEC 5-6 V", (36, 20, 10), 322, -12),
                                    ("airspeed", "airspeed sensor", (32, 20, 10), 280, 12),
                                    ("receiver", "ELRS receiver", (22, 14, 5), 330, 12)):
        items.append(_item(name, label, "box", (x, y, UNDER_SHELF - size[2] / 2), "#3a7d44", "avionics", True,
                           size=list(size)))
    items.append(_item("gps", "GPS + compass (M10)", "cyl", (P.GPS_X, 0, gps_top() + 1.0 + GPS_H / 2), "#30343a",
                       "avionics", False, r=GPS_D / 2, h=GPS_H, axis=[0, 0, 1]))
    items.append(_item("pitot", "pitot tube", "cyl", (sum(PITOT_X) / 2, P.PITOT_Y, pitot_z()), "#b8bcc2",
                       "avionics", False, r=2.0, h=PITOT_X[1] - PITOT_X[0], axis=[1, 0, 0]))
    bl, bh, bd = P.SERVO_BODY
    for sgn, s in ((1, "r"), (-1, "l")):
        y0 = P.Y_POD[0] if sgn > 0 else -P.Y_POD[0]
        items.append(_item(f"tilt_servo_{s}", "tilt servo", "box",
                           (P.X_PIVOT - P.SERVO_SHAFT_FROM_FRONT + bl / 2, y0 + sgn * bd / 2, P.Z_PIVOT),
                           "#4a4f57", "servos", False, size=[bl, bd, bh]))
        for y in AIL_SERVO_Y:
            z = _wing_lower_z(AIL_SERVO_X, y) + P.LWPLA_WALL + 1.6 + SERVO9[2] / 2
            items.append(_item(f"aileron_servo_{s}{int(y)}", "aileron servo", "box", (AIL_SERVO_X, sgn * y, z),
                               "#4a4f57", "servos", False, size=list(SERVO9)))
        d = math.radians(P.VT_DIHEDRAL)
        e_s = np.array([0.0, sgn * math.cos(d), math.sin(d)])
        e_t = np.array([0.0, -sgn * math.sin(d), math.cos(d)])
        c = np.array([P.VT_X_LE + 55.0, sgn * P.VT_ROOT[0], P.VT_ROOT[1]]) + 45.0 * e_s
        items.append(_item(f"vtail_servo_{s}", "ruddervator servo", "box", c, "#4a4f57", "servos", False,
                           size=list(SERVO9), basis=[[1.0, 0.0, 0.0], e_s.tolist(), e_t.tolist()]))
    return items


def routes(pin=None):
    """Sketch of the main cable runs, for the viewer only: polylines with a diameter."""
    xb = battery_x(pin) - BATTERY_SIZE[0] / 2
    zt = P.TRAY_Z
    e0, e1 = P.ESC_BLOCK_X
    ze = esc_z()
    yl, yc, yr = esc_y()
    zh = UNDER_SHELF - 5
    plug_x = 330.0
    out = [
        dict(name="battery lead to power module", d=6.0, color="#c0392b",
             pts=[(xb, 0, zt + 25), (xb - 12, 0, zt + 30), (xb - 12, -8, 0), (232, -12, zh), (252, -12, zh)]),
        dict(name="power module to the ESCs", d=6.0, color="#c0392b",
             pts=[(292, -12, zh), (330, -18, zh - 4), (e0 - 8, yl, ze), (e0, yl, ze)]),
        dict(name="rear motor leads (from the boom)", d=5.0, color="#d4a017",
             pts=[(P.BOOM_X[0], 0, P.BOOM_Z), (P.BOOM_X[0] - 3, 0, -2), (e1 + 3, 0, ze - 4), (e1, 0, ze)]),
        dict(name="GPS cable", d=3.0, color="#2e86c1",
             pts=[(P.GPS_X, 0, gps_top() - P.GPS_PAD_T), (P.GPS_X - 20, 0, 50), (480, 0, 52), (420, 0, 54),
                  (360, 0, 50), (FC_X + 40, 0, P.FC_SHELF_Z + 10)]),
    ]
    for sgn, s in ((1, "right"), (-1, "left")):
        hole = (P.RIB_WIRE_X, sgn * (P.Y_ROOT_SEC[0] - 3), P.RIB_WIRE_Z + 2)
        out.append(dict(name=f"{s} wing: motor leads to plugs at x~{plug_x:.0f}, then the ESC", d=5.0,
                        color="#d4a017",
                        pts=[hole, (430, sgn * 47, 5), (370, sgn * 41, 4), (plug_x, sgn * 37, 4),
                             (plug_x + 14, sgn * 27, 10), (e0 - 6, sgn * yr, ze), (e0, sgn * yr, ze)]))
        out.append(dict(name=f"{s} wing: servo leads to the Pixhawk", d=3.0, color="#2e86c1",
                        pts=[hole, (430, sgn * 50, 13), (370, sgn * 45, 14), (plug_x, sgn * 40, 16),
                             (FC_X + 36, sgn * 30, P.FC_SHELF_Z + 4), (FC_X + 44, sgn * 18, P.FC_SHELF_Z + 6)]))
    out.append(dict(name="pitot tubing", d=3.0, color="#8fbc8f",
                    pts=[(PITOT_X[1], P.PITOT_Y, pitot_z()), (P.RIB_WIRE_X, P.PITOT_Y - 20, P.RIB_WIRE_Z),
                         (P.RIB_WIRE_X, 120, P.RIB_WIRE_Z), (P.RIB_WIRE_X, P.Y_ROOT_SEC[0] - 3, P.RIB_WIRE_Z + 2),
                         (420, 45, 12), (300, 22, zh), (296, 12, zh)]))
    return out
