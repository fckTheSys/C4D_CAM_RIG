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

The current facade exposes scene state, rig listing/state, controls, targets,
time, reset, and known-runtime upgrade. All mutations use one Cinema 4D Undo
boundary. Production operations such as bake, overwrite-save, render and
batch are intentionally not silently emulated; they will be added only when
the underlying CamRig command has a verified implementation.

Example intent:

```text
Set /Cam_Rig_0 to Height=180, Orbit=720, Spring Amount=40,
then evaluate frames 0, 30 and 60 and report diagnostics.
```
