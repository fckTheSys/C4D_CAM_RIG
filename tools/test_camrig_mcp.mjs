/* Contract smoke: uses the public stdio protocol, never imports CamRig Python. */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here=path.dirname(fileURLToPath(import.meta.url));
const client=new Client({name:"camrig-agent-contract",version:"1.0.0"},{capabilities:{}});
const transport=new StdioClientTransport({command:process.execPath,args:[path.join(here,"camrig_mcp_server.js")],env:process.env});
await client.connect(transport);
const listed=await client.listTools();
if(!listed.tools.some(tool=>tool.name==="camrig_scene_state")) throw new Error("camrig_scene_state missing");
const reply=await client.callTool({name:"camrig_scene_state",arguments:{}});
const text=reply.content.filter(part=>part.type==="text").map(part=>part.text).join("\n");
const state=JSON.parse(text);
if(!state.ok || !state.scene) throw new Error("invalid scene state: "+text);
const rig="/CamRig_Axis_Test";
async function tool(name, arguments_) {
  const result=await client.callTool({name,arguments:arguments_});
  return JSON.parse(result.content.filter(part=>part.type==="text").map(part=>part.text).join("\n"));
}
const controls=await tool("camrig_set_controls",{rig,controls:{use_target:false},evaluate:true});
if(!controls.ok) throw new Error("boolean transport failed: "+JSON.stringify(controls));
const targets=await tool("camrig_set_targets",{rig,targets:{focus_target:null}});
if(!targets.ok) throw new Error("null transport failed: "+JSON.stringify(targets));
const undoA=await tool("camrig_undo",{}), undoB=await tool("camrig_undo",{});
if(!undoA.ok || !undoB.ok) throw new Error("undo failed");
console.log(JSON.stringify({tools:listed.tools.length,scene:state.scene,ok:state.ok,boolean:true,null:true}));
await transport.close();
