# C4D Cam Rig (Cam Rig Builder)

Cinema 4D Python command plugin, v1.4.0.

CamRig creates an orbital camera rig controlled by User Data on `Cam_Rig`. It supports Target A/B blending, offset and rotation, focal/focus controls, procedural shake and optional drift. The complete runtime is embedded into a Python Tag so scenes can remain portable.

## Requirements

- Cinema 4D 2026 with Python support.
- Redshift is optional; the builder falls back to a standard camera.

## Installation

Copy the complete repository folder into the active Cinema 4D `plugins` directory. `cam_rig_builder.pyp` and the `camrig` folder must be siblings. Restart Cinema 4D and check Script Log for `[CamRig] v1.4.0 loaded`.

See [INSTALL.md](INSTALL.md) for the full procedure.

## Development

- Architecture: [docs/SUMMARY.md](docs/SUMMARY.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- MCP setup: [docs/MCP_SETUP.md](docs/MCP_SETUP.md)
- Release notes: [CHANGELOG.md](CHANGELOG.md)

Keep `PLUGIN_VERSION` and `EMBEDDED_RUNTIME_VERSION` synchronized. Obtain unique PluginCafe IDs before public distribution.
