# Notes for agents

- When the user starts or asks about printing, read the "Reminders for print time" section in
  `tracker.md` and remind them of every unchecked item before they print the full set.
- Pipeline and slicer settings: `SLICING.md`. Design numbers come from `scripts/mass_balance.py`.
  Design, assembly order and hand-drilled holes: `DESIGN.md`.
- After any change to `scripts/` or `slicer_profiles/`, run `python scripts/build_all.py` (rebuild,
  re-slice, verify). `scripts/check_parts.py` must pass before anything is printed.
- When a finding is fixed or a new one is found, update its status in `REPORT.md` (the
  "Current status" section and the round tables) in the same commit. Never leave a fixed
  finding marked open, or an open one marked fixed.
- Renders: after a geometry change, run `python scripts/make_viewer.py` and
  `python scripts/serve_viewer.py`, then open `http://127.0.0.1:28765/viewer/?capture=1` to
  re-render `renders/*.png`, so the pictures match the files.
