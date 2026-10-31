#!/usr/bin/env python3
"""Misc small parts (build123d, PETG).

  battery_tray.stl : 160x60x3 mm plate that sits on the fuselage floor
    under the battery, with two Velcro strap slots (30x5 mm). The
    battery + tray slide in through the front when the removable nose
    (fuse_1) is off — there is no separate battery hatch.
"""
import os

from build123d import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "parts")


def battery_tray():
    part = Box(160, 60, 3)
    for sx in (-55, 55):
        part -= Pos(sx, 0, 0) * Box(5, 40, 5)
    return part


def main():
    os.makedirs(OUT, exist_ok=True)
    part = battery_tray()
    path = os.path.join(OUT, "battery_tray.stl")
    export_stl(part, path)
    print(f"battery_tray.stl: vol={part.volume:.0f} mm^3")


if __name__ == "__main__":
    main()
