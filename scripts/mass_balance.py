"""Mass, CG, hover thrust split, endurance and airspeed numbers for DESIGN.md.

Printed-part masses come from the sliced G-code when it exists (else an estimate from the
mesh); positions come from the assembly-frame STLs. Purchased parts are listed in ITEMS.
"""
import math
import os
import re

import numpy as np

import geom as G
import params as P
from make_print_ready import PARTS

G0 = 9.81
CG_TARGET = 0.27                  # fraction of MAC
CG_BAND = (0.25, 0.30)
BATTERY = dict(name="4S 5000 mAh LiPo", mass=520.0, length=155.0)
# Emax ECOII 2807 1700KV (Emax's 4S winding), 7-in 2-blade: 1810 g max at 16.8 V on the data
# sheet; ~1550 g on a loaded full pack and ~1250 g near empty (thrust ~ voltage squared).
T_MAX_FULL, T_MAX_EMPTY = 1550.0, 1250.0
P_COEF, P_OFFSET = 0.0090, 4.0   # hover power per motor [W] = P_COEF * T[g]^1.5 + P_OFFSET (data-sheet fit)
V_PACK, PACK_AH, USABLE = 14.8, 5.0, 0.8
AVIONICS_W = 8.0
RHO = {"sea level 15 C": 1.225, "Austin 35 C": 1.12}


def tube_g_per_mm(od, idd=0.0, density=1.55e-3):
    return math.pi / 4 * (od ** 2 - idd ** 2) * density


_z_motor = P.YOKE_PLATE_Z0 + P.YOKE_PLATE_T + 16.0
_z_prop = P.YOKE_PLATE_Z0 + P.YOKE_PLATE_T + P.MOTOR_BASE_TO_PROP
ITEMS = [  # name, mass each [g], qty, x in fixed-wing config, x in hover config
    ("front motor Emax ECOII 2807 1700KV", 50.0, 2, P.X_PIVOT - _z_motor, P.X_PIVOT),
    ("front prop 7x4.5", 8.0, 2, P.X_PIVOT - _z_prop, P.X_PIVOT),
    ("front ESC 50 A (in root section)", 11.0, 2, 450.0, 450.0),
    ("tilt servo KM1203MD (20 g)", 20.0, 2, P.X_PIVOT + 6.0, P.X_PIVOT + 6.0),
    ("rear motor Emax ECOII 2807 1700KV", 50.0, 1, P.X_REAR_MOTOR, P.X_REAR_MOTOR),
    ("rear prop 7x4.5", 8.0, 1, P.X_REAR_MOTOR, P.X_REAR_MOTOR),
    ("rear ESC 50 A (pod tail)", 11.0, 1, 700.0, 700.0),
    ("aileron servo 9 g", 9.0, 4, 455.0, 455.0),
    ("V-tail servo 9 g", 9.0, 2, P.VT_X_LE + 55.0, P.VT_X_LE + 55.0),
    ("Pixhawk 6C", 59.3, 1, 305.0, 305.0),
    ("GPS + compass (M10)", 32.0, 1, 560.0, 560.0),
    ("ELRS receiver", 3.0, 1, 330.0, 330.0),
    ("airspeed sensor, pitot, tubing", 15.0, 1, 400.0, 400.0),
    ("power module PM02", 20.0, 1, 255.0, 255.0),
    ("wiring, connectors, extensions", 70.0, 1, 450.0, 450.0),
    ("main spars 10x8 carbon, 2 x 650 mm", 650 * tube_g_per_mm(10, 8), 2, P.MAIN_SPAR["x"], P.MAIN_SPAR["x"]),
    ("rear spars 6x4 carbon, 2 x 650 mm", 650 * tube_g_per_mm(6, 4), 2, P.REAR_SPAR["x"], P.REAR_SPAR["x"]),
    ("main joiner 8x6 carbon, 420 mm", 420 * tube_g_per_mm(8, 6), 1, P.MAIN_SPAR["x"], P.MAIN_SPAR["x"]),
    ("rear joiner 4 mm carbon rod, 320 mm", 320 * tube_g_per_mm(4, 0, 1.6e-3), 1, P.REAR_SPAR["x"],
     P.REAR_SPAR["x"]),
    ("tail boom 16x14 carbon, 630 mm", 630 * tube_g_per_mm(16, 14), 1, sum(P.BOOM_X) / 2, sum(P.BOOM_X) / 2),
    ("V-tail pins 4 mm carbon, 2 x 20 mm", 20 * tube_g_per_mm(4, 0, 1.6e-3), 2, P.VT_X_LE + 54, P.VT_X_LE + 54),
    ("bearings, bolts, inserts, pins", 20.0, 1, 450.0, 450.0),
    ("glue (epoxy + CA) and hinge tape", 35.0, 1, 470.0, 470.0),
]
LOOSE_X = {"servo_cage": [455.0] * 4 + [P.VT_X_LE + 55.0] * 2,
           "control_horn": [535.0] * 4 + [P.VT_X_LE + 135.0] * 2}


