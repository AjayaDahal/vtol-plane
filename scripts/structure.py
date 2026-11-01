"""PETG structure in the aircraft frame (build123d): wing ribs, boom ribs and pods, tilt yokes,
couplers, frames, shelf, tray, pod collar, rear motor mount, tail block, V-tail ribs, cages, horns.

Writes parts/assembly/*.stl. Left-hand parts are y-mirrors of the right-hand ones.
"""
import math
import os

import numpy as np
from build123d import (Axis, Box, Cylinder, Face, Keep, Plane, Pos, Rot, Vector, Wire,
                       export_stl, extrude, loft, mirror, split)

import geom as G
import params as P
from skins import vt_chord, vt_frame

L = P.SPIGOT_LEN


# --- small helpers ------------------------------------------------------------
def poly_face(pts):
    return Face(Wire.make_polygon([Vector(*map(float, p)) for p in pts], close=True))


def prism_y(loop_xz, y0, y1):
    lo, hi = min(y0, y1), max(y0, y1)
    face = poly_face([(x, lo, z) for x, z in loop_xz])
    return extrude(face, amount=hi - lo, dir=(0, 1, 0))


def prism_x(loop_yz, x0, x1):
    face = poly_face([(x0, y, z) for y, z in loop_yz])
    return extrude(face, amount=x1 - x0, dir=(1, 0, 0))


def cyl_y(r, x, z, y0, y1):
    lo, hi = min(y0, y1), max(y0, y1)
    return Pos(x, (lo + hi) / 2, z) * Rot(90, 0, 0) * Cylinder(r, hi - lo)


def cyl_x(r, y, z, x0, x1):
    return Pos((x0 + x1) / 2, y, z) * Rot(0, 90, 0) * Cylinder(r, x1 - x0)


def cyl_z(r, x, y, z0, z1):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def ellipse_yz(a, b, zc, n=72):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([a * np.cos(t), zc + b * np.sin(t)], axis=1)


# --- wing ---------------------------------------------------------------------
def airfoil_xz(y, hinge=None, n=40):
    c = P.chord(y)
    lp = G.airfoil_loop("clarky", n=n, hinge=hinge)
    return np.stack([P.X_LE + c * lp[:, 0], P.Z_WING + c * lp[:, 1]], axis=1)


def spigot(y_face, sgn, hinge=None):
    """Ring that slides 10 mm into a section's open end; returns (ring, solid envelope)."""
    y_far = y_face + sgn * L
    c = min(P.chord(y_face), P.chord(y_far))
    lp = G.airfoil_loop("clarky", n=40)
    loop = np.stack([P.X_LE + c * lp[:, 0], P.Z_WING + c * lp[:, 1]], axis=1)
    x_cut = P.X_LE + (P.SPIGOT_CUT * c if hinge is None else hinge * c - P.HINGE_MARGIN)
    outer = G.clip_x(G.offset_loop(loop, P.INSET), x_cut)
    inner = G.clip_x(G.offset_loop(loop, P.INSET + P.RING_WALL), x_cut - P.RING_WALL)
    # Envelope overlaps the flange by 0.5 mm: coplanar unions leave open mesh edges.
    env = prism_y(outer, y_face - sgn * 0.5, y_far)
    return env - prism_y(inner, y_face, y_far + sgn * 0.1), env


def spar_features(y0, y1, envelopes):
    """Spar bosses clipped to the spigot envelopes, and the through-holes."""
    bosses, holes = None, None
    for s in (P.MAIN_SPAR, P.REAR_SPAR):
        hr = (s["od"] + P.SPAR_HOLE_CLEAR) / 2
        for env in envelopes:
            b = cyl_y(hr + P.SPAR_BOSS_WALL, s["x"], s["z"], y0, y1) & env
            bosses = b if bosses is None else bosses + b
        h = cyl_y(hr, s["x"], s["z"], y0 - 1, y1 + 1)
        holes = h if holes is None else holes + h
    return bosses, holes


def root_rib():
    y0, y1 = P.Y_ROOT_RIB
    part = prism_y(airfoil_xz(y1), y0, y1)
    ring, env = spigot(y1, +1)
    bosses, holes = spar_features(y0, y1 + L, [env])
    part = part + ring + bosses - holes
    part -= cyl_y(P.RIB_WIRE_R + 1.0, P.RIB_WIRE_X, P.RIB_WIRE_Z + 2.0, y0 - 1, y1 + 1)
    # Drill guide for the M2.5 nylon pin that locks the rear spar to its joiner.
    part -= cyl_z(1.3, P.REAR_SPAR["x"], y1 + 5.0, -20, 20)
    return part


