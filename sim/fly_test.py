#!/usr/bin/env python3
"""Automated check flight of the VTOL plane in PX4 SITL + Gazebo (SIMULATION.md).

Start the simulation first, in the PX4-Autopilot tree (sim/install.sh puts the model there):
    make px4_sitl gz_vtol_plane              (HEADLESS=1 make ... runs without the GUI)
then, from this repository, in the same Linux (WSL) system:
    python3 sim/fly_test.py [--plot flight.png] [--video flight.mp4]

The mission: a VTOL takeoff to 30 m with the front transition, a 950 x 400 m circuit in
fixed-wing flight at 40 m ending in a 450 m straight final, and a VTOL landing at home with the
back transition. The script checks that each phase happens, that the airspeed stays between 1 m/s
under FW_AIRSPD_MIN and FW_AIRSPD_MAX once settled in fixed-wing flight, that the back transition
neither balloons nor pitches up past 45 deg, and that the aircraft lands near home and disarms.
Then it reads PX4's log of the flight and reports the hover throttle, the transitions and how well
attitude and airspeed were tracked. --video films the flight from a chase camera (chase_cam.py).
Exit code 0 when every check passes.
"""
import argparse
import glob
import math
import os
import sys
import time

from pymavlink import mavutil

MAV = mavutil.mavlink
CONNECT = "udpin:0.0.0.0:14540"         # PX4 SITL's onboard (API) MAVLink link
TAKEOFF_ALT, CRUISE_ALT = 30.0, 40.0
# north, east of home (m); the last leg lines up a 450 m straight final, so the back transition
# starts with the wings level
CIRCUIT = [(500.0, 0.0), (500.0, 400.0), (-450.0, 400.0), (-450.0, 0.0)]
AIRSPEED = (16.0, 25.0)                 # FW_AIRSPD_MIN, FW_AIRSPD_MAX (sim/airframes)
TIMEOUT = 900.0                         # s of simulated time (PX4's clock: it slows down while filming)
TIMEOUT_WALL = 3600.0
VTOL_STATE = {0: "undefined", 1: "transition to FW", 2: "transition to MC", 3: "MC", 4: "FW"}
LANDED = {0: "undefined", 1: "on ground", 2: "in air", 3: "taking off", 4: "landing"}


def offset(lat, lon, north, east):
    r = 6378137.0
    return (lat + math.degrees(north / r), lon + math.degrees(east / (r * math.cos(math.radians(lat)))))


def distance(lat1, lon1, lat2, lon2):
    r = 6378137.0
    dn = math.radians(lat2 - lat1) * r
    de = math.radians(lon2 - lon1) * r * math.cos(math.radians(lat1))
    return math.hypot(dn, de)


