# Camera Rigs 0.5.6

Verified live in Cinema 4D 2026 on 2026-09-15 using detached owned documents.

- 27 CK math tests passed, including configurable speed gain, unchanged phase,
  full-speed saturation, zero-speed output and invalid threshold rejection.
- Source menu, browser, look and experimental animated Tracer tests passed.
- All four newly created rig types have sphere/triangle target displays,
  explicit colors, Radius 20 and rig-qualified names through panel creation.
- Look regression covers external and local targets, Manual explanation,
  invalid links and scene save/load. Existing rigs are not migrated.
- A detached load of camTest/Test.c4d was sampled before and after replacing
  its test-only embedded stages and adding Full Walk Speed=40. FX displacement
  length at frame 600 changed from 0.15255 to 0.74644 cm; frame 650 changed from
  0.04328 to 0.24583 cm. At frame 680 residual was below 1e-8 cm and at 700 zero.
  Status remained Ready. The user's source file was not saved or changed.
- Installed menu create/navigation/reset acceptance passed and the updated
  asynchronous panel opened successfully without restarting Cinema 4D.

Package: release/private/Camera_Rigs-0.5.6.zip (21 files).
SHA256: 197d719515f2ff46d8afb74a3bb72b98f48abf98abea3d6d9f487f8dcba13d37.
Previous installed package was backed up by the manifest-checked packager.
No GitHub publication, farm test or new clean-host test is implied.
