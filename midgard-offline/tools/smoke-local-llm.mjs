// Real optional inference check; requires prepare-ai-model.mjs first.
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
const require=createRequire(import.meta.url),{create}=require('../llm.js');
const root=fileURLToPath(new URL('../',import.meta.url)),base=path.join(root,'work/local-ai');
const manifest=JSON.parse(await readFile(path.join(base,'manifest.json'),'utf8'));
// From here forward, even accidental network calls fail the check.
globalThis.fetch=async()=>{throw new Error('Network disabled by smoke-local-llm.mjs');};
const ai=create({baseUrl:pathToFileURL(base+path.sep).href,runtimeModule:pathToFileURL(path.join(root,'work/llm-runtime/node_modules/@huggingface/transformers/dist/transformers.node.mjs')).href,modelPath:path.join(base,'models')+path.sep,device:'cpu',maxNewTokens:48});
const started=Date.now();await ai.load();const loaded=Date.now();
const reply=await ai.chat('Chào Ánh Dương. Tôi còn ít máu, nên làm gì trong trận? Trả lời ngắn bằng tiếng Việt.',{player:{hp:20,maxHp:100}});
const completed=Date.now();await ai.dispose();
if(reply.mode!=='local-llm'||typeof reply.text!=='string'||reply.text.trim().length<5)throw new Error('Real model inference returned no useful text.');
const report={time:new Date().toISOString(),model:manifest.modelId,revision:manifest.revision,dtype:manifest.dtype,device:'cpu',runtimeVersion:manifest.runtimeVersion,network:'fetch disabled before model load',loadMs:loaded-started,inferenceMs:completed-loaded,reply:reply.text,scope:'Node CPU inference only; browser/WebGPU/Android device inference not verified'};
await writeFile(path.join(root,'work/local-ai-smoke.private.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
