"""Chase camera for the Gazebo simulation: films the aircraft from behind, as an MP4.

Gazebo's CameraVideoRecorder system records what a camera sensor sees, on the server, with or
without the GUI. This module spawns a small model carrying such a camera (gravity off, no
collisions) and flies it behind the aircraft with Gazebo's VelocityControl system: each update
gives it the aircraft's own velocity plus a correction toward its place behind it, so between
updates it moves with the aircraft and the picture stays steady. Its heading follows the
aircraft's with a lag, it always looks at the aircraft, and its horizon stays level.
fly_test.py --video uses it. Needs Gazebo's Python bindings (python3-gz-transport13, installed
with Gazebo Harmonic) and a server that can render: under WSL, WSLg's display does.

Service calls go through the gz command line: a blocking request from Python holds the
interpreter lock that the pose subscription's callback needs on gz-transport's shared receive
thread, so its reply would only arrive after the timeout. The camera publishes on its own topic,
outside PX4's GstCameraSystem pattern, so PX4 does not stream it as well.
"""
import math
import os
import shutil
import subprocess
import threading
import time

from gz.msgs10.pose_v_pb2 import Pose_V
from gz.msgs10.twist_pb2 import Twist
from gz.transport13 import Node

NAME = "chase_cam"
SDF = """<?xml version='1.0'?>
<sdf version='1.9'>
<model name='{name}'>
<link name='link'><gravity>false</gravity>
<inertial><mass>0.1</mass><inertia><ixx>1e-3</ixx><ixy>0</ixy><ixz>0</ixz><iyy>1e-3</iyy><iyz>0</iyz>
<izz>1e-3</izz></inertia></inertial>
<sensor name='camera' type='camera'><topic>/{name}/image</topic><always_on>1</always_on>
<update_rate>{fps}</update_rate>
<camera><horizontal_fov>{fov}</horizontal_fov><image><width>{w}</width><height>{h}</height>
<format>R8G8B8</format></image><clip><near>0.1</near><far>3000</far></clip></camera>
<plugin filename='gz-sim-camera-video-recorder-system' name='gz::sim::systems::CameraVideoRecorder'>
<service>/{name}/record_video</service><use_sim_time>true</use_sim_time><fps>{fps}</fps>
<bitrate>{bitrate}</bitrate></plugin></sensor></link>
<plugin filename='gz-sim-velocity-control-system' name='gz::sim::systems::VelocityControl'/>
</model></sdf>"""


def _service(service, reqtype, req, timeout_ms=10000):
    """Call a Gazebo service that answers gz.msgs.Boolean, with the gz command line."""
    try:
        out = subprocess.run(["gz", "service", "-s", service, "--reqtype", reqtype, "--reptype", "gz.msgs.Boolean",
                              "--timeout", str(timeout_ms), "--req", req], capture_output=True, text=True,
                             timeout=timeout_ms / 1000 + 20)
    except subprocess.TimeoutExpired:
        return False
    return "data: true" in out.stdout


def _qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def _qconj(q):
    return q[0], -q[1], -q[2], -q[3]


def _rotate(q, v):
    """Vector v rotated by quaternion q (w, x, y, z)."""
    return _qmul(_qmul(q, (0.0, *v)), _qconj(q))[1:]


def _look(d):
    """Orientation of a camera (x forward, z up) looking along d with its horizon level."""
    yaw = math.atan2(d[1], d[0])
    pitch = math.atan2(-d[2], math.hypot(d[0], d[1]))
    cp, sp, cy, sy = math.cos(pitch / 2), math.sin(pitch / 2), math.cos(yaw / 2), math.sin(yaw / 2)
    return cy * cp, -sy * sp, cy * sp, sy * cp


