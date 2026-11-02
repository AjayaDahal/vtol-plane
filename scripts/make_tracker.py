"""Rewrite the print table and the totals in tracker.md from viewer/manifest.json: every print
file with its material, printer, copies and sliced mass and time. The Status column and any
note after a part's name are kept; a part without G-code shows "not sliced", and becomes
"sliced" once it has some.

build_all.py and slice_all.py run this after make_viewer.py; check_parts.py fails if
tracker.md is stale.
Usage: python make_tracker.py
"""
import json
import os
import re

import geom as G

PATH = os.path.join(G.ROOT, "tracker.md")
MAT = {"lwpla": "LW-PLA vase", "petg": "PETG"}
PRN = {"s1": "S1", "x": "X"}
ORDER = [("lwpla", "s1"), ("lwpla", "x"), ("petg", "s1"), ("petg", "x")]
TABLE = re.compile(r"\| Part \| Material \| Printer \| Qty \|[^\n]*\n(?:\|[^\n]*\n)*")
TOTALS = re.compile(r"\| Printer \| Material \| Mass \| Time \|[^\n]*\n(?:\|[^\n]*\n)*")
NAME = re.compile(r"`([^`]+)`(?: \((.*)\))?")


def hours(minutes):
    h, m = divmod(int(round(minutes)), 60)
    return f"{h}h {m:02d}m"


def kept(table):
    """Note and status of each part in the existing table."""
    out = {}
    for line in table.splitlines()[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = NAME.fullmatch(cells[0])
        if m:
            out[m.group(1)] = (m.group(2), cells[-1])
    return out


def render(text, prints):
    """tracker.md's text with the print table and totals made from `prints`."""
    nl = "\r\n" if "\r\n" in text else "\n"
    body = text.replace("\r\n", "\n")
    table, totals = TABLE.search(body), TOTALS.search(body)
    if not table or not totals:
        raise ValueError("tracker.md: print table or totals table not found")
    old = kept(table.group(0))
    lines = ["| Part | Material | Printer | Qty | Mass each (g) | Time each | Status |",
             "|---|---|---|---|---|---|---|"]
    for p in sorted(prints, key=lambda p: (ORDER.index((p["material"], p["printer"])), p["name"])):
        note, status = old.get(p["name"], (None, None))
        if p["grams"] is None:
            status = "not sliced"
        elif status in (None, "not sliced"):
            status = "sliced"
        name = f"`{p['name']}`" + (f" ({note})" if note else "")
        grams = "?" if p["grams"] is None else f"{p['grams']:.1f}"
        time = "?" if p["minutes"] is None else hours(p["minutes"])
        lines.append(f"| {name} | {MAT[p['material']]} | {PRN[p['printer']]} | {p['qty']} | {grams} | {time} | {status} |")
    sums = {}
    for p in prints:
        g, t = sums.get((p["material"], p["printer"]), (0.0, 0.0))
        sums[(p["material"], p["printer"])] = (g + (p["grams"] or 0.0) * p["qty"], t + (p["minutes"] or 0.0) * p["qty"])
    tlines = ["| Printer | Material | Mass | Time |", "|---|---|---|---|"]
    for k in ORDER:
        if k in sums:
            tlines.append(f"| {PRN[k[1]]} | {'LW-PLA' if k[0] == 'lwpla' else 'PETG'} | {sums[k][0]:.0f} g | {sums[k][1] / 60:.1f} h |")
    body = body[:table.start()] + "\n".join(lines) + "\n" + body[table.end():]
    totals = TOTALS.search(body)
    body = body[:totals.start()] + "\n".join(tlines) + "\n" + body[totals.end():]
    return body.replace("\n", nl)


def prints_from_manifest():
    with open(os.path.join(G.ROOT, "viewer", "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)["prints"]


def main():
    with open(PATH, "rb") as fh:
        text = fh.read().decode("utf-8")
    new = render(text, prints_from_manifest())
    if new != text:
        with open(PATH, "wb") as fh:
            fh.write(new.encode("utf-8"))
    print(f"tracker.md: {'updated' if new != text else 'already current'}")


if __name__ == "__main__":
    main()
