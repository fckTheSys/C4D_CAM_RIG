# CamRig Agent MCP acceptance

Status: development acceptance on Cinema 4D 2026.2 / bundled Python 3.11.4.
The test fixture is `tests/artifacts/CamRig_Axis_Controls_Test.c4d` and is
intentionally excluded from releases.

## Verified

| Area | Evidence |
|---|---|
| stdio transport | Standard MCP client completed initialize, tools/list and tools/call; 21 tools were published. |
| JSON values | `false` and `null` crossed Node, the Cinema 4D bridge and host Python; both mutations were undone. |
| Keyframes | Orbit keys at frames 0 and 60.5 retained `-720` and `1080`; C4D reported Linear=2, Step=3 and Spline=1. |
| Reset All | Aim Offset, Focus Offset and Spring returned to defaults while target links remained unchanged. |
| Viewport capture | FX camera produced a verified 320×180 PNG through Preview Hardware. |
| Static boundary | `tools/check_project.py` compiled host/runtime files, checked schema parity and Markdown links. |

## Current limits

- Bake Camera is a dry-run only.
- Render Preview and Repair are not CamRig Agent tools yet.
- Redshift camera acceptance requires a machine with Redshift installed.
- A timed-out render requires an explicit bridge/document health check before
  the caller issues another mutation.

## Re-run

Start Cinema 4D with `C4D_MCP_ENABLE_EXEC_PYTHON=1` and the configured token,
then run from `tools/`:

```powershell
$env:C4D_MCP_ENABLE_EXEC_PYTHON='1'
$env:C4D_MCP_ENABLE_PYTHON_OPS='1'
node test_camrig_mcp.mjs
```

The contract test uses the public stdio MCP protocol; it does not import
`camrig.agent_api` directly.