class ChaseCam:
    def __init__(self, world="vtol_field", target="vtol_plane_0", offset=(-4.5, -2.2, 1.3), turn_lag=1.0,
                 size=(1280, 720), fps=25, fov=1.0, bitrate=6_000_000):
        """offset: the camera's place in the aircraft's heading frame (m; forward, left, up)."""
        self.world, self.target, self.offset, self.turn_lag = world, target, offset, turn_lag
        self.size, self.fps, self.fov, self.bitrate = size, fps, fov, bitrate
        self.node = Node()
        self.lock = threading.Lock()
        self.plane = None               # sim time, position, yaw
        self.vel = (0.0, 0.0, 0.0)
        self.cam = None                 # position, orientation
        self.running = False
        self.path = self.tmp = None
        self.node.subscribe(Pose_V, f"/world/{world}/pose/info", self._on_poses)

    def _on_poses(self, msg):
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        plane = cam = None
        for p in msg.pose:
            if p.name == self.target:
                plane = p
            elif p.name == NAME:
                cam = p
        with self.lock:
            if plane is not None:
                pos = (plane.position.x, plane.position.y, plane.position.z)
                q = plane.orientation
                yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
                if self.plane is not None and t > self.plane[0]:
                    dt = t - self.plane[0]
                    raw = [(pos[i] - self.plane[1][i]) / dt for i in range(3)]
                    a = min(1.0, dt / 0.1)
                    self.vel = tuple(self.vel[i] + a * (raw[i] - self.vel[i]) for i in range(3))
                self.plane = (t, pos, yaw)
            if cam is not None:
                o = cam.orientation
                self.cam = ((cam.position.x, cam.position.y, cam.position.z), (o.w, o.x, o.y, o.z))

    def _goal(self, heading, pos):
        ox, oy, oz = self.offset
        c, s = math.cos(heading), math.sin(heading)
        return pos[0] + c * ox - s * oy, pos[1] + s * ox + c * oy, max(pos[2] + oz, 0.8)

    def spawn(self):
        """Put the camera behind the aircraft and start flying it there."""
        end = time.time() + 15
        while self.plane is None and time.time() < end:
            time.sleep(0.1)
        if self.plane is None:
            raise RuntimeError(f"no pose of {self.target} on /world/{self.world}/pose/info")
        _, pos, yaw = self.plane
        self.heading = yaw
        start = self._goal(yaw, pos)
        q = _look([pos[i] - start[i] for i in range(3)])
        sdf = " ".join(SDF.format(name=NAME, fps=self.fps, fov=self.fov, w=self.size[0], h=self.size[1],
                                  bitrate=self.bitrate).split("\n"))
        req = (f'name: "{NAME}", allow_renaming: false, sdf: "{sdf}", pose: {{position: {{x: {start[0]:.4f}, '
               f'y: {start[1]:.4f}, z: {start[2]:.4f}}}, orientation: {{w: {q[0]:.6f}, x: {q[1]:.6f}, '
               f'y: {q[2]:.6f}, z: {q[3]:.6f}}}}}')
        _service(f"/world/{self.world}/create", "gz.msgs.EntityFactory", req)
        end = time.time() + 30
        while self.cam is None and time.time() < end:
            time.sleep(0.1)
        if self.cam is None:
            raise RuntimeError("the chase camera did not appear in the world")
        self.pub = self.node.advertise(f"/model/{NAME}/cmd_vel", Twist)
        self.running = True
        threading.Thread(target=self._follow, daemon=True).start()

    def _follow(self, kp=2.0, kr=4.0, max_correction=15.0):
        last_t = None
        while self.running:
            with self.lock:
                plane, cam, vel = self.plane, self.cam, self.vel
            if plane is not None and cam is not None:
                t, pos, yaw = plane
                if last_t is not None and t > last_t:
                    turn = (yaw - self.heading + math.pi) % (2 * math.pi) - math.pi
                    self.heading += turn * min(1.0, (t - last_t) / self.turn_lag)
                last_t = t
                c, q = cam
                goal = self._goal(self.heading, pos)
                corr = [kp * (goal[i] - c[i]) for i in range(3)]
                n = math.sqrt(sum(x * x for x in corr))
                if n > max_correction:
                    corr = [x * max_correction / n for x in corr]
                v_body = _rotate(_qconj(q), [vel[i] + corr[i] for i in range(3)])
                qe = _qmul(_qconj(q), _look([pos[i] - c[i] for i in range(3)]))
                if qe[0] < 0:
                    qe = tuple(-x for x in qe)
                s = math.sqrt(qe[1] ** 2 + qe[2] ** 2 + qe[3] ** 2)
                w_body = [kr * 2 * math.atan2(s, qe[0]) * x / s for x in qe[1:]] if s > 1e-9 else [0.0] * 3
                msg = Twist()
                msg.linear.x, msg.linear.y, msg.linear.z = v_body
                msg.angular.x, msg.angular.y, msg.angular.z = w_body
                self.pub.publish(msg)
            time.sleep(1 / 60)

    def record(self, path):
        """Start filming; the MP4 is written to `path` when stop() is called."""
        self.path = os.path.abspath(path)
        self.tmp = f"/tmp/{NAME}_{os.getpid()}.mp4"     # the server's file system: it moves the file there
        if os.path.exists(self.tmp):
            os.remove(self.tmp)
        end = time.time() + 30          # the recorder's service comes up with the camera
        while not _service(f"/{NAME}/record_video", "gz.msgs.VideoRecord",
                           f'start: true, format: "mp4", save_filename: "{self.tmp}"'):
            if time.time() > end:
                raise RuntimeError("the chase camera would not start recording")
            time.sleep(1.0)

    def stop(self, wait=120.0):
        """Stop filming and move the finished file into place. Returns its path, or None."""
        _service(f"/{NAME}/record_video", "gz.msgs.VideoRecord", "stop: true")
        end, size = time.time() + wait, -1
        while time.time() < end:
            if os.path.exists(self.tmp) and os.path.getsize(self.tmp) == size > 0:
                break
            size = os.path.getsize(self.tmp) if os.path.exists(self.tmp) else -1
            time.sleep(1.0)
        self.running = False
        if not (self.tmp and os.path.exists(self.tmp)):
            return None
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        shutil.move(self.tmp, self.path)
        return self.path
