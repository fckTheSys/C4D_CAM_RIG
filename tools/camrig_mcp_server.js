#!/usr/bin/env node
/* CamRig-specific MCP facade.  It owns no socket: only stdio and the existing
 * Cinema 4D MCP child are used. */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ListToolsRequestSchema, CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";

const TOOLS = [
  ["camrig_scene_state","Read active scene and all CamRigs",{}],
  ["camrig_list_rigs","List CamRigs",{}],
  ["camrig_get_state","Read a CamRig by path",{rig:{type:"string"},include:{type:"array",items:{type:"string"}}}],
  ["camrig_set_controls","Atomically set stable CamRig controls",{rig:{type:"string"},controls:{type:"object"},keyframe:{type:"boolean"},evaluate:{type:"boolean"}}],
  ["camrig_set_targets","Set external target links by path",{rig:{type:"string"},targets:{type:"object"}}],
  ["camrig_set_camera_mode","Set targeting, focus and focal controls",{rig:{type:"string"},values:{type:"object"}}],
  ["camrig_set_root_transform","Set root position/rotation",{rig:{type:"string"},transform:{type:"object"}}],
  ["camrig_set_keyframes","Create or update control keys",{rig:{type:"string"},tracks:{type:"object"},replace_existing:{type:"boolean"},confirm:{type:"boolean"}}],
  ["camrig_set_time","Evaluate a frame or second",{frame:{type:"number"},seconds:{type:"number"}}],
  ["camrig_sample","Sample camera transforms without leaving the current frame",{rig:{type:"string"},frames:{type:"array",items:{type:"number"}}}],
  ["camrig_diagnostics","Run CamRig Inspector diagnostics",{rig:{type:"string"}}],
  ["camrig_reset","Reset a control group",{rig:{type:"string"},group:{type:"string"}}],
  ["camrig_upgrade","Upgrade a known legacy rig",{rig:{type:"string"}}],
  ["camrig_create","Create a new CamRig",{name:{type:"string"}}],
  ["camrig_duplicate","Duplicate a CamRig",{rig:{type:"string"},name:{type:"string"}}],
  ["camrig_save_scene","Save the active document",{path:{type:"string"},confirm:{type:"boolean"}}],
  ["camrig_bake_camera","Dry-run or explicitly request camera bake",{rig:{type:"string"},confirm:{type:"boolean"}}],
  ["camrig_batch","Dry-run or apply one atomic operation to multiple rigs",{rigs:{type:"array",items:{type:"string"}},action:{type:"string"},controls:{type:"object"},group:{type:"string"},dry_run:{type:"boolean"},confirm:{type:"boolean"}}],
  ["camrig_undo","Undo the last Cinema 4D operation",{}],
  ["camrig_redo","Redo the last Cinema 4D operation",{}],
];
let client;
async function backend(){
  if(client) return client;
  const command=process.platform === "win32" ? "npx.cmd" : "npx";
  client=new Client({name:"camrig-agent",version:"1.0.0"},{capabilities:{}});
  await client.connect(new StdioClientTransport({command,args:["--yes","@kumoproductions/mcp-cinema4d@0.3.1"],env:process.env}));
  return client;
}
async function call(action,args){
  const c=await backend();
  const code="import json, c4d\nfrom camrig.agent_api import dispatch\ndoc=c4d.documents.GetActiveDocument()\nresult=dispatch(doc,"+JSON.stringify(action)+","+JSON.stringify(args||{})+")\nprint(json.dumps(result,default=str))";
  const r=await c.callTool({name:"exec_python",arguments:{code,timeout_ms:30000}});
  const text=(r.content||[]).filter(x=>x.type==="text").map(x=>x.text).join("\n");
  return {content:[{type:"text",text}]};
}
const server=new Server({name:"camrig-agent",version:"1.0.0"},{capabilities:{tools:{}}});
server.setRequestHandler(ListToolsRequestSchema,async()=>({tools:TOOLS.map(([name,description,properties])=>({name,description,inputSchema:{type:"object",properties,additionalProperties:false}}))}));
server.setRequestHandler(CallToolRequestSchema,async(req)=>{
  const name=req.params.name; const action=name.replace(/^camrig_/ ,"");
  try{return await call(action,req.params.arguments||{});}catch(e){return {isError:true,content:[{type:"text",text:JSON.stringify({ok:false,warnings:[],errors:[{code:"C4D_BRIDGE_UNAVAILABLE",message:String(e.message||e)}]})}]};}
});
server.connect(new StdioServerTransport()).catch(e=>{console.error(e);process.exit(1);});