def midtip_rib():
    y0, y1 = P.Y_MIDTIP_RIB
    h = P.AIL_HINGE
    part = prism_y(airfoil_xz(y1, hinge=h), y0, y1)
    r_in, e_in = spigot(y0, -1, hinge=h)
    r_out, e_out = spigot(y1, +1, hinge=h)
    bosses, holes = spar_features(y0 - L, y1 + L, [e_in, e_out])
    part = part + r_in + r_out + bosses - holes
    return part - cyl_y(P.RIB_WIRE_R, P.RIB_WIRE_X, P.RIB_WIRE_Z, y0 - 1, y1 + 1)


def tip_rib():
    y0, y1 = P.Y_TIP_RIB
    part = prism_y(airfoil_xz(y0, hinge=P.AIL_HINGE), y0, y1)
    ring, env = spigot(y0, -1, hinge=P.AIL_HINGE)
    bosses, holes = spar_features(y0 - L, y1, [env])
    return part + ring + bosses - holes


def pod_profile():
    """Boom pod side profile (x, z): round nose about the tilt axis, flat aft face ahead of the LE.

    The lower front leaves the arc at 225 deg on a 45 deg tangent to the bed, so the pod
    prints upright without supports.
    """
    xp, zp, r = P.X_PIVOT, P.Z_PIVOT, P.NOSE_R
    a0 = math.pi - math.asin((P.POD_TOP - zp) / r)
    arc = [(xp + r * math.cos(a), zp + r * math.sin(a)) for a in np.linspace(a0, 1.25 * math.pi, 20)]
    xt, zt = arc[-1]
    x_bed = xt + (zt - P.Z_WING)
    return np.array([(x_bed, P.Z_WING), (P.POD_AFT_X, P.Z_WING), (P.POD_AFT_X, P.POD_TOP)] + arc)


BOOM_WIRE_X_END = 412.0      # boom-rib wire groove runs from the tongue tip to here
CUP_PLATE_T = 1.5


def boom_rib():
    """6 mm rib between root and mid sections; its tongue runs forward into the pod.

    The inboard spigot ring is a separate part (boom_cup) so this one prints flat on its
    inboard face with no supports. The wire groove is open on that face; the cup's plate
    closes it once glued on.
    """
    y0, y1 = P.Y_BOOM_RIB
    band = loft([poly_face([(x, y0, z) for x, z in airfoil_xz(y0)]),
                 poly_face([(x, y1, z) for x, z in airfoil_xz(y1)])], ruled=True)
    f0, f1 = P.TONGUE_FAIR_X
    tongue = [(P.TONGUE_X0, P.Z_WING), (f1, P.Z_WING), (f1, 14.0), (f0, P.TONGUE_TOP),
              (P.TONGUE_X0, P.TONGUE_TOP)]
    part = band + prism_y(tongue, y0, y1)
    r_out, e_out = spigot(y1, +1, hinge=P.AIL_HINGE)
    bosses, holes = spar_features(y0, y1 + L, [e_out])
    part = part + r_out + bosses - holes
    zc, xc_end = P.Z_WING + 7.0, BOOM_WIRE_X_END
    # Groove 5 mm deep from the inboard face; the 1 mm left on the outboard face ties the
    # lower edge of the tongue to the rest of it.
    part -= box(P.TONGUE_X0 - 1, xc_end, y0 - 1, y1 - 1, zc - P.WIRE_D / 2, zc + P.WIRE_D / 2)
    part -= cyl_y(P.WIRE_D / 2, xc_end, zc, y0 - 1, y1 - 1)
    # Aileron leads and pitot tubing: same line as the root and mid/tip rib holes.
    part -= cyl_y(P.RIB_WIRE_R, P.RIB_WIRE_X, P.RIB_WIRE_Z, y0 - 1, y1 + L + 1)
    for x in P.POD_BOLTS_X:
        part -= cyl_y(1.65, x, 12.0, y0 - 1, y1 + 1)
    return part


