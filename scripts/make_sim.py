"""PX4 SITL model of the aircraft for Gazebo Harmonic, generated from the design (SIMULATION.md).

Writes sim/models/vtol_plane/ (model.sdf, model.config, meshes/) and the PX4 airframe
sim/airframes/22100_gz_vtol_plane; sim/install.sh copies both into a PX4-Autopilot tree.

Everything comes from the other scripts, so the model follows the design:
- masses: mass_balance.py's rows (the same 2.00 kg and CG), placed in 3-D from payload.py and the
  assembly STLs (a printed part's mass spread over its surface), in the hover configuration;
- geometry: params.py (tilt pivots, rotors, wing strips, V-tail panels, hinge lines);
- aerodynamics: one LiftDrag element per wing strip and per V-tail panel and plane, from the
  planform, the Clark Y's camber line and the hinge positions;
- visuals: the assembly STLs, one mesh per link and material;
- PX4: PX4_GUIDE.md's actuator geometry and outputs, mass_balance.py's airspeeds.

Frames: the design's (mm; x aft from the nose tip, y right, z up) becomes the model's (m; x
forward, y left, z up) with its origin at the hover CG, the point PX4's CA_ROTORn_PX/PY use.

Usage: python make_sim.py
"""
import hashlib
import math
import os
from collections import defaultdict

import numpy as np

import geom as G
import make_viewer as V
import mass_balance as MB
import params as P
import payload as PL
import skins
from make_print_ready import PARTS

MODEL = "vtol_plane"
WORLD = "vtol_field"
AIRFRAME_ID = 22100                 # PX4 keeps 22000-22999 for custom SITL airframes
SIM = os.path.join(G.ROOT, "sim")
MODEL_DIR = os.path.join(SIM, "models", MODEL)
AIRFRAME = os.path.join(SIM, "airframes", f"{AIRFRAME_ID}_gz_{MODEL}")

# --- propulsion: Emax ECOII 2807 1700KV on 7x4.5 props (mass_balance.py) ---------------------
THRUST_MAX = MB.T_MAX_FULL * MB.G0 / 1000.0   # N at full throttle; the sim's pack never sags
OMEGA_MAX = 2200.0                  # rad/s there (~21,000 rpm): a 7x4.5's CT ~0.10
MOMENT_RATIO = 0.0127               # prop torque / thrust (m): CP/CT * D / 2 pi for a 7x4.5
MOTOR_TAU = (0.025, 0.035)          # spin-up and spin-down time constants (s)
ROTOR_SLOWDOWN = 10.0               # the drawn rotor turns this much slower than the prop
IDLE = 0.05                         # armed idle, fraction of OMEGA_MAX
PROP_MASS = 8.0                     # g, as in mass_balance.ITEMS
# --- PX4 safety settings, as PX4_GUIDE.md sets them (REPORT.md, round 13) ----------------------
OPEN_LOOP_TRANS_S = 12.0            # VT_F_TR_OL_TM: by then the model is at ~19 m/s (8 s: ~15)
QUADCHUTE = {"VT_FW_QC_P": 35, "VT_FW_QC_R": 65, "VT_FW_MIN_ALT": 15, "VT_QC_ALT_LOSS": 15, "VT_QC_T_ALT_LOSS": 10}
# --- servos: 9 g surface servos and the 12 mm tilt servos, ~0.10 s per 60 deg ------------------
SERVO_RATE = math.radians(60.0) / 0.10
SERVO_TORQUE = {"tilt": 0.3, "surface": 0.2}   # N m: ~3 and ~2 kg cm; also makes gz enforce the joint limits
SURFACE_DEG = P.AIL_BEVEL_DEG       # ailerons and ruddervators: +-25 deg, what the bevel allows
# The joints' stops sit this far beyond the range PX4 commands: DART ignores a servo's command while
# its joint rests on a stop, so a servo driven onto one stays there (REPORT.md, round 12).
STOP_MARGIN_DEG = 5.0
# --- aerodynamics -------------------------------------------------------------------------------
RHO = 1.225                         # ISA sea level: what the gz airspeed sensor assumes near home
CD0 = 0.040                         # whole aircraft on the gross wing area (SIMULATION.md)
OSWALD = 0.8
CL_REF = 0.65                       # the wing strips' linear drag matches CL^2/(pi e AR) here
CL_MAX = 1.1                        # the Clark Y wing near Re 2.5e5
TAU_GAP = 0.8                       # flap effectiveness kept by a taped, bevelled hinge
FUSE_A0 = 0.35                      # the drag element's offset angle: cd = cda * (a0 + |angle|)
BELLY_PAD = (250.0, 500.0, 60.0, 7.0)   # EVA landing strip (DESIGN.md): x from, x to, width, thickness

FLIP = np.array([-1.0, -1.0, 1.0])  # design axes (x aft, y right) -> model axes (x forward, y left)
COLOR = {"lwpla": "0.92 0.90 0.85", "petg": "0.18 0.43 0.71", "carbon": "0.11 0.11 0.11",
         "motor": "0.23 0.23 0.23", "bell": "0.69 0.19 0.19", "prop": "0.60 0.64 0.68"}
SIDES = ((1, "r"), (-1, "l"))       # design y sign, suffix
TILT_LINK = {"r": "tilt_r", "l": "tilt_l"}
ROTOR = {"r": 0, "l": 1}            # PX4_GUIDE.md: rotor 0 front right (CW), 1 front left, 2 rear
SURFACES = [f"aileron_{w}_{s}" for s in "rl" for w in ("mid", "tip")] + ["ruddervator_r", "ruddervator_l"]
# gz servo topic n carries PX4 output SIM_GZ_SV_FUNC(n+1); the same order as PX4_GUIDE.md's MAIN1-8.
SERVO_ORDER = ["tilt_r", "tilt_l"] + SURFACES
LINK_OF = {"yoke_r": "tilt_r", "yoke_l": "tilt_l", **{s: s for s in SURFACES}}


# --- small helpers ------------------------------------------------------------------------------
def _num(v, nd=5):
    s = f"{float(v):.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _vec(v, nd=5):
    return " ".join(_num(c, nd) for c in v)


def _sci(v):
    s = f"{float(v):.6g}"
    return "0" if s in ("-0", "0") else s


def lift_slope(ar):
    """Lift-curve slope (1/rad) of a straight wing of aspect ratio ar (Helmbold)."""
    return 2 * math.pi * ar / (2 + math.sqrt(ar * ar + 4))


def flap_tau(hinge):
    """Flap effectiveness d(alpha)/d(delta) of a plain flap hinged at `hinge` chord (thin airfoil),
    reduced for the hinge gap and bevel."""
    th = math.acos(1 - 2 * hinge)
    return (1 - (th - math.sin(th)) / math.pi) * TAU_GAP


