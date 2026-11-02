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
AIL_SERVO_Y = (325.0, 530.0)          # hatch blocks clear of the rib spigots (end at y = 293 and 500)
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


def _vt_lower(u, s, sgn):
    """Point on a V-tail panel's lower outer surface (u aft of the LE, s from the root rib face),
    and the panel's span and thickness axes."""
    d = math.radians(P.VT_DIHEDRAL)
    e_s = np.array([0.0, sgn * math.cos(d), math.sin(d)])
    e_t = np.array([0.0, -sgn * math.sin(d), math.cos(d)])
    o = np.array([P.VT_X_LE, sgn * P.VT_ROOT[0], P.VT_ROOT[1]])
    c = P.VT_ROOT_CHORD + (P.VT_TIP_CHORD - P.VT_ROOT_CHORD) * s / P.VT_SPAN
    t = -c * float(G.naca0012_half(u / c))
    return o + np.array([u, 0.0, 0.0]) + s * e_s + t * e_t, e_s, e_t


def _minimax_plane(pts, inward):
    """Plane through skin points with the smallest largest deviation (a small linear programme),
    moved along its normal until no point lies beyond it on the `inward` side. Returns a point on
    it and its unit normal (pointing to `inward`)."""
    from scipy.optimize import linprog
    c = pts.mean(axis=0)
    e1, e2, n = np.linalg.svd(pts - c)[2]
    u, v, w = (pts - c) @ e1, (pts - c) @ e2, (pts - c) @ n
    one = np.ones_like(u)
    a_ub = np.vstack([np.stack([-one, -u, -v, -one], 1), np.stack([one, u, v, -one], 1)])
    res = linprog([0, 0, 0, 1], A_ub=a_ub, b_ub=np.concatenate([-w, w]),
                  bounds=[(None, None)] * 3 + [(0, None)])
    al, be, ga, _ = res.x
    nn = n - be * e1 - ga * e2
    nn /= np.linalg.norm(nn)
    if np.dot(nn, inward) < 0:
        nn = -nn
    p0 = c + al * n
    return p0 + ((pts - p0) @ nn).max() * nn, nn


def servo_hatches():
    """Frame of each removable servo hatch: origin on the outer skin at the hatch centre, a
    chordwise, b spanwise, n into the airfoil (right-handed). The wing hatches sit on the Clark Y's
    flat bottom. A V-tail hatch's plane is the flattest fit to the skin over the opening and the
    blocks' glue faces, moved in until none of that skin lies inside it: the flat cover is never
    proud of the gently curved skin, and sits a fraction of a millimetre under it elsewhere."""
    out = []
    a_o, b_o = P.HATCH_A + P.HATCH_CLEAR, P.HATCH_B + P.HATCH_CLEAR
    foot = [(du, ds) for du in np.linspace(-a_o, a_o, 11) for ds in np.linspace(-b_o, b_o, 15)]
    foot += [(du, k * ds) for du in np.linspace(-P.HATCH_BLOCK_A, P.HATCH_BLOCK_A, 5)
             for ds in np.linspace(b_o, b_o + P.HATCH_GLUE, 4) for k in (-1, 1)]
    for sgn, s in ((1, "r"), (-1, "l")):
        for y in AIL_SERVO_Y:
            out.append(dict(name=f"aileron_{s}{int(y)}", where="wing",
                            origin=[AIL_SERVO_X, sgn * y, _wing_lower_z(AIL_SERVO_X, y)],
                            a=[1.0, 0.0, 0.0], b=[0.0, 1.0, 0.0], n=[0.0, 0.0, 1.0]))
        u_c, s_c = P.HATCH_VT
        pts = np.array([_vt_lower(u_c + du, s_c + ds, sgn)[0] for du, ds in foot])
        centre, _, e_t = _vt_lower(u_c, s_c, sgn)
        base, n = _minimax_plane(pts, e_t)      # into the panel from its lower surface
        a = np.array([1.0, 0.0, 0.0]) - n[0] * n
        a /= np.linalg.norm(a)
        b = np.cross(n, a)
        origin = centre - ((centre - base) @ n) * n
        out.append(dict(name=f"ruddervator_{s}", where="vtail", origin=origin.tolist(),
                        a=a.tolist(), b=b.tolist(), n=n.tolist()))
    return out


def hatch_point(h, a, b, n):
    """World point of local hatch coordinates."""
    return np.asarray(h["origin"]) + a * np.asarray(h["a"]) + b * np.asarray(h["b"]) + n * np.asarray(h["n"])


# The servo lies on the cover with its tabs on the posts' +b face: body from b = -12 to +10.5,
# output shaft and horn beyond +10.5 (inside |b| < HATCH_MID).
SERVO_ON_HATCH = (0.0, -0.75, P.HATCH_T + SERVO9[2] / 2)
SERVO9_HORN = 4.0                     # case top to the horn's outer face (spline + horn)


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
        items.append(_item(f"tilt_plug_{s}", "tilt-servo plug (in the pod's plug pocket)", "box",
                           (sum(P.POD_PLUG_X) / 2, y0 + sgn * P.POD_PLUG_DEPTH / 2, P.POD_PLUG_Z[0] + 2.0),
                           "#c9a227", "servos", False, size=[25.0, 7.6, 4.0]))
    for h in servo_hatches():
        c = hatch_point(h, *SERVO_ON_HATCH)
        label = "aileron servo" if h["where"] == "wing" else "ruddervator servo"
        items.append(_item(f"servo_{h['name']}", label, "box", c, "#4a4f57", "servos", False,
                           size=list(SERVO9), basis=[h["a"], h["b"], h["n"]], hatch=h["name"]))
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
    # The two Velcro straps: over the battery, down a slot beside it, under the plate through the
    # rail gaps and up the other slot. Threaded before the tray is glued in.
    top, ys = zt + BATTERY_SIZE[2] + 1.0, sum(P.TRAY_STRAP_Y) / 2
    loop = [(-20, top), (20, top), (ys, top - 5), (ys, zt - 1), (20, zt - 4.5), (-20, zt - 4.5), (-ys, zt - 1),
            (-ys, top - 5), (-20, top)]
    for xs in P.TRAY_STRAP_X:
        out.append(dict(name=f"battery strap at x = {xs:.0f}", d=2.0, color="#22262b",
                        pts=[(xs, y, z) for y, z in loop]))
    return out
