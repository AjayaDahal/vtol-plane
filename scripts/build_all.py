"""Regenerate everything in order: skins, PETG parts, print orientation, slicing, viewer
manifest, the print table in tracker.md, checks. The manifest and the tracker come after
slicing because they carry each file's sliced mass and print time.

Usage: python build_all.py [--no-slice]
"""
import os
import shutil
import subprocess
import sys

import geom as G
import make_print_ready
import make_tracker
import make_viewer
import skins
import structure


def main():
    shutil.rmtree(G.ASSEMBLY, ignore_errors=True)
    skins.build()
    structure.build()
    make_print_ready.build()
    args = []
    try:
        if "--no-slice" in sys.argv:
            print("--no-slice: G-code checks skipped; run slice_all.py before printing")
            args.append("--no-gcode")
        else:
            import slice_all
            slice_all.main()
    finally:
        # Even when a part fails to slice: the viewer needs the new geometry.
        make_viewer.main()
        make_tracker.main()
    here = os.path.dirname(os.path.abspath(__file__))
    sys.exit(subprocess.call([sys.executable, "check_parts.py", *args], cwd=here))


if __name__ == "__main__":
    main()