def boom_cup():
    """Inboard spigot ring of the boom rib with a 1.5 mm glue plate on the rib face.

    Prints standing on the plate. Both spars pass through it and the rib, so they align
    the two parts while the epoxy cures.
    """
    y0 = P.Y_BOOM_RIB[0]
    y_far = y0 - L
    c = P.chord(y0)
    lp = G.airfoil_loop("clarky", n=40)
    loop = np.stack([P.X_LE + c * lp[:, 0], P.Z_WING + c * lp[:, 1]], axis=1)
    x_cut = P.X_LE + P.SPIGOT_CUT * c
    outer = G.clip_x(G.offset_loop(loop, P.INSET), x_cut)
    inner = G.clip_x(G.offset_loop(loop, P.INSET + P.RING_WALL), x_cut - P.RING_WALL)
    env = prism_y(outer, y_far, y0)
    part = env - prism_y(inner, y_far - 0.1, y0 - CUP_PLATE_T)
    bosses, holes = spar_features(y_far, y0, [env])
    part = part + bosses - holes
    zc = P.Z_WING + 7.0
    part -= cyl_y(P.WIRE_D / 2, BOOM_WIRE_X_END, zc, y_far - 1, y0 + 1)
    # Aileron leads and pitot tubing (also lightens the plate).
    return part - cyl_y(6.0, P.RIB_WIRE_X, P.RIB_WIRE_Z + 1.0, y_far - 1, y0 + 1)


def boom_pod():
    """Servo housing and tilt axle; slides over the boom-rib tongue (epoxy + 2x M3)."""
    y0, y1 = P.Y_POD
    xp, zp = P.X_PIVOT, P.Z_PIVOT
    part = prism_y(pod_profile(), y0, y1)
    part -= box(P.TONGUE_X0 - 1, P.POD_AFT_X + 1, P.BOOM_Y - 3.15, P.BOOM_Y + 3.15,
                P.Z_WING - 1, P.TONGUE_TOP + 0.2)
    # Axle boss on the outboard face: M3 bolt through the yoke bearing into a heat-set insert.
    y_end = y1 + P.AXLE_BOSS_LEN
    part += cyl_y(P.AXLE_BOSS_R, xp, zp, y1 - 1, y_end)
    # 45 deg gusset under the boss (teardrop section) so it prints without supports: flat top at
    # the boss's 45 deg tangent points, 45 deg underside from the boss's lowest point at its tip.
    hw = P.AXLE_BOSS_R * math.sin(math.radians(45))
    z_top = zp - P.AXLE_BOSS_R * math.cos(math.radians(45))
    z_tip = zp - P.AXLE_BOSS_R
    run = y_end - (y1 - 0.5)
    gusset = [(y1 - 0.5, z_top), (y_end, z_top), (y_end, z_tip), (y1 - 0.5, max(z_tip - run, P.Z_WING))]
    face = poly_face([(xp - hw, y, z) for y, z in gusset])
    part += extrude(face, amount=2 * hw, dir=(1, 0, 0))
    part -= cyl_y(P.INSERT_HOLE[0] / 2, xp, zp, y_end - P.INSERT_HOLE[1], y_end + 1)
    part -= cyl_y(1.65, xp, zp, y1 - 2, y_end)
    # Servo bay on the inboard face: tabs on the face, output shaft on the tilt axis.
    bl, bh, bd = P.SERVO_BODY
    bx0 = xp - P.SERVO_SHAFT_FROM_FRONT - 0.5
    part -= box(bx0, bx0 + bl, y0 - 1, y0 + bd, zp - bh / 2, zp + bh / 2)
    for dx in (-P.SERVO_TAB_PITCH / 2, P.SERVO_TAB_PITCH / 2):
        part -= cyl_y(0.9, bx0 + bl / 2 + dx, zp, y0 - 1, y0 + 10)
    # Wires: enter beside the axle boss, run aft under the servo into the tongue channel.
    zc = P.Z_WING + 7.0
    part -= cyl_y(P.WIRE_D / 2, xp + 10, zc, P.BOOM_Y, y1 + 1)
    part -= cyl_x(P.WIRE_D / 2, P.BOOM_Y, zc, xp + 8, P.TONGUE_X0 + 1)
    part -= cyl_z(3.0, bx0 + bl - 4, P.BOOM_Y - 4, zc, zp)
    for x in P.POD_BOLTS_X:
        part -= cyl_y(1.65, x, 12.0, y0 - 1, y1 + 1)
    return part


