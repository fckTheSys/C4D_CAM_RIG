# CamRig installation

1. Copy the complete CamRig folder into the plugins directory of Cinema 4D 2026, for example `%APPDATA%\Maxon\Maxon Cinema 4D 2026_<hash>\plugins\CamRig\`.
2. Keep `cam_rig_builder.pyp` and `camrig\` at the same level.
3. Restart Cinema 4D.
4. Check Script Log for `[CamRig] v1.6.0 loaded`.
5. Run **Extensions → Plugins → Cam Rig Builder**.

For MCP-assisted development, install the matching `cinema4d_mcp_bridge` plugin and follow [docs/MCP_SETUP.md](docs/MCP_SETUP.md).

Existing scenes are not upgraded automatically. See [Upgrade 1.5](docs/UPGRADE_1_5.md) and [Follow Spring 1.6](docs/SPRING_1_6.md). Restart C4D after installing: a running Python process can still hold the old camrig modules.