class Flight:
    def __init__(self, url):
        self.m = mavutil.mavlink_connection(url, source_system=245)
        self.texts = []
        self.state = dict(vtol=0, landed=0, armed=False, alt=0.0, airspeed=0.0, groundspeed=0.0,
                          throttle=0, lat=None, lon=None, mode="", clock=0.0)
        self.reached = set()
        self.rows = []

    def pump(self, timeout=0.1):
        """Read everything waiting; keep the latest state and every status text."""
        msg = self.m.recv_match(blocking=True, timeout=timeout)
        while msg is not None:
            t = msg.get_type()
            s = self.state
            if t == "HEARTBEAT" and msg.get_srcSystem() == self.m.target_system and msg.type != MAV.MAV_TYPE_GCS:
                s["armed"] = bool(msg.base_mode & MAV.MAV_MODE_FLAG_SAFETY_ARMED)
                s["mode"] = mavutil.mode_string_v10(msg)
            elif t == "EXTENDED_SYS_STATE":
                s["vtol"], s["landed"] = msg.vtol_state, msg.landed_state
            elif t == "GLOBAL_POSITION_INT":
                s["alt"], s["lat"], s["lon"] = msg.relative_alt / 1000.0, msg.lat / 1e7, msg.lon / 1e7
                s["clock"] = msg.time_boot_ms / 1000.0      # PX4's time: simulated, in lockstep with Gazebo
            elif t == "VFR_HUD":
                s["airspeed"], s["groundspeed"], s["throttle"] = msg.airspeed, msg.groundspeed, msg.throttle
            elif t == "MISSION_ITEM_REACHED":
                self.reached.add(msg.seq)
            elif t == "STATUSTEXT":
                text = msg.text.rstrip("\x00")
                self.texts.append(text)
                print(f"  PX4: {text}")
            msg = self.m.recv_match(blocking=False)

    def command(self, cmd, *params, wait=True):
        p = list(params) + [0] * (7 - len(params))
        self.m.mav.command_long_send(self.m.target_system, self.m.target_component, cmd, 0, *p)
        if not wait:
            return None
        end = time.time() + 5
        while time.time() < end:
            ack = self.m.recv_match(type="COMMAND_ACK", blocking=True, timeout=1)
            if ack is not None and ack.command == cmd:
                return ack.result
        return None

    def set_param(self, name, value):
        """Set a PX4 parameter, as the type PX4 reports for it (ints are sent bytewise)."""
        import struct
        m = self.m
        cur = None
        for _ in range(3):      # a request or its reply can be lost on UDP, more so while PX4 starts up
            m.mav.param_request_read_send(m.target_system, m.target_component, name.encode(), -1)
            cur = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=5,
                               condition=f"PARAM_VALUE.param_id=='{name}'")
            if cur is not None:
                break
        if cur is None:
            raise RuntimeError(f"PX4 has no parameter {name}")
        if cur.param_type == MAV.MAV_PARAM_TYPE_REAL32:
            wire = float(value)
        else:
            wire = struct.unpack("<f", struct.pack("<i", int(float(value))))[0]
        m.mav.param_set_send(m.target_system, m.target_component, name.encode(), wire, cur.param_type)
        ack = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=5, condition=f"PARAM_VALUE.param_id=='{name}'")
        print(f"param {name} = {value}" + ("" if ack else " (no echo)"))

    def connect(self):
        print(f"waiting for PX4 on {CONNECT} ...")
        self.m.wait_heartbeat(timeout=120)
        print(f"connected to system {self.m.target_system}")
        for msg_id, hz in ((MAV.MAVLINK_MSG_ID_EXTENDED_SYS_STATE, 4), (MAV.MAVLINK_MSG_ID_VFR_HUD, 10),
                           (MAV.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 10)):
            self.command(MAV.MAV_CMD_SET_MESSAGE_INTERVAL, msg_id, 1e6 / hz)
        end = time.time() + 120
        while self.state["lat"] is None or abs(self.state["lat"]) < 1e-6:
            if time.time() > end:
                raise RuntimeError("no position from PX4")
            self.pump(0.5)
        self.home = (self.state["lat"], self.state["lon"])
        print(f"home {self.home[0]:.6f}, {self.home[1]:.6f}")

    def upload(self, items):
        m = self.m
        m.mav.mission_count_send(m.target_system, m.target_component, len(items), MAV.MAV_MISSION_TYPE_MISSION)
        end = time.time() + 30
        while time.time() < end:
            msg = m.recv_match(type=["MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK"], blocking=True,
                               timeout=5)
            if msg is None:
                continue
            if msg.get_type() == "MISSION_ACK":
                if msg.type != MAV.MAV_MISSION_ACCEPTED:
                    raise RuntimeError(f"mission refused ({msg.type})")
                print(f"mission uploaded: {len(items)} items")
                return
            cmd, params, lat, lon, alt, frame = items[msg.seq]
            m.mav.mission_item_int_send(m.target_system, m.target_component, msg.seq, frame, cmd, 0, 1, *params,
                                        int(round(lat * 1e7)), int(round(lon * 1e7)), alt,
                                        MAV.MAV_MISSION_TYPE_MISSION)
        raise RuntimeError("mission upload timed out")

    def mission(self, approach_speed=None):
        """VTOL takeoff, the circuit, and a VTOL landing at home. With approach_speed, the aircraft
        slows to that airspeed on the final leg, before the back transition."""
        lat0, lon0 = self.home
        nan = float("nan")
        g = MAV.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT
        items = [(MAV.MAV_CMD_NAV_VTOL_TAKEOFF, (0, 0, 0, nan), *offset(lat0, lon0, 300.0, 0.0), TAKEOFF_ALT, g)]
        for n, e in CIRCUIT:
            items.append((MAV.MAV_CMD_NAV_WAYPOINT, (0, 0, 0, nan), *offset(lat0, lon0, n, e), CRUISE_ALT, g))
        if approach_speed:
            items.append((MAV.MAV_CMD_DO_CHANGE_SPEED, (0, approach_speed, -1, 0), 0.0, 0.0, 0.0,
                          MAV.MAV_FRAME_MISSION))
        items.append((MAV.MAV_CMD_NAV_VTOL_LAND, (0, 0, nan, nan), lat0, lon0, 0.0, g))
        return items

    def start(self):
        end = time.time() + 180
        while time.time() < end:
            self.m.set_mode("MISSION")
            self.pump(0.5)
            if self.command(MAV.MAV_CMD_COMPONENT_ARM_DISARM, 1) == MAV.MAV_RESULT_ACCEPTED:
                print("armed in MISSION mode")
                return
            self.pump(3.0)
        raise RuntimeError("PX4 would not arm (see the PX4 messages above)")

    def fly(self):
        """Follow the flight until the aircraft has landed and disarmed (True) or time runs out."""
        wall0, t0 = time.time(), self.state["clock"]
        airborne = False
        last = -1.0
        while time.time() - wall0 < TIMEOUT_WALL and self.state["clock"] - t0 < TIMEOUT:
            self.pump(0.05)
            s = self.state
            t = s["clock"] - t0
            if t - last >= 0.2:
                last = t
                self.rows.append((t, s["alt"], s["airspeed"], s["groundspeed"], s["throttle"], s["vtol"],
                                  s["landed"], s["armed"]))
                if int(t) % 10 == 0 and abs(t - round(t)) < 0.11:
                    print(f"  t={t:5.0f}s alt {s['alt']:6.1f} m  airspeed {s['airspeed']:5.1f} m/s  "
                          f"throttle {s['throttle']:3d} %  {VTOL_STATE.get(s['vtol'], s['vtol'])}, "
                          f"{LANDED.get(s['landed'], s['landed'])}, {s['mode']}")
            airborne = airborne or s["alt"] > 5.0
            if airborne and not s["armed"]:
                return True
        return False


