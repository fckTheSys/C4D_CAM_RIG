# CamRig Agent MCP

`camrig-agent` is a thin stdio facade over the existing Cinema 4D MCP bridge.
It adds stable CamRig keys and path-based operations; it does not open an HTTP
port and it never replaces the embedded runtime in a saved scene.

## Setup

Install the proxy dependency from `tools/` and add the example server entry to
the agent MCP configuration:

```powershell
cd tools
npm.cmd install
```

Cinema 4D must be running with the CamRig bridge plugin on `127.0.0.1:18710`.
Set the same `C4D_MCP_TOKEN` for the bridge and the proxy. The proxy starts the
version-pinned `@kumoproductions/mcp-cinema4d@0.3.1` child on demand.

## Safe workflow

Use `camrig_scene_state` or `camrig_get_state` first and pass a unique object
path such as `/Cam_Rig_0`. Combine related edits into one
`camrig_set_controls` call, then call `camrig_set_time` to evaluate. Orbit is
never normalized, so values such as `720` remain intact in User Data and keys.

The facade exposes scene state, controls, targets, time, keyframes, sampling,
reset, upgrade, create/duplicate, guarded save, batch, Undo/Redo and viewport
capture. Every scene mutation has one Cinema 4D Undo boundary. Bake Camera is
currently a dry-run and must not be presented as a production bake command.

`camrig_capture_viewport` is the exception for QA: it uses Cinema 4D's
Preview Hardware `RenderDocument` path, temporarily selects the rig FX camera,
restores the viewport state, and writes a PNG plus metadata. It does not need
ComfyUI or the Lesta bridge.

See `AGENT_MCP_ACCEPTANCE.md` for the current live acceptance evidence and
known limits.

Example intent:

```text
Set /Cam_Rig_0 to Height=180, Orbit=720, Spring Amount=40,
then evaluate frames 0, 30 and 60 and report diagnostics.
```
