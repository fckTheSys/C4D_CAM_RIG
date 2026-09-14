# Native Walk feasibility — FCK-78

Independent experiment; no changes to CamRig 1.6 or existing scenes.

## Result, 2026-09-14

Live C4D 2026.2 / Python 3.11.4 tested through the existing Kumo bridge.
An ordinary Null is a valid Motion Camera Base Link. The graph needs only one
actual Redshift camera:

```
Root
  Route spline
  Route and Aim Null [Align -20, Target -10]
  Look Target
  Camera OUTPUT [Motion Camera 0, Base Link -> Route and Aim]
```

The source path is at ground level. Motion Camera adds the configured height.
Parallax must explicitly be zero (the native default is nonzero). Lens inheritance,
internal spline/target, chase, banking, secondary noise and all four Dynamics
switches are disabled. Footsteps remain history-dependent despite those switches.

## Measured evidence

Tests use new detached documents only, not the active user document. There are six
route keys, 181 evaluated frames at 30 fps, with stationary and changing-speed
segments. Linear timing here is a diagnostic fixture, not final cinematography.

| Check | Result |
| --- | --- |
| Footsteps zero, random-frame position difference | 0 cm |
| Footsteps 1, height 170 cm, mixed jump order vs sequential | 39.665045 cm maximum |
| Footsteps 1, height 15 cm, mixed jump order vs sequential | 3.499857 cm maximum |
| Fresh document jump to frame 90 vs sequential | 6.150989 cm |
| Insert frame 89.5 before 90 vs integer-only evaluation | 1.801583 cm at frame 90 |
| Replay from start vs original sequence | 0 cm |
| Save/reopen followed by sequential evaluation | 0 cm |
| One rig, 181 sequential frames | 15.1543 ms total / 0.08373 ms per frame |
| Six rigs, 181 sequential frames | 57.4934 ms total / 0.31764 ms per frame |

Timings are one small-fixture measurement including Python sampling, not a full
viewport/render benchmark, not a speedup claim against old CamRig. Exported speed
responds to route speed and returns to zero during the hold.

Raw evidence: `../../tests/artifacts/native_walk/probe_v002.json`,
`checks_v001.json`, `native_walk_v001.c4d` (ignored binary/evidence directory).
`probe.py` can be loaded using runpy inside C4D and its `run()` called on the main
thread. It does not insert or activate a document. Run `acceptance.py` for the
extended reproducible suite when available; it requires a fresh output directory.

## Gate decision required

This is a feasible native graph, but NOT an accepted rig. Arbitrary timeline
evaluation fails. Do not proceed to the controller/package stage under a claim
of deterministic Footsteps. A sequential editing workflow with a separate export
bake is a possible compromise, not yet accepted by the user. Otherwise replace
the Footsteps mechanism under a revised scope; do not silently add a custom solver.

Still unverified: pitched-target behavior/height offsets, independent visual
framing acceptance, UI/Undo, motion-blur render, low-POV gait scaling strategy,
performance comparison to old CamRig. No production shot has been edited.

## Native IDs and reuse

Motion Camera tag 1027742; Base Link 100903; Inherit Parameters 100907 false;
Override Dimensions 100908 false; Height 100101; Parallax 100102 zero;
Footsteps intensity 100841, scale 100842, frequency multiplier 100843;
diagnostic speed 300007. Frequency is a multiplier, not steps per second.

Small priority-setting idiom adapted from `camrig/scene_support.py:set_priority`.
No legacy runtime imported. Serena source review identified UD builders and
`focus_depth` as optional future helpers; not needed by this probe.

Official references:
- https://help.maxon.net/c4d/2026/en-us/Content/html/TMOTIONCAM-TMOTIONCAM_NMOTION.html
- https://help.maxon.net/c4d/2026/en-us/Content/html/TMOTIONCAM-TMOTIONCAM_RIG.html
- https://developers.maxon.net/docs/py/2026_0_0/cinema_resource/tag/tmotioncam.html

Subagents independently reviewed native docs/installed resource IDs and legacy
helper boundaries. Only the primary agent ran host experiments.
