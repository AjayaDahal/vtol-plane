"""v0.2 airframe geometry: the single source of truth for every generator and check.

Units are mm and g. Datum: x aft from the nose tip, y toward the right wing tip,
z up, with z = 0 on the fuselage centreline. Left-hand parts are the y-mirror of
the right-hand parts.
"""

# --- print fits -----------------------------------------------------------
LWPLA_WALL = 0.6            # effective LW-PLA vase wall (0.42 mm line, foamed)
FIT = 0.25                  # slip gap per side, PETG insert inside an LW-PLA shell
INSET = LWPLA_WALL + FIT    # PETG insert outer surface sits this far inside the skin
RING_WALL = 1.2             # PETG spigot / coupler ring wall

# --- wing (Clark Y, straight LE, flat bottom parallel to the datum, 0 deg dihedral)
X_LE = 380.0
Z_WING = -5.0
ROOT_CHORD, TIP_CHORD = 220.0, 150.0
Y_ROOT, Y_TIP = 60.0, 710.0


def chord(y):
    """Local wing chord at span station y (either wing)."""
    return ROOT_CHORD + (TIP_CHORD - ROOT_CHORD) * (abs(y) - Y_ROOT) / (Y_TIP - Y_ROOT)


RIB_T = 3.0
SPIGOT_LEN = 10.0
SPIGOT_CUT = 0.80           # spigot rings stop at 80 % chord (HINGE_MARGIN ahead of a hinge)
HINGE_MARGIN = 2.0          # 8 mm left a 7.7 mm unsupported ledge on the mid/tip rib flange
BOOM_Y = 280.0
BOOM_W = 28.0               # pod width (servo bay + walls)
BOOM_RIB_T = 6.0            # boom rib between the root and mid sections
Y_ROOT_RIB = (60.0, 63.0)
Y_ROOT_SEC = (63.0, BOOM_Y - BOOM_RIB_T / 2)
Y_BOOM_RIB = (BOOM_Y - BOOM_RIB_T / 2, BOOM_Y + BOOM_RIB_T / 2)
Y_POD = (BOOM_Y - BOOM_W / 2, BOOM_Y + BOOM_W / 2)
Y_MID_SEC = (BOOM_Y + BOOM_RIB_T / 2, 487.0)
Y_MIDTIP_RIB = (487.0, 490.0)
Y_TIP_SEC = (490.0, 707.0)
Y_TIP_RIB = (707.0, 710.0)

MAIN_SPAR = dict(x=432.0, z=Z_WING + 8.5, od=10.0, id=8.0)
REAR_SPAR = dict(x=480.0, z=Z_WING + 6.0, od=6.0, id=4.0)
SPAR_HOLE_CLEAR = 0.25      # hole diameter = tube OD + this
SPAR_BOSS_WALL = 1.4
MAIN_JOINER = dict(od=8.0, length=420.0)   # carbon tube inside both main spars
REAR_JOINER = dict(od=4.0, length=320.0)   # carbon rod inside both rear spars
RIB_WIRE_X, RIB_WIRE_Z, RIB_WIRE_R = 457.0, 5.0, 5.0   # spanwise wire/pitot hole between the spars

AIL_HINGE = 0.75            # hinge line at 75 % local chord (straight, top-surface tape)
AIL_BEVEL_DEG = 25.0        # underside bevel lets a top hinge deflect both ways
AIL_GAP = 0.6
AILERONS = {"mid": (286.0, 485.0), "tip": (492.0, 705.0)}

