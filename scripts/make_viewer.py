"""Write viewer/manifest.json for the three.js viewer (viewer/index.html) from params.py.

Lists every assembly STL with its material, role and where it goes in the burst (exploded)
view; the carbon tubes, motors and props, which have no STL; the equipment and cable runs from
payload.py; and every print file with its printer, copies and sliced mass and time.
build_all.py runs this; then `python scripts/serve_viewer.py` and open
http://127.0.0.1:28765/viewer/
"""
import json
import math
import os
import re

import numpy as np

import geom as G
import params as P
import payload as PL
from make_print_ready import PARTS

LOOSE = {"servo_cage", "control_horn"}          # print-only parts modelled at the origin
LWPLA = ("wing_", "aileron_", "fuse_", "vtail_l", "vtail_r", "ruddervator_")
BED = {"s1": 250.0, "x": 260.0}

ROLE = {
    "fuse_1": "removable nose, one M3 nylon screw: the access opening",
    "coupler_240": "nose joint, heat-set insert for the nose screw",
    "fuse_2": "battery and avionics bay",
    "fc_shelf": "Pixhawk shelf; small boards hang underneath",
    "battery_tray": "battery tray with stop-pin holes, ESC deck behind",
    "coupler_370": "joins fuse_2 and fuse_3",
    "fuse_3": "wing section of the fuselage",
    "frame_main": "main joiner sleeve and boom bore",
    "frame_rear": "rear joiner sleeve and boom bore",
    "gps_mount": "external GPS saddle, glued on top",
    "coupler_610": "joins fuse_3 and fuse_4, boom web",
    "fuse_4": "tail cone",
    "pod_collar": "boom exit collar",
    "rear_motor_mount": "rear motor clamp on the boom",
    "tail_block": "V-tail mount on the end of the boom",
    "rib_root": "root rib: spars, wire hole, joiner lock pin",
    "boom_cup": "spigot ring on the boom rib's inboard face",
    "boom_rib": "boom rib with the pod tongue",
    "boom_pod": "tilt-servo pod and axle boss",
    "yoke": "tilting motor mount",
    "rib_midtip": "mid/tip joint rib",
    "rib_tip": "tip rib",
    "wing_root": "wing skin with internal webs",
    "wing_mid": "wing skin with internal webs",
    "wing_tip": "wing skin with internal webs",
    "aileron_mid": "aileron",
    "aileron_tip": "aileron",
    "vtail": "V-tail panel",
    "ruddervator": "ruddervator",
    "vtail_root_rib": "V-tail root rib (carbon pin into the tail block)",
    "vtail_tip_cap": "V-tail tip cap",
    "servo_cage": "9 g servo cage, glued inside a skin",
    "control_horn": "control horn",
}

# Burst view: the fuselage spreads along x from fuse_3 (which carries the wing), each wing slides
# out along the span with every joint opened, the inserts and equipment lift out of the
# fuselage, and the tail slides off the end of the boom.
WING_OUT, WING_GAP = 150.0, 60.0
WING_ORDER = {"rib_root": 0, "wing_root": 1, "boom_cup": 2, "boom_rib": 3, "boom_pod": 3, "wing_mid": 4,
              "aileron_mid": 4, "rib_midtip": 5, "wing_tip": 6, "aileron_tip": 6, "rib_tip": 7}
FUSE_X = {"fuse_1": -330.0, "coupler_240": -210.0, "fuse_2": -120.0, "coupler_370": -55.0, "fuse_3": 0.0,
          "coupler_610": 90.0, "fuse_4": 170.0, "pod_collar": 260.0}
IN_FUSE_2 = FUSE_X["fuse_2"]
LIFT = {"fc_shelf": (IN_FUSE_2, 190.0), "battery_tray": (IN_FUSE_2, -170.0), "frame_main": (0.0, 190.0),
        "frame_rear": (0.0, 190.0), "gps_mount": (0.0, 110.0)}
TAIL_X = 430.0
POD_OUT = -80.0
VT_OUT = {"vtail_root_rib": 40.0, "vtail": 100.0, "ruddervator": 100.0, "vtail_tip_cap": 170.0}


def split(name):
    return (name[:-2], name[-1]) if name[-2:] in ("_r", "_l") else (name, "c")


def vt_axes(side):
    d = math.radians(P.VT_DIHEDRAL)
    sgn = 1.0 if side == "r" else -1.0
    return np.array([0.0, sgn * math.cos(d), math.sin(d)]), np.array([0.0, -sgn * math.sin(d), math.cos(d)])


def wing_burst(base, side):
    sgn = 1.0 if side == "r" else -1.0
    v = np.array([0.0, sgn * (WING_OUT + WING_GAP * WING_ORDER[base]), 0.0])
    if base.startswith("aileron"):
        v += (45.0, 0.0, -35.0)
    if base == "boom_pod":
        v[0] = POD_OUT
    return v


