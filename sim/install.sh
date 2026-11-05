#!/bin/bash
# Install this aircraft's generated Gazebo model, its field (world) and PX4 airframe
# (scripts/make_sim.py writes them into sim/) into a PX4-Autopilot tree, v1.17. Then, from that tree:
#   make px4_sitl gz_vtol_plane            # Gazebo GUI + PX4 (HEADLESS=1 for no GUI)
# Run it again whenever make_sim.py has regenerated sim/.
# Usage: sim/install.sh [PX4-Autopilot directory, default ~/PX4-Autopilot]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
px4="$(cd "${1:-$HOME/PX4-Autopilot}" && pwd)"
model=vtol_plane
airframes="$px4/ROMFS/px4fmu_common/init.d-posix/airframes"
models="$px4/Tools/simulation/gz/models"
[ -f "$airframes/CMakeLists.txt" ] && [ -d "$models" ] || {
  echo "$px4 is not a PX4-Autopilot tree with its Tools/simulation/gz submodule" >&2; exit 1; }

rm -rf "${models:?}/$model"
cp -r "$here/models/$model" "$models/"
cp "$here"/worlds/*.sdf "$px4/Tools/simulation/gz/worlds/"
for f in "$here"/airframes/*_gz_"$model"; do
  name="$(basename "$f")"
  cp "$f" "$airframes/$name"
  # PX4 only installs the airframes its CMakeLists.txt lists.
  python3 - "$airframes/CMakeLists.txt" "$name" <<'EOF'
import re, sys
path, name = sys.argv[1], sys.argv[2]
text = open(path).read()
if not re.search(rf"^\s*{re.escape(name)}\s*$", text, re.M):
    text = re.sub(r"\n\)\s*$", f"\n\t{name}\n)\n", text)
    open(path, "w").write(text)
    print(f"added {name} to {path}")
EOF
done
echo "installed $model into $px4"
echo "next: cd $px4 && make px4_sitl gz_$model"
