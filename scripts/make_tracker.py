"""Rewrite the print tables and the totals in tracker.md from viewer/manifest.json: every print
file with its material, printer, copies and sliced mass and time, every PETG plate with what is
on it, and each printer's total with the PETG printed as plates. The Status column and any note
after a name are kept; a file without G-code shows "not sliced", and becomes "sliced" once it
has some.

build_all.py and slice_all.py run this after make_viewer.py; check_parts.py fails if
tracker.md is stale.
Usage: python make_tracker.py
"""
import json
import os
import re
from collections import Counter

import geom as G

PATH = os.path.join(G.ROOT, "tracker.md")
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


def main():
    with open(PATH, "rb") as fh:
        text = fh.read().decode("utf-8")
    new = render(text, *load_manifest())
    if new != text:
        with open(PATH, "wb") as fh:
            fh.write(new.encode("utf-8"))
    print(f"tracker.md: {'updated' if new != text else 'already current'}")


if __name__ == "__main__":
    main()
