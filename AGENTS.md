# Notes for agents

- When the user starts or asks about printing, read the "Reminders for print time" section in
  `tracker.md` and remind them of every unchecked item before they print the full set.
- Pipeline and slicer settings: `SLICING.md`. Design numbers come from `scripts/mass_balance.py`.
  Design, assembly order and hand-drilled holes: `DESIGN.md`.
- After any change to `scripts/` or `slicer_profiles/`, run `python scripts/build_all.py` (rebuild,
  re-slice, verify). `scripts/check_parts.py` must pass before anything is printed.
- The print table and totals in `tracker.md` are generated from the sliced files
  (`scripts/make_tracker.py`, run by `build_all.py` and `slice_all.py` after slicing). Edit only
  the Status column, the notes in brackets after a part's name and the text around the tables;
  the gate fails when the table is stale.
- PETG prints as plates on the S1 (`scripts/plates.py`): every PETG copy must sit on exactly one
  plate, so a new or changed PETG part (or `qty`) needs its plate entry too; the gate checks
  this and the layouts. LW-PLA vase parts cannot share a bed. Printer split: the S1 prints the
  right wing and the PETG, the X the left wing, the fuselage and the V-tail (about 35 h each);
  keep them balanced when moving parts (`tracker.md` totals).
- When a finding is fixed or a new one is found, update its status in `REPORT.md` (the
  "Current status" section and the round tables) in the same commit. Never leave a fixed
  finding marked open, or an open one marked fixed.
- Renders: after a geometry change, run `python scripts/make_viewer.py` and
  `python scripts/serve_viewer.py`, then open `http://127.0.0.1:28765/viewer/?capture=1` to
  re-render `renders/*.png`, so the pictures match the files.
- Purchased equipment (battery, ESCs, Pixhawk, boards, GPS, servos, pitot) lives in
  `scripts/payload.py`: size and position of each item, and a sketch of the cable runs. Move
  equipment there, not in the docs; the mass balance, the gate's fit checks and the viewer all
  read it. The servo hatch frames (`servo_hatches()`) live there too.
- Nothing that may need replacing (battery, servos, motors, boards) may be glued in or sit
  behind a joint that has to be cut: the nose, the screwed servo hatches and the pods' plug
  pockets are the ways in (`DESIGN.md`, "Servicing"). The gate checks the hatches, the plug
  pockets and the battery-strap path.
- The hover margin is thin (front motors ~60 % of their near-empty thrust, the gate's limit):
  count every new gram in `mass_balance.py` and re-run the gate.
- The wing webs depend on two vase-profile settings, `slice_closing_radius` 0.01 and
  `detect_thin_wall` 0 (`SLICING.md`). Do not let a preset update reset them. The G-code
  stamp only covers the STL, so after any profile change re-slice everything.
