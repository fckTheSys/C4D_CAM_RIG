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
