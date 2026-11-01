# Slicing (v0.2)

Slicer: **Anycubic Slicer Next 1.3.3.3** (OrcaSlicer based), driven from the command line.
Printers: **S1** = Anycubic Kobra S1 (250 x 250 x 250 mm, enclosed), **X** = Anycubic Kobra X
(260 x 260 x 260 mm, open frame). LW-PLA skins are split between the two; every PETG part goes
on the S1. `tracker.md` lists each part with its printer, mass and print time.

## Pipeline

```
python scripts/build_all.py        # everything below in order (--no-slice to skip slicing)
python scripts/skins.py            # LW-PLA skins     -> parts/assembly/*.stl
python scripts/structure.py        # PETG structure   -> parts/assembly/*.stl
python scripts/make_print_ready.py # rotates into print orientation -> parts/print_ready/*.stl
python scripts/slice_all.py        # -> gcode/<s1|x>_<lwpla|petg>/<part>.gcode  (one part: slice_all.py fuse_1)
python scripts/mass_balance.py     # mass, CG, battery position (reads masses from the G-code)
```

`scripts/make_print_ready.py` holds the print table: printer, material, slicer process,
orientation and copy count per part. Set `VTOL_SLICER` if the slicer is not at
`C:\Program Files\AnycubicSlicerNext\AnycubicSlicerNext.exe`.
Orientations are baked into the STLs (the CLI `--rotate-*` options crash this build), and the
slicer is called with `--orient 0 --arrange 1 --ensure-on-bed`.

## Profiles (`slicer_profiles/`, self-contained, built by `scripts/make_slicer_profiles.py`)

| File | Use |
|---|---|
| `machine_kobra_s1.json`, `machine_kobra_x.json` | printer definitions |
| `process_lwpla_vase.json` (S1), `process_lwpla_vase_x.json` (X) | spiral mode, 1 wall, 0.2 mm, 8 mm outer brim. Each printer needs its own variant: a process derived from one printer is rejected by the other |
| `process_petg.json` | 3 walls, 15 % crosshatch infill, 5 top / 3 bottom layers, 5 mm auto brim, no supports |
| `process_petg_support.json` | same, with tree supports (boom ribs, boom pods, rear motor mount) |
| `filament_lwpla.json` | 235 C (220 C first layer), flow 0.55, fan 100 % |
| `filament_petg.json` | 255 C, flow 0.95, fan 40 % |

Numbers in the preset JSONs are strings ("1", "0.2", "0%"); integer overrides are rejected.

## G-code check (Oct 31, 2026)

All 44 files in `gcode/` were parsed:

- Every part fits its bed, brim included (largest: `wing_root` 234 x 40 mm on the 250 mm S1 bed;
  tallest: 240 mm `fuse_1`/`fuse_3`/`vtail_r` against 250 mm).
- LW-PLA files: `spiral_mode = 1`, 235 C, bed 35 C, no supports, one layer count that matches the
  height (e.g. 1201 layers for 240 mm).
- PETG files: 255 C, bed 60 C, 3 walls. Supports are on only for `boom_rib_l/r`, `boom_pod_l/r` and
  `rear_motor_mount`.
- Masses and times in `tracker.md` equal the slicer's footer (`total filament used [g]`,
  `print_time`). Totals: S1 LW-PLA 124 g / 23.0 h, X LW-PLA 105 g / 20.7 h, S1 PETG 463 g / 22.8 h.

Not checked: print quality. The LW-PLA flow (0.55) and vase-mode wall quality need a real test print
(one `wing_tip_r`) before the full set is printed, and the boom-rib tree supports should be watched
on the first print.
