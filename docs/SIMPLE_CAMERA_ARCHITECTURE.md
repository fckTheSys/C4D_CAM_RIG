# Simple Camera — architecture v1

Status: private working candidate implemented; core live checks pass. 2026-09-15.
Visual user acceptance and Redshift motion-blur acceptance remain open.
Tracking: FCK-77, stages FCK-78 → FCK-79 → FCK-80 → FCK-81.

## Goal and boundary

One independent editable camera rig for a passage with acceleration, walking,
stopping, looking aside and a jump. Old CamRig and its camera animations remain
unchanged and serve as framing/timing references. No legacy migration.

Native Align to Spline and Target are retained. Motion Camera/Footsteps is NOT
the new runtime: the native experiment measured history-dependent differences
(39.665 cm mixed jumps, 1.802 cm after a subframe). See
../experiments/native_walk/README.md. A small portable Python runtime supplies
distance mapping, manual controls and deterministic Walk/Shake/Drift.

## Object graph and ownership

```
Rig                         public controls; static rigid transform, scale 1
├─ Path                     editable static Bezier spline, single open segment
├─ Target                   independently keyable target
└─ Route                    native Align: POSITION ONLY, tangential OFF
   └─ Body                  Python: height + XYZ jump offset, rotation zero
      └─ Aim                native Target in target mode; identity in manual mode
         └─ Look            Python: Pan/Tilt/Roll, explicitly composed rotations
            └─ FX           Python: combined walk/shake/drift local correction
               └─ Camera    one Redshift camera; native lens settings
```

Path points may be edited between evaluations. Animated/deformed splines, animated
root/parent transforms, non-unit scale and path switching are out of v1 scope;
report unsupported sources rather than reuse stale cached motion. Target may be
animated, but may not reference Camera/FX or dependent descendants.

Route does not rotate with the tangent. Thus Body Y is always rig-up even when
looking down; Body X/Z are rig axes, not view-relative. Arbitrary route direction
is framed through Target or keyed Pan/Tilt/Roll. No extra auto-heading mode in v1.
Body motion occurs BEFORE aiming, so Target evaluates the jumped camera origin.
FX is secondary motion after aiming and is intentionally not re-aimed away.

Each transform/property has exactly one writer. No direct keys on driven nodes.
Camera PSR stays identity; all Redshift lens/exposure/DOF parameters belong to
Camera. The root does not silently mirror/overwrite them; a Select Camera command
provides access. Reuse focus_depth only if a later task actually needs autofocus.

## Evaluation contract

Two Python stages from one small embedded source, not one monolithic late tag:
1. Prepare (-30 candidate): evaluate controls, map distance progress to Align's
   native parameter, set Body and explicit manual/target mode state.
2. Align (-20 candidate), Target (-10 candidate).
3. Finish (+10 candidate): apply Look and the final FX transform once.

These priorities pass the bounded C4D reproducibility/edit/control fixtures. A single late tag
cannot feed Align earlier in the same pass. Confirm absence of one-frame lag in
fresh-document, reverse and subframe tests. No SetTime/ExecutePasses from expressions,
document structure changes, file reads or previous-frame state in runtime.

## Path, speed and approximation

Progress p(t) is normalized distance in [0,1], keyable with normal C4D curves.
Spline shape and progress timing are independent. Clamp outside the range; v1
does not loop. Stops are flat intervals; reverse travel is supported. Progress
Step keys/teleports are rejected in v1, not interpreted as infinite velocity.
Historical progress, step length and frequency inputs must be native keyed or
constant controls, not externally expression-driven values.

Use adaptive arc-length table (parameter u, distance s) for the Bezier geometry.
Initial target spatial tolerance: 0.01 cm, with subdivision/resource cap and clear
diagnostic if convergence fails. Verify against denser independent sampling.
Inversion maps requested distance to the native Align parameter. Do not assume
Align's parameter equals raw Bezier u: verify mapping against actual native
evaluation on nonuniform/curved fixtures. Degenerate zero-length path gives no
travel/zero gait and a diagnostic. Approximation never edits the source spline.

Distance s(t)=L*clamp(p(t)); route speed is |ds/dt|. For gait use horizontal route
travel projected to Rig XZ; vertical climbing/jump must not accelerate footsteps.
On a horizontal path this equals arc travel. Reverse contributes positive travel.
Splitting turning points/extrema is essential; endpoint subtraction is not total
distance on an interval that reverses direction.

## Walk, Shake and Drift

Walk phase in radians is phi0 + pi * integral(v_horizontal(t)/step_length(t), dt)
from fixed start time. One step advances pi, a left/right pair advances 2*pi.
Vertical waveform repeats each step, lateral sway/roll over a pair. Step length
must be positive. This supports animated step length without a phase jump from
dividing total distance by the current length.

Walk strength uses a smooth speed envelope that reaches zero at rest, multiplied
by keyed user Strength. No previous-frame low-pass. If temporal smoothing is
needed, use a fixed time-domain sampling window reproducible at any requested t.
Phase integrates travel even while Strength=0; resuming strength does not reset
phase. During jumps key Walk Strength to zero; jump is not auto-detected.

Walk positional axes: rig-up and rig-horizontal route lateral; at zero horizontal
tangent use a deterministic fixed fallback, never the last visited frame. Use
the increasing-path-parameter tangent for lateral orientation, not velocity sign,
so reversing travel does not instantly flip the lateral frame. Rotation is small
camera-local secondary motion. Convert translation
into FX parent coordinates explicitly so tilt/roll does not tilt vertical bob.

