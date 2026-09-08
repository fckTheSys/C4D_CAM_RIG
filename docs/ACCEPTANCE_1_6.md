# CamRig 1.6 — review corrections

The initial 1.6 report overstated acceptance. The earlier development ZIPs contain solver, subframe and migration defects and are superseded by the review-fixes build.

## Confirmed checks

- Pure solver: independent RK4 comparison for a moving target at damping 0/65/100, step overshoot/settling, subinterval composition, embedded/host math parity.
- Static compilation under Cinema 4D Python 3.11.4, parameter/default parity and local Markdown links.
- Cinema 4D 2026200: all 15 general acceptance scenarios pass.
- Native Align versus exact detached sampler: negative/multiple orbit turns, circle tilt, XYZ Offset and rotated/scaled parent; position tolerance 1e-4.
- Actual embedded stage execution: lag/settling, random subframes, warm/cold cache, same motion at 24/25/30/60 FPS, metadata dispatch after tag renaming.
- Cache signature excludes Amount; includes constant source transforms, parent chains, track Before/After, keys/tangents, document start and FPS.
- Source guard accepts a display tag and rejects expression/frozen sources.
- Exact schema-2 fixture: both camera matrices preserved through Upgrade, Undo and Redo; Orbit DescID preserved; repeated Upgrade is idempotent.
- The general suite also checks schema-0 migration, standard camera, focus, Repair, cloning, save/reopen and Undo.

The Spring-specific harness is tests/c4d_spring_acceptance.py. It runs document passes rather than invoking the solver stage directly. JSON evidence is under ignored tests/artifacts/.

## Remaining acceptance boundaries

Full one/ten-rig performance benchmarks, all external-expression dependencies, animated-scale/Motion Clip support and cold application startup remain outside these confirmed checks. Saved-scene Spring rendering without the installed package and the three polished demonstration scenes still need separate acceptance. No performance threshold is claimed.

Experimental schema-3 scenes produced by earlier 1.6 builds are not silently rewritten: unknown embedded code is refused. Use a fresh rig or the original 1.5 scene and explicit Upgrade.

Licensing is unchanged; this remains a private development build.
