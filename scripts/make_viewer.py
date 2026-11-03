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
import plates as PT
from make_print_ready import PARTS

LOOSE = {"servo_hatch", "hatch_block", "control_horn"}   # modelled at the origin; hatches placed as instances
# Parts sealed inside the airframe, left out of the exterior model (renders/vtol_plane.stl): GitHub's
# 3-D viewer draws one opaque colour, so they would only add size (it shows files up to 10 MB).
INSIDE = {"battery_tray", "boom_cup_l", "boom_cup_r", "coupler_240", "coupler_370", "coupler_610", "fc_shelf",
          "frame_main", "frame_rear", "pod_collar", "rib_tip_l", "rib_tip_r", "vtail_tip_cap_l", "vtail_tip_cap_r"}
LWPLA = ("wing_", "aileron_", "fuse_", "vtail_l", "vtail_r", "ruddervator_", "tip_fairing_", "vtail_tip_fairing_")
BED = {"s1": 250.0, "x": 260.0}

ROLE = {
    "fuse_1": "removable nose, one M3 nylon screw: the access opening",
    "coupler_240": "nose joint, heat-set insert for the nose screw",
    "fuse_2": "battery and avionics bay",
    "fc_shelf": "Pixhawk on top; the ESC block and small boards hang underneath",
    "battery_tray": "battery tray: stop-pin holes, two strap loops round the battery",
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
    "rib_tip": "hidden tip ring: the spar ends; the tip skin and the tip fairing butt over it",
    "tip_fairing": "wing tip fairing: the top surface comes down to the flat bottom (Hoerner tip)",
    "wing_root": "wing skin with internal webs",
    "wing_mid": "wing skin with internal webs",
    "wing_tip": "wing skin with internal webs",
    "aileron_mid": "aileron",
    "aileron_tip": "aileron",
    "vtail": "V-tail panel",
    "ruddervator": "ruddervator",
    "vtail_root_rib": "V-tail root rib (carbon pin into the tail block)",
    "vtail_tip_cap": "hidden V-tail tip ring: the panel and its tip fairing butt over it",
    "vtail_tip_fairing": "V-tail tip fairing",
    "servo_hatch": "removable servo hatch: the servo screws to its posts, 2 M2 screws hold it in",
    "hatch_block": "glued inside the skin at a hatch end; the hatch's M2 screw goes into it",
    "control_horn": "control horn",
}

# Burst view: the fuselage spreads along x from fuse_3 (which carries the wing), each wing slides
# out along the span with every joint opened, the inserts and equipment lift out of the
# fuselage, and the tail slides off the end of the boom.
WING_OUT, WING_GAP = 150.0, 60.0
WING_ORDER = {"rib_root": 0, "wing_root": 1, "boom_cup": 2, "boom_rib": 3, "boom_pod": 3, "wing_mid": 4,
              "aileron_mid": 4, "rib_midtip": 5, "wing_tip": 6, "aileron_tip": 6, "rib_tip": 7, "tip_fairing": 8}
FUSE_X = {"fuse_1": -330.0, "coupler_240": -210.0, "fuse_2": -120.0, "coupler_370": -55.0, "fuse_3": 0.0,
          "coupler_610": 90.0, "fuse_4": 170.0, "pod_collar": 260.0}
IN_FUSE_2 = FUSE_X["fuse_2"]
LIFT = {"fc_shelf": (IN_FUSE_2, 190.0), "battery_tray": (IN_FUSE_2, -170.0), "frame_main": (0.0, 190.0),
        "frame_rear": (0.0, 190.0), "gps_mount": (0.0, 110.0)}
TAIL_X = 430.0
POD_OUT = -80.0
VT_OUT = {"vtail_root_rib": 40.0, "vtail": 100.0, "ruddervator": 100.0, "vtail_tip_cap": 170.0,
          "vtail_tip_fairing": 230.0}


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


def hatch_base(h):
    """Burst offset of the wing section or V-tail panel a servo hatch sits in."""
    side = h["name"].split("_")[1][0]
    if h["where"] == "wing":
        return wing_burst("wing_mid" if abs(h["origin"][1]) < P.Y_MID_SEC[1] else "wing_tip", side)
    return vt_burst("vtail", side)