Shake/Drift use continuous seeded noise at absolute time. With animated frequency,
noise coordinate is integral(frequency(t), dt), NOT t*frequency(t). Each axis/layer
has a separate seed offset. No per-frame RNG, frame-number quantization or hash()
dependent seed. User intensity animation gates amplitude without resetting phase.
Shake speed coupling is optional and defaults off; Drift can continue at rest.
All positional offsets sum in their specified basis; rotations compose in fixed
documented order (walk then shake then drift), not arbitrary Euler addition.

Pure sampler/cumulative integrals use a fixed origin and deterministic adaptive
quadrature or fixed grid with convergence tests. Caches accelerate only: cold/warm
results must agree. Invalidate on path geometry, relevant curve values/tangents,
units, source links, control settings, time origin and Undo/Redo. Do not share live
object references globally between rigs/documents. Never depend on visitation
order. Do not rescan all keys at every integration sample.

## Compact interface

Four sections, with secondary options folded:
- Route/Body: Path, Progress %, Height cm, Body Offset XYZ cm (folded jump group).
- Look: Manual/Target, Target link, Pan/Tilt/Roll degrees. Pan yaw about Aim-up,
  then Tilt about yawed right, then Roll about optical axis. Positive signs must
  match documented C4D UI tests. Target mode applies these as framing corrections.
- Motion: Walk strength, Step length cm, Amplitude cm, Lean degrees, Softness;
  Shake strength/frequency and Drift strength/frequency in folded subgroups.
  Advanced: position/rotation amplitude split, seed, phase, speed coupling.
- Camera: select the sole camera for native lens/focus/exposure controls.

No animated mode toggle in v1. An explicit switch command may preserve framing
at the current time by solving the new Look correction; it must not silently
rewrite existing keys. At singularities/ambiguous Euler solution report the issue.
Native Target stays scheduled in both modes, with a null link in manual mode.
Finish explicitly resets manual Aim after native Target evaluation. Toggling native
EXPRESSION_ENABLE caused a one-pass delay in live testing and is not used.
Plain mode selection must reset the inactive Aim state explicitly, never inherit
an orientation from the previous visited frame. Seamless switching within a shot
requires a future blending contract, not an implied guarantee.

Jump uses keyed Body Y for anticipation → takeoff → apex → contact → compression
→ recovery. Progress defines horizontal travel; Body X/Z are optional corrections.
Do not duplicate the same jump arc in both spline and Body. A keyed Shake strength
pulse can add impact texture; no automatic collision or physics solver.

## Source reuse and files

Separate new module under prototypes/simple_camera; no import of legacy runtime.
Serena-confirmed helper candidates: ud_build.add_slider/add_group/add_link,
scene_support.set_priority, optional tag_embedded._noise_1d (inspect before reuse).
Preserve provenance for locally adapted helpers. Existing functions importing
legacy config are patterns, not an excuse to couple the new package to schema 3.

Builder creates detached subtree, inserts with one owned Undo transaction. Tests
retain exact owned document identities, never cleanup by a document name.
Portable expressions contain no external module dependencies. Explicit compile
checks must cover nested files (legacy check_project does not).

## Verification gates

FCK-78 retains historical native findings and now verifies the replacement math
and minimal live graph. No claimed implementation until tests execute.
- Uneven Bezier spacing: distance mapping and speed against independent reference.
- Stops, easing, reverse/turning points, endpoints, zero-length path.
- Same camera matrix at sequential/random/reverse/subframe times, cold/warm cache,
  repeated evaluation, edited curves/path and save/reopen.
- Animated step length and noise frequency retain continuous phase.
- Look down/roll 90 degrees while jumping: Body remains rig-up.
- Pan with target, manual aim reset, two rigs, target cycle rejection.
- All effects zero: exact base pose within floating-point tolerance.
- No source keys/lens data changed by evaluation; Undo/Redo and rebuild links.
- Live motion blur and short visual passage; output .c4d stays editable.
- Benchmark 1/6 rigs, cold seek and edited-source rebuild; compare equal fixtures.

Provisional same-time reproducibility thresholds: position 1e-5 cm, rotation
1e-6 rad. Arc-length approximation has its separate 0.01 cm target. Confirm
thresholds with host numerical precision; never relax a failure silently.
User visual acceptance is separate from numerical/source checks.

## Candidate evidence (2026-09-15)

See prototypes/simple_camera/README.md for scripts and instructions. Outputs live
under ignored tests/artifacts/simple_camera/:
- python_v005: eased curves, animated step length/frequency, reverse/random/cold/
  subframe/save-reopen PASS.
- edit_v002: six input edits, Undo/Redo with resolved links, two-rig isolation PASS.
- controls_v003: 15 control/ownership cases PASS, including both aim-mode transitions,
  zero FX identity, jump basis, preserved lens data and source keys.
- numerical_v001: 120/480 Hz refinement error <0.000185 cm and <5.52e-7 basis
  component; five invalid-source guards PASS. One/six rig warm costs ~1.74/10.21ms
  per frame; cold frame180 ~132/769ms on six-second fixtures, without render.
- passage_v003: editable demonstration and viewport-only PNG sequence/MP4.

25 pure tests pass separately. These are bounded fixtures, not a proof for arbitrary
external expression graphs, all animation durations or Redshift motion blur.
V1 UI omits phase/speed-coupling and preserve-framing commands; mode switching is
explicit and may change composition. Camera selection is a Script Manager command.