def gcode_mass(name):
    spec = PARTS[name]
    folder = f"{spec['printer']}_{'lwpla' if spec['material'].startswith('lwpla') else 'petg'}"
    path = os.path.join(G.ROOT, "gcode", folder, name + ".gcode")
    if not os.path.exists(path):
        return None
    with open(path, "r", errors="replace") as f:
        f.seek(max(0, os.path.getsize(path) - 200_000))
        m = re.search(r"; total filament used \[g\] = ([\d.]+)", f.read())
    return float(m.group(1)) if m else None


def estimate_mass(name, tris):
    if PARTS[name]["material"].startswith("lwpla"):
        area = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1).sum()
        return area * 0.42 * 0.55 * 1.24e-3
    return G.signed_volume(tris) * 1.27e-3 * 0.6


def printed_parts():
    rows = []
    for name, spec in sorted(PARTS.items()):
        src = spec["src"] or name
        mass = gcode_mass(name)
        if name in LOOSE_X:
            xs = LOOSE_X[name]
            m = mass if mass is not None else estimate_mass(name, G.read_stl(os.path.join(G.PRINT, name + ".stl")))
            rows += [(name, m, 1, x, x, mass is not None) for x in xs]
            continue
        tris = G.read_stl(os.path.join(G.ASSEMBLY, src + ".stl"))
        if mass is None:
            m, measured = estimate_mass(name, tris), False
        else:
            m, measured = mass, True
        c = tris.mean(axis=1)
        w = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
        x = float((c[:, 0] * w).sum() / w.sum())
        rows.append((name, m, spec["qty"], x, x, measured))
    return rows


def compute(verbose=True):
    mac = 2 / 3 * P.ROOT_CHORD * (1 + (lam := P.TIP_CHORD / P.ROOT_CHORD) + lam ** 2) / (1 + lam)
    x_cg_target = P.X_LE + CG_TARGET * mac
    rows = [(n, m, q, xf, xh, True) for n, m, q, xf, xh in ITEMS] + printed_parts()
    m0 = sum(m * q for _, m, q, *_ in rows)
    mx_fw = sum(m * q * xf for _, m, q, xf, _, _ in rows)
    mx_h = sum(m * q * xh for _, m, q, _, xh, _ in rows)
    mb = BATTERY["mass"]
    auw = m0 + mb
    x_b = (x_cg_target * auw - mx_fw) / mb
    x_cg_h = (mx_h + mb * x_b) / auw
    x_f, x_r = P.X_PIVOT, P.X_REAR_MOTOR
    t_rear = auw * (x_cg_h - x_f) / (x_r - x_f)
    t_front = (auw - t_rear) / 2
    p_motor = lambda t: P_COEF * t ** 1.5 + P_OFFSET
    p_hover = 2 * p_motor(t_front) + p_motor(t_rear) + AVIONICS_W
    i_hover = p_hover / V_PACK
    s_gross = (P.ROOT_CHORD + P.TIP_CHORD) / 2 * (P.Y_TIP - P.Y_ROOT) * 2 + 2 * P.Y_ROOT * P.ROOT_CHORD
    s_m2 = s_gross / 1e6
    w_n = auw / 1000 * G0
    stall = {(cl, k): math.sqrt(2 * w_n / (rho * s_m2 * cl)) for cl in (1.0, 1.1, 1.2) for k, rho in RHO.items()}
    v_stall = stall[(1.0, "Austin 35 C")]
    # V-tail effectiveness with the cos^2/sin^2 projection; straight LE so MAC LE = panel LE.
    lam_t = P.VT_TIP_CHORD / P.VT_ROOT_CHORD
    mac_t = 2 / 3 * P.VT_ROOT_CHORD * (1 + lam_t + lam_t ** 2) / (1 + lam_t)
    s_vt = (P.VT_ROOT_CHORD + P.VT_TIP_CHORD) / 2 * P.VT_SPAN * 2
    d = math.radians(P.VT_DIHEDRAL)
    arm = (P.VT_X_LE + 0.25 * mac_t) - (P.X_LE + 0.25 * mac)
    vh = s_vt * math.cos(d) ** 2 * arm / (s_gross * mac)
    vv = s_vt * math.sin(d) ** 2 * arm / (s_gross * 2 * P.Y_TIP)
    x_np = P.X_LE + 0.25 * mac + mac * vh * 0.75 * 0.6
    rear_end = x_b + BATTERY["length"] / 2
    stop = rear_end
    battery_ok = rear_end <= P.BOOM_X[0] - 5 and P.TRAY_X[0] <= stop <= P.TRAY_X[1] + 50
    r = dict(
        auw=auw, mass_ex_battery=m0, mac=mac, x_cg=x_cg_target, x_cg_hover=x_cg_h, x_battery=x_b,
        cg_band=(P.X_LE + CG_BAND[0] * mac, P.X_LE + CG_BAND[1] * mac),
        t_front=t_front, t_rear=t_rear, front_share=t_front / auw, rear_share=t_rear / auw,
        front_frac_max=t_front / T_MAX_EMPTY, throttle_front=math.sqrt(t_front / T_MAX_FULL),
        p_hover=p_hover, i_hover=i_hover, hover_min=USABLE * PACK_AH / i_hover * 60,
        s_m2=s_m2, wing_loading=auw / (s_m2 * 100), stall=stall, v_stall=v_stall,
        fw_min=math.ceil(1.25 * v_stall), vh=vh, vv=vv, arm=arm, x_np=x_np,
        static_margin=(x_np - x_cg_target) / mac, battery_ok=battery_ok,
        battery_note=f"centre x={x_b:.0f}, rear end x={rear_end:.0f} (boom starts {P.BOOM_X[0]:.0f}; "
                     f"rear stop pin goes at x={stop:.0f})",
        rows=rows,
    )
    if verbose:
        report(r)
    return r


