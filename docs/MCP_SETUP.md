# Serena and Cinema 4D MCP setup

This runbook is for the local CamRig development checkout and Cinema 4D 2026.

## Current installation

- Serena: global Codex stdio server, `Serena 1.6.1`.
- Cinema 4D MCP: `@kumoproductions/mcp-cinema4d@0.3.1`.
- C4D bridge: `%APPDATA%\Maxon\Maxon Cinema 4D 2026_1ABCDC12\plugins\cinema4d_mcp_bridge\`.
- C4D bundled Python: `C:\Program Files\Maxon Cinema 4D 2026\resource\modules\python\libs\win64\python.exe` (3.11.4).

## Environment

The user environment must contain `C4D_MCP_TOKEN`, `C4D_MCP_HOST=127.0.0.1`, `C4D_MCP_PORT=18710`, `C4D_MCP_ENABLE_EXEC_PYTHON=1`, and `C4D_MCP_ENABLE_PYTHON_OPS=1`. The same host, port, and token must be available to the C4D bridge. Restart C4D after changing them.

Full Python mode is intentionally enabled for this development setup. `exec_python` has access to the Cinema 4D process, files, subprocesses, and network. Use it only with trusted scenes and keep approval for `open_document`, `import_scene`, `save_document`, `render`, `call_command`, `remove_entity`, and Python execution.

## Startup and smoke test

1. Start Cinema 4D 2026 and confirm the bridge log reports listening on `127.0.0.1:18710`.
2. In Codex, run `codex mcp list` and `codex mcp get cinema4d`.
3. Call the Cinema 4D MCP `ping` tool, then `list_entities`.
4. In a disposable scene, create one test object, inspect it, remove it, and verify Undo in Cinema 4D.
5. Load CamRig and verify Create Rig, User Data, Python Tag, Reset, and Break.

`Unsupported` in CLI auth status does not prove tools unavailable. Test an actual ping first; refresh the task tool inventory only if tools are genuinely missing.

## Static checks

```powershell
& 'C:\Program Files\Maxon Cinema 4D 2026\resource\modules\python\libs\win64\python.exe' tools/check_project.py
python tools/build_production_release.py --development --keep-docs
```

A successful compile under bundled Python does not prove a live c4d import. Import and scene behavior must be tested inside the running C4D process. See [1.5 acceptance](ACCEPTANCE_1_5.md).
