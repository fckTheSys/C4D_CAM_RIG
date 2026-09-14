# Chiken_CAM / CK_CAM 0.1.0 — 2026-09-15 (private development)

- Added the independent `Chiken_CAM (CK_CAM)` Cinema 4D command plugin.
- Kept legacy CamRig unchanged; CK_CAM creates only the new path-camera rig.
- Added immediate preview for keyed User Data and split geometry/motion caches.
- Documented bounded validation and private installation layout.

# 1.6.0 — 2026-09-08 (local development, not published)

- Review corrections: moving-target forcing term, subframe endpoint/time precision, exact native circle sampling, input cache signature, metadata stage roles and complete 1.5 runtime replacement during Upgrade.
- Added independent RK4 comparison and actual-expression C4D checks for sampler parity, random subframes, FPS, renamed stages and schema-2 Undo/Redo.

- Added Follow Spring with Amount, Response and Damping controls.
- Added a deterministic 120 Hz analytic position solver with reproducible random-frame and subframe evaluation.
- Added per-tag cache invalidation, supported-source diagnostics and a dedicated Spring_Offset stage before Shake/Drift.
- Added schema-2 to schema-3 Upgrade, Reset Spring and conservative Break protection.
- Added pure solver tests and live Cinema 4D smoke coverage for lift/settle behavior.
- Hardened Agent MCP acceptance lifecycle: the source document is tracked by
  exact interpreter identity, the on-disk clone is reopened and fingerprinted
  before QA, and snapshot recovery is reported separately from ordinary PASS.
- Added live document lifecycle regression coverage for duplicate names,
  setup/cleanup fault injection, exact transforms, User Data links/tracks,
  materials, selection and render settings.
- Fixed Windows stdio test shutdown so the proxy and its pinned Cinema 4D MCP
  child do not remain as orphan processes after a successful run.

# 1.5.0 — 2026-09-08 (local development, not published)

- Unlimited signed Orbit degrees and Radius without artificial maximum; independent soft slider ranges.
- Root-space center offsets/height, circle HPB and independent Orbit Center position.
- Aim Offset, independent focus modes/target/offset, standard and Redshift camera distances.
- Ordered portable early/runtime and late/focus tags; structural cleanup moved to explicit commands.
- Shared rig selection/navigation, Reset Orbit Rig/Aim, Inspector and schema-aware Repair.
- Explicit schema-2 Upgrade for the exact baseline 1.4 runtime; code backup, stable DescIDs and curves, Undo/Redo.
- Conservative Break guards; full camera bake is not included.
- Repeatable C4D acceptance scenarios, static checks and safe private development packaging.
- Outstanding: automatic native HUD Show/Hide is unavailable through the Python SDK; UI fallback awaiting owner choice.
- Licensing conflict remains unresolved; no licensing change or public release.

# Changelog

## 1.4.0 — 2026-05-08

- Added Rig Inspector, Repair Selected Rig, and Self Check.
- Added optional Camera Drift controls.
- Synchronized the embedded runtime version with the plugin version.

## 1.3.1 — 2026-05-08

- Split build, User Data, reset, and break logic into modules.
- Added User Data template validation and centralized logging.

## 1.3.0 — 2026-05-08

- Removed Motion Camera and inertia from the product.
- Preserved recognition of legacy `Inertia_Follow` scenes.
