# Cine Orbit / Trajectory / Free — 0.4.0 prototype

Packaged creation/navigation menu: [Cine Camera](../../Cine_CAM/README.md).
Build and acceptance evidence: [package notes](../../docs/CINE_CAM_PACKAGE.md).

Three fixed-purpose builds sharing one runtime and one native User Data panel.
No Movement mode switch, no unused movement parameters or unused controllers.
The universal CamRig 2 P3 remains [legacy](../cine_camera/LEGACY.md).

In Cinema 4D Script Manager, open and run:

- `create_orbit.py`: angle, radius, height, orbit center.
- `create_trajectory.py`: editable spline and Progress.
- `create_free.py`: Free Controller with ordinary position/rotation keys.

Each creates a new rig in the current document with one Undo step. Shared controls:
local XYZ offset, target/manual aim, pan/tilt/roll, native camera optics, inertia,
drift and shake. Different movement requires another build; no automatic animation
conversion is provided. The scripts are needed only for creation. Every scene
stores its complete expression code; no rig/UI plugin is required on render workers.
Compatible C4D, Python Tags and the chosen renderer remain necessary.

Inherited [P3 effect limitations](../../docs/CAMRIG_2.md) still apply. Actual farm,
Redshift motion blur and visual approval are separate from local host validation.
The builder accepts `build(document, mode=0|1|2, use_redshift=True)`.

Live acceptance (15.09.2026, C4D 2026.2): PASS. Each variant matches the legacy
camera position/orientation under the same animation, inertia, shake and drift,
including shuffled subframes and stops. All three reproduce results after native
save/load with cold caches. Only their own movement controls and source objects
exist. Fixture: `tests/artifacts/cine_variants_041bd7f5c234427bbb174fca6beebb09.c4d`.
Run `acceptance.py:run()` in C4D to repeat the isolated comparison.
