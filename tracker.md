# VTOL Plane — Print Tracker

Two printers: **S1** = Anycubic Kobra S1 (250³ mm, enclosed),
**X** = Anycubic Kobra X (260³ mm, open frame).
Rule: LW-PLA airframe split across both; PETG structural parts on S1.

| Part | Material | Printer | Status |
|---|---|---|---|
| Wing section root (L/R ×1 each) | LW-PLA vase | S1 + X | sliced, not printed |
| Wing section mid (L/R) | LW-PLA vase | S1 + X | sliced, not printed |
| Wing section tip (L/R) | LW-PLA vase | S1 + X | sliced, not printed |
| Fuselage sections 1–4 | LW-PLA vase | S1 + X | sliced, not printed |
| V-tail panels, all-flying (L/R) | LW-PLA vase | S1 (R) + X (L) | sliced, not printed |
| Tip caps (×2) | PETG | S1 | sliced, not printed |
| Nose cap (×1) | PETG | S1 | sliced, not printed |
| Fuselage joiner sleeves (240/480/720) | PETG | S1 | sliced, not printed |
| Battery tray (×1) | PETG | S1 | sliced, not printed |
| Tilt nacelles (2) | PETG | S1 | sliced, not printed |
| Tilt brackets (4 = 2 per nacelle) | PETG | S1 | sliced, not printed |
| Rear motor mount — socket version (1) | PETG solid | S1 | sliced, not printed |
| V-tail pivot blocks (×2, print unrotated) | PETG | S1 | sliced, not printed |

Not modeled parts (deliberate, not missing):
- Booms: not applicable. This is a tilt-rotor tricopter — the front
  motors mount on the wing, the rear on the tail. There are no booms.
  The old "booms" tracker line was a leftover from the quadplane idea.
- Servo doors: cut by hand with a knife after printing, hinged with
  tape. A modeled door would break the vase-mode wall.
- FC mount: the FC sits on the battery tray with foam tape.

Superseded (do not print): the old rigid `vtail_panel.stl` and its
G-code — replaced by the all-flying `vtail_l/r.stl`. Deleted from
parts/ on Oct 31. The old stub-style rear motor mount is likewise
replaced by the socket version.

Status values: STL pending / STL ready / sliced / printing / printed / failed.
