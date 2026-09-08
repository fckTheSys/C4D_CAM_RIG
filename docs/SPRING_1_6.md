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

The source trajectory includes Orbit, Radius, Orbit Rig, Offset and supported root/parent and Orbit Center transforms. A detached unit circle is initialized with SplineHelp. Its exact spline point and tangent are sampled using SplineLengthData.UniformToNatural: SplineHelp.GetMatrix alone approximates a line and did not match native Align within tolerance. No helper geometry is inserted into the document. Shake and Drift are excluded from the spring source.

The analytic step includes the moving-target lag term 2*zeta*target_velocity/omega. Substeps interpolate the target endpoint by the fraction of the full interval, keeping the midpoint Response/Damping fixed. BaseTime uses an explicit rational denominator so C4D does not round the 120 Hz sample times to milliseconds.

The hierarchy is:

`Follow → Offset → Spring_Offset → RS_CAM → FX_CAM → Focus`

`Spring_Offset` stores only the calculated local position correction. Its rotation is zero and scale is one. At Amount 0 its position is strictly zero and the ordinary CamRig path is preserved.

## Supported-source limitation

The source guard rejects expression tags on source objects and their parents, animated or non-positive scale, frozen transforms and non-main Takes. Ordinary display tags are accepted. Inspector identifies the rejected object and reason. This is a conservative local dependency check, not a complete analysis of expressions elsewhere in a scene that can modify these objects.

The expression never calls `SetTime`, recursively calls `ExecutePasses`, changes source User Data or changes document structure. Structural repair and migration remain explicit commands.

## Upgrade and safety

Upgrade from a known CamRig 1.5 schema adds the three controls, inserts `Spring_Offset`, installs the Spring stage and writes schema 3 in one Undo operation. It initializes Amount to 0, so the camera matrix and lens remain unchanged until the user enables the effect. Unknown or edited embedded code is never overwritten automatically.

Break is blocked when Spring has a nonzero value or an animation track, because flattening that behavior requires a future full camera bake. Repair only restores a known structure and known runtime.

## Acceptance scenes

The regression harnesses are tests/c4d_acceptance.py and tests/c4d_spring_acceptance.py. Spring tests now execute actual document passes, including native Align and Target; they do not call execute_spring directly. Pure math is checked against an independent RK4 integration in tests/test_spring_math.py.

The earlier 1.6 development archives predate these corrections and should be replaced. Existing scenes retain their embedded code: reinstalling the plugin alone does not change it. Known 1.4/1.5 scenes can use Upgrade; older experimental schema-3 scenes with different code are refused rather than overwritten.
