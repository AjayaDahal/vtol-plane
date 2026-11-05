#!/usr/bin/env python3
"""Stress variants of the SITL model installed in a PX4 tree: the premortem's what-ifs
(SIMULATION.md, "Stress tests"). It edits the installed copy only; sim/install.sh puts the
generated model back. Run it after install.sh and before starting PX4:

    sim/install.sh ~/PX4-Autopilot
    python3 sim/variant.py ~/PX4-Autopilot --mass 1.10 --thrust 0.81
    cd ~/PX4-Autopilot && make px4_sitl gz_vtol_plane

--mass K         every link's mass and inertia x K: a heavier build, CG unchanged
--thrust K       every motor's thrust x K (0.81: a near-empty 4S pack, from mass_balance.py)
--wing-a0 DEG    the wing lifts as if set DEG steeper: more lift at a level attitude
--cg-aft MM      the centre of mass MM further aft
--motor-tau MS   the motors' spin-up and spin-down time constants, "up,down" in ms
--moment K       the props' torque x K
--no-airspeed    no airspeed sensor (also set SYS_HAS_NUM_ASPD 0, or PX4 will not arm)
"""
import argparse
import math
import os
import re
import sys

MODEL = "Tools/simulation/gz/models/vtol_plane/model.sdf"


def scale_tag(text, tag, k):
    return re.sub(rf"<{tag}>([-0-9.e+]+)</{tag}>", lambda m: f"<{tag}>{float(m.group(1)) * k:.6g}</{tag}>", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("px4", help="PX4-Autopilot tree that sim/install.sh installed into")
    ap.add_argument("--mass", type=float, default=1.0)
    ap.add_argument("--thrust", type=float, default=1.0)
    ap.add_argument("--wing-a0", type=float, default=0.0)
    ap.add_argument("--cg-aft", type=float, default=0.0)
    ap.add_argument("--motor-tau")
    ap.add_argument("--moment", type=float, default=1.0)
    ap.add_argument("--no-airspeed", action="store_true")
    a = ap.parse_args()
    path = os.path.join(os.path.expanduser(a.px4), MODEL)
    text = open(path).read()
    if "<!-- variant" in text:
        sys.exit(f"{path} is already a variant: run sim/install.sh again first")
    masses = [float(m) for m in re.findall(r"<mass>([-0-9.e+]+)</mass>", text)]
    if a.cg_aft:
        # Move the base link's centre of mass so that the whole aircraft's moves by --cg-aft (model x is forward).
        base = re.search(r"(<link name='base_link'>\s*<inertial><pose>)([-0-9.e+]+)", text)
        dx = -a.cg_aft / 1000 * sum(masses) / masses[0]
        text = text[:base.start(2)] + f"{float(base.group(2)) + dx:.6g}" + text[base.end(2):]
    if a.mass != 1.0:
        for tag in ("mass", "ixx", "ixy", "ixz", "iyy", "iyz", "izz"):
            text = scale_tag(text, tag, a.mass)
    if a.thrust != 1.0:
        text = scale_tag(text, "motorConstant", a.thrust)
    if a.moment != 1.0:
        text = scale_tag(text, "momentConstant", a.moment)
    if a.motor_tau:
        up, down = (float(v) / 1000 for v in a.motor_tau.split(","))
        text = re.sub(r"<timeConstantUp>[^<]+</timeConstantUp>", f"<timeConstantUp>{up:g}</timeConstantUp>", text)
        text = re.sub(r"<timeConstantDown>[^<]+</timeConstantDown>", f"<timeConstantDown>{down:g}</timeConstantDown>",
                      text)
    if a.wing_a0:
        shift = math.radians(a.wing_a0)

        def wing(m):
            return re.sub(r"<a0>([-0-9.e+]+)</a0>", lambda n: f"<a0>{float(n.group(1)) + shift:.6g}</a0>", m.group(0))
        text, n = re.subn(r"<plugin [^\n]*LiftDrag'><!-- wing_[^\n]*", wing, text)
        if n != 6:
            sys.exit(f"expected 6 wing elements, found {n}")
    if a.no_airspeed:
        text, n = re.subn(r"<sensor name='air_speed'.*?</sensor>", "", text, flags=re.S)
        if n != 1:
            sys.exit("no airspeed sensor found")
    defaults = {"mass": 1.0, "thrust": 1.0, "wing_a0": 0.0, "cg_aft": 0.0, "motor_tau": None, "moment": 1.0,
                "no_airspeed": False}
    note = " ".join(f"{k}={v}" for k, v in vars(a).items() if k in defaults and v != defaults[k])
    text = text.replace("<sdf version", f"<!-- variant: {note} -->\n<sdf version", 1)
    open(path, "w").write(text)
    print(f"variant written to {path}: {note or 'unchanged'} (mass {sum(masses) * a.mass:.3f} kg)")


if __name__ == "__main__":
    main()
