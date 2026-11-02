"""Write viewer/manifest.json for the three.js viewer (viewer/index.html) from params.py.

Lists every assembly STL with its material, plus the carbon tubes, motors and props, which
have no STL. build_all.py runs this; then `python scripts/serve_viewer.py` and open
http://127.0.0.1:28765/viewer/
"""
import json
import os

import geom as G
import params as P

LOOSE = {"servo_cage", "control_horn"}          # print-only parts modelled at the origin
LWPLA = ("wing_", "aileron_", "fuse_", "vtail_l", "vtail_r", "ruddervator_")


def tube(name, a, b, od, idd=0.0):
    return dict(name=name, a=list(map(float, a)), b=list(map(float, b)), od=od, id=idd)


def main():
    parts = []
    for f in sorted(os.listdir(G.ASSEMBLY)):
        name = f[:-4]
        if not f.endswith(".stl") or name in LOOSE:
            continue
        mat = "lwpla" if name.startswith(LWPLA) and not name.startswith(("vtail_root", "vtail_tip")) else "petg"
        side = "r" if name.endswith("_r") else "l" if name.endswith("_l") else "c"
        group = "skin" if mat == "lwpla" else "structure"
        tilt = name.startswith("yoke_")
        parts.append(dict(name=name, url=f"../parts/assembly/{f}", material=mat, side=side, group=group,
                          tilt=tilt))
    ms, rs = P.MAIN_SPAR, P.REAR_SPAR
    tubes = []
    for sgn, s in ((1, "r"), (-1, "l")):
        tubes += [tube(f"main_spar_{s}", (ms["x"], sgn * P.Y_ROOT, ms["z"]), (ms["x"], sgn * P.Y_TIP, ms["z"]),
                       ms["od"], ms["id"]),
                  tube(f"rear_spar_{s}", (rs["x"], sgn * P.Y_ROOT, rs["z"]), (rs["x"], sgn * P.Y_TIP, rs["z"]),
                       rs["od"], rs["id"])]
    hj, hr = P.MAIN_JOINER["length"] / 2, P.REAR_JOINER["length"] / 2
    tubes += [tube("main_joiner", (ms["x"], -hj, ms["z"]), (ms["x"], hj, ms["z"]), P.MAIN_JOINER["od"]),
              tube("rear_joiner", (rs["x"], -hr, rs["z"]), (rs["x"], hr, rs["z"]), P.REAR_JOINER["od"]),
              tube("tail_boom", (P.BOOM_X[0], 0, P.BOOM_Z), (P.BOOM_X[1], 0, P.BOOM_Z), P.BOOM_OD, P.BOOM_ID)]
    z_plate = P.Z_PIVOT + P.YOKE_PLATE_Z0 + P.YOKE_PLATE_T
    motors = [dict(name=f"motor_{s}", base=[P.X_PIVOT, sgn * P.BOOM_Y, z_plate], tilt=True,
                   pivot=[P.X_PIVOT, sgn * P.BOOM_Y, P.Z_PIVOT], prop_z=P.MOTOR_BASE_TO_PROP)
              for sgn, s in ((1, "r"), (-1, "l"))]
    motors.append(dict(name="motor_rear", base=[P.X_REAR_MOTOR, 0.0, P.REAR_PLATE_Z + 4.0], tilt=False,
                       prop_z=P.MOTOR_BASE_TO_PROP))
    out = dict(parts=parts, tubes=tubes, motors=motors, prop_d=P.PROP_D,
               tilt_range=[P.TILT_MIN_DEG, P.TILT_MAX_DEG], x_le=P.X_LE, y_tip=P.Y_TIP,
               joints_y=[P.Y_ROOT_SEC[0], P.Y_BOOM_RIB[0], P.Y_BOOM_RIB[1], P.Y_MIDTIP_RIB[0],
                         P.Y_MIDTIP_RIB[1], P.Y_TIP_RIB[0]])
    path = os.path.join(G.ROOT, "viewer", "manifest.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {path}: {len(parts)} parts, {len(tubes)} tubes, {len(motors)} motors")


if __name__ == "__main__":
    main()