# --- tilt yoke (hover orientation: thrust axis +z) ----------------------------
def yoke_plate():
    xp, yb, zp = P.X_PIVOT, P.BOOM_Y, P.Z_PIVOT
    z0 = zp + P.YOKE_PLATE_Z0
    hu, y_out = P.YOKE_PLATE_U / 2, P.YOKE_ARM_IN + P.YOKE_ARM_T
    return box(xp - hu, xp + hu, yb - y_out, yb + y_out, z0, z0 + P.YOKE_PLATE_T)


def yoke():
    xp, yb, zp = P.X_PIVOT, P.BOOM_Y, P.Z_PIVOT
    z0 = zp + P.YOKE_PLATE_Z0
    hu = P.YOKE_PLATE_U / 2
    y_out = P.YOKE_ARM_IN + P.YOKE_ARM_T
    plate = yoke_plate()
    r = P.YOKE_BOSS_R
    arm_xz = [(xp - r, zp), (xp + r, zp), (xp + hu, z0 + 0.5), (xp - hu, z0 + 0.5)]
    part = plate
    for sgn in (-1, 1):
        ya, yb2 = yb + sgn * P.YOKE_ARM_IN, yb + sgn * y_out
        part += prism_y(arm_xz, ya, yb2) + cyl_y(r, xp, zp, ya, yb2)
    s = P.MOTOR_HOLE_SQ / 2
    for dx in (-s, s):
        for dy in (-s, s):
            part -= cyl_z(P.MOTOR_HOLE_D / 2, xp + dx, yb + dy, z0 - 1, z0 + 6)
    part -= cyl_z(P.MOTOR_CENTER_D / 2, xp, yb, z0 - 1, z0 + 6)
    part -= cyl_y(3.5, xp, zp, yb - y_out - 1, yb - P.YOKE_ARM_IN + 1)
    part -= cyl_y(P.BEARING_OD / 2, xp, zp, yb + P.YOKE_ARM_IN - 1, yb + y_out + 1)
    return part


# --- fuselage inserts ---------------------------------------------------------
def fuse_loft(x0, x1, inset, step=5.0):
    xs = np.linspace(x0, x1, max(2, int(math.ceil((x1 - x0) / step)) + 1))
    faces = []
    for x in xs:
        w, h, zc = G.fuse_dims(x)
        faces.append(poly_face([(x, y, z) for y, z in ellipse_yz(w / 2 - inset, h / 2 - inset, zc)]))
    return loft(faces, ruled=True)


def coupler(xj):
    x0, x1 = xj - P.COUPLER_HALF, xj + P.COUPLER_HALF
    part = fuse_loft(x0, x1, P.INSET) - fuse_loft(x0 - 1, x1 + 1, P.INSET + P.COUPLER_WALL)
    if xj == P.FUSE_SPLITS[1]:
        # Nose retention: M3 nylon screw up through the nose shell into a heat-set insert.
        xs = P.NOSE_SCREW_X
        w, h, zc = G.fuse_dims(xs)
        zb = zc - h / 2 + P.INSET
        boss = box(x0, xs + 6, -6, 6, zb - 1, zb + P.COUPLER_WALL + 7)
        part += boss & fuse_loft(x0, x1, P.INSET)
        part -= cyl_z(P.INSERT_HOLE[0] / 2, xs, 0, zb + P.COUPLER_WALL + 7 - P.INSERT_HOLE[1], zb + 20)
        part -= cyl_z(1.65, xs, 0, zb - 2, zb + 10)
    if xj == P.FUSE_SPLITS[3]:
        # Tail-boom support web at the front end (prints on the bed).
        w, h, zc = G.fuse_dims(x0)
        rim = ellipse_yz(w / 2 - P.INSET - 0.5, h / 2 - P.INSET - 0.5, zc)
        web = prism_x(rim, x0, x0 + P.FRAME_T)
        web -= prism_x(ellipse_yz(w / 2 - 10, h / 2 - 10, zc), x0 - 1, x0 + P.FRAME_T + 1)
        web += box(x0, x0 + P.FRAME_T, -4, 4, zc - h / 2 + 2, zc + h / 2 - 2) & prism_x(rim, x0, x0 + P.FRAME_T)
        web += cyl_x(P.BOOM_HOLE / 2 + 4, 0, P.BOOM_Z, x0, x0 + P.FRAME_T)
        part = part + web - cyl_x(P.BOOM_HOLE / 2, 0, P.BOOM_Z, x0 - 1, x0 + 10)
    return part


