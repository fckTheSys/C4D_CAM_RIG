# CamRig Agent MCP acceptance

Status: **incomplete development acceptance**. The full acceptance plan has not
passed. Historical live checks below are not proof for the current working tree.
The test fixture is `tests/artifacts/CamRig_Axis_Controls_Test.c4d` and is
intentionally excluded from releases.

## Historical checks (must be re-run on the final package)

| Area | Evidence |
|---|---|
| stdio transport | Standard MCP client completed initialize, tools/list and tools/call; 21 tools were published. |
| JSON values | `false` and `null` crossed Node, the Cinema 4D bridge and host Python; both mutations were undone. |
| Keyframes | Orbit keys at frames 0 and 60.5 retained `-720` and `1080`; C4D reported Linear=2, Step=3 and Spline=1. |
| Reset All | Aim Offset, Focus Offset and Spring returned to defaults while target links remained unchanged. |
| Viewport capture | FX camera produced a verified 320×180 PNG through Preview Hardware. |
| Static boundary | `tools/check_project.py` compiled host/runtime files, checked schema parity and Markdown links. |

## Current live evidence — 2026-09-09

Cinema 4D 2026.2 (2026200) with bundled Python 3.11.4 loaded CamRig directly
from this repository. `tests/c4d_agent_regression.py` passed ten isolated
scenarios: exact 60.5-frame keys with Linear/Step/Spline, finite-value
rejection, 24/25/30/60 FPS timing, escaped duplicate paths, batch preflight,
key Undo/Redo, root-transform preflight and batch rollback after an injected
second-rig failure.

`tools/test_camrig_mcp.mjs` then used the real stdio protocol against the local
Cinema 4D bridge. It discovered 21 tools and successfully ran get-state,
multi-control mutation, `null` target assignment, replace-confirmed subframe
keys, sample, FX capture, Save, Bake dry-run, invalid-control rejection, time
restoration and Undo restoration of Orbit, Height and Focus Target. The saved
scene reopened with both schema-3 / runtime-1.6.0 rigs present.

The contract script now treats restored Orbit, Height and Focus Target as hard
assertions and also requires non-empty PNG and `.c4d` outputs. A second strict
run used a separately inserted `CamRig MCP Strict QA` document. After it
passed, that document was closed and `CamRig MCP Contract QA` was made active
again. The live save/reopen regression sampled frames 0, 10, 15, 30, 60.5 and
100: camera/FX matrices and key time/value/interpolation matched before and
after reopening.

The contract script creates its own uniquely named QA document through the
trusted local bridge, runs the public `camrig-agent` stdio tools against it and
then restores the exact source document through a session registry. Before QA
starts it writes and reopens a verified `.c4d` clone. The clone is an emergency
recovery path, not the normal success path, and remains in the ignored artifact
directory for review. A source restored from a clone is returned as
`status: "RECOVERED"` and makes the public contract command fail instead of
printing an ordinary PASS.

`tests/c4d_document_harness_regression.py` exercised a populated source scene:
object transforms, User Data link, animated User Data track, material colour,
selection, FPS 47, frame 13 and a 1234×567 render size. It passed normal
identity restore, duplicate document names, injected setup failure, injected
cleanup failure followed by retry, and an intentionally forced snapshot
recovery. The forced recovery was explicitly reported as `RECOVERED`.

The full public stdio run then passed from a saved disposable source fixture:
21 published tools; controls/targets/samples restored by Undo; FX PNG and
saved scene non-empty; lifecycle `source: "original"`, `status: "PASS"`.
It compares returned controls and targets plus sampled matrices at frames 0,
30.25 and 60.5 before and after Undo. Cleanup errors fail the run.

Visual artefacts are intentionally ignored under `tests/artifacts/`:

- `mcp_contract_qa_20260909/mcp_fx.png` and `mcp_contract.c4d`
- `spring_movie_20260909/spring_lift_settle.mp4` — 640×360, 15 FPS, 3.4 s

The movie is a preview-hardware viewport capture. It demonstrates spring
motion visually; numerical spring acceptance remains in the host regression
and solver tests.

## Current limits

- As of the 2026-09-09 continuation, the C4D bridge refused connections on
  `127.0.0.1:18710` and no Cinema 4D process was found. No live acceptance was
  performed during that continuation. After the user started C4D, the bridge
  connected successfully (2026200 / Python 3.11.4, package loaded from this repo).
  Nine isolated host-API regression scenarios passed, including exact subframes,
  interpolation, invalid animation, escaped paths, missing-DescID batch preflight,
  key Undo/Redo, and transform validation/partial XYZ Undo. Active document and
  time were unchanged. An additional injected failure on the second batch rig
  returned an error and restored both Height values to 111 and 222. This proves
  those values rolled back, not a complete matrix/link/track snapshot comparison.
  These are live host-API checks, not the complete stdio MCP acceptance matrix.
- Current static checks pass under bundled Python 3.11.4: 36 files compile,
  37 template parameters and local Markdown links validate; 10 unit tests pass.
  Unit preflight tests exercise extracted host functions without simulating C4D.
- Root transform validation now rejects non-finite values, booleans and unknown
  axes before starting Undo. Scale requires literal `confirm=true` and rejects
  animated scale/frozen transforms on the root and its ancestors. These C4D
  safeguards still require live verification.
- Save now requires an absolute `.c4d` path with an existing parent directory.
  Reopening a newly saved scene remains a live acceptance requirement.
- `tests/c4d_agent_regression.py` includes exact subframe/interpolation checks
  and a new root-transform rejection/partial-XYZ/Undo case. Re-run it in C4D
  on the main thread; it owns a separate document.
- Comprehensive geometry, capture failure recovery, batch fault injection and
  the full stdio operation matrix remain acceptance work, not confirmed PASS.

- Bake Camera is a dry-run only.
- Render Preview and Repair are not CamRig Agent tools yet.
- Redshift camera acceptance requires a machine with Redshift installed.
- A timed-out render requires an explicit bridge/document health check before
  the caller issues another mutation.

## Re-run

Start Cinema 4D with `C4D_MCP_ENABLE_EXEC_PYTHON=1` and the configured token,
then run from the repository root. Use a saved disposable source fixture for
an ordinary PASS. The contract harness creates/removes its own temporary QA
document; a verified recovery snapshot is retained under the output directory:

```powershell
$env:C4D_MCP_ENABLE_EXEC_PYTHON='1'
$env:C4D_MCP_ENABLE_PYTHON_OPS='1'
$env:CAMRIG_TEST_OUTPUT='C:\absolute\output\directory'
node test_camrig_mcp.mjs
```

The contract test uses the public stdio MCP protocol; it does not import
`camrig.agent_api` directly.
