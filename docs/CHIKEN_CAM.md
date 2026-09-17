# Chiken_CAM / CK_CAM 0.1.0 (legacy reference)

The standalone CK_CAM reference is preserved for old scenes. New work should
use the bundled `Camera Rigs 0.5.6` package and its CK_CAM POV creation action.

**[Параметры для POV: что означает каждый регулятор, меньше/больше и примеры](../prototypes/simple_camera/PARAMETERS_RU.md)**

`Chiken_CAM (CK_CAM)` is a separate private Cinema 4D 2026 command plugin. It
creates the new path-camera rig and never migrates or changes legacy CamRig rigs.

## Use

Open the target document, then choose **Extensions → Plugins → Chiken_CAM
(CK_CAM)**. The command creates and selects one top-level `Simple Camera
PROTOTYPE` root. It does not save the document or switch the viewport camera.

Animate `Progress` for normalized travel, `Body Y` for a jump, and `Pan/Tilt/Roll`
for framing. `Walk`, `Shake`, and `Drift` are grouped in the root User Data. The
camera's lens, exposure, and DOF remain native camera settings.

Keyed User Data supports temporary live preview: an unkeyed slider adjustment is
visible immediately but does not write a key. Recording a key preserves the edit;
timeline evaluation returns to the recorded curve.

## Supported sources

Since 0.5.7 the root may sit inside groups: plain, static Nulls (no transform keys,
no expression tags except Annotation) with world scale 1. Service nulls live on
the `L_CAM_RIG` layer; keep its Expressions/Animation/Generators enabled. The rig
needs one static, open Bezier path.
Do not animate/deform the Path, add expression drivers, animate `Use Target`, or
key PSR on Route, Body, Aim, Look, FX, or Camera. `Status` reports a diagnostic
when the source is unsupported.

## Installation

The installed folder is `%APPDATA%\Maxon\Maxon Cinema 4D 2026_1ABCDC12\plugins\Chiken_CAM\`.
It contains `CK_CAM.pyp` and `prototypes/simple_camera/`. Cinema 4D loads Python
command plugins on startup, so restart C4D after installation. This ID is private
development-only (`10699111`); request a PluginCafe ID before distributing the
plugin.

## Validation

The candidate has passed pure geometry/motion tests and bounded live C4D checks
for repeatability, save/reopen, edits, Undo/Redo, control ownership, live keyed
preview, and cache optimization. Redshift motion blur and a production
`apartment_block` passage remain user acceptance gates.