def zero_lift_angle():
    """The Clark Y's zero-lift angle (rad) to its flat bottom, the wing's datum (thin airfoil)."""
    th = np.linspace(1e-4, math.pi - 1e-4, 4001)
    x = (1 - np.cos(th)) / 2
    up, lo = G.SECTIONS["clarky"]
    camber = (up(x) + lo(x)) / 2
    slope = np.gradient(camber, x)
    return float(-np.trapezoid(slope * (np.cos(th) - 1), th) / math.pi)


def _span_integrals(chord, y0, y1, n=20001):
    """Area, area centroid and mean aerodynamic chord of a strip of chord(y) between y0 and y1."""
    ys = np.linspace(y0, y1, n)
    c = np.array([chord(y) for y in ys])
    area = np.trapezoid(c, ys)
    return float(area), float(np.trapezoid(ys * c, ys) / area), float(np.trapezoid(c * c, ys) / area)


def wing_chord(y):
    """Local chord: the root chord carries on through the fuselage (the gross area)."""
    return P.ROOT_CHORD if abs(y) <= P.Y_ROOT else P.chord(y)


# --- mass model ---------------------------------------------------------------------------------
def _shell(tris):
    """Unit mass spread evenly over a surface mesh (mm): centroid and inertia about it, per gram."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    w = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    cen = (a + b + c) / 3.0
    p = (w[:, None] * cen).sum(0) / w.sum()
    s = sum(np.einsum("n,ni,nj->ij", w, v - p, v - p) for v in (a, b, c))
    s = (s + 9 * np.einsum("n,ni,nj->ij", w, cen - p, cen - p)) / (12 * w.sum())
    return p, np.trace(s) * np.eye(3) - s


def _point(p):
    return np.asarray(p, float), np.zeros((3, 3))


def _rod(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    u = (b - a) / np.linalg.norm(b - a)
    return (a + b) / 2, np.linalg.norm(b - a) ** 2 / 12 * (np.eye(3) - np.outer(u, u))


def _box(p, size, basis=None):
    l, w, h = size
    d = np.diag([w * w + h * h, l * l + h * h, l * l + w * w]) / 12
    bas = np.eye(3) if basis is None else np.asarray(basis, float)
    return np.asarray(p, float), bas.T @ d @ bas


def _cyl(p, r, h, axis):
    u = np.asarray(axis, float) / np.linalg.norm(axis)
    return np.asarray(p, float), (3 * r * r + h * h) / 12 * (np.eye(3) - np.outer(u, u)) \
        + r * r / 2 * np.outer(u, u)


def _prop(p):
    """A two-blade prop, averaged over a turn: D^2/12 about its axis (blades as a rod), and a little
    more than half that in the disc's plane for the hub and blade width (it keeps the inertia valid)."""
    d2 = P.PROP_D ** 2
    return np.asarray(p, float), np.diag([d2 / 20, d2 / 20, d2 / 12])


def _equip(e):
    if e["kind"] == "box":
        return _box(e["pos"], e["size"], e.get("basis"))
    return _cyl(e["pos"], e["r"], e["h"], e["axis"])


def front_motor_base(sgn):
    """Motor mounting face on the yoke, hover position."""
    return np.array([P.X_PIVOT, sgn * P.BOOM_Y, P.Z_PIVOT + P.YOKE_PLATE_Z0 + P.YOKE_PLATE_T])


REAR_MOTOR_BASE = np.array([P.X_REAR_MOTOR, 0.0, P.REAR_PLATE_Z + 4.0])   # as check_parts / make_viewer