def frame(spar, joiner):
    """Bulkhead with a spanwise joiner sleeve; the aft face is flat for printing."""
    xs = spar["x"]
    t = (joiner["od"] + 0.3) / 2 + P.SLEEVE_WALL
    xa, xf = xs + t, xs - t
    w, h, zc = G.fuse_dims(xa)
    outline = ellipse_yz(w / 2 - P.INSET, h / 2 - P.INSET, zc)
    env = prism_x(outline, xf, xa)
    part = prism_x(outline, xa - P.FRAME_T, xa)
    part += box(xf, xa, -w / 2, w / 2, spar["z"] - t, spar["z"] + t) & env
    part -= cyl_y((joiner["od"] + 0.3) / 2, xs, spar["z"], -w, w)
    inner = prism_x(ellipse_yz(w / 2 - 9, h / 2 - 9, zc), xf - 1, xa + 1)
    part -= inner & box(xf - 1, xa + 1, -w, w, spar["z"] + t + 3, 99)
    keep = cyl_x(P.BOOM_HOLE / 2 + 5, 0, P.BOOM_Z, xf - 1, xa + 1) + box(xf - 1, xa + 1, -4, 4, -99, 99)
    part -= (inner & box(xf - 1, xa + 1, -w, w, -99, spar["z"] - t - 3)) - keep
    return part - cyl_x(P.BOOM_HOLE / 2, 0, P.BOOM_Z, xf - 1, xa + 1)


def fc_shelf():
    x0, x1 = P.FC_SHELF_X
    zt = P.FC_SHELF_Z
    xs = np.linspace(x0, x1, 21)
    hw = [G.fuse_half_width(x, zt, P.INSET) - 0.2 for x in xs]
    outline = [(x, -y) for x, y in zip(xs, hw)] + [(x, y) for x, y in zip(xs[::-1], hw[::-1])]
    part = extrude(poly_face([(x, y, zt - 2.5) for x, y in outline]), amount=2.5, dir=(0, 0, 1))
    for sgn in (-1, 1):
        y_in, y_out = 24.0, min(hw) - 6.0
        part -= box(x0 + 7, x1 - 7, *sorted((sgn * y_in, sgn * y_out)), zt - 5, zt + 1)
    return part


def battery_tray():
    x0, x1 = P.TRAY_X
    zt, hw = P.TRAY_Z, P.TRAY_W / 2
    part = box(x0, x1, -hw, hw, zt - 3, zt)
    xs = np.linspace(x0, x1, 25)
    for yr in (-24.0, 24.0):
        floor = []
        for x in xs:
            w, h, zc = G.fuse_dims(x)
            a, b = w / 2 - P.INSET, h / 2 - P.INSET
            floor.append(zc - b * math.sqrt(max(0.0, 1 - (yr / a) ** 2)) + 0.3)
        rail = [(x0, zt - 2)] + [(x1, zt - 2)] + list(zip(xs[::-1], floor[::-1]))
        part += prism_y(rail, yr - 1.5, yr + 1.5)
    for x in np.arange(*P.TRAY_PIN_X):
        part -= cyl_z(P.TRAY_PIN_R, x, 0, zt - 5, zt + 1)
    for x in (280.0, 330.0):
        part -= box(x - 1.5, x + 1.5, -12, 12, zt - 5, zt + 1)
    for xa, xb in ((252.0, 275.0), (286.0, 324.0), (336.0, 360.0)):
        for ya, yb in ((5.0, 19.0), (-19.0, -5.0)):
            part -= box(xa, xb, ya, yb, zt - 5, zt + 1)
    return part


def pod_collar():
    x0, x1 = P.POD_COLLAR_X
    return fuse_loft(x0, x1, P.INSET, step=3.0) - cyl_x(P.BOOM_HOLE / 2, 0, P.BOOM_Z, x0 - 1, x1 + 1)


