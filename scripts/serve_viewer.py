"""Serve the 3-D viewer: python scripts/serve_viewer.py [port], then open
http://127.0.0.1:<port>/viewer/ (default port 28765).

Also accepts POST /__capture__/<name>.png from the viewer's capture mode
(http://127.0.0.1:<port>/viewer/?capture=1) and writes the images to renders/.

Only the viewer page, its manifest and the assembly STLs are served; anything else in the
repo (.git included) is 404. It binds to 127.0.0.1, answers only to a 127.0.0.1/localhost
Host header (no DNS rebinding), and accepts captures only from its own page (Origin).
"""
import http.server
import os
import re
import sys
import urllib.parse

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "renders")
GET_OK = re.compile(r"/viewer(/(index\.html|manifest\.json)?)?|/parts/assembly/[A-Za-z0-9_\-]+\.stl")
POST_OK = re.compile(r"/__capture__/([a-z0-9_\-]{1,60})\.png")
MAX_UPLOAD = 32 * 1024 * 1024


class Handler(http.server.SimpleHTTPRequestHandler):
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
        m = POST_OK.fullmatch(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if not m:
            self.send_error(404)
            return
        if self.headers.get("Host") not in self._local() \
                or self.headers.get("Origin") not in self._local("http://") or not 0 < n <= MAX_UPLOAD:
            self.send_error(403)
            return
        data = self.rfile.read(n)
        if not data.startswith(b"\x89PNG"):
            self.send_error(400)
            return
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, m.group(1) + ".png"), "wb") as f:
            f.write(data)
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


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 28765
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler) as srv:
        print(f"viewer: http://127.0.0.1:{port}/viewer/   (captures go to {OUT})", flush=True)
        srv.serve_forever()