HATCHES = {h["name"]: h for h in PL.servo_hatches()}
HATCH_OUT = 50.0       # burst: a hatch cover and its servo come this far out of the skin
SVC_OUT = 55.0         # service view: the same, with everything else in place


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
    if e.get("hatch"):
        h = HATCHES[e["hatch"]]
        return hatch_base(h) - HATCH_OUT * np.array(h["n"])
    side = n[-1]
    sgn = 1.0 if side == "r" else -1.0
    if n.startswith("tilt_servo"):
        return wing_burst("boom_pod", side) + (0.0, -sgn * 45.0, 0.0)
    if n.startswith("tilt_plug"):
        return wing_burst("boom_pod", side) + (0.0, -sgn * 25.0, -20.0)
    return np.zeros(3)


def hatch_instances():
    """The loose hatch parts placed in the aircraft: a cover and two blocks per servo hatch."""
    out = []
    for h in HATCHES.values():
        a, b, n = (np.array(h[k]) for k in ("a", "b", "n"))
        base = hatch_base(h)
        out.append(dict(name=f"servo_hatch@{h['name']}", src="servo_hatch", basis=[a, b, n], origin=h["origin"],
                        burst=base - HATCH_OUT * n, role=ROLE["servo_hatch"]))
        for sgn, end in ((1, "+"), (-1, "-")):
            out.append(dict(name=f"hatch_block@{h['name']}{end}", src="hatch_block",
                            basis=[sgn * a, sgn * b, n], origin=h["origin"], burst=base, role=ROLE["hatch_block"]))
    return [dict(i, basis=[[float(c) for c in v] for v in i["basis"]], origin=[float(c) for c in i["origin"]],
                 burst=[round(float(c), 2) for c in i["burst"]], url=f"../parts/assembly/{i['src']}.stl",
                 material="petg") for i in out]


def service_moves():
    """Service view: every servo hatch comes out with its servo, then each yoke lifts off its pod
    and the tilt servo slides out of its bay. Fractions of the animation in `stage`."""
    moves = {}
    for h in HATCHES.values():
        v = [round(float(c), 2) for c in -SVC_OUT * np.array(h["n"])]
        moves[f"servo_hatch@{h['name']}"] = dict(v=v, stage=[0.0, 0.45])
        moves[f"servo_{h['name']}"] = dict(v=v, stage=[0.0, 0.45])
    for sgn, s in ((1, "r"), (-1, "l")):
        moves[f"pivot_{s}"] = dict(v=[0.0, 0.0, 80.0], stage=[0.3, 0.7])
        moves[f"tilt_servo_{s}"] = dict(v=[0.0, -sgn * 40.0, 0.0], stage=[0.65, 1.0])
    return moves


# One label per kind of item; the duplicates stay unlabelled.
LABELS = {"battery": "4S 5000 mAh LiPo", "esc_1": "3 x ESC 50 A", "fc": "Pixhawk 6C",
          "power_module": "power module", "bec": "servo BEC", "airspeed": "airspeed sensor",
          "receiver": "ELRS receiver", "gps": "GPS + compass", "pitot": "pitot tube",
          "tilt_servo_r": "tilt servo (x2)", "tilt_plug_r": "tilt-servo plug pocket",
          "servo_aileron_r325": "aileron servo on its hatch (x4)",
          "servo_ruddervator_r": "ruddervator servo on its hatch (x2)"}


def tube(name, a, b, od, idd=0.0, ex=(0.0, 0.0, 0.0)):
    return dict(name=name, a=list(map(float, a)), b=list(map(float, b)), od=od, id=idd,
                burst=[float(v) for v in ex])