def rear_motor_mount():
    """Boom clamp + web + motor plate, one constant section along x so it prints standing on
    an end with no overhangs. The plate stands REAR_PLATE_Z above the boom top so a hex key
    reaches the motor screw heads (fit the motor before sliding the mount onto the boom).
    """
    xm, zb, zp = P.X_REAR_MOTOR, P.BOOM_Z, P.REAR_PLATE_Z
    h = P.REAR_MOUNT_LEN / 2
    ro, ri = P.BOOM_HOLE / 2 + 3.3, P.BOOM_HOLE / 2
    part = cyl_x(ro, 0, zb, xm - h, xm + h)
    part += box(xm - h, xm + h, -6, 6, zb - ro - 6, zb - ri)
    part += box(xm - h, xm + h, -5.5, 5.5, zb, zp)
    part += box(xm - h, xm + h, -h, h, zp, zp + 4)
    part -= cyl_x(ri, 0, zb, xm - h - 1, xm + h + 1)
    part -= box(xm - h - 1, xm + h + 1, -0.75, 0.75, zb - ro - 7, zb - ri + 1)
    for dx in (-h / 2, h / 2):
        part -= cyl_y(1.65, xm + dx, zb - ro - 2.5, -8, 8)
    s = P.MOTOR_HOLE_SQ / 2
    for dx in (-s, s):
        for dy in (-s, s):
            part -= cyl_z(P.MOTOR_HOLE_D / 2, xm + dx, dy, zp - 1, zp + 5)
    return part - cyl_z(P.MOTOR_CENTER_D / 2, xm, 0, zp - 1, zp + 5)


# --- V-tail -----------------------------------------------------------------
def vt_plane():
    origin, _, e_t = vt_frame()
    return Plane(origin=tuple(origin), x_dir=(1, 0, 0), z_dir=tuple(e_t))


def vt_section_local(s, n=36):
    """Truncated NACA 0012 loop (u, t) at span s of the panel."""
    c = vt_chord(s)
    lp = G.airfoil_loop("naca0012", n=n, hinge=P.VT_HINGE)
    return np.stack([c * lp[:, 0], c * lp[:, 1]], axis=1), c


def prism_s(loop_ut, s0, s1):
    lo, hi = min(s0, s1), max(s0, s1)
    face = poly_face([(u, lo, t) for u, t in loop_ut])
    return extrude(face, amount=hi - lo, dir=(0, 1, 0))


def vt_rib_local(s_face, sgn, flange_t):
    """Flange outside the skin plus a spigot ring 10 mm (or 6 mm) into it, local (u, s, t)."""
    loop, c = vt_section_local(s_face)
    depth = L if flange_t >= P.RIB_T else 6.0
    flange = prism_s(loop, s_face, s_face - sgn * flange_t)
    c_far = vt_chord(s_face + sgn * depth)
    full = G.airfoil_loop("naca0012", n=36)
    sec = np.stack([min(c, c_far) * full[:, 0], min(c, c_far) * full[:, 1]], axis=1)
    x_cut = P.VT_HINGE * min(c, c_far) - P.HINGE_MARGIN
    outer = G.clip_x(G.offset_loop(sec, P.INSET), x_cut)
    inner = G.clip_x(G.offset_loop(sec, P.INSET + P.RING_WALL), x_cut - P.RING_WALL)
    env = prism_s(outer, s_face - sgn * 0.5, s_face + sgn * depth)
    return flange + env - prism_s(inner, s_face, s_face + sgn * (depth + 0.1)), env


def vtail_root_rib_local():
    part, env = vt_rib_local(0.0, +1, P.RIB_T)
    u_pin = 0.30 * P.VT_ROOT_CHORD
    boss = Pos(u_pin, L / 2 - P.RIB_T / 2, 0) * Rot(90, 0, 0) * Cylinder(P.VT_PIN_D / 2 + 2.0, L + P.RIB_T)
    part += boss & (env + prism_s(vt_section_local(0.0)[0], 0.0, -P.RIB_T))
    part -= Pos(u_pin, 0, 0) * Rot(90, 0, 0) * Cylinder(P.VT_PIN_D / 2, 40)
    # One slot serves both sides: the tail block's wire holes sit at 45 % (right) and 58 % (left).
    return part - box(0.43 * P.VT_ROOT_CHORD, 0.60 * P.VT_ROOT_CHORD, -6, 2, -P.WIRE_D / 2, P.WIRE_D / 2)


def vtail_tip_cap_local():
    part, _ = vt_rib_local(P.VT_SPAN, -1, 1.5)
    return part


