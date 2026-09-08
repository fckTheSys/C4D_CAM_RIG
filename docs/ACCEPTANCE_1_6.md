# CamRig 1.6 acceptance status

This is a local development record, not a release claim.

## Confirmed statically

- Python source and `.pyp` compile checks pass.
- Schema/default/template parity passes for 37 controls.
- Embedded runtime version, plugin version and schema are 1.6.0 / 3.
- Local Markdown links resolve.
- Pure analytic solver tests cover critical damping, overshoot, decay, Amount blending, random access and cache-independent results.

## Confirmed in Cinema 4D 2026.2

- Bridge ping succeeds on C4D 2026200.
- A new rig creates `Follow → Offset → Spring_Offset → RS_CAM → FX_CAM → Focus` and three ordered Python stages.
- A Height key transition produces a position lag and damped oscillation; repeated frame requests reproduce the same Spring Offset.
- Unit-circle sampling remains detached from the document and matches the observed native Align orientation convention.

## Not yet certified

The full 24/25/30/60 FPS matrix, Redshift/standard comparison, performance budget, unsupported-expression diagnostics and saved-scene reopen matrix still require the dedicated live acceptance harness. They must be reported separately from static checks and bridge smoke tests.

Licensing remains unchanged: the existing MIT file conflicts with the commercial production-builder text. No public release is authorized by this development branch.
