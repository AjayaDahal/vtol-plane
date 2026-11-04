"""Slice previews: pictures of what the slicer prints, drawn from the G-code the way its preview
draws it: every extrusion a line, coloured by what it is (walls, infill, bridges, brims, supports,
the printer's purge line), over the bed.

- renders/48_sliced_plates_x_lwpla.png: the Kobra X project's 22 plates (one LW-PLA skin each).
- renders/49_sliced_plates_s1_petg.png: the Kobra S1 project's seven PETG plates.
- renders/50_first_layers_s1_petg.png: the PETG plates' first layers from above: what touches the
  bed, the brims and the purge line.

Each plate is drawn from its job's G-code in gcode/, which the plate slices to (make_projects.py
--verify, run by build_all.py, slices every plate of both projects and compares). Each picture
carries a hash of the G-code it shows, and check_parts.py fails when it is stale. build_all.py
and slice_all.py run this after slicing; audit_print.py --render uses draw() for the support audit.

Run: python scripts/preview_slices.py
"""
import hashlib
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

import geom as G

# The slicer's feature types (";TYPE:" in the G-code), coloured roughly as its preview colours them.
COLORS = {
    "Outer wall": (255, 140, 30),
    "Inner wall": (250, 205, 70),
    "Overhang wall": (30, 160, 255),
    "Sparse infill": (175, 55, 50),
    "Internal solid infill": (150, 95, 205),
    "Top surface": (230, 60, 60),
    "Bottom surface": (110, 100, 200),
    "Bridge": (30, 90, 220),
    "Internal Bridge": (80, 140, 230),
    "Gap infill": (235, 235, 235),
    "Brim": (20, 160, 120),
    "Skirt": (20, 160, 120),
    "Support": (235, 25, 235),
    "Support interface": (255, 125, 255),
    "Support transition": (235, 25, 235),
    "Custom": (120, 120, 120),
}
NAMES = list(COLORS)
OTHER = len(NAMES)
LEGEND = {"Custom": "Purge line (printer start)"}
WALLS = [NAMES.index(n) for n in ("Outer wall", "Inner wall", "Overhang wall")]
OUTER = [NAMES.index(n) for n in ("Outer wall", "Overhang wall")]
SUPPORT = [NAMES.index(n) for n in ("Support", "Support interface", "Support transition")]
KEY = "vtol_gcode_sha256"
OUT = {"x": "48_sliced_plates_x_lwpla.png", "s1": "49_sliced_plates_s1_petg.png",
       "first": "50_first_layers_s1_petg.png"}
SS = 2   # supersampling


def parse(path, unknown=None):
    """Every extrusion move in the file: (N, 6) float32 rows x0 y0 z0 x1 y1 z1, and the feature
    type of each (index into NAMES, OTHER if unknown; unknown: a set that collects those names)."""
    idx = {n: i for i, n in enumerate(NAMES)}
    rows, kinds = [], []
    x = y = z = 0.0
    t = OTHER
    with open(path, errors="ignore") as f:
        for line in f:
            if line[0] == ";":
                if line.startswith(";TYPE:"):
                    t = idx.get(line[6:].strip(), OTHER)
                    if t == OTHER and unknown is not None:
                        unknown.add(line[6:].strip())
                continue
            if not line.startswith(("G1 ", "G0 ")):
                continue
            nx, ny, nz, e = x, y, z, 0.0
            for tok in line.split(";", 1)[0].split()[1:]:
                k = tok[0]
                if k == "X":
                    nx = float(tok[1:])
                elif k == "Y":
                    ny = float(tok[1:])
                elif k == "Z":
                    nz = float(tok[1:])
                elif k == "E":
                    e = float(tok[1:])
            if e > 0 and (nx != x or ny != y):
                rows.append((x, y, z, nx, ny, nz))
                kinds.append(t)
            x, y, z = nx, ny, nz
    return np.array(rows, np.float32).reshape(-1, 6), np.array(kinds, np.int16)


