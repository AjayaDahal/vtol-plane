"""Regenerate everything in order: skins, PETG parts, print orientation, slicing, the complete
slicer projects (each plate sliced again and checked), viewer manifest, the print table in
tracker.md, checks. The manifest and the tracker come after slicing because they carry each file's
sliced mass and print time.

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
    args, projects_ok = [], True
    try:
        if "--no-slice" in sys.argv:
            print("--no-slice: G-code checks skipped; run slice_all.py before printing")
            args.append("--no-gcode")
        else:
            import make_projects
            import slice_all
            slice_all.main()
            # The two complete projects, every plate sliced again and checked against its job's G-code.
            projects_ok = make_projects.main(check=True)
    finally:
        # Even when a part fails to slice: the viewer needs the new geometry.
        make_viewer.main()
        make_tracker.main()
    here = os.path.dirname(os.path.abspath(__file__))
    code = subprocess.call([sys.executable, "check_parts.py", *args], cwd=here)
    sys.exit(code or (0 if projects_ok else 1))


if __name__ == "__main__":
    main()