def tail_block():
    x0, x1 = P.TAIL_BLOCK_X
    zb, ro = P.BOOM_Z, P.BOOM_HOLE / 2 + 3.3
    part = box(x0, x1, -19, 19, zb, 14) + cyl_x(ro, 0, zb, x0, x1)
    for right, u_wire in ((True, 0.45), (False, 0.58)):
        origin, e_s, _ = vt_frame()
        if not right:
            origin, e_s = origin * [1, -1, 1], e_s * [1, -1, 1]
        q = origin - P.RIB_T * e_s
        part = split(part, bisect_by=Plane(origin=tuple(q), z_dir=tuple(e_s)), keep=Keep.BOTTOM)
        pin_c = q + [0.30 * P.VT_ROOT_CHORD, 0, 0]
        # 8 mm deep: a longer hole meets the other side's hole at y=0 (degenerate mesh).
        part -= Pos(*(pin_c + 3.0 * e_s)) * _along(e_s) * Cylinder(P.VT_PIN_D / 2, 22)
        wire_c = q + [u_wire * P.VT_ROOT_CHORD, 0, 0]
        part -= Pos(*wire_c) * _along(e_s) * Cylinder(P.WIRE_D / 2, 60)
    return part - cyl_x(P.BOOM_HOLE / 2, 0, zb, x0 - 1, x1 + 1)


def _along(v):
    """Rotation taking +z onto unit vector v (v lies in the y-z plane)."""
    return Rot(-math.degrees(math.atan2(v[1], v[2])), 0, 0)


# --- small loose parts (print-only) ---------------------------------------------
def servo_cage():
    """9 g micro servo lying on its side: base glues to the skin, tabs screw to the posts."""
    part = box(-18, 18, -9, 9, 0, 1.6)
    for x in (-P.SERVO_TAB_PITCH / 2, P.SERVO_TAB_PITCH / 2):
        part += box(x - 2.5, x + 2.5, -4, 4, 0, 13)
        part -= cyl_y(0.8, x, 8.0, -5, 5)
    return part


def control_horn():
    part = box(-9, 9, -4, 4, 0, 1.5) + box(-5, 5, -1.2, 1.2, 0, 15)
    for z in (8.0, 10.5, 13.0):
        part -= cyl_y(0.8, 0, z, -2, 2)
    return part


def build():
    parts = {
        "rib_root_r": root_rib(),
        "rib_midtip_r": midtip_rib(),
        "rib_tip_r": tip_rib(),
        "boom_rib_r": boom_rib(),
        "boom_cup_r": boom_cup(),
        "boom_pod_r": boom_pod(),
        "yoke_r": yoke(),
    }
    for name in list(parts):
        parts[name[:-2] + "_l"] = mirror(parts[name], about=Plane.XZ)
    for i, xj in enumerate(P.FUSE_SPLITS[1:-1], start=1):
        parts[f"coupler_{int(xj)}"] = coupler(xj)
    parts["frame_main"] = frame(P.MAIN_SPAR, P.MAIN_JOINER)
    parts["frame_rear"] = frame(P.REAR_SPAR, P.REAR_JOINER)
    parts["fc_shelf"] = fc_shelf()
    parts["battery_tray"] = battery_tray()
    parts["pod_collar"] = pod_collar()
    parts["rear_motor_mount"] = rear_motor_mount()
    parts["tail_block"] = tail_block()
    loc = vt_plane().location
    parts["vtail_root_rib_r"] = loc * vtail_root_rib_local()
    parts["vtail_tip_cap_r"] = loc * vtail_tip_cap_local()
    for name in ("vtail_root_rib", "vtail_tip_cap"):
        parts[name + "_l"] = mirror(parts[name + "_r"], about=Plane.XZ)
    parts["servo_cage"] = servo_cage()
    parts["control_horn"] = control_horn()
    os.makedirs(G.ASSEMBLY, exist_ok=True)
    for name, part in parts.items():
        export_stl(part, os.path.join(G.ASSEMBLY, name + ".stl"), tolerance=0.02, angular_tolerance=0.1)
        bb = part.bounding_box()
        print(f"{name:18s} vol {part.volume:9.0f} mm3  x {bb.min.X:7.1f}..{bb.max.X:7.1f}  "
              f"y {bb.min.Y:7.1f}..{bb.max.Y:7.1f}  z {bb.min.Z:6.1f}..{bb.max.Z:6.1f}")
    return parts


if __name__ == "__main__":
    build()