def report(r):
    measured = all(row[5] for row in r["rows"])
    print("## Mass and balance (generated by scripts/mass_balance.py)\n")
    print(f"Printed-part masses: {'sliced G-code' if measured else 'ESTIMATED from meshes (slice to update)'}.\n")
    print("| Item | Qty | Mass each (g) | x FW (mm) | x hover (mm) |")
    print("|---|---|---|---|---|")
    for n, m, q, xf, xh, _ in sorted(r["rows"], key=lambda row: row[3]):
        print(f"| {n} | {q} | {m:.1f} | {xf:.0f} | {xh:.0f} |")
    print(f"| {BATTERY['name']} | 1 | {BATTERY['mass']:.0f} | {r['x_battery']:.0f} | {r['x_battery']:.0f} |")
    print()
    print(f"- All-up weight: **{r['auw']:.0f} g** ({r['mass_ex_battery']:.0f} g without battery).")
    print(f"- MAC {r['mac']:.1f} mm, LE at x={P.X_LE:.0f}. CG target 27 % MAC = **x={r['x_cg']:.0f} mm** "
          f"(25-30 % band x={r['cg_band'][0]:.0f}-{r['cg_band'][1]:.0f}); hover CG x={r['x_cg_hover']:.0f}.")
    print(f"- Battery centre for that CG: **x={r['x_battery']:.0f} mm** ({r['battery_note']}).")
    print(f"- Hover thrust: front {r['t_front']:.0f} g each ({100 * r['front_share']:.0f} %), "
          f"rear {r['t_rear']:.0f} g ({100 * r['rear_share']:.0f} %).")
    print(f"- Front motor at hover: {100 * r['t_front'] / T_MAX_FULL:.0f} % of max on a full pack, "
          f"{100 * r['front_frac_max']:.0f} % near empty; throttle ~{100 * r['throttle_front']:.0f} %.")
    print(f"- Hover power ~{r['p_hover']:.0f} W, ~{r['i_hover']:.0f} A -> **~{r['hover_min']:.1f} min** "
          f"pure hover on 80 % of a 4S 5000 (estimate).")
    print(f"- Wing area {r['s_m2']:.3f} m2 (gross), loading {r['wing_loading']:.0f} g/dm2.")
    print("- Stall speed (m/s): " + ", ".join(
        f"CL {cl} {k}: {v:.1f}" for (cl, k), v in sorted(r['stall'].items())))
    print(f"- Tail: arm {r['arm']:.0f} mm, Vh {r['vh']:.2f}, Vv {r['vv']:.3f}; "
          f"neutral point ~x={r['x_np']:.0f}, static margin ~{100 * r['static_margin']:.0f} % MAC.")
    print(f"- Suggested PX4: FW_AIRSPD_STALL {math.ceil(r['v_stall'])}, FW_AIRSPD_MIN {r['fw_min']}, "
          f"VT_ARSP_TRANS {r['fw_min'] + 2}.")


if __name__ == "__main__":
    compute()
