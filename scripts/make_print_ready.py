"""Rotate assembly-frame STLs into print orientation (proper rotations only) and hold the print table.

The print table is the single list of what gets printed, on which printer, with which
slicer process, and how many copies. slice_all.py and mass_balance.py read it.
"""
import os

import numpy as np

import geom as G

LW, PETG, PETG_SUP = "lwpla_vase", "petg", "petg_support"


def _p(material, printer, rot, qty=1, src=None):
    return dict(material=material, printer=printer, rot=rot, qty=qty, src=src)


PARTS = {
    # LW-PLA skins: right-hand set on the S1, left-hand set on the X.
    "fuse_1": _p(LW, "s1", [("y", 90)]),
    "fuse_2": _p(LW, "x", [("y", -90)]),
    "fuse_3": _p(LW, "s1", [("y", -90)]),
    "fuse_4": _p(LW, "x", [("y", -90)]),
    "vtail_r": _p(LW, "s1", [("x", 55)]),
    "vtail_l": _p(LW, "x", [("x", -55)]),
    "ruddervator_r": _p(LW, "s1", [("x", 55)]),
    "ruddervator_l": _p(LW, "x", [("x", -55)]),
    # PETG structure: all on the enclosed S1. Ribs lie on a flange or ring end so the
    # spigot rings print as vertical walls (upright they would be 10 mm overhangs).
    "rib_root_r": _p(PETG, "s1", [("x", 90)]),
    "rib_root_l": _p(PETG, "s1", [("x", -90)]),
    "rib_midtip_r": _p(PETG, "s1", [("x", 90)]),
    "rib_midtip_l": _p(PETG, "s1", [("x", -90)]),
    # The tip rib is a hidden ring: it stands on its fairing end, the full-chord side.
    "rib_tip_r": _p(PETG, "s1", [("x", -90)]),
    "rib_tip_l": _p(PETG, "s1", [("x", 90)]),
    # Boom rib prints flat on its inboard face; its inboard spigot ring is the separate cup.
    "boom_rib_r": _p(PETG, "s1", [("x", 90), ("z", 45)]),
    "boom_rib_l": _p(PETG, "s1", [("x", -90), ("z", 45)]),
    "boom_cup_r": _p(PETG, "s1", [("x", -90)]),
    "boom_cup_l": _p(PETG, "s1", [("x", 90)]),
    # Pod prints upright: the gusset and nose chamfer are 45 deg, the slot and bay are bridges.
    "boom_pod_r": _p(PETG, "s1", []),
    "boom_pod_l": _p(PETG, "s1", []),
    "yoke_r": _p(PETG, "s1", [("x", 180)]),
    "yoke_l": _p(PETG, "s1", [("x", 180)]),
    "coupler_240": _p(PETG, "s1", [("y", -90)]),
    "coupler_370": _p(PETG, "s1", [("y", -90)]),
    "coupler_610": _p(PETG, "s1", [("y", -90)]),
    "frame_main": _p(PETG, "s1", [("y", 90)]),
    "frame_rear": _p(PETG, "s1", [("y", 90)]),
    "fc_shelf": _p(PETG, "s1", []),
    "battery_tray": _p(PETG, "s1", [("x", 180)]),
    # Top plate on the bed; the skirt's skin-following edge is the last layer.
    "gps_mount": _p(PETG, "s1", [("x", 180)]),
    "pod_collar": _p(PETG, "s1", [("y", -90)]),
    # Constant section along the boom: stands on an end, bore vertical, no supports.
    "rear_motor_mount": _p(PETG, "s1", [("y", 90)]),
    "tail_block": _p(PETG, "s1", [("y", -90)]),
    "vtail_root_rib": _p(PETG, "s1", [("x", 55)], qty=2, src="vtail_root_rib_r"),
    # Hidden tip rings stand on their fairing end, like the wing's tip rib.
    "vtail_tip_cap": _p(PETG, "s1", [("x", 235)], qty=2, src="vtail_tip_cap_r"),
    # V-tail tip fairing: symmetric, one file for both sides, root down like the panels.
    "vtail_tip_fairing": _p(LW, "x", [("x", 55)], qty=2, src="vtail_tip_fairing_r"),
    # Servo hatch: outer face on the bed, posts up. Hatch block: upside down, top face on the bed.
    "servo_hatch": _p(PETG, "s1", [], qty=6),
    "hatch_block": _p(PETG, "s1", [("x", 180)], qty=12),
    "control_horn": _p(PETG, "s1", [], qty=6),
}
for _sec in ("wing_root", "wing_mid", "wing_tip", "aileron_mid", "aileron_tip", "tip_fairing"):
    PARTS[_sec + "_r"] = _p(LW, "s1", [("x", 90)])
    PARTS[_sec + "_l"] = _p(LW, "x", [("x", -90)])


def print_mesh(name):
    spec = PARTS[name]
    tris = G.read_stl(os.path.join(G.ASSEMBLY, (spec["src"] or name) + ".stl"))
    R = np.eye(3)
    for axis, deg in spec["rot"]:
        R = G.rotation(axis, deg) @ R
    assert abs(np.linalg.det(R) - 1.0) < 1e-9, "print orientation must be a proper rotation"
    tris = G.transform(tris, R)
    v = tris.reshape(-1, 3)
    lo, hi = v.min(0), v.max(0)
    return G.transform(tris, None, (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))


def build():
    os.makedirs(G.PRINT, exist_ok=True)
    for f in os.listdir(G.PRINT):
        if f.endswith(".stl"):
            os.remove(os.path.join(G.PRINT, f))
    for name in sorted(PARTS):
        tris = print_mesh(name)
        G.write_stl(os.path.join(G.PRINT, name + ".stl"), tris)
        v = tris.reshape(-1, 3)
        ext = v.max(0) - v.min(0)
        print(f"{name:18s} {PARTS[name]['material']:12s} {PARTS[name]['printer']:3s} x{PARTS[name]['qty']}  "
              f"{ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:6.1f} mm")


if __name__ == "__main__":
    build()