def _font(size):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _project(p, az, el):
    """Screen right, screen up and depth (larger = farther) of world points, for a camera at
    azimuth az (deg; 0 looks from the bed's front edge towards +y) and elevation el (deg)."""
    a, e = math.radians(az), math.radians(el)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    xr = x * math.cos(a) - y * math.sin(a)
    yr = x * math.sin(a) + y * math.cos(a)
    return xr, z * math.cos(e) + yr * math.sin(e), yr * math.cos(e) - z * math.sin(e)


def draw(segs, kinds, size, bed=None, zmax=None, az=-30.0, el=32.0, top=False, xray=False,
         width=1.0, margin=12):
    """One picture of the toolpaths. bed: (w, d) of the printable area, drawn under the parts and
    used for the framing (with zmax, the height to leave room for), so plates of one printer come
    out at one scale; without it the picture is framed to the toolpaths. top: straight down.
    xray: everything pale and the supports drawn over it, so they show inside the part."""
    W, H = size
    if top:
        az, el = 0.0, 90.0
    pts = segs.reshape(-1, 3)
    frame = [pts] if len(pts) else []
    if bed is not None:
        bx, by = bed
        frame.append(np.array([[0, 0, 0], [bx, 0, 0], [bx, by, 0], [0, by, 0]], float))
        if zmax:
            frame.append(np.array([[0, 0, zmax], [bx, 0, zmax], [bx, by, zmax], [0, by, zmax]], float))
    allp = np.concatenate(frame)
    u, v, _ = _project(allp, az, el)
    du, dv = max(float(np.ptp(u)), 1e-6), max(float(np.ptp(v)), 1e-6)
    s = min((W - 2 * margin) / du, (H - 2 * margin) / dv)
    ou = margin + ((W - 2 * margin) - du * s) / 2 - float(u.min()) * s
    ov = margin + ((H - 2 * margin) - dv * s) / 2 - float(v.min()) * s

    def screen(p):
        uu, vv, dd = _project(p, az, el)
        return (uu * s + ou) * SS, (H - (vv * s + ov)) * SS, dd

    img = Image.new("RGB", (W * SS, H * SS), (250, 250, 252))
    dr = ImageDraw.Draw(img)
    if bed is not None:
        bx, by = bed
        cu, cv, _ = screen(np.array([[0, 0, 0], [bx, 0, 0], [bx, by, 0], [0, by, 0]], float))
        dr.polygon(list(zip(cu.tolist(), cv.tolist())), fill=(214, 217, 224), outline=(140, 144, 155))
        for g in np.arange(50.0, max(bx, by), 50.0):
            for a0, a1 in ((np.array([g, 0, 0]), np.array([g, by, 0])), (np.array([0, g, 0]), np.array([bx, g, 0]))):
                if (a0[0] <= bx and a1[0] <= bx) and (a0[1] <= by and a1[1] <= by):
                    gu, gv, _ = screen(np.array([a0, a1], float))
                    dr.line((gu[0], gv[0], gu[1], gv[1]), fill=(200, 203, 211), width=SS)
    if not len(segs):
        return img.resize((W, H), Image.LANCZOS)
    x0, y0, d0 = screen(segs[:, 0:3])
    x1, y1, d1 = screen(segs[:, 3:6])
    # An outer wall wins a near-tie in depth: what lies just inside it (gap infill, inner walls)
    # would otherwise show through the 1-pixel lines.
    depth = (d0 + d1) / 2 - np.where(np.isin(kinds, OUTER), 0.5, 0.0)
    base = np.array([COLORS[n] for n in NAMES] + [(160, 160, 160)], float)[kinds]
    # Walls are shaded by how squarely they face the camera, so a skin reads as a surface.
    a = math.radians(az)
    look = np.array([math.sin(a), math.cos(a)])
    dx, dy = segs[:, 3] - segs[:, 0], segs[:, 4] - segs[:, 1]
    ln = np.hypot(dx, dy) + 1e-9
    face = np.abs(dy / ln * look[0] - dx / ln * look[1])
    shade = np.where(np.isin(kinds, WALLS), 0.4 + 0.6 * face, 0.95)
    if top:
        shade = np.full(len(segs), 1.0)
    sup = np.isin(kinds, SUPPORT)
    if xray:
        col = 255 - (255 - np.full_like(base, 150.0)) * shade[:, None] * 0.35
        col[sup] = base[sup]
    else:
        col = base * shade[:, None]
    col = np.clip(col, 0, 255).astype(np.uint8)
    lw = max(1, int(round(width * SS)))
    coords = np.stack([x0, y0, x1, y1], axis=1).tolist()
    cols = [tuple(c) for c in col.tolist()]
    order = np.argsort(-depth, kind="stable")
    if xray:   # the part first, then the supports over it
        order = np.concatenate([order[~sup[order]], order[sup[order]]])
    for i in order.tolist():
        dr.line(coords[i], fill=cols[i], width=lw * (2 if xray and sup[i] else 1))
    return img.resize((W, H), Image.LANCZOS)