def _cylinder(a, b, r, n=24):
    """Closed cylinder from a to b, faces wound outward."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    w = (b - a) / np.linalg.norm(b - a)
    u = np.cross(w, [1.0, 0.0, 0.0] if abs(w[0]) < 0.9 else [0.0, 1.0, 0.0])
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    t = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    ring = r * (np.cos(t)[:, None] * u + np.sin(t)[:, None] * v)
    p, q = a + ring, b + ring
    out = []
    for i in range(n):
        j = (i + 1) % n
        out += [[p[i], p[j], q[j]], [p[i], q[j], q[i]], [a, p[j], p[i]], [b, q[i], q[j]]]
    return np.array(out)


def _box(c, axes, half):
    """Box centred on c along right-handed unit axes, half-sizes `half`, faces wound outward."""
    c = np.asarray(c, float)
    e = [np.asarray(x, float) * h for x, h in zip(axes, half)]
    out = []
    for k in range(3):
        i, j = (k + 1) % 3, (k + 2) % 3
        for s in (1, -1):
            f = [c + s * e[k] - e[i] - e[j], c + s * e[k] + e[i] - e[j], c + s * e[k] + e[i] + e[j],
                 c + s * e[k] - e[i] + e[j]]
            out += [[f[0], f[1], f[2]], [f[0], f[2], f[3]]] if s > 0 else [[f[0], f[2], f[1]], [f[0], f[3], f[2]]]
    return np.array(out)


def exterior_model(motors, tubes):
    """The outside of the assembled aircraft in hover, as one mesh: every part that shows, the tail
    boom, and the motors and two-blade props drawn simply. README.md links it: GitHub shows
    renders/vtol_plane.stl in its 3-D viewer."""
    tris = [G.read_stl(os.path.join(G.ASSEMBLY, f)).reshape(-1, 3, 3) for f in sorted(os.listdir(G.ASSEMBLY))
            if f.endswith(".stl") and f[:-4] not in LOOSE | INSIDE]
    boom = next(t for t in tubes if t["name"] == "tail_boom")
    tris.append(_cylinder(boom["a"], boom["b"], boom["od"] / 2, 32))
    z, r = np.array([0.0, 0.0, 1.0]), P.PROP_D / 2
    for m in motors:
        b, h = np.asarray(m["base"], float), m["prop_z"]
        tris += [_cylinder(b, b + 6 * z, 14), _cylinder(b + 6 * z, b + 30 * z, 17),
                 _cylinder(b + 30 * z, b + (h + 3.5) * z, 2.5, 12), _cylinder(b + (h - 3.5) * z, b + (h + 3.5) * z, 6)]
        d = np.array([math.cos(math.radians(30)), math.sin(math.radians(30)), 0.0])
        for s in (1, -1):
            tris.append(_box(b + h * z + s * d * (r + 4) / 2, (d, np.cross(z, d), z), ((r - 4) / 2, 7.0, 0.8)))
    return np.concatenate(tris)


def gcode_stats(name):
    """Sliced filament mass (g) and print time (min) from a part's or a plate's G-code, if it exists."""
    if name in PT.PLATES:
        path = PT.gcode_path(name)
    else:
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


def plates():
    """The PETG plates: each placed copy (bed coordinates, turn about z) and the sliced totals."""
    out = []
    for plate, items in PT.PLATES.items():
        grams, minutes = gcode_stats(plate)
        out.append(dict(name=plate, printer=PT.PRINTER, material="petg", bed=BED[PT.PRINTER],
                        contents=[[name, copies] for name, copies in items],
                        parts=[dict(part=name, copy=k, x=x, y=y, angle=a) for name, k, x, y, a in PT.layout(plate)],
                        grams=grams, minutes=None if minutes is None else round(minutes, 1)))
    return out


def main():
    parts = []
    for f in sorted(os.listdir(G.ASSEMBLY)):
        name = f[:-4]
        if not f.endswith(".stl") or name in LOOSE:
            continue
        mat = "lwpla" if name.startswith(LWPLA) and not name.startswith(("vtail_root_rib", "vtail_tip_cap")) else "petg"
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
               nose=nose, instances=hatch_instances(), service=service_moves(), prints=prints(), plates=plates(),
               tilt_range=[P.TILT_MIN_DEG, P.TILT_MAX_DEG], x_le=P.X_LE, y_tip=P.Y_TIP,
               joints_y=[P.Y_ROOT_SEC[0], P.Y_BOOM_RIB[0], P.Y_BOOM_RIB[1], P.Y_MIDTIP_RIB[0],
                         P.Y_MIDTIP_RIB[1], P.Y_TIP_SEC[1]])
    path = os.path.join(G.ROOT, "viewer", "manifest.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {path}: {len(parts)} parts, {len(out['instances'])} hatch parts placed, {len(tubes)} tubes, "
          f"{len(motors)} motors, {len(equipment)} equipment items, {len(routes)} cable runs, "
          f"{len(out['prints'])} print files, {len(out['plates'])} PETG plates")
    model = exterior_model(motors, tubes)
    path = os.path.join(G.ROOT, "renders", "vtol_plane.stl")
    G.write_stl(path, model)
    print(f"wrote {path}: {len(model)} triangles, {os.path.getsize(path) / 1e6:.1f} MB (GitHub shows up to 10 MB)")


if __name__ == "__main__":
    main()