def phases(rows):
    """Start and end times of each VTOL state from the telemetry rows."""
    out, cur, start = [], None, 0.0
    for t, *_, vtol, _landed, armed in rows:
        if vtol != cur:
            if cur is not None:
                out.append((cur, start, t))
            cur, start = vtol, t
    if cur is not None:
        out.append((cur, start, rows[-1][0]))
    return out


def analyse_log(path, plot=None):
    """Hover throttle, transitions and tracking from PX4's ULog of the flight."""
    import numpy as np
    from pyulog import ULog
    log = ULog(path)
    data = {d.name: d.data for d in log.data_list if d.multi_id == 0}
    t0 = log.start_timestamp
    sec = lambda d: (d["timestamp"].astype(np.int64) - np.int64(t0)) / 1e6   # noqa: E731  (uint64 wraps)
    motors = data["actuator_motors"]
    tm = sec(motors)
    vs = data["vtol_vehicle_status"]
    tv, state = sec(vs), vs["vehicle_vtol_state"]
    def state_at(t):
        i = np.searchsorted(tv, t, side="right") - 1
        return np.where(i >= 0, state[np.clip(i, 0, None)], 0)
    lpos = data["vehicle_local_position"]
    tl = sec(lpos)
    alt = -np.interp(tm, tl, lpos["z"])
    vz = np.interp(tm, tl, lpos["vz"])
    vxy = np.hypot(np.interp(tm, tl, lpos["vx"]), np.interp(tm, tl, lpos["vy"]))
    st = state_at(tm)
    hover = (st == 3) & (alt > 8) & (np.abs(vz) < 0.3) & (vxy < 1.0)     # still air: no wing lift
    fw = st == 4
    res = {}
    if hover.any():
        res["hover front motors"] = float(np.nanmean((motors["control[0]"][hover] + motors["control[1]"][hover]) / 2))
        res["hover rear motor"] = float(np.nanmean(motors["control[2]"][hover]))
    if fw.any():
        res["FW front motors"] = float(np.nanmean((motors["control[0]"][fw] + motors["control[1]"][fw]) / 2))
        rear = motors["control[2]"][fw]
        # PX4 sends NaN to a motor it has switched off: the rear lift motor stops in fixed-wing flight.
        res["FW rear motor, highest command (0 = off)"] = float(np.nanmax(rear)) if np.isfinite(rear).any() else 0.0
    for k, (code, name) in enumerate(((1, "front transition"), (2, "back transition"))):
        idx = np.flatnonzero(state == code)
        if idx.size:
            runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
            res[f"{name} (s)"] = float(max(tv[min(r[-1] + 1, len(tv) - 1)] - tv[r[0]] for r in runs))
    if "airspeed_validated" in data and fw.any():
        a = data["airspeed_validated"]
        ta = sec(a)
        st_a = state_at(ta)
        cas = a["calibrated_airspeed_m_s"][st_a == 4]
        if cas.size:
            res["FW airspeed min/mean/max (m/s)"] = (float(cas.min()), float(cas.mean()), float(cas.max()))
    att, sp = data["vehicle_attitude"], data["vehicle_attitude_setpoint"]
    def euler(d, pre):
        w, x, y, z = (d[f"{pre}[{i}]"] for i in range(4))
        roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
        pitch = np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1)))
        return roll, pitch
    ra, pa = euler(att, "q")
    rs, ps = euler(sp, "q_d")
    tsp = sec(sp)
    ta = sec(att)
    res["largest pitch (deg)"] = float(np.max(np.abs(pa)))
    for mode, code in (("MC", 3), ("FW", 4)):
        mask = state_at(tsp) == code
        if mask.any():
            er = np.interp(tsp[mask], ta, ra) - rs[mask]
            ep = np.interp(tsp[mask], ta, pa) - ps[mask]
            res[f"{mode} roll / pitch tracking RMS (deg)"] = (float(np.sqrt(np.mean(er ** 2))),
                                                            float(np.sqrt(np.mean(ep ** 2))))
    if plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(4, 1, figsize=(11, 11), sharex=True)
        shade = [(tv[i], tv[i + 1] if i + 1 < len(tv) else tm[-1], state[i]) for i in range(len(tv))]
        for a_ in ax:
            for t_a, t_b, s_ in shade:
                if s_ in (1, 2, 4):
                    a_.axvspan(t_a, t_b, color={1: "#f6d6a8", 2: "#f6d6a8", 4: "#d8e8f6"}[s_], lw=0)
        ax[0].plot(tl, -lpos["z"], "k")
        ax[0].set_ylabel("altitude (m)")
        if "airspeed_validated" in data:
            ax[1].plot(sec(data["airspeed_validated"]), data["airspeed_validated"]["calibrated_airspeed_m_s"],
                       label="airspeed")
        ax[1].plot(tl, np.hypot(lpos["vx"], lpos["vy"]), alpha=0.6, label="ground speed")
        ax[1].axhline(AIRSPEED[0], color="r", ls=":", lw=1)
        ax[1].set_ylabel("m/s")
        ax[1].legend(loc="upper right")
        for i, lab in enumerate(("motor 1 front right", "motor 2 front left", "motor 3 rear")):
            ax[2].plot(tm, motors[f"control[{i}]"], label=lab)
        if "actuator_servos" in data:
            sv = data["actuator_servos"]
            ax[2].plot(sec(sv), (sv["control[6]"] + 1) / 2, "k--", label="tilt (0 = back stop, 1 = forward)")
        ax[2].set_ylabel("motor thrust (of full), tilt")
        ax[2].legend(loc="upper right", fontsize=8)
        ax[3].plot(ta, pa, label="pitch")
        ax[3].plot(tsp, ps, "--", label="pitch setpoint")
        ax[3].plot(ta, ra, label="roll")
        ax[3].plot(tsp, rs, "--", label="roll setpoint")
        ax[3].set_ylabel("deg")
        ax[3].set_xlabel("time since arming (s); orange: transitions, blue: fixed-wing")
        ax[3].legend(loc="upper right", fontsize=8)
        fig.suptitle(f"VTOL plane, PX4 SITL + Gazebo: {os.path.basename(path)}")
        fig.tight_layout()
        fig.savefig(plot, dpi=110)
        print(f"plot: {plot}")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--connect", default=CONNECT)
    ap.add_argument("--px4", default=os.path.expanduser("~/PX4-Autopilot"), help="PX4-Autopilot tree (for the log)")
    ap.add_argument("--plot", help="write a plot of the flight log to this PNG")
    ap.add_argument("--video", help="film the flight from a chase camera into this MP4 (chase_cam.py)")
    ap.add_argument("--world", default="vtol_field", help="Gazebo world name (for --video)")
    ap.add_argument("--param", action="append", default=[], metavar="NAME=VALUE",
                    help="set a PX4 parameter before the flight (repeatable)")
    ap.add_argument("--approach-speed", type=float, metavar="M/S",
                    help="slow to this airspeed on the final leg, before the back transition")
    args = ap.parse_args()
    f = Flight(args.connect)
    f.connect()
    for p in args.param:
        name, value = p.split("=", 1)
        f.set_param(name.strip(), value.strip())
    f.upload(f.mission(args.approach_speed))
    cam = None
    if args.video:
        os.environ.setdefault("GZ_IP", "127.0.0.1")     # as PX4's make target starts the gz bridge
        from chase_cam import ChaseCam
        cam = ChaseCam(world=args.world)
        cam.spawn()
        time.sleep(2.0)
        cam.record(args.video)
        print(f"filming with the chase camera into {os.path.abspath(args.video)}")
    f.start()
    done = f.fly()
    if cam:
        end = time.time() + 3.0     # a moment on the ground after the landing
        while time.time() < end:
            f.pump(0.1)
        print(f"video: {cam.stop() or 'not written (see the gz server output)'}")
    s = f.state
    checks = []
    ph = phases(f.rows)
    fw = [(a, b) for v, a, b in ph if v == 4]
    checks.append(("took off above 25 m", max(r[1] for r in f.rows) > 25))
    checks.append(("front transition to fixed-wing", bool(fw)))
    checks.append(("every circuit waypoint reached", all(k in f.reached for k in range(1, 1 + len(CIRCUIT)))))
    if fw:
        a, b = fw[0][0] + 5.0, fw[-1][1]
        cruise = [r for r in f.rows if a <= r[0] <= b]
        if cruise:
            lo, hi = min(r[2] for r in cruise), max(r[2] for r in cruise)
            checks.append((f"fixed-wing airspeed {lo:.1f}-{hi:.1f} m/s within {AIRSPEED[0] - 1:.0f}-{AIRSPEED[1]:.0f}",
                           AIRSPEED[0] - 1 <= lo and hi <= AIRSPEED[1]))
            checks.append((f"fixed-wing altitude never below 15 m (lowest {min(r[1] for r in cruise):.1f})",
                           min(r[1] for r in cruise) >= 15))
    checks.append(("back transition to multicopter", any(v == 3 and a > fw[0][1] for v, a, _ in ph) if fw else False))
    bt = [a for v, a, _ in ph if v == 2]
    if bt:
        start = next(r for r in f.rows if r[0] >= bt[0])
        rise = max(r[1] for r in f.rows if r[0] >= bt[0]) - start[1]
        # A glider can climb at most v^2/2g on its airspeed: anything above that came from the rotors
        limit = start[2] ** 2 / (2 * 9.81)
        checks.append((f"back transition climbs {rise:.1f} m, no more than its airspeed buys "
                       f"({start[2]:.1f} m/s: {limit:.1f} m)", rise <= limit))
    landed_d = distance(*f.home, s["lat"], s["lon"]) if s["lat"] else float("inf")
    checks.append((f"landed and disarmed {landed_d:.1f} m from home", done and landed_d < 15))
    bad = [t for t in f.texts if any(w in t.lower() for w in ("failsafe", "critical", "emergency", "crash"))]
    checks.append(("no failsafe or critical messages" + (f": {bad}" if bad else ""), not bad))
    print("\nphases (s since arming):")
    for v, a, b in ph:
        print(f"  {VTOL_STATE.get(v, v):18s} {a:6.1f} - {b:6.1f}")
    logs = sorted(glob.glob(os.path.join(args.px4, "build/px4_sitl_default/rootfs/log/*/*.ulg")),
                  key=os.path.getmtime)
    if logs:
        time.sleep(2)
        print(f"\nPX4 log {logs[-1]}:")
        res = analyse_log(logs[-1], args.plot)
        for k, v in res.items():
            print(f"  {k}: " + (", ".join(f"{x:.3f}" for x in v) if isinstance(v, tuple) else f"{v:.3f}"))
        if "largest pitch (deg)" in res:
            checks.append((f"pitch never past 45 deg (largest {res['largest pitch (deg)']:.1f})",
                           res["largest pitch (deg)"] <= 45))
    print()
    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    failed = [n for n, ok in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
