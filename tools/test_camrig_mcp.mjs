/* Public stdio MCP contract smoke. Creates no scene objects and restores mutations. */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const here=path.dirname(fileURLToPath(import.meta.url));
const output=process.env.CAMRIG_TEST_OUTPUT;
if(!output || !path.isAbsolute(output)) throw new Error("CAMRIG_TEST_OUTPUT must be an absolute directory");
const rig="/QA Rig";
const client=new Client({name:"camrig-agent-contract",version:"1.0.0"},{capabilities:{}});
const transport=new StdioClientTransport({command:process.execPath,args:[path.join(here,"camrig_mcp_server.js")],env:process.env});
const raw=new Client({name:"camrig-agent-contract-harness",version:"1.0.0"},{capabilities:{}});
const rawTransport=new StdioClientTransport({command:process.platform==="win32"?"npx.cmd":"npx",args:["--yes","@kumoproductions/mcp-cinema4d@0.3.1"],env:process.env});
const marker="__CAMRIG_CONTRACT_HARNESS__";
const harnessToken=Date.now()+"_"+Math.random().toString(36).slice(2);
const temporaryDocument="CamRig MCP Contract "+harnessToken;
const harnessPath=path.join(here,"c4d_mcp_harness.py");
const snapshotPath=path.join(output,"mcp_harness_"+harnessToken+".c4d");
fs.mkdirSync(output,{recursive:true});
async function tool(name, arguments_) {
  const result=await client.callTool({name,arguments:arguments_});
  return JSON.parse(result.content.filter(part=>part.type==="text").map(part=>part.text).join("\n"));
}
function closeEnough(left, right, tolerance=1e-5) {
  if(typeof left === "number" && typeof right === "number") return Math.abs(left-right)<=tolerance;
  if(Array.isArray(left) && Array.isArray(right)) return left.length===right.length && left.every((value,index)=>closeEnough(value,right[index],tolerance));
  if(left && right && typeof left === "object" && typeof right === "object") {
    const keys=Object.keys(left);
    return keys.length===Object.keys(right).length && keys.every(key=>Object.hasOwn(right,key) && closeEnough(left[key],right[key],tolerance));
  }
  return left===right;
}
function requireOk(value, label) {
  if(!value.ok) throw new Error(label+": "+JSON.stringify(value));
  return value;
}
async function rawPython(bridge, code) {
  const reply=await bridge.callTool({name:"exec_python",arguments:{code,timeout_ms:30000}});
  const text=reply.content.filter(part=>part.type==="text").map(part=>part.text).join("\n");
  let envelope;
  try { envelope=JSON.parse(text); }
  catch(error) { throw new Error("bridge response was not JSON: "+text); }
  if(envelope.error) throw new Error(envelope.error);
  const index=(envelope.stdout||"").lastIndexOf(marker);
  if(index<0) throw new Error("harness result missing: "+(envelope.stdout||text));
  return JSON.parse(envelope.stdout.slice(index+marker.length).trim());
}
let undoCount=0;
let initialFrame;
let connected=false;
let rawConnected=false;
let setup;
let failure;
let successReport;
try {
  await raw.connect(rawTransport);
  rawConnected=true;
  setup=await rawPython(raw,"import base64,json,runpy\ndata=json.loads(base64.b64decode("+JSON.stringify(Buffer.from(JSON.stringify({harness:harnessPath,fixture:path.join(here,"..","tests","build_agent_qa.py"),snapshot:snapshotPath,temporary:temporaryDocument,token:harnessToken}),"utf8").toString("base64"))+").decode('utf-8'))\nharness=runpy.run_path(data['harness'])\nresult=harness['prepare'](data['snapshot'],data['temporary'],data['fixture'],data['token'])\nprint('"+marker+"'+json.dumps(result))");
  await raw.close();
  rawConnected=false;
  await client.connect(transport);
  connected=true;
  const listed=await client.listTools();
  if(listed.tools.length!==21 || !listed.tools.some(tool=>tool.name==="camrig_set_keyframes")) throw new Error("unexpected public tool inventory");
  const scene=requireOk(await tool("camrig_scene_state",{}),"scene_state");
  initialFrame=scene.scene.current_frame;
  const before=requireOk(await tool("camrig_get_state",{rig,include:["controls","targets","camera","spring"]}),"get_state");
  const baseline=requireOk(await tool("camrig_sample",{rig,frames:[0,30.25,60.5]}),"baseline sample");
  requireOk(await tool("camrig_set_controls",{rig,controls:{orbit:720,height:180,spring_amount:40,use_target:false},evaluate:true}),"set_controls"); undoCount++;
  requireOk(await tool("camrig_set_targets",{rig,targets:{focus_target:null}}),"set_targets null"); undoCount++;
  requireOk(await tool("camrig_set_keyframes",{rig,tracks:{orbit:[{frame:0,value:0},{frame:60.5,value:720}]},interpolation:"linear",replace_existing:true,confirm:true}),"set_keyframes"); undoCount++;
  const sampled=requireOk(await tool("camrig_sample",{rig,frames:[0,30.25,60.5]}),"sample");
  if(sampled.state.samples.length!==3 || !closeEnough(sampled.state.samples.map(row=>row.frame),[0,30.25,60.5],1e-9)) throw new Error("sample did not preserve requested subframes");
  requireOk(await tool("camrig_capture_viewport",{rig,path:path.join(output,"mcp_fx.png"),frame:30,width:640,height:360,camera:"fx",confirm:true}),"capture");
  requireOk(await tool("camrig_save_scene",{path:path.join(output,"mcp_contract.c4d"),confirm:true}),"save_scene");
  const bake=requireOk(await tool("camrig_bake_camera",{rig}),"bake dry-run");
  if(!bake.state.bake?.dry_run) throw new Error("bake must remain dry-run");
  const invalid=await tool("camrig_set_controls",{rig,controls:{unknown_control:1}});
  if(invalid.ok || invalid.errors?.[0]?.code!=="INVALID_CONTROL") throw new Error("invalid-control error contract failed");
  requireOk(await tool("camrig_set_time",{frame:initialFrame}),"restore time");
  while(undoCount) { requireOk(await tool("camrig_undo",{}),"undo"); undoCount--; }
  const after=requireOk(await tool("camrig_get_state",{rig,include:["controls","targets"]}),"get_state after undo");
  const restoredControls=closeEnough(after.state.controls,before.state.controls);
  const restoredTargets=closeEnough(after.state.targets,before.state.targets);
  const afterSamples=requireOk(await tool("camrig_sample",{rig,frames:[0,30.25,60.5]}),"sample after undo");
  const restoredSamples=closeEnough(afterSamples.state.samples,baseline.state.samples);
  const capturePath=path.join(output,"mcp_fx.png"), scenePath=path.join(output,"mcp_contract.c4d");
  if(!restoredControls || !restoredTargets || !restoredSamples) throw new Error("Undo did not restore complete CamRig state");
  if(!fs.existsSync(capturePath) || fs.statSync(capturePath).size===0) throw new Error("capture output missing");
  if(!fs.existsSync(scenePath) || fs.statSync(scenePath).size===0) throw new Error("saved scene missing");
  successReport={tools:listed.tools.length,initialFrame,restoredControls,restoredTargets,restoredSamples,capture:capturePath,scene:scenePath,ok:true};
} catch(error) {
  failure=error;
} finally {
  const cleanupErrors=[];
  if(connected && initialFrame !== undefined) {
    try { requireOk(await tool("camrig_set_time",{frame:initialFrame}),"cleanup time"); }
    catch(error) { cleanupErrors.push(error); }
  }
  for(let pending=undoCount; connected && pending>0; pending--) {
    try { requireOk(await tool("camrig_undo",{}),"cleanup undo"); }
    catch(error) { cleanupErrors.push(error); }
  }
  undoCount=0;
  try { await transport.close(); } catch(error) { cleanupErrors.push(error); }
  if(rawConnected) {
    try { await raw.close(); } catch(error) { cleanupErrors.push(error); }
  }
  if(setup) {
    const cleanupRaw=new Client({name:"camrig-agent-contract-cleanup",version:"1.0.0"},{capabilities:{}});
    const cleanupTransport=new StdioClientTransport({command:process.platform==="win32"?"npx.cmd":"npx",args:["--yes","@kumoproductions/mcp-cinema4d@0.3.1"],env:process.env});
    try {
      await cleanupRaw.connect(cleanupTransport);
      const restored=await rawPython(cleanupRaw,"import base64,json,runpy\ndata=json.loads(base64.b64decode("+JSON.stringify(Buffer.from(JSON.stringify({harness:harnessPath,snapshot:setup.snapshot,temporary:setup.temporary,token:setup.token,before:setup.before}),"utf8").toString("base64"))+").decode('utf-8'))\nharness=runpy.run_path(data['harness'])\nresult=harness['cleanup'](data['snapshot'],data['temporary'],data['token'],data['before'])\nprint('"+marker+"'+json.dumps(result))");
      if(!restored.restored || !restored.fingerprint_match) throw new Error("original document was not restored");
    } catch(error) { cleanupErrors.push(error); }
    finally { await cleanupRaw.close().catch(error=>cleanupErrors.push(error)); }
  }
  if(cleanupErrors.length) {
    const cleanupFailure=new Error("MCP cleanup failed: "+cleanupErrors.map(error=>error.message).join("; "));
    failure=failure ? new Error(failure.message+"; "+cleanupFailure.message) : cleanupFailure;
  }
}
if(failure) throw failure;
console.log(JSON.stringify(successReport));
