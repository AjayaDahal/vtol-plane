"""Regenerate everything in order: skins, PETG parts, print orientation, slicing, checks.

Usage: python build_all.py [--no-slice]
"""
import os
import shutil
import subprocess
import sys

import geom as G
import make_print_ready
import skins
import structure


def main():
    shutil.rmtree(G.ASSEMBLY, ignore_errors=True)
    skins.build()
    structure.build()
    make_print_ready.build()
    if "--no-slice" not in sys.argv:
        import slice_all
        slice_all.main()
    here = os.path.dirname(os.path.abspath(__file__))
    sys.exit(subprocess.call([sys.executable, "check_parts.py"], cwd=here))


if __name__ == "__main__":
    main()