def _wrap(dr, text, font, width):
    """text broken at spaces into lines no wider than width pixels."""
    lines = []
    for word in text.split():
        if lines and dr.textlength(f"{lines[-1]} {word}", font=font) <= width:
            lines[-1] = f"{lines[-1]} {word}"
        else:
            lines.append(word)
    return lines or [""]


def sheet(cells, cols, title, note, kinds_used, width=None, extra=()):
    """Pictures in a grid under a title, each with its caption lines (wrapped to the picture's
    width), and a colour legend: any extra (label, colour) entries, then the feature types used."""
    cw, ch = cells[0][0].size
    pad = 14
    f1, f2 = _font(15), _font(13)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    caps = [(_wrap(probe, l1, f1, cw - 8), _wrap(probe, l2, f2, cw - 8)) for _, l1, l2 in cells]
    n1 = max(len(a) for a, _ in caps)
    n2 = max(len(b) for _, b in caps)
    cap = 9 + 20 * n1 + 17 * n2
    rows = math.ceil(len(cells) / cols)
    W = width or cols * (cw + pad) + pad
    head = 84
    legend = 44
    H = head + rows * (ch + cap + pad) + legend + pad
    out = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(out)
    dr.text((pad, 10), title, fill=(25, 28, 35), font=_font(26))
    dr.text((pad, 48), note, fill=(85, 90, 100), font=_font(16))
    for i, ((img, _, _), (l1, l2)) in enumerate(zip(cells, caps)):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = head + r * (ch + cap + pad)
        out.paste(img, (x, y + cap))
        dr.rectangle((x, y + cap, x + cw - 1, y + cap + ch - 1), outline=(215, 218, 225))
        for j, t in enumerate(l1):
            dr.text((x + 4, y + 4 + 20 * j), t, fill=(25, 28, 35), font=f1)
        for j, t in enumerate(l2):
            dr.text((x + 4, y + 4 + 20 * n1 + 17 * j), t, fill=(95, 100, 110), font=f2)
    x, y = pad, H - legend
    entries = list(extra) + [(LEGEND.get(k, k), COLORS[k]) for k in sorted(set(kinds_used), key=NAMES.index)]
    for label, colour in entries:
        dr.rectangle((x, y + 8, x + 18, y + 26), fill=colour, outline=(90, 90, 90))
        dr.text((x + 24, y + 7), label, fill=(40, 44, 52), font=_font(15))
        x += 24 + int(dr.textlength(label, font=_font(15))) + 22
    return out


def _stats(job):
    """'12.3 g, 1 h 05 min': the slicer's estimate for a part's or a plate's G-code."""
    import make_viewer
    grams, minutes = make_viewer.gcode_stats(job)
    if grams is None or minutes is None:
        return "not sliced"
    hours, mins = divmod(int(round(minutes)), 60)
    return f"{grams:.1f} g, {hours} h {mins:02d} min"


def sources():
    """What each picture shows, cell by cell, in drawing order: {picture: [(label, G-code path),
    ...]}, one cell per plate of the printer's complete project (make_projects.jobs())."""
    import make_projects as MP
    x = [(label, g) for label, _, g, _, _ in MP.jobs("x")]
    s1 = [(label, g) for label, _, g, _, _ in MP.jobs("s1")]
    return {OUT["x"]: x, OUT["s1"]: s1, OUT["first"]: s1}


