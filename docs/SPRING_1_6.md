# Follow Spring 1.6

Follow Spring adds a restrained physical feel to the existing CamRig orbit. It affects only the position of the main camera before Shake/Drift; Target Expression still aims from the resulting camera position.

## Controls

| Control | Key | Default | Meaning |
|---|---|---:|---|
| Spring Amount | `spring_amount` | 0 | Blend from the ordinary position to the spring position |
| Spring Response | `spring_response` | 60 | Reaction speed, mapped to 0.5–5 Hz |
| Spring Damping | `spring_damping` | 65 | Damping, mapped to ratio 0.2–1.0 |

The effect is intentionally one compact control group. Amount is the safe blend; Response controls how quickly the camera catches up; Damping controls overshoot. Reset Spring restores 0 / 60 / 65. Reset All also resets these values while preserving links, keys and the root transform.

## Runtime model

The runtime samples the supported keyed trajectory at a fixed 120 samples per second and solves the three world-space position coordinates analytically. It does not rely on the order in which frames were visited. Random access, reverse playback and subframes therefore produce the same result as sequential playback. The cache is only an acceleration and is local to one Python Tag instance.

The source trajectory includes Orbit, Radius, Orbit Rig, Offset and supported root/parent and Orbit Center transforms. Native circle parameterization is reproduced with a detached unit circle and `SplineHelp`; no helper geometry is inserted into the document. Shake and Drift are deliberately excluded from the source, so decorative noise is not fed back into the spring.

The hierarchy is:

`Follow → Offset → Spring_Offset → RS_CAM → FX_CAM → Focus`

`Spring_Offset` stores only the calculated local position correction. Its rotation is zero and scale is one. At Amount 0 its position is strictly zero and the ordinary CamRig path is preserved.

## Supported-source limitation

The first version supports ordinary CTracks and positive constant scale. Sources driven by XPresso, Constraints, Dynamics, Python Tags, Motion Clips, Takes or animated scale are not used for historical reconstruction. Inspector reports the unsupported source and the ordinary CamRig remains active.

The expression never calls `SetTime`, recursively calls `ExecutePasses`, changes source User Data or changes document structure. Structural repair and migration remain explicit commands.

## Upgrade and safety

Upgrade from a known CamRig 1.5 schema adds the three controls, inserts `Spring_Offset`, installs the Spring stage and writes schema 3 in one Undo operation. It initializes Amount to 0, so the camera matrix and lens remain unchanged until the user enables the effect. Unknown or edited embedded code is never overwritten automatically.

Break is blocked when Spring has a nonzero value or an animation track, because flattening that behavior requires a future full camera bake. Repair only restores a known structure and known runtime.

## Acceptance scenes

Use three short scenes: Lift and Settle, Orbit Stop and Direction Change. Check targeting, focus, random-frame access, reverse playback, 24/25/30/60 FPS and save/reopen. The live harness is `tests/c4d_acceptance.py`; pure solver behavior is covered by `tests/test_spring_math.py`.
