"""Rewrite the print tables and the totals in tracker.md from viewer/manifest.json: every print
file with its material, printer, copies and sliced mass and time, every PETG plate with what is
on it, and each printer's total with the PETG printed as plates. The Status column and any note
after a name are kept; a file without G-code shows "not sliced", and becomes "sliced" once it
has some. Also draws the two printers' queues as renders/print_schedule.svg (README.md).

build_all.py and slice_all.py run this after make_viewer.py; check_parts.py fails if
tracker.md or the chart is stale.
Usage: python make_tracker.py
"""
import json
import os
import re
from collections import Counter
from xml.sax.saxutils import escape

import geom as G

PATH = os.path.join(G.ROOT, "tracker.md")
SVG = os.path.join(G.ROOT, "renders", "print_schedule.svg")
MAT = {"lwpla": "LW-PLA vase", "petg": "PETG"}
PRN = {"s1": "S1", "x": "X"}
ORDER = [("lwpla", "s1"), ("lwpla", "x"), ("petg", "s1"), ("petg", "x")]
TABLE = re.compile(r"\| Part \| Material \| Printer \| Qty \|[^\n]*\n(?:\|[^\n]*\n)*")
PLATES = re.compile(r"\| Plate \| Printer \|[^\n]*\n(?:\|[^\n]*\n)*")
TOTALS = re.compile(r"\| Printer \| What \|[^\n]*\n(?:\|[^\n]*\n)*")
NAME = re.compile(r"`([^`]+)`(?: \((.*)\))?")


def hours(minutes):
    h, m = divmod(int(round(minutes)), 60)
    return f"{h}h {m:02d}m"


