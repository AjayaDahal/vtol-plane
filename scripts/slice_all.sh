#!/bin/bash
# Slice every VTOL part for both printers with Anycubic Slicer Next.
# Run from ~/workspace/vtol-plane. Requires the sysroot libs (see SLICING.md).
set -e
cd "$(dirname "$0")/.."

export LD_LIBRARY_PATH=/home/hatch/workspace/tools/sysroot/usr/lib/x86_64-linux-gnu:/home/hatch/workspace/tools/anycubic/squashfs-root/lib:/home/hatch/workspace/tools/anycubic/squashfs-root/usr/lib
SLICER=/home/hatch/workspace/tools/anycubic/squashfs-root/bin/AnycubicSlicerNext
CFG=/tmp/anycubic_cfg

slice() {
  # $1 = outdir, $2 = machine json, $3 = process json, $4 = filament json,
  # $5 = model path (relative), $6 = target name.
  # No CLI rotation flags: orientations are baked into parts/print_ready/
  # by make_print_ready.py (CLI --rotate-* segfaults in this build).
  local outdir="$1" machine="$2" process="$3" filament="$4" model="$5" target="$6"
  mkdir -p "$outdir"
  rm -f "$outdir/plate_1.gcode"
  "$SLICER" --slice 0 --ensure-on-bed --datadir "$CFG" \
    --load-settings "slicer_profiles/$machine;slicer_profiles/$process" \
    --load-filaments "slicer_profiles/$filament" \
    --outputdir "$outdir" "$model" > /dev/null 2>&1
  mv "$outdir/plate_1.gcode" "$outdir/$target"
  echo "sliced $target ($(stat -c%s "$outdir/$target") bytes)"
}

LWPLA_PARTS="wing_root wing_mid wing_tip"
for printer in s1 x; do
  if [ "$printer" = s1 ]; then machine=machine_kobra_s1.json; process=process_lwpla_vase.json;
  else machine=machine_kobra_x.json; process=process_lwpla_vase_x.json; fi
  for p in $LWPLA_PARTS; do
    slice "gcode/${printer}_lwpla" "$machine" "$process" filament_lwpla.json "parts/$p.stl" "$p.gcode"
  done
  for p in fuse_1 fuse_2 fuse_3 fuse_4; do
    slice "gcode/${printer}_lwpla" "$machine" "$process" filament_lwpla.json "parts/print_ready/$p.stl" "$p.gcode"
  done
done

# V-tail panels: all-flying, LW-PLA VASE mode (the horn prints because
# it is on the outer contour; the pivot rod glues into the open root
# instead of a printed spanwise hole, and the 2.2 mm horn hole is
# drilled after printing). Vase keeps each panel ~19 g instead of
# ~75 g in standard profile — that tail weight decides the CG.
# Split across printers: right panel S1, left panel X.
slice gcode/s1_lwpla machine_kobra_s1.json process_lwpla_vase.json filament_lwpla.json parts/vtail_r.stl vtail_r.gcode
slice gcode/x_lwpla machine_kobra_x.json process_lwpla_vase_x.json filament_lwpla.json parts/vtail_l.stl vtail_l.gcode

# PETG structural parts, Kobra S1 (enclosed).
slice gcode/s1_petg machine_kobra_s1.json process_petg.json filament_petg.json parts/print_ready/tilt_nacelle_r.stl tilt_nacelle_r.gcode
slice gcode/s1_petg machine_kobra_s1.json process_petg.json filament_petg.json parts/print_ready/tilt_nacelle_l.stl tilt_nacelle_l.gcode
slice gcode/s1_petg machine_kobra_s1.json process_petg.json filament_petg.json parts/print_ready/tilt_bracket.stl tilt_bracket.gcode
slice gcode/s1_petg machine_kobra_s1.json process_petg_solid.json filament_petg.json parts/print_ready/motor_mount_rear.stl motor_mount_rear.gcode
slice gcode/s1_petg machine_kobra_s1.json process_petg.json filament_petg.json parts/print_ready/vtail_pivot_block.stl vtail_pivot_block.gcode
# Caps, sleeves, tray: flat plates / open tubes, print as-is.
for p in tip_cap nose_cap sleeve_240 sleeve_480 sleeve_720 battery_tray; do
  slice gcode/s1_petg machine_kobra_s1.json process_petg.json filament_petg.json "parts/$p.stl" "$p.gcode"
done

echo "ALL SLICES DONE"