def vt_burst(base, side):
    e_s, _ = vt_axes(side)
    v = np.array([TAIL_X + 90.0 + (50.0 if base == "ruddervator" else 0.0), 0.0, 0.0])
    return v + VT_OUT[base] * e_s


def burst(name):
    base, side = split(name)
    if base in WING_ORDER:
        return wing_burst(base, side)
    if name in FUSE_X:
        return np.array([FUSE_X[name], 0.0, 0.0])
    if name in LIFT:
        dx, dz = LIFT[name]
        return np.array([dx, 0.0, dz])
    if name == "rear_motor_mount":
        return np.array([TAIL_X, 0.0, 80.0])
    if name == "tail_block":
        return np.array([TAIL_X + 90.0, 0.0, 0.0])
    if base in VT_OUT:
        return vt_burst(base, side)
    return np.zeros(3)    # yokes ride in the tilt group, which carries their offset


def equipment_burst(e):
    n = e["name"]
    if n == "battery":
        return np.array([IN_FUSE_2, 0.0, -110.0])
    if n == "fc":
        return np.array([IN_FUSE_2, 0.0, 260.0])
    if n in ("power_module", "bec", "airspeed", "receiver") or n.startswith("esc_"):
        return np.array([IN_FUSE_2, 0.0, 120.0])
    if n == "gps":
        return np.array([0.0, 0.0, 180.0])
    if n == "pitot":
        return wing_burst("wing_mid", "r") + (-70.0, 0.0, 0.0)
    side = n[-1] if n[-1] in "rl" else n.split("_")[-1][0]
    sgn = 1.0 if side == "r" else -1.0
    if n.startswith("tilt_servo"):
        return wing_burst("boom_pod", side) + (0.0, -sgn * 45.0, 0.0)
    if n.startswith("aileron_servo"):
        sec = "wing_mid" if abs(e["pos"][1]) < P.Y_MID_SEC[1] else "wing_tip"
        return wing_burst(sec, side) + (0.0, 0.0, -45.0)
    if n.startswith("vtail_servo"):
        return vt_burst("vtail", side) - 45.0 * vt_axes(side)[1]
    return np.zeros(3)


# One label per kind of item; the duplicates stay unlabelled.
LABELS = {"battery": "4S 5000 mAh LiPo", "esc_1": "3 x ESC 50 A", "fc": "Pixhawk 6C",
          "power_module": "power module", "bec": "servo BEC", "airspeed": "airspeed sensor",
          "receiver": "ELRS receiver", "gps": "GPS + compass", "pitot": "pitot tube",
          "tilt_servo_r": "tilt servo (x2)", "aileron_servo_r320": "aileron servo (x4)",
          "vtail_servo_r": "ruddervator servo (x2)"}


def tube(name, a, b, od, idd=0.0, ex=(0.0, 0.0, 0.0)):
    return dict(name=name, a=list(map(float, a)), b=list(map(float, b)), od=od, id=idd,
                burst=[float(v) for v in ex])


def gcode_stats(name):
    """Sliced filament mass (g) and print time (min) from a part's G-code, if it exists."""
    spec = PARTS[name]
    folder = f"{spec['printer']}_{'lwpla' if spec['material'].startswith('lwpla') else 'petg'}"
    path = os.path.join(G.ROOT, "gcode", folder, name + ".gcode")
    if not os.path.exists(path):
        return None, None
    with open(path, "r", errors="replace") as f:
        f.seek(max(0, os.path.getsize(path) - 300_000))
        tail = f.read()
    m = re.search(r"; total filament used \[g\] = ([\d.]+)", tail)
    t = re.search(r"; estimated printing time \(normal mode\) = ([^\n]+)", tail)
    minutes = None
    if t:
        u = dict(d=1440, h=60, m=1, s=1 / 60)
        minutes = sum(float(v) * u[k] for v, k in re.findall(r"(\d+)([dhms])", t.group(1)))
    return (float(m.group(1)) if m else None), minutes


def prints():
    out = []
    for name, spec in sorted(PARTS.items()):
        v = G.read_stl(os.path.join(G.PRINT, name + ".stl")).reshape(-1, 3)
        grams, minutes = gcode_stats(name)
        mat = "lwpla" if spec["material"].startswith("lwpla") else "petg"
        out.append(dict(name=name, url=f"../parts/print_ready/{name}.stl", material=mat, printer=spec["printer"],
                        qty=spec["qty"], supports=spec["material"] == "petg_support", bed=BED[spec["printer"]],
                        size=[round(float(e), 1) for e in v.max(0) - v.min(0)], grams=grams,
                        minutes=None if minutes is None else round(minutes, 1),
                        role=ROLE.get(split(name)[0], ROLE.get(name, ""))))
    return out