# --- tilt mechanism (Stallion-style boom, direct-drive servo, one bearing) --
X_PIVOT = 315.0             # tilt axis, 65 mm ahead of the LE
Z_PIVOT = Z_WING + 20.0
POD_TOP = Z_PIVOT + 8.5
NOSE_R = 20.0
POD_AFT_X = X_LE - 2.0      # wide pod stops just ahead of the wing LE
TONGUE_X0 = 336.0           # boom-rib tongue runs forward into a slot in the pod
TONGUE_TOP = Z_PIVOT + 6.0
TONGUE_FAIR_X = (400.0, 445.0)   # tongue top ramps down into the wing between these x
POD_BOLTS_X = (348.0, 368.0)     # M3 bolts through pod and tongue
YOKE_PLATE_Z0 = 27.0        # plate back face above the pivot (hover orientation)
YOKE_PLATE_T = 4.0
YOKE_PLATE_U = 36.0
YOKE_ARM_T = 4.0
YOKE_BOSS_R = 9.0
BEARING_OD = 8.1            # 3x8x4 flanged bearing pocket (ream to fit)
SERVO_BODY = (24.0, 13.0, 21.0)   # bay length (x), height (z), depth (y): 12 mm mini servo
SERVO_SHAFT_FROM_FRONT = 6.0
SERVO_TAB_PITCH = 28.0
SERVO_ABOVE_TAB = 11.0      # tab face to spline top
HORN_T = 2.5
YOKE_ARM_IN = BOOM_W / 2 + SERVO_ABOVE_TAB + HORN_T   # arm inner face from the boom centre plane
AXLE_BOSS_R = 6.0
AXLE_BOSS_LEN = YOKE_ARM_IN - BOOM_W / 2 - 0.5
INSERT_HOLE = (4.2, 6.0)    # M3 heat-set insert: hole dia, depth
WIRE_D = 7.0
TILT_MIN_DEG, TILT_MAX_DEG = -20.0, 90.0   # 0 = thrust up, 90 = thrust forward

MOTOR_HOLE_SQ = 19.0        # Emax ECOII 2807: 19x19 mm M3 pattern
MOTOR_HOLE_D = 3.4
MOTOR_CENTER_D = 9.5
MOTOR_BASE_TO_PROP = 37.0   # motor base to prop disc, 2807 class
PROP_D = 178.0              # 7 in props

# --- fuselage pod (LW-PLA vase) + carbon tail boom -------------------------
FUSE_STATIONS = [           # x, width, height, centre z
    (0, 12, 12, 0), (60, 60, 70, 0), (120, 95, 115, 0), (240, 120, 140, 0),
    (360, 120, 135, 0), (480, 110, 120, 0), (600, 95, 105, 0),
    (680, 64, 70, -8), (740, 36, 36, -16), (760, 28, 28, -19)]
FUSE_SPLITS = [0.0, 240.0, 370.0, 610.0, 760.0]
COUPLER_HALF = 20.0
COUPLER_WALL = 1.0
FRAME_T = 3.0
SLEEVE_WALL = 1.6
NOSE_SCREW_X = 228.0        # M3 nylon screw holding the removable nose

BOOM_OD, BOOM_ID = 16.0, 14.0
BOOM_HOLE = BOOM_OD + 0.3
BOOM_Z = -20.0
BOOM_X = (420.0, 1050.0)
POD_COLLAR_X = (745.0, 760.0)

FC_SHELF_X = (255.0, 355.0)
FC_SHELF_Z = 32.0           # top surface
TRAY_X = (243.0, 367.0)
TRAY_Z = -52.0              # top surface
TRAY_W = 60.0
TRAY_PIN_X = (250.0, 361.0, 10.0)   # battery stop-pin holes: start, stop (exclusive), pitch
TRAY_PIN_R = 1.6

# --- rear lift motor (vertical, on the boom) --------------------------------
X_REAR_MOTOR = 820.0
REAR_PLATE_Z = 15.0         # plate underside; leaves ~25 mm under the screw heads for a hex key
REAR_MOUNT_LEN = 36.0       # clamp, web and plate share this length along the boom

# --- V-tail (fixed panels + ruddervators) ----------------------------------
VT_X_LE = 920.0
VT_ROOT_CHORD, VT_TIP_CHORD, VT_SPAN = 180.0, 110.0, 240.0
VT_DIHEDRAL = 35.0          # each panel from horizontal (110 deg included)
VT_HINGE = 0.70
VT_ROOT = (11.0, -2.0)      # (y, z) of the right panel root chord line, rib outer face
VT_RUDDERVATOR = (5.0, 236.0)
TAIL_BLOCK_X = (950.0, 1030.0)
VT_PIN_D = 4.1