def mass_items(r):
    """Every mass in mass_balance.py's rows plus the battery: (link, name, g, centroid mm, inertia
    g mm^2 about it), hover configuration. The x of each is mass_balance's, so the CG matches it."""
    eq = {e["name"]: e for e in PL.equipment(r["pin"])}
    hatches = PL.servo_hatches()
    wing_h = [h for h in hatches if h["where"] == "wing"]
    vt_h = [h for h in hatches if h["where"] == "vtail"]
    out = []
    seen = defaultdict(int)

    def add(link, name, m, shape):
        p, i = shape
        out.append((link, name, float(m), np.asarray(p, float), m * i))

    for name, m, qty, xf, xh, _ in r["rows"]:
        k = seen[name]
        seen[name] += 1
        if name in PARTS:
            if name == "servo_hatch":
                add("base_link", name, m, _point(hatches[k]["origin"]))
            elif name == "hatch_block":
                h = hatches[k // 2]
                add("base_link", name, m, _point(PL.hatch_point(h, 0, (k % 2 * 2 - 1) * P.HATCH_SCREW_B, 2)))
            elif name == "control_horn":
                h = (wing_h + vt_h)[k]
                add("base_link", name, m, _point([xh, h["origin"][1], h["origin"][2]]))
            else:
                src = PARTS[name]["src"] or name
                for f in [src] if qty == 1 else [src, src[:-2] + "_l"]:
                    tris = G.read_stl(os.path.join(G.ASSEMBLY, f + ".stl"))
                    add(LINK_OF.get(f, "base_link"), f, m, _shell(tris))
        elif name.startswith("front motor"):
            for sgn, s in SIDES:
                p = [P.X_PIVOT, sgn * P.BOOM_Y, P.Z_PIVOT + MB._z_motor]
                add(TILT_LINK[s], name, m, _cyl(p, 17.0, 30.0, [0, 0, 1]))
        elif name.startswith("front prop"):
            for sgn, s in SIDES:
                add(f"rotor_{ROTOR[s]}", name, m, _prop([P.X_PIVOT, sgn * P.BOOM_Y, P.Z_PIVOT + MB._z_prop]))
        elif name.startswith("front ESC"):
            for e in ("esc_0", "esc_2"):
                add("base_link", name, m, _equip(eq[e]))
        elif name.startswith("rear ESC"):
            add("base_link", name, m, _equip(eq["esc_1"]))
        elif name.startswith("tilt servo"):
            for s in "rl":
                add("base_link", name, m, _equip(eq[f"tilt_servo_{s}"]))
        elif name.startswith("rear motor"):
            add("base_link", name, m, _cyl(REAR_MOTOR_BASE + [0, 0, 16.0], 17.0, 30.0, [0, 0, 1]))
        elif name.startswith("rear prop"):
            add("rotor_2", name, m, _prop(REAR_MOTOR_BASE + [0, 0, P.MOTOR_BASE_TO_PROP]))
        elif name.startswith("aileron servo"):
            for h in wing_h:
                add("base_link", name, m, _equip(eq[f"servo_{h['name']}"]))
        elif name.startswith("V-tail servo"):
            for h in vt_h:
                add("base_link", name, m, _equip(eq[f"servo_{h['name']}"]))
        elif name.startswith(("Pixhawk", "GPS", "ELRS", "airspeed sensor", "power module", "servo BEC")):
            key = {"Pixhawk": "fc", "GPS": "gps", "ELRS": "receiver", "airspeed": "airspeed",
                   "power": "power_module", "servo": "bec"}[name.split()[0]]
            add("base_link", name, m, _equip(eq[key]))
        elif name.startswith("pitot"):
            add("base_link", name, m, _point([xh, P.PITOT_Y / 2, 0.0]))   # tube at the wing, tubing inboard
        elif name.startswith("wiring"):
            add("base_link", name, m / 2, _point([xh, 0.0, 0.0]))
            add("base_link", name, m / 2, _rod([xh, -520.0, 0.0], [xh, 520.0, 0.0]))   # servo leads
        elif name.startswith("battery straps"):
            for x in P.TRAY_STRAP_X:
                add("base_link", name, m, _point([x, 0.0, P.TRAY_Z + PL.BATTERY_SIZE[2] / 2]))
        elif name.startswith("M2 screws"):
            for h in (wing_h if "wing" in name else vt_h):
                add("base_link", name, m * qty / len(wing_h if "wing" in name else vt_h), _point(h["origin"]))
        elif name.startswith("pushrod"):
            for h in (wing_h if "ailerons" in name else vt_h):
                add("base_link", name, m, _point([xh, h["origin"][1], h["origin"][2]]))
        elif name.startswith(("main spars", "rear spars")):
            sp = P.MAIN_SPAR if name.startswith("main") else P.REAR_SPAR
            for sgn, _ in SIDES:
                add("base_link", name, m, _rod([sp["x"], sgn * P.Y_ROOT, sp["z"]], [sp["x"], sgn * P.Y_TIP, sp["z"]]))
        elif name.startswith(("main joiner", "rear joiner")):
            sp, j = (P.MAIN_SPAR, P.MAIN_JOINER) if name.startswith("main") else (P.REAR_SPAR, P.REAR_JOINER)
            add("base_link", name, m, _rod([sp["x"], -j["length"] / 2, sp["z"]], [sp["x"], j["length"] / 2, sp["z"]]))
        elif name.startswith("tail boom"):
            add("base_link", name, m, _rod([P.BOOM_X[0], 0, P.BOOM_Z], [P.BOOM_X[1], 0, P.BOOM_Z]))
        elif name.startswith("V-tail pins"):
            for sgn, _ in SIDES:
                add("base_link", name, m, _point([xh, sgn * P.VT_ROOT[0], P.VT_ROOT[1]]))
        elif name.startswith("bearings"):
            add("base_link", name, m, _point([xh, 0.0, 0.0]))
        elif name.startswith("glue"):
            add("base_link", name, m, _rod([xh, -P.Y_TIP, 0.0], [xh, P.Y_TIP, 0.0]))   # mostly the wing joints
        else:
            raise KeyError(f"make_sim.py does not place '{name}' (mass_balance.py); add it to mass_items()")
    add("base_link", MB.BATTERY["name"], MB.BATTERY["mass"], _equip(eq["battery"]))
    return out


def combine(items):
    m = sum(it[2] for it in items)
    p = sum(it[2] * it[3] for it in items) / m
    inertia = np.zeros((3, 3))
    for _, _, mi, pi, ii in items:
        d = pi - p
        inertia += ii + mi * (d @ d * np.eye(3) - np.outer(d, d))
    return m, p, inertia


# --- geometry of the moving parts ----------------------------------------------------------------
def _hinge_axis(a, b, normal):
    """Unit hinge direction (design frame) along a->b, turned so that a positive joint angle lifts
    the trailing edge toward `normal` (the surface's upper side): PX4's 'up = positive'."""
    h = (np.asarray(b, float) - np.asarray(a, float))
    h /= np.linalg.norm(h)
    want = np.cross([1.0, 0.0, 0.0], normal)    # design x points aft, toward the trailing edge
    return h if h @ want > 0 else -h


def surfaces_geometry():
    """Hinge point (link origin, design mm), hinge axis and upper-side normal of each surface."""
    up, _ = G.SECTIONS["clarky"]
    out = {}
    for sgn, s in SIDES:
        for w, (y0, y1) in P.AILERONS.items():
            ends = [np.array([P.X_LE + P.AIL_HINGE * P.chord(y), sgn * y,
                              P.Z_WING + P.chord(y) * float(up(P.AIL_HINGE))]) for y in (y0, y1)]
            n = np.array([0.0, 0.0, 1.0])
            out[f"aileron_{w}_{s}"] = dict(origin=ends[0], axis=_hinge_axis(*ends, n), normal=n)
        o, e_s, e_t = skins.vt_frame()
        o, e_s, e_t = o * [1, sgn, 1], e_s * [1, sgn, 1], e_t * [1, sgn, 1]
        ends = []
        for sv in P.VT_RUDDERVATOR:
            c = skins.vt_chord(sv)
            ends.append(o + [P.VT_HINGE * c, 0, 0] + sv * e_s + c * float(G.naca0012_half(P.VT_HINGE)) * e_t)
        out[f"ruddervator_{s}"] = dict(origin=ends[0], axis=_hinge_axis(*ends, e_t), normal=e_t)
    return out


def link_origins(geo):
    """Origin of every link (design mm); all link frames are parallel to the model frame."""
    org = {"base_link": None, "airspeed_link": np.array([PL.PITOT_X[0], P.PITOT_Y, PL.pitot_z()])}
    for sgn, s in SIDES:
        org[TILT_LINK[s]] = np.array([P.X_PIVOT, sgn * P.BOOM_Y, P.Z_PIVOT])
        org[f"rotor_{ROTOR[s]}"] = front_motor_base(sgn) + [0, 0, P.MOTOR_BASE_TO_PROP]
    org["rotor_2"] = REAR_MOTOR_BASE + [0, 0, P.MOTOR_BASE_TO_PROP]
    for name, g in geo.items():
        org[name] = g["origin"]
    return org


# --- aerodynamics ---------------------------------------------------------------------------------
def aero(r):
    """LiftDrag elements (design frame cp, model frame vectors) and the derived numbers."""
    span = 2 * P.Y_TIP
    s_w = 2 * _span_integrals(wing_chord, 0.0, P.Y_TIP)[0]
    ar = span ** 2 / s_w
    a_w = lift_slope(ar)
    a0 = -zero_lift_angle()
    eps_a = 2 * a_w / (math.pi * ar)                        # downwash gradient at the tail
    cda_w = CL_REF ** 2 / (math.pi * OSWALD * ar) / (CL_REF / a_w)
    up, lo = G.SECTIONS["clarky"]
    elems = []
    a_mid, a_tip = P.AILERONS["mid"], P.AILERONS["tip"]
    split = (a_mid[1] + a_tip[0]) / 2
    tau_a = flap_tau(P.AIL_HINGE)
    for sgn, s in SIDES:
        for w, y0, y1, ail in (("inner", 0.0, a_mid[0], None), ("mid", a_mid[0], split, a_mid),
                               ("tip", split, P.Y_TIP, a_tip)):
            area, yc, cmac = _span_integrals(wing_chord, y0, y1)
            cp = [P.X_LE + 0.25 * cmac, sgn * yc, P.Z_WING + cmac * float(up(0.25) + lo(0.25)) / 2]
            e = dict(name=f"wing_{w}_{s}", cp=cp, area=area, a0=a0, cla=a_w, cda=cda_w,
                     alpha_stall=CL_MAX / a_w, cla_stall=-1.5, cda_stall=1.0,
                     forward=[1, 0, 0], upward=[0, 0, 1])
            if ail:
                cover = _span_integrals(wing_chord, *ail)[0] / area
                e.update(joint=f"aileron_{w}_{s}_joint", rad_to_cl=-a_w * tau_a * cover)
            elems.append(e)
    # V-tail: each panel's normal force split into its pitch- and yaw-plane parts; the downwash
    # gradient acts on the pitch part only. The control derivative carries no downwash factor.
    d = math.radians(P.VT_DIHEDRAL)
    s_p, sc, cmac_t = _span_integrals(skins.vt_chord, 0.0, P.VT_SPAN)
    a_t = lift_slope((2 * P.VT_SPAN) ** 2 / (2 * s_p))
    tau_r = flap_tau(P.VT_HINGE)
    cover = _span_integrals(skins.vt_chord, *P.VT_RUDDERVATOR)[0] / s_p
    o, e_s, e_t = skins.vt_frame()
    for sgn, s in SIDES:
        cp = (o + 0.25 * cmac_t * np.array([1.0, 0, 0]) + sc * e_s) * [1, sgn, 1]
        joint = f"ruddervator_{s}_joint"
        elems.append(dict(name=f"vtail_{s}_pitch", cp=cp, area=s_p * math.cos(d) ** 2, a0=0.0,
                          cla=a_t * (1 - eps_a), cda=0.05, alpha_stall=0.3, cla_stall=-1.0, cda_stall=1.0,
                          forward=[1, 0, 0], upward=[0, 0, 1], joint=joint,
                          rad_to_cl=-a_t * tau_r * cover / math.cos(d)))
        elems.append(dict(name=f"vtail_{s}_yaw", cp=cp, area=s_p * math.sin(d) ** 2, a0=0.0,
                          cla=a_t, cda=0.05, alpha_stall=0.3, cla_stall=-1.0, cda_stall=1.0,
                          forward=[1, 0, 0], upward=[0, sgn, 0], joint=joint,
                          rad_to_cl=-a_t * tau_r * cover / math.sin(d)))
    # Parasitic drag of the whole aircraft at the CG; it grows with the angle to the flow.
    elems.append(dict(name="body_drag", cp=[r["x_cg_hover"], 0.0, 0.0], area=s_w, a0=FUSE_A0, cla=0.0,
                      cda=CD0 / FUSE_A0, alpha_stall=math.pi / 2, cla_stall=0.0, cda_stall=0.0,
                      forward=[1, 0, 0], upward=[0, 0, 1], radial=True))
    # Stick-fixed neutral point of this model: the lift-slope-weighted mean of the pitch-plane cps.
    pitch = [e for e in elems if e["upward"] == [0, 0, 1] and e["cla"] > 0]
    x_np = sum(e["cla"] * e["area"] * e["cp"][0] for e in pitch) / sum(e["cla"] * e["area"] for e in pitch)
    # Level cruise at FW_AIRSPD_TRIM in this model: the wing's angle, the drag, and the throttle that
    # balances it (thrust goes with the square of the command, and gz keeps it at any airspeed).
    v = r["fw_min"] + 2
    q = 0.5 * RHO * v * v
    cl = r["auw"] / 1000 * MB.G0 / (q * s_w * 1e-6)
    alpha = cl / a_w
    cd = cda_w * alpha + CD0 / FUSE_A0 * (FUSE_A0 + abs(alpha - a0))
    drag = q * s_w * 1e-6 * cd
    cruise = dict(v=v, cl=cl, aoa=alpha - a0, drag=drag, thrust=drag / (2 * THRUST_MAX))
    return dict(elems=elems, s_w=s_w, ar=ar, a_w=a_w, a0=a0, a_t=a_t, eps_a=eps_a, tau_a=tau_a, tau_r=tau_r,
                x_np=x_np, static_margin=(x_np - r["x_cg_pin"]) / r["mac"], cruise=cruise)


# --- visuals ----------------------------------------------------------------------------------------
def _motor(base, prop=None):
    """Motor drawn as in make_viewer.exterior_model: (motor, bell) triangles, and the prop's."""
    z = np.array([0.0, 0.0, 1.0])
    b = np.asarray(base, float)
    h = P.MOTOR_BASE_TO_PROP
    motor = np.concatenate([V._cylinder(b, b + 6 * z, 14), V._cylinder(b + 30 * z, b + (h + 3.5) * z, 2.5, 12)])
    bell = V._cylinder(b + 6 * z, b + 30 * z, 17)
    r = P.PROP_D / 2
    d = np.array([math.cos(math.radians(30)), math.sin(math.radians(30)), 0.0])
    blades = [V._box(b + h * z + s * d * (r + 4) / 2, (d, np.cross(z, d), z), ((r - 4) / 2, 7.0, 0.8))
              for s in (1, -1)]
    return motor, bell, np.concatenate([V._cylinder(b + (h - 3.5) * z, b + (h + 3.5) * z, 6)] + blades)


def visual_groups():
    """Triangles (design mm) per (link, material): the parts that show, as in renders/vtol_plane.stl."""
    groups = defaultdict(list)
    for f in sorted(os.listdir(G.ASSEMBLY)):
        name = f[:-4]
        if not f.endswith(".stl") or name in V.LOOSE or name in V.INSIDE:
            continue
        lw = name.startswith(V.LWPLA) and not name.startswith(("vtail_root_rib", "vtail_tip_cap"))
        groups[(LINK_OF.get(name, "base_link"), "lwpla" if lw else "petg")].append(
            G.read_stl(os.path.join(G.ASSEMBLY, f)))
    groups[("base_link", "carbon")].append(
        V._cylinder([P.BOOM_X[0], 0, P.BOOM_Z], [P.BOOM_X[1], 0, P.BOOM_Z], P.BOOM_OD / 2, 32))
    eq = {e["name"]: e for e in PL.equipment()}
    g, pt = eq["gps"], eq["pitot"]
    groups[("base_link", "motor")].append(V._cylinder(np.array(g["pos"]) - [0, 0, g["h"] / 2],
                                                      np.array(g["pos"]) + [0, 0, g["h"] / 2], g["r"], 32))
    groups[("base_link", "prop")].append(V._cylinder([PL.PITOT_X[0], P.PITOT_Y, PL.pitot_z()],
                                                     [PL.PITOT_X[1], P.PITOT_Y, PL.pitot_z()], pt["r"], 12))
    for link, rotor, base in [(TILT_LINK[s], f"rotor_{ROTOR[s]}", front_motor_base(sgn)) for sgn, s in SIDES] + \
            [("base_link", "rotor_2", REAR_MOTOR_BASE)]:
        motor, bell, prop = _motor(base)
        groups[(link, "motor")].append(motor)
        groups[(link, "bell")].append(bell)
        groups[(rotor, "prop")].append(prop)
    return groups


def _stl_bytes(tris):
    """Binary STL, as geom.write_stl writes it."""
    tris = np.asarray(tris, np.float64)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-20
    rec = np.zeros(len(tris), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = nrm
    rec["v"] = tris
    return b"vtol_plane sim mesh".ljust(80, b"\0") + np.uint32(len(tris)).tobytes() + rec.tobytes()


# --- the model --------------------------------------------------------------------------------------
def build():
    """Everything make_sim writes: {relative path: bytes}, plus the numbers for the report."""
    r = MB.compute(verbose=False)
    items = mass_items(r)
    m_all, p_all, _ = combine(items)
    assert abs(m_all - r["auw"]) < 1e-6, (m_all, r["auw"])
    assert abs(p_all[0] - r["x_cg_hover"]) < 0.01, (p_all[0], r["x_cg_hover"])
    origin = np.round([r["x_cg_hover"], 0.0, p_all[2]], 2)   # rounded: the same bytes on any machine
    to_m = lambda p: (np.asarray(p, float) - origin) * FLIP / 1000.0   # noqa: E731
    geo = surfaces_geometry()
    org = link_origins(geo)
    org["base_link"] = origin
    links = {}
    by_link = defaultdict(list)
    for it in items:
        by_link[it[0]].append(it)
    for name, its in by_link.items():
        m, p, inertia = combine(its)
        f = np.diag(FLIP)
        links[name] = dict(mass=m / 1000.0, com=to_m(p) - to_m(org[name]), inertia=f @ inertia @ f * 1e-9,
                           pose=to_m(org[name]))
    links["airspeed_link"] = dict(mass=1e-4, com=np.zeros(3), inertia=np.eye(3) * 1e-8,   # the pitot's mass is
                                  pose=to_m(org["airspeed_link"]))                          # in base_link
    ae = aero(r)

    files, meshes = {}, defaultdict(list)
    for (link, mat), tris in sorted(visual_groups().items()):
        t = to_m(np.concatenate(tris).reshape(-1, 3)).reshape(-1, 3, 3) - links[link]["pose"]
        fname = f"{link}_{mat}.stl"
        files[f"models/{MODEL}/meshes/{fname}"] = _stl_bytes(t)
        meshes[link].append((mat, fname))
    stamp = hashlib.sha256(b"".join(files[k] for k in sorted(files))).hexdigest()[:16]

    belly_z = min(G.fuse_dims(x)[2] - G.fuse_dims(x)[1] / 2 for x in np.linspace(*BELLY_PAD[:2], 26))
    pad_c = [(BELLY_PAD[0] + BELLY_PAD[1]) / 2, 0.0, belly_z - BELLY_PAD[3] + 6.0]
    pad_size = [(BELLY_PAD[1] - BELLY_PAD[0]) / 1000, BELLY_PAD[2] / 1000, 0.012]
    spawn_z = -to_m(pad_c)[2] + pad_size[2] / 2 + 0.002

    sdf = model_sdf(links, meshes, geo, ae, to_m, pad_c, pad_size, spawn_z, stamp, r)
    files[f"models/{MODEL}/model.sdf"] = sdf.encode()
    files[f"models/{MODEL}/model.config"] = model_config().encode()
    files[f"worlds/{WORLD}.sdf"] = world_sdf().encode()
    rotors = {k: to_m(org[f"rotor_{k}"]) for k in range(3)}
    files[f"airframes/{AIRFRAME_ID}_gz_{MODEL}"] = airframe(r, rotors, ae).encode()
    return files, dict(r=r, links=links, aero=ae, origin=origin, rotors=rotors, items=items)


def _inertial(lk):
    i = lk["inertia"]
    return (f"<inertial><pose>{_vec(lk['com'])} 0 0 0</pose><mass>{_num(lk['mass'], 6)}</mass>"
            f"<inertia><ixx>{_sci(i[0, 0])}</ixx><ixy>{_sci(i[0, 1])}</ixy><ixz>{_sci(i[0, 2])}</ixz>"
            f"<iyy>{_sci(i[1, 1])}</iyy><iyz>{_sci(i[1, 2])}</iyz><izz>{_sci(i[2, 2])}</izz></inertia></inertial>")


def _visuals(link, meshes):
    return [f"<visual name='{mat}'><geometry><mesh><uri>model://{MODEL}/meshes/{f}</uri></mesh></geometry>"
            f"<material><ambient>{COLOR[mat]} 1</ambient><diffuse>{COLOR[mat]} 1</diffuse>"
            f"<specular>0.2 0.2 0.2 1</specular></material></visual>" for mat, f in meshes[link]]


IMU_NOISE = ("<noise type='gaussian'><mean>0</mean><stddev>{0}</stddev><dynamic_bias_stddev>{1}"
             "</dynamic_bias_stddev><dynamic_bias_correlation_time>{2}</dynamic_bias_correlation_time></noise>")


def _sensors():
    gyro = IMU_NOISE.format(0.0003394, 3.8785e-05, 1000)
    acc = IMU_NOISE.format(0.004, 0.006, 300)
    mag = "<noise type='gaussian'><stddev>3e-7</stddev></noise>"
    return [
        "<sensor name='imu_sensor' type='imu'><always_on>1</always_on>"
        "<update_rate>250</update_rate><imu>"
        f"<angular_velocity><x>{gyro}</x><y>{gyro}</y><z>{gyro}</z></angular_velocity>"
        f"<linear_acceleration><x>{acc}</x><y>{acc}</y><z>{acc}</z></linear_acceleration></imu></sensor>",
        "<sensor name='air_pressure_sensor' type='air_pressure'>"
        "<always_on>1</always_on><update_rate>50</update_rate><air_pressure><pressure>"
        "<noise type='gaussian'><mean>0</mean><stddev>0.01</stddev></noise></pressure></air_pressure></sensor>",
        # Tesla, as PX4's server.config sets use_units_gauss false.
        "<sensor name='magnetometer_sensor' type='magnetometer'>"
        f"<always_on>1</always_on><update_rate>100</update_rate><magnetometer><x>{mag}</x><y>{mag}</y>"
        f"<z>{mag}</z></magnetometer></sensor>",
        "<sensor name='navsat_sensor' type='navsat'><always_on>1</always_on>"
        "<update_rate>30</update_rate></sensor>",
    ]


def model_sdf(links, meshes, geo, ae, to_m, pad_c, pad_size, spawn_z, stamp, r):
    L = ["<?xml version='1.0'?>",
         f"<!-- Generated by scripts/make_sim.py from the design; do not edit. Meshes {stamp}. -->",
         "<sdf version='1.9'>",
         f"<model name='{MODEL}'>",
         f"<pose>0 0 {_num(spawn_z)} 0 0 0</pose>"]
    base = links["base_link"]
    L += ["<link name='base_link'>", _inertial(base), *_visuals("base_link", meshes),
          f"<collision name='belly_pad'><pose>{_vec(to_m(pad_c))} 0 0 0</pose><geometry><box><size>"
          f"{_vec(pad_size)}</size></box></geometry></collision>", *_sensors(), "</link>"]
    asp = links["airspeed_link"]
    L += [f"<link name='airspeed_link'><pose>{_vec(asp['pose'])} 0 0 0</pose>{_inertial(asp)}",
          "<sensor name='air_speed' type='air_speed'><always_on>1"
          "</always_on><update_rate>10</update_rate></sensor></link>",
          "<joint name='airspeed_joint' type='fixed'><parent>base_link</parent><child>airspeed_link</child></joint>"]
    lo, hi = math.radians(P.TILT_MIN_DEG - STOP_MARGIN_DEG), math.radians(P.TILT_MAX_DEG + STOP_MARGIN_DEG)
    for sgn, s in SIDES:
        t = TILT_LINK[s]
        L += [f"<link name='{t}'><pose>{_vec(links[t]['pose'])} 0 0 0</pose>{_inertial(links[t])}",
              *_visuals(t, meshes), "</link>",
              f"<joint name='{t}_joint' type='revolute'><parent>base_link</parent><child>{t}</child><axis>"
              f"<xyz>0 1 0</xyz><limit><lower>{_num(lo)}</lower><upper>{_num(hi)}</upper>"
              f"<effort>{SERVO_TORQUE['tilt']}</effort></limit>"
              "<dynamics><damping>0.01</damping></dynamics></axis></joint>"]
    for k in range(3):
        rl, parent = f"rotor_{k}", ("tilt_r", "tilt_l", "base_link")[k]
        L += [f"<link name='{rl}'><pose>{_vec(links[rl]['pose'])} 0 0 0</pose>{_inertial(links[rl])}",
              *_visuals(rl, meshes), "</link>",
              f"<joint name='{rl}_joint' type='revolute'><parent>{parent}</parent><child>{rl}</child><axis>"
              "<xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis></joint>"]
    lim = math.radians(SURFACE_DEG + STOP_MARGIN_DEG)
    for sname in SURFACES:
        g = geo[sname]
        L += [f"<link name='{sname}'><pose>{_vec(links[sname]['pose'])} 0 0 0</pose>{_inertial(links[sname])}",
              *_visuals(sname, meshes), "</link>",
              f"<joint name='{sname}_joint' type='revolute'><parent>base_link</parent><child>{sname}</child>"
              f"<axis><xyz>{_vec(g['axis'] * FLIP, 6)}</xyz><limit><lower>{_num(-lim)}</lower><upper>{_num(lim)}"
              f"</upper><effort>{SERVO_TORQUE['surface']}</effort></limit>"
              "<dynamics><damping>0.001</damping></dynamics></axis></joint>"]
    for e in ae["elems"]:
        ctrl = (f"<control_joint_name>{e['joint']}</control_joint_name>"
                f"<control_joint_rad_to_cl>{_num(e['rad_to_cl'])}</control_joint_rad_to_cl>") if "joint" in e else ""
        L.append(f"<plugin filename='gz-sim-lift-drag-system' name='gz::sim::systems::LiftDrag'><!-- {e['name']} -->"
                 f"<link_name>base_link</link_name><air_density>{_num(RHO, 4)}</air_density>"
                 f"<area>{_num(e['area'] * 1e-6, 6)}</area><a0>{_num(e['a0'])}</a0><cla>{_num(e['cla'])}</cla>"
                 f"<cda>{_num(e['cda'])}</cda><cma>0</cma><alpha_stall>{_num(e['alpha_stall'])}</alpha_stall>"
                 f"<cla_stall>{_num(e['cla_stall'])}</cla_stall><cda_stall>{_num(e['cda_stall'])}</cda_stall>"
                 f"<cma_stall>0</cma_stall><cp>{_vec(to_m(e['cp']))}</cp>"
                 f"<forward>{_vec(e['forward'])}</forward><upward>{_vec(e['upward'])}</upward>"
                 f"{'<radial_symmetry>true</radial_symmetry>' if e.get('radial') else ''}{ctrl}</plugin>")
    for k, joint in enumerate(SERVO_ORDER):
        init = 0.0
        L.append("<plugin filename='gz-sim-joint-position-controller-system' "
                 f"name='gz::sim::systems::JointPositionController'><joint_name>{joint}_joint</joint_name>"
                 f"<sub_topic>servo_{k}</sub_topic><use_velocity_commands>true</use_velocity_commands>"
                 f"<cmd_max>{_num(SERVO_RATE, 3)}</cmd_max><cmd_min>{_num(-SERVO_RATE, 3)}</cmd_min>"
                 f"<initial_position>{_num(init)}</initial_position></plugin>")
    for k in range(3):
        cw = k == 0
        L.append("<plugin filename='gz-sim-multicopter-motor-model-system' "
                 f"name='gz::sim::systems::MulticopterMotorModel'><jointName>rotor_{k}_joint</jointName>"
                 f"<linkName>rotor_{k}</linkName><turningDirection>{'cw' if cw else 'ccw'}</turningDirection>"
                 f"<timeConstantUp>{MOTOR_TAU[0]}</timeConstantUp><timeConstantDown>{MOTOR_TAU[1]}</timeConstantDown>"
                 f"<maxRotVelocity>{_num(OMEGA_MAX)}</maxRotVelocity>"
                 f"<motorConstant>{_sci(THRUST_MAX / OMEGA_MAX ** 2)}</motorConstant>"
                 f"<momentConstant>{MOMENT_RATIO}</momentConstant><commandSubTopic>command/motor_speed</commandSubTopic>"
                 f"<actuator_number>{k}</actuator_number><rotorDragCoefficient>2e-05</rotorDragCoefficient>"
                 f"<rollingMomentCoefficient>1e-06</rollingMomentCoefficient>"
                 f"<rotorVelocitySlowdownSim>{_num(ROTOR_SLOWDOWN)}</rotorVelocitySlowdownSim>"
                 "<motorType>velocity</motorType></plugin>")
    L += ["</model>", "</sdf>"]
    return "\n".join(L) + "\n"


def model_config():
    return ("<?xml version='1.0'?>\n<model>\n"
            f"  <name>{MODEL}</name>\n  <version>1.0</version>\n  <sdf version='1.9'>model.sdf</sdf>\n"
            "  <author><name>AjayaDahal/vtol-plane</name></author>\n"
            "  <description>3-D printed tilt-rotor tricopter VTOL, generated from the design by "
            "scripts/make_sim.py (github.com/AjayaDahal/vtol-plane).</description>\n</model>\n")


def world_sdf():
    """The field the aircraft flies from: PX4's default world (physics, gravity, magnetic field and
    geodetic origin, so PX4's home is the same) with a sky, a 4 km grass field marked every 50 m for a
    sense of speed and height on video, and a landing pad at home. Nothing on it collides but the ground."""
    grass, mark, pad = "0.36 0.50 0.27", "0.27 0.40 0.20", "0.62 0.63 0.64"
    box = lambda name, x, y, z, sx, sy, sz, col: (   # noqa: E731
        f"<visual name='{name}'><pose>{_num(x)} {_num(y)} {_num(z)} 0 0 0</pose><geometry><box><size>{_num(sx)} "
        f"{_num(sy)} {_num(sz)}</size></box></geometry><material><ambient>{col} 1</ambient><diffuse>{col} 1"
        f"</diffuse><specular>0.05 0.05 0.05 1</specular></material></visual>")
    marks = []
    for k in range(-20, 21):
        marks.append(box(f"mark_ns_{k + 20}", 50.0 * k, 0, 0.004, 0.5, 2000, 0.008, mark))
        marks.append(box(f"mark_ew_{k + 20}", 0, 50.0 * k, 0.004, 2000, 0.5, 0.008, mark))
    marks += [box("pad", 0, 0, 0.005, 6, 6, 0.01, pad), box("pad_h_1", 0, -1.0, 0.011, 3, 0.4, 0.004, "0.95 0.95 0.95"),
              box("pad_h_2", 0, 1.0, 0.011, 3, 0.4, 0.004, "0.95 0.95 0.95"),
              box("pad_h_3", 0, 0, 0.011, 0.4, 2.0, 0.004, "0.95 0.95 0.95")]
    return "\n".join([
        "<?xml version='1.0'?>",
        "<!-- Generated by scripts/make_sim.py; do not edit. -->",
        "<sdf version='1.9'>",
        f"<world name='{WORLD}'>",
        "<physics type='ode'><max_step_size>0.004</max_step_size><real_time_factor>1.0</real_time_factor>"
        "<real_time_update_rate>250</real_time_update_rate></physics>",
        "<gravity>0 0 -9.8</gravity>",
        "<magnetic_field>6e-06 2.3e-05 -4.2e-05</magnetic_field>",
        "<atmosphere type='adiabatic'/>",
        "<scene><grid>false</grid><ambient>0.5 0.5 0.5 1</ambient><background>0.63 0.76 0.90 1</background>"
        "<sky></sky><shadows>true</shadows></scene>",
        "<model name='ground_plane'><static>true</static><link name='link'>",
        "<collision name='collision'><pose>0 0 -5 0 0 0</pose><geometry><box><size>100000 100000 10</size></box>"
        "</geometry></collision>",
        f"<visual name='grass'><geometry><plane><normal>0 0 1</normal><size>4000 4000</size></plane></geometry>"
        f"<material><ambient>{grass} 1</ambient><diffuse>{grass} 1</diffuse><specular>0.05 0.05 0.05 1</specular>"
        "</material></visual>",
        *marks,
        "</link></model>",
        "<light name='sun' type='directional'><pose>0 0 500 0 0 0</pose><cast_shadows>true</cast_shadows>"
        "<intensity>1</intensity><direction>0.3 0.5 -0.8</direction><diffuse>0.95 0.95 0.92 1</diffuse>"
        "<specular>0.3 0.3 0.3 1</specular></light>",
        "<spherical_coordinates><surface_model>EARTH_WGS84</surface_model>"
        "<world_frame_orientation>ENU</world_frame_orientation><latitude_deg>47.397971057728974</latitude_deg>"
        "<longitude_deg>8.546163739800146</longitude_deg><elevation>488</elevation></spherical_coordinates>",
        "</world>",
        "</sdf>",
        ""])


def airframe(r, rotors, ae):
    """PX4 airframe: PX4_GUIDE.md's geometry and outputs, the gz bridge's channel mapping, the
    airspeeds from mass_balance.py, the throttles from this model."""
    tilt = lambda deg: (deg - P.TILT_MIN_DEG) / (P.TILT_MAX_DEG - P.TILT_MIN_DEG)   # noqa: E731
    stall = math.ceil(r["v_stall_px4"])
    lines = [
        "#!/bin/sh",
        "#",
        "# @name VTOL plane (3-D printed tilt-rotor tricopter)",
        "#",
        "# @type VTOL Tiltrotor",
        "#",
        "# @maintainer AjayaDahal/vtol-plane",
        "#",
        "# Generated by scripts/make_sim.py from the design; do not edit. The actuator geometry and",
        "# outputs are PX4_GUIDE.md's, with SIM_GZ_* in place of the PWM/DShot outputs.",
        "#",
        "",
        ". ${R}etc/init.d/rc.vtol_defaults",
        "",
        "PX4_SIMULATOR=${PX4_SIMULATOR:=gz}",
        f"PX4_GZ_WORLD=${{PX4_GZ_WORLD:={WORLD}}}",
        f"PX4_SIM_MODEL=${{PX4_SIM_MODEL:={MODEL}}}",
        "",
        "param set-default SIM_GZ_EN 1",
        "param set-default MAV_TYPE 21",
        "param set-default VT_TYPE 1",
        "param set-default CA_AIRFRAME 3",
        "",
        "# Rotors relative to the hover CG, x forward, y right (PX4_GUIDE.md, Geometry)",
        "param set-default CA_ROTOR_COUNT 3",
    ]
    km = {0: -0.05, 1: 0.05, 2: 0.05}
    for k in range(3):
        px, py = rotors[k][0], -rotors[k][1]
        lines += [f"param set-default CA_ROTOR{k}_PX {px:.3f}", f"param set-default CA_ROTOR{k}_PY {py:.3f}",
                  f"param set-default CA_ROTOR{k}_KM {km[k]}"]
        if k < 2:
            lines.append(f"param set-default CA_ROTOR{k}_TILT {k + 1}")
    lines += ["", "# Tilt servos: 0 deg = thrust up, -20 (back) to 90 (forward), used for yaw",
              "param set-default CA_SV_TL_COUNT 2"]
    for k in range(2):
        lines += [f"param set-default CA_SV_TL{k}_MINA {P.TILT_MIN_DEG:.0f}",
                  f"param set-default CA_SV_TL{k}_MAXA {P.TILT_MAX_DEG:.0f}",
                  f"param set-default CA_SV_TL{k}_TD 0", f"param set-default CA_SV_TL{k}_CT 1"]
    # Control surfaces in PX4_GUIDE.md's order; torque scales 1/N per axis (QGC's default rule).
    cs = [(2, 0.25, 0, 0), (2, 0.25, 0, 0), (1, -0.25, 0, 0), (1, -0.25, 0, 0), (8, 0, 0.5, -0.5), (7, 0, 0.5, 0.5)]
    lines += ["", "# Control surfaces: right aileron mid, tip; left mid, tip; right, left ruddervator",
              f"param set-default CA_SV_CS_COUNT {len(cs)}"]
    for k, (typ, tr, tp, ty) in enumerate(cs):
        lines.append(f"param set-default CA_SV_CS{k}_TYPE {typ}")
        lines += [f"param set-default CA_SV_CS{k}_TRQ_{ax} {v}" for ax, v in (("R", tr), ("P", tp), ("Y", ty)) if v]
    lines += ["", "# Outputs: ESC 1-3 = PX4_GUIDE.md's AUX1-3; servo 1-8 = its MAIN1-8 (gz servo_0-7)"]
    for k in range(3):
        lines += [f"param set-default SIM_GZ_EC_FUNC{k + 1} {101 + k}",
                  f"param set-default SIM_GZ_EC_MIN{k + 1} {round(IDLE * OMEGA_MAX)}",
                  f"param set-default SIM_GZ_EC_MAX{k + 1} {round(OMEGA_MAX)}"]
    funcs = [207, 208, 201, 202, 203, 204, 205, 206]
    for k, fn in enumerate(funcs):
        n = k + 1
        lo, hi = (P.TILT_MIN_DEG, P.TILT_MAX_DEG) if k < 2 else (-SURFACE_DEG, SURFACE_DEG)
        lines += [f"param set-default SIM_GZ_SV_FUNC{n} {fn}", f"param set-default SIM_GZ_SV_MINA{n} {lo:.0f}",
                  f"param set-default SIM_GZ_SV_MAXA{n} {hi:.0f}"]
        if k < 2:   # disarmed: motors straight up, as PX4_GUIDE.md sets the real tilt servos
            lines.append(f"param set-default SIM_GZ_SV_DIS{n} {round(1000 * tilt(0.0))}")
    lines += ["", "# Transition and airspeeds (PX4_GUIDE.md; stall at CL 1.0, 35 C, AUW +10 %). The front",
              "# transition ends 1 m/s above stall: held level, the wing carried the aircraft by ~15 m/s and",
              "# the rotors unloaded, so a higher VT_ARSP_TRANS was never reached (REPORT.md, round 12).",
              f"param set-default VT_TILT_MC {tilt(0.0):.2f}",
              "param set-default VT_TILT_TRANS 0.55",
              "param set-default VT_TILT_FW 1.0",
              f"param set-default FW_AIRSPD_STALL {stall}",
              f"param set-default FW_AIRSPD_MIN {r['fw_min']}",
              f"param set-default FW_AIRSPD_TRIM {r['fw_min'] + 2}",
              "param set-default FW_AIRSPD_MAX 25",
              f"param set-default VT_ARSP_TRANS {stall + 1}",
              "param set-default VT_F_TRANS_DUR 8",
              "# The front transition holds FW_PSP_OFF, the cruise attitude: this model's, rounded down. The",
              "# lower it is, the further the speed where the wing takes the weight lies above VT_ARSP_TRANS.",
              f"param set-default FW_PSP_OFF {math.floor(math.degrees(ae['cruise']['aoa'])):.0f}",
              "# Without a valid airspeed PX4 ends the transition after VT_F_TR_OL_TM (default 6 s; a",
              "# tiltrotor also waits for its tilt ramp, VT_F_TRANS_DUR), and with one it gives up if the",
              "# airspeed is still under VT_ARSP_BLEND then. Real props lose thrust as the speed builds.",
              f"param set-default VT_F_TR_OL_TM {OPEN_LOOP_TRANS_S:.0f}",
              "",
              "# Quadchute (back to hover, then Return): fixed-wing pitch or roll past these, below 15 m, 15 m",
              "# under the altitude setpoint, or 10 m lost in the front transition (PX4_GUIDE.md, Failsafes)",
              *(f"param set-default {k} {v}" for k, v in QUADCHUTE.items()),
              "",
              "# Thrust curve: in this model thrust goes with the square of the motor command, which",
              f"# THR_MDL_FAC {(1 - IDLE) ** 2:.2f} undoes (the real one comes from a thrust stand). Hover and cruise are",
              "# then fractions of full thrust. gz keeps a prop's thrust at any airspeed, so the real",
              "# aircraft's cruise throttle is higher.",
              f"param set-default THR_MDL_FAC {(1 - IDLE) ** 2:.2f}",
              f"param set-default MPC_THR_HOVER {r['t_front'] / MB.T_MAX_FULL:.2f}",
              f"param set-default FW_THR_TRIM {ae['cruise']['thrust']:.2f}",
              "",
              "# Simulation only: the gz ESCs report no current, which PX4's ESC check reads as a failure",
              "param set-default FD_ESCS_EN 0",
              ""]
    return "\n".join(lines)


def report(info):
    r, links, ae = info["r"], info["links"], info["aero"]
    b = links["base_link"]
    m = sum(lk["mass"] for lk in links.values())
    print(f"model mass {m:.4f} kg (mass_balance {r['auw'] / 1000:.4f}), origin (hover CG) x={info['origin'][0]:.2f} "
          f"z={info['origin'][2]:.2f} mm")
    i = b["inertia"]
    print(f"base_link {b['mass']:.4f} kg, Ixx {i[0, 0]:.4f} Iyy {i[1, 1]:.4f} Izz {i[2, 2]:.4f} Ixz {i[0, 2]:.5f} kg m2")
    for k, p in info["rotors"].items():
        print(f"rotor {k}: PX {p[0]:.3f} PY {-p[1]:.3f} PZ {-p[2]:.3f} m")
    print(f"wing: S {ae['s_w'] * 1e-6:.4f} m2, AR {ae['ar']:.2f}, a {ae['a_w']:.3f}/rad, zero-lift "
          f"{-math.degrees(ae['a0']):.2f} deg; V-tail a {ae['a_t']:.3f}/rad, de/da {ae['eps_a']:.3f}; "
          f"tau aileron {ae['tau_a']:.3f}, ruddervator {ae['tau_r']:.3f}")
    print(f"neutral point x={ae['x_np']:.1f} mm, static margin {100 * ae['static_margin']:.1f} % MAC "
          f"(mass_balance {100 * r['static_margin']:.1f} %)")
    c = ae["cruise"]
    print(f"cruise at {c['v']} m/s: CL {c['cl']:.3f}, wing datum {math.degrees(c['aoa']):+.1f} deg, drag "
          f"{c['drag']:.2f} N (L/D {r['auw'] / 1000 * MB.G0 / c['drag']:.1f}), thrust {c['thrust']:.3f} of full")


def stale():
    """Generated files that differ from what make_sim.py would write now (the gate's check), and the
    numbers behind them."""
    files, info = build()
    out = []
    for rel, data in files.items():
        path = os.path.join(SIM, *rel.split("/"))
        if not os.path.exists(path) or open(path, "rb").read() != data:
            out.append("sim/" + rel)
    mesh_dir = os.path.join(MODEL_DIR, "meshes")
    if os.path.isdir(mesh_dir):
        out += [f"sim/models/{MODEL}/meshes/{f}" + " (stray)" for f in sorted(os.listdir(mesh_dir))
                if f"models/{MODEL}/meshes/{f}" not in files]
    return out, info


def main():
    files, info = build()
    mesh_dir = os.path.join(MODEL_DIR, "meshes")
    if os.path.isdir(mesh_dir):
        for f in os.listdir(mesh_dir):
            if f"models/{MODEL}/meshes/{f}" not in files:
                os.remove(os.path.join(mesh_dir, f))
    for rel, data in files.items():
        path = os.path.join(SIM, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
    report(info)
    print(f"wrote {len(files)} files under sim/")


if __name__ == "__main__":
    main()