def stamp(cells):
    """Hash of a picture's cells: each one's label, and the name and bytes of its G-code. A plate
    renamed, put on hold or added changes it as well as a re-slice."""
    h, digest = hashlib.sha256(), {}
    for label, p in cells:
        if p not in digest:
            with open(p, "rb") as f:
                digest[p] = hashlib.sha256(f.read()).digest()
        h.update(f"{label}\n{os.path.basename(p)}\n".encode())
        h.update(digest[p])
    return h.hexdigest()


def _save(img, name, cells):
    info = PngInfo()
    info.add_text(KEY, stamp(cells))
    path = os.path.join(G.ROOT, "renders", name)
    img.save(path, pnginfo=info, optimize=True)
    print(f"wrote {os.path.relpath(path, G.ROOT)} ({os.path.getsize(path) // 1024} KB)")


def bed_size(printer):
    import slice_all as SA
    import json
    with open(os.path.join(SA.PROFILES, SA.MACHINE[printer])) as f:
        prof = json.load(f)
    area = np.array([[float(c) for c in p.split("x")] for p in prof["printable_area"]])
    return tuple((area.max(0) - area.min(0)).tolist()), float(prof["printable_height"])


def main():
    import make_projects as MP
    src = sources()
    used = {"x": set(), "s1": set()}
    parsed = {}

    def load(path):
        if path not in parsed:
            parsed[path] = parse(path)
        return parsed[path]

    # Kobra X: one skin per plate, all at one scale.
    bed, height = bed_size("x")
    cells, drawn = [], {}
    for label, job, gcode, _, _ in MP.jobs("x"):
        if gcode not in drawn:
            segs, kinds = load(gcode)
            used["x"].update(NAMES[k] for k in np.unique(kinds) if k < OTHER)
            drawn[gcode] = draw(segs, kinds, (330, 400), bed=bed, zmax=240.0, az=-35.0, el=30.0)
        cells.append((drawn[gcode], label, _stats(job)))
    note = ("Every plate of 3mf/complete_project_kobra_x_lwpla.3mf as the slicer prints it: one vase-mode skin per plate, "
            "a single spiral wall on an 8 mm brim, no supports.")
    _save(sheet(cells, 6, f"Kobra X, LW-PLA: {len(cells)} plates, sliced", note, used["x"]), OUT["x"], src[OUT["x"]])
    parsed.clear()

    # Kobra S1: the PETG plates, and their first layers from above.
    bed, height = bed_size("s1")
    cells, firsts = [], []
    for label, job, gcode, _, _ in MP.jobs("s1"):
        segs, kinds = load(gcode)
        used["s1"].update(NAMES[k] for k in np.unique(kinds) if k < OTHER)
        cells.append((draw(segs, kinds, (720, 520), bed=bed, zmax=80.0, az=-30.0, el=38.0, width=0.8),
                      label, _stats(job)))
        z1 = float(segs[:, 2].min()) if len(segs) else 0.0
        first = segs[:, 2] <= z1 + 0.05
        firsts.append((draw(segs[first], kinds[first], (520, 540), bed=bed, top=True, width=1.0),
                       label, "first layer from above"))
        parsed.clear()
    note = ("Every plate of 3mf/complete_project_kobra_s1_petg.3mf as the slicer prints it: no supports; brims only on the "
            "parts that stand tall on a small base; bridges (blue) over holes and pockets.")
    _save(sheet(cells, 4, f"Kobra S1, PETG: {len(cells)} plates, sliced", note, used["s1"]), OUT["s1"], src[OUT["s1"]])
    note = (f"First layer of each PETG plate, from above, on the {bed[0]:.0f} x {bed[1]:.0f} mm bed: the brims (green) "
            "and, beyond the bed's back edge, the printer's purge line.")
    _save(sheet(firsts, 4, "Kobra S1, PETG: first layers", note, used["s1"]), OUT["first"], src[OUT["first"]])


if __name__ == "__main__":
    sys.exit(main())
