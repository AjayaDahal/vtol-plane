"""Serve the 3-D viewer: python scripts/serve_viewer.py [port], then open
http://127.0.0.1:<port>/viewer/ (default port 28765).

Also accepts POST /__capture__/<name>.png from the viewer's capture mode
(http://127.0.0.1:<port>/viewer/?capture=1) and writes the images to renders/. The animations
arrive as frames, POST /__frame__/<name>/<i>.png?ms=<how long it shows>, then
POST /__movie__/<name>.gif?w=<width> writes renders/<name>.gif (needs Pillow).

Only the viewer page, its manifest, the assembly STLs and the print-ready STLs are served;
anything else in the repo (.git included) is 404. It binds to 127.0.0.1, answers only to a
127.0.0.1/localhost Host header (no DNS rebinding), and accepts captures only from its own page
(Origin).
"""
import http.server
import io
import os
import re
import sys
import threading
import urllib.parse

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "renders")
GET_OK = re.compile(r"/viewer(/(index\.html|manifest\.json)?)?|/parts/(assembly|print_ready)/[A-Za-z0-9_\-]+\.stl")
POST_OK = re.compile(r"/__capture__/([a-z0-9_\-]{1,60})\.png")
POST_FRAME = re.compile(r"/__frame__/([a-z0-9_\-]{1,60})/(\d{1,4})\.png\?ms=(\d{1,5})")
POST_MOVIE = re.compile(r"/__movie__/([a-z0-9_\-]{1,60})\.gif\?w=(\d{2,4})")
MAX_UPLOAD = 32 * 1024 * 1024
FRAMES, LOCK = {}, threading.Lock()


def write_gif(frames, path, width):
    """Frames [(PNG bytes, ms)] -> a looping GIF `width` px wide. One palette for every frame (from
    a strip of up to 12 of them), so colours do not flicker; Pillow stores each frame as the
    rectangle that changed."""
    from PIL import Image
    ims = []
    for data, _ in frames:
        im = Image.open(io.BytesIO(data)).convert("RGB")
        ims.append(im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS))
    pick = ims[::max(1, len(ims) // 12)]
    strip = Image.new("RGB", (width, sum(i.height for i in pick)))
    y = 0
    for i in pick:
        strip.paste(i, (0, y))
        y += i.height
    pal = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    out = [i.quantize(palette=pal, dither=Image.Dither.NONE) for i in ims]
    out[0].save(path, save_all=True, append_images=out[1:], duration=[ms for _, ms in frames], loop=0,
                disposal=1, optimize=False)


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"   # keep-alive: the viewer sends hundreds of requests in a row

    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def _local(self, scheme=""):
        port = self.server.server_address[1]
        return {f"{scheme}127.0.0.1:{port}", f"{scheme}localhost:{port}"}

    def send_head(self):
        path = urllib.parse.urlsplit(self.path).path
        if self.headers.get("Host") not in self._local() or not GET_OK.fullmatch(path):
            self.send_error(404)
            return None
        return super().send_head()

    def do_POST(self):
        m, frame, movie = POST_OK.fullmatch(self.path), POST_FRAME.fullmatch(self.path), POST_MOVIE.fullmatch(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if not (m or frame or movie):
            self.send_error(404)
            return
        if self.headers.get("Host") not in self._local() \
                or self.headers.get("Origin") not in self._local("http://") \
                or not (n == 0 if movie else 0 < n <= MAX_UPLOAD):
            self.send_error(403)
            return
        data = self.rfile.read(n) if n else b""
        if movie:
            with LOCK:
                got = FRAMES.pop(movie.group(1), {})
            if not got:
                self.send_error(400)
                return
            os.makedirs(OUT, exist_ok=True)
            write_gif([got[i] for i in sorted(got)], os.path.join(OUT, movie.group(1) + ".gif"), int(movie.group(2)))
            self._ok()
            return
        if not data.startswith(b"\x89PNG"):
            self.send_error(400)
            return
        if frame:
            with LOCK:
                FRAMES.setdefault(frame.group(1), {})[int(frame.group(2))] = (data, int(frame.group(3)))
            self._ok()
            return
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, m.group(1) + ".png"), "wb") as f:
            f.write(data)
        self._ok()

    def _ok(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 128        # the viewer asks for every STL at once
    daemon_threads = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 28765
    with Server(("127.0.0.1", port), Handler) as srv:
        print(f"viewer: http://127.0.0.1:{port}/viewer/   (captures go to {OUT})", flush=True)
        srv.serve_forever()
