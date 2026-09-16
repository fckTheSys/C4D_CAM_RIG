# Camera Rigs 0.5.5 — historical verification

This document records the 0.5.5 acceptance run. The current package is 0.5.6;
see `ACCEPTANCE_056.md` for the current release evidence.

Verified on 2026-09-15 in Cinema 4D 2026.2 (2026200), Python 3.11.4.

## Experimental animated Tracer

Enable `Experimental: Animated Tracer` on a newly created Cine Trajectory.
Animate Progress and Position keys on the Nulls connected by Tracer. The
experimental sampler reconstructs historical geometry for deterministic inertia.
The option is off by default. Existing scene rigs are not upgraded automatically.

Supported: Connect Objects, fixed ordered list of 2–64 leaf Nulls, Position
animation, Linear/Cubic/Akima/B-Spline. Keep the Tracer transform and configuration
static. Bezier, changing topology, expression-driven controls, frozen transforms
and animated rotation/scale are outside this experimental contract.

`tests/c4d_experimental_path_acceptance.py` passed for all four spline types,
including the installed runtime. Native-path discrepancy was below 0.000002 cm.
Checks cover nonsequential evaluation, edited keys, inertia and saved/reloaded
embedded runtime with local file access disabled. A four-control one-second cold
sample took 5–10 ms in the installed test; this is not a general performance bound.

## Camera browser and creation

`tests/c4d_camera_browser_acceptance.py` passed against source and installed menu:
six bundle rigs, unique names, parent Null colors, foreign-camera exclusion,
search, explicit activation from editor/foreign camera, immediate switching from
an active bundle camera, bounded arrows, deleted-camera rejection and separate
rig selection. Object Manager selection does not activate live switching.

The installed 0.5.5 dialog opened successfully in the existing C4D session.
Camera selector, both arrows and Activate camera controls have valid layout bounds.
QA scene mutations used owned detached documents; the user document was preserved.

## Regression and package

Live regression covered look modes, Cine reference comparison, four-mode menu
actions, static spline paths and static Tracer paths with animated Progress.
Evidence: `tests/artifacts/bundle_055_5f62e8f00f004e2b8e73518b179c259d.json`
(local ignored artifact). All 26 pure CK math tests passed.

Private installed package: `release/private/Camera_Rigs-0.5.5.zip`, 21 files.
SHA256: `1807ee9c215d9ac9a1f97fb0b25e6597ed28abdecc1c56ff7f11df7358341c81`.
The packager validated compilation and archive/installation manifests and backed
up the prior installation. No public release or GitHub push was performed.

Render-farm execution, motion blur and clean-host installation are not verified
by these checks. CK_CAM continues to require Redshift. Legacy rigs are preserved.

## Interactive route editing stress

`tests/c4d_tracer_stress.py` passed against the installed 0.5.5 builder on
2026-09-15: 257 checked evaluations per spline type, 1028 total, plus direct
linked-object deletion probes. Tests repeatedly add/remove/reorder linked Nulls
and change positions at a fixed frame, with inertia 0 and 0.65. Repeated-frame
positions remain deterministic; without inertia they match native Tracer output.
Empty lists, one controller, coincident points and 65 controllers stop cleanly;
restoring a valid route resumes evaluation. The 64-controller boundary passes.

Deleting a linked object while retaining its stale list entry reports
`Stopped: Tracer contains a missing controller`. Removing that missing entry
from the Tracer list restores the rig. This is an explicit validation stop,
not automatic cleanup of user links.

Median evaluation time was 0.54–0.62 ms and the largest sampled evaluation was
34 ms in these small detached fixtures. This is not a production-scene benchmark.
Evidence: `tests/artifacts/tracer_stress_2e9ca441d9cc4a508a58d1dca3a6bd56.json`.
These checks cover editing topology between evaluations, not animating the
controller list over time; historical topology animation remains unsupported.
Undo/Redo and long-duration playback are not covered by this stress script.