def kept(table):
    """Note and status of each row in an existing table."""
    out = {}
    for line in table.splitlines()[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = NAME.fullmatch(cells[0])
        if m:
            out[m.group(1)] = (m.group(2), cells[-1])
    return out


def _row_status(old, name, sliced):
    note, status = old.get(name, (None, None))
    if not sliced:
        status = "not sliced"
    elif status in (None, "not sliced"):
        status = "sliced"
    return f"`{name}`" + (f" ({note})" if note else ""), status


def _replace(body, pattern, lines, what):
    m = pattern.search(body)
    if not m:
        raise ValueError(f"tracker.md: {what} not found")
    return body[:m.start()] + "\n".join(lines) + "\n" + body[m.end():]


def render(text, prints, plates):
    """tracker.md's text with the part table, the plate table and the totals made from the
    manifest's `prints` and `plates`."""
    nl = "\r\n" if "\r\n" in text else "\n"
    body = text.replace("\r\n", "\n")
    for pattern, what in ((TABLE, "part table"), (PLATES, "plate table"), (TOTALS, "totals table")):
        if not pattern.search(body):
            raise ValueError(f"tracker.md: {what} not found")
    old = kept(TABLE.search(body).group(0))
    lines = ["| Part | Material | Printer | Qty | Mass each (g) | Time each | Status |",
             "|---|---|---|---|---|---|---|"]
    for p in sorted(prints, key=lambda p: (ORDER.index((p["material"], p["printer"])), p["name"])):
        name, status = _row_status(old, p["name"], p["grams"] is not None)
        grams = "?" if p["grams"] is None else f"{p['grams']:.1f}"
        time = "?" if p["minutes"] is None else hours(p["minutes"])
        lines.append(f"| {name} | {MAT[p['material']]} | {PRN[p['printer']]} | {p['qty']} | {grams} | {time} | {status} |")
    body = _replace(body, TABLE, lines, "part table")

    old = kept(PLATES.search(body).group(0))
    lines = ["| Plate | Printer | On it | Mass (g) | Time | Status |", "|---|---|---|---|---|---|"]
    for q in plates:
        name, status = _row_status(old, q["name"], q["grams"] is not None)
        on = ", ".join(f"`{n}`" + (f" ×{c}" if c > 1 else "") for n, c in q["contents"])
        grams = "?" if q["grams"] is None else f"{q['grams']:.1f}"
        time = "?" if q["minutes"] is None else hours(q["minutes"])
        lines.append(f"| {name} | {PRN[q['printer']]} | {on} | {grams} | {time} | {status} |")
    body = _replace(body, PLATES, lines, "plate table")

    # Totals as it is meant to be printed: LW-PLA one part per job, PETG as plates (any PETG
    # copies on no plate as single files).
    plated = Counter()
    for q in plates:
        for n, c in q["contents"]:
            plated[n] += c
    lines = ["| Printer | What | Jobs | Mass | Time |", "|---|---|---|---|---|"]

    def fmt(jobs, g, m):
        return f"{jobs} | {g:.0f} g | {m / 60:.1f} h |"
    for pr in ("s1", "x"):
        rows = []
        lw = [p for p in prints if p["printer"] == pr and p["material"] == "lwpla"]
        if lw:
            rows.append(("LW-PLA vase, one part per job", sum(p["qty"] for p in lw),
                         sum((p["grams"] or 0) * p["qty"] for p in lw), sum((p["minutes"] or 0) * p["qty"] for p in lw)))
        pq = [q for q in plates if q["printer"] == pr]
        if pq:
            rows.append((f"PETG, {len(pq)} plates", len(pq), sum(q["grams"] or 0 for q in pq),
                         sum(q["minutes"] or 0 for q in pq)))
        loose = [(p, p["qty"] - plated[p["name"]]) for p in prints
                 if p["printer"] == pr and p["material"] == "petg" and p["qty"] > plated[p["name"]]]
        if loose:
            rows.append(("PETG, single files", sum(c for _, c in loose), sum((p["grams"] or 0) * c for p, c in loose),
                         sum((p["minutes"] or 0) * c for p, c in loose)))
        for what, jobs, g, m in rows:
            lines.append(f"| {PRN[pr]} | {what} | " + fmt(jobs, g, m))
        if len(rows) > 1:
            lines.append(f"| {PRN[pr]} | total | " + fmt(*(sum(r[i] for r in rows) for i in (1, 2, 3))))
    single = [p for p in prints if p["material"] == "petg"]
    if plates and single:
        lines.append("| S1 | for comparison: the same PETG as single files (reprints) | " +
                     fmt(sum(p["qty"] for p in single), sum((p["grams"] or 0) * p["qty"] for p in single),
                         sum((p["minutes"] or 0) * p["qty"] for p in single)))
    body = _replace(body, TOTALS, lines, "totals table")
    return body.replace("\n", nl)


def load_manifest():
    with open(os.path.join(G.ROOT, "viewer", "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    return man["prints"], man.get("plates", [])


# The suggested order (tracker.md): the test prints first, then each printer's LW-PLA, then plates.
FIRST = ["wing_tip_r", "petg_1_fit_tests", "tip_fairing_r", "wing_mid_r"]
PRINTERS = {"s1": "Kobra S1", "x": "Kobra X"}


def queues(prints, plates):
    """Each printer's jobs in order: (name, copies, minutes each, kind), kind lwpla/petg/plate."""
    plated = Counter()
    for q in plates:
        for n, c in q["contents"]:
            plated[n] += c
    jobs = [(p["name"], p["printer"], p["qty"] - (plated[p["name"]] if p["material"] == "petg" else 0),
             p["minutes"] or 0.0, p["material"]) for p in prints]
    jobs = [j for j in jobs if j[2] > 0] + [(q["name"], q["printer"], 1, q["minutes"] or 0.0, "plate") for q in plates]
    rank = {n: i for i, n in enumerate(FIRST)}
    jobs.sort(key=lambda j: (rank.get(j[0], len(FIRST)), j[4] == "plate", j[0]))
    return {pr: [(n, c, m, k) for n, p, c, m, k in jobs if p == pr] for pr in PRINTERS}


def schedule_svg(prints, plates):
    """Both printers' queues as a Gantt chart, one row per job, each printer starting at 0 h."""
    qs = queues(prints, plates)
    span = max(sum(c * m for _, c, m, _ in q) for q in qs.values()) / 60
    hmax = max(4, 4 * -(-span // 4))
    left, width, row, head = 190, 600, 19, 30
    x = lambda h: left + width * h / hmax
    rows = sum(len(q) for q in qs.values())
    top = 80
    height = top + len(qs) * head + rows * row + 58
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" '
           f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="12">',
           '<rect width="900" height="100%" rx="8" fill="#f6f8fa"/>',
           '<text x="24" y="28" font-size="16" font-weight="600" fill="#1f2328">Print queue, both printers '
           'running at once</text>',
           '<text x="24" y="46" fill="#59636e">Sliced times (Anycubic Slicer Next). Test prints first: check '
           'them before the rest (tracker.md).</text>']
    for h in range(0, int(hmax) + 1, 4):
        out.append(f'<line x1="{x(h):.1f}" y1="{top - 4}" x2="{x(h):.1f}" y2="{height - 48}" stroke="#d1d9e0"/>')
        out.append(f'<text x="{x(h):.1f}" y="{top - 8}" text-anchor="middle" fill="#59636e">{h} h</text>')
    y = top
    for pr, q in qs.items():
        total = sum(c * m for _, c, m, _ in q)
        out.append(f'<text x="24" y="{y + 20}" font-weight="600" fill="#1f2328">{PRINTERS[pr]}</text>')
        out.append(f'<text x="{left}" y="{y + 20}" fill="#59636e">{sum(c for _, c, _, _ in q)} jobs, '
                   f'{total / 60:.1f} h</text>')
        y += head
        t = 0.0
        for name, copies, minutes, kind in q:
            fill, stroke = ("#2f6db5", "#1f4f8a") if kind != "lwpla" else ("#e6dfcc", "#a59c84")
            label = escape(name + (f" ×{copies}" if copies > 1 else ""))
            dur = copies * minutes
            test = name in FIRST
            out.append(f'<text x="40" y="{y + 13}" fill="{"#bc4c00" if test else "#1f2328"}">{label}</text>')
            out.append(f'<rect x="{x(t / 60):.1f}" y="{y + 3}" width="{max(1.5, x(dur / 60) - left):.1f}" height="13" '
                       f'rx="2" fill="{fill}" stroke="{"#e36209" if test else stroke}" '
                       f'stroke-width="{2 if test else 1}"/>')
            out.append(f'<text x="{x((t + dur) / 60) + 5:.1f}" y="{y + 13}" fill="#59636e">'
                       f'{f"{round(dur)} min" if dur < 59.5 else hours(dur)}</text>')
            t += dur
            y += row
    y += 22
    for i, (fill, stroke, text) in enumerate([("#e6dfcc", "#a59c84", "LW-PLA, vase mode, one part per job"),
                                              ("#2f6db5", "#1f4f8a", "PETG plate"),
                                              ("#ffffff", "#e36209", "test print: check it first")]):
        lx = 24 + 290 * i
        out.append(f'<rect x="{lx}" y="{y - 10}" width="22" height="12" rx="2" fill="{fill}" stroke="{stroke}" '
                   f'stroke-width="{2 if i == 2 else 1}"/>')
        out.append(f'<text x="{lx + 30}" y="{y}" fill="#1f2328">{text}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def expected(text, prints, plates):
    """What tracker.md and the schedule chart should hold, by path."""
    return {PATH: render(text, prints, plates), SVG: schedule_svg(prints, plates)}


def read_text(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")


def main():
    want = expected(read_text(PATH), *load_manifest())
    for path, new in want.items():
        old = read_text(path)
        if new != old:
            with open(path, "wb") as fh:
                fh.write(new.encode("utf-8"))
        print(f"{os.path.relpath(path, G.ROOT)}: {'updated' if new != old else 'already current'}")


if __name__ == "__main__":
    main()