def main():
    parts = []
    for f in sorted(os.listdir(G.ASSEMBLY)):
        name = f[:-4]
        if not f.endswith(".stl") or name in LOOSE:
            continue
        mat = "lwpla" if name.startswith(LWPLA) and not name.startswith(("vtail_root", "vtail_tip")) else "petg"
        base, side = split(name)
        spec = PARTS.get(name) or PARTS.get(base) or {}
        parts.append(dict(name=name, url=f"../parts/assembly/{f}", material=mat, side=side,
                          group="skin" if mat == "lwpla" else "structure", tilt=base == "yoke",
                          burst=[round(float(v), 2) for v in burst(name)], role=ROLE.get(base, ""),
                          printer=spec.get("printer"), qty=spec.get("qty")))
    ms, rs = P.MAIN_SPAR, P.REAR_SPAR
    tubes = []
    for sgn, s in ((1, "r"), (-1, "l")):
        out = (0.0, sgn * WING_OUT, 0.0)
        tubes += [tube(f"main_spar_{s}", (ms["x"], sgn * P.Y_ROOT, ms["z"]), (ms["x"], sgn * P.Y_TIP, ms["z"]),
                       ms["od"], ms["id"], out),
                  tube(f"rear_spar_{s}", (rs["x"], sgn * P.Y_ROOT, rs["z"]), (rs["x"], sgn * P.Y_TIP, rs["z"]),
                       rs["od"], rs["id"], out)]
    hj, hr = P.MAIN_JOINER["length"] / 2, P.REAR_JOINER["length"] / 2
    tubes += [tube("main_joiner", (ms["x"], -hj, ms["z"]), (ms["x"], hj, ms["z"]), P.MAIN_JOINER["od"]),
              tube("rear_joiner", (rs["x"], -hr, rs["z"]), (rs["x"], hr, rs["z"]), P.REAR_JOINER["od"]),
              tube("tail_boom", (P.BOOM_X[0], 0, P.BOOM_Z), (P.BOOM_X[1], 0, P.BOOM_Z), P.BOOM_OD, P.BOOM_ID,
                   (TAIL_X, 0.0, 0.0))]
    z_plate = P.Z_PIVOT + P.YOKE_PLATE_Z0 + P.YOKE_PLATE_T
    motors = []
    for sgn, s in ((1, "r"), (-1, "l")):
        pod = wing_burst("boom_pod", s)
        motors.append(dict(name=f"motor_{s}", base=[P.X_PIVOT, sgn * P.BOOM_Y, z_plate], tilt=True,
                           pivot=[P.X_PIVOT, sgn * P.BOOM_Y, P.Z_PIVOT], prop_z=P.MOTOR_BASE_TO_PROP,
                           burst_pivot=[float(pod[0]), float(pod[1]), 70.0], burst_local=[0.0, 0.0, 70.0]))
    motors.append(dict(name="motor_rear", base=[P.X_REAR_MOTOR, 0.0, P.REAR_PLATE_Z + 4.0], tilt=False,
                       prop_z=P.MOTOR_BASE_TO_PROP, burst=[TAIL_X, 0.0, 170.0]))
    import mass_balance
    pin = mass_balance.compute(verbose=False)["pin"]     # battery where the balance puts it
    equipment = []
    for e in PL.equipment(pin):
        e = dict(e, burst=[round(float(v), 2) for v in equipment_burst(e)], tag=LABELS.get(e["name"]))
        if e.get("basis") is not None:
            e["basis"] = [[float(c) for c in row] for row in e["basis"]]
        equipment.append(e)
    routes = [dict(r, pts=[[float(c) for c in p] for p in r["pts"]]) for r in PL.routes(pin)]
    # Nose off, then the battery slides out forward (fractions of the animation).
    nose = {"fuse_1": dict(v=[-260.0, 0.0, 0.0], stage=[0.0, 0.55]),
            "battery": dict(v=[-215.0, 0.0, 0.0], stage=[0.45, 1.0])}
    out = dict(parts=parts, tubes=tubes, motors=motors, prop_d=P.PROP_D, equipment=equipment, routes=routes,
               nose=nose, prints=prints(), tilt_range=[P.TILT_MIN_DEG, P.TILT_MAX_DEG], x_le=P.X_LE,
               y_tip=P.Y_TIP,
               joints_y=[P.Y_ROOT_SEC[0], P.Y_BOOM_RIB[0], P.Y_BOOM_RIB[1], P.Y_MIDTIP_RIB[0],
                         P.Y_MIDTIP_RIB[1], P.Y_TIP_RIB[0]])
    path = os.path.join(G.ROOT, "viewer", "manifest.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {path}: {len(parts)} parts, {len(tubes)} tubes, {len(motors)} motors, "
          f"{len(equipment)} equipment items, {len(routes)} cable runs, {len(out['prints'])} print files")


if __name__ == "__main__":
    main()
