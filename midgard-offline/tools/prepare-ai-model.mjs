// Optional development-time downloads only. Nothing here runs when playing offline.
import {mkdir,readFile,writeFile,copyFile,stat,rename,open} from 'node:fs/promises';
import {createReadStream,createWriteStream} from 'node:fs';
import {Readable} from 'node:stream';
import {pipeline as streamPipeline} from 'node:stream/promises';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const work=path.join(root,'work'),runtimeRoot=path.join(work,'llm-runtime'),out=path.join(work,'local-ai');
const modelId='onnx-community/Qwen2.5-0.5B-Instruct',revision='516c8d04add8a80c5228f32102b57953b8d421a9';
const modelName='Qwen2.5-0.5B-Instruct',modelRoot=path.join(out,'models',modelName);
const weight={name:'onnx/model_quantized.onnx',size:512096557,sha256:'41834041ab1b29eff9fc592f1a29a1844133aea35832ea9fa91682be13016100'};
const hashFile=async file=>{const h=createHash('sha256');for await(const chunk of createReadStream(file))h.update(chunk);return h.digest('hex');};
await mkdir(runtimeRoot,{recursive:true});
let installed;try{installed=JSON.parse(await readFile(path.join(runtimeRoot,'node_modules/@huggingface/transformers/package.json'),'utf8'));}catch{}
if(installed?.version!=='3.8.1'){
  const npmCli=process.env.npm_execpath||path.join(path.dirname(process.execPath),'node_modules/npm/bin/npm-cli.js');
  try{await stat(npmCli);}catch{throw new Error('Không tìm thấy npm CLI. Cài runtime bằng npm install --prefix midgard-offline/work/llm-runtime --ignore-scripts --save-exact @huggingface/transformers@3.8.1 rồi chạy lại.');}
  const r=spawnSync(process.execPath,[npmCli,'install','--prefix',runtimeRoot,'--ignore-scripts','--no-audit','--no-fund','--save-exact','@huggingface/transformers@3.8.1'],{stdio:'inherit'});
  if(r.status!==0)throw new Error('Không cài được runtime Transformers.js 3.8.1.');
}
await mkdir(path.join(out,'runtime'),{recursive:true});
const runtimeFiles=['transformers.min.js','ort-wasm-simd-threaded.jsep.mjs','ort-wasm-simd-threaded.jsep.wasm'];
for(const file of runtimeFiles)await copyFile(path.join(runtimeRoot,'node_modules/@huggingface/transformers/dist',file),path.join(out,'runtime',file));
await copyFile(path.join(runtimeRoot,'node_modules/@huggingface/transformers/LICENSE'),path.join(out,'runtime','LICENSE-TRANSFORMERS.txt'));
await copyFile(path.join(runtimeRoot,'node_modules/@huggingface/jinja/LICENSE'),path.join(out,'runtime','LICENSE-JINJA.txt'));
await mkdir(modelRoot,{recursive:true});
const manifest={modelId,revision,modelName,dtype:'q8',runtimeVersion:'3.8.1',files:[]};
async function download(url,destination,expected){
  await mkdir(path.dirname(destination),{recursive:true});
  if(expected){try{const s=await stat(destination);if(s.size===expected.size&&await hashFile(destination)===expected.sha256){console.log('Verified existing '+path.relative(out,destination));return;}}catch{}}
  const temporary=destination+'.partial';
  if(expected&&expected.size>64*1024*1024){
    // Bounded parallel range requests avoid very long stalled CDN streams.
    const file=await open(temporary,'w'),chunkSize=4*1024*1024,total=Math.ceil(expected.size/chunkSize);let next=0,done=0;
    try{await Promise.all(Array.from({length:16},async()=>{
      while(next<total){const index=next++,start=index*chunkSize,end=Math.min(expected.size-1,start+chunkSize-1);let bytes;
        for(let attempt=0;attempt<3;attempt++){
          try{const r=await fetch(url,{headers:{Range:`bytes=${start}-${end}`},signal:AbortSignal.timeout(90000)});if(r.status!==206||r.headers.get('content-range')!==`bytes ${start}-${end}/${expected.size}`)throw new Error('CDN did not return the expected byte range.');bytes=Buffer.from(await r.arrayBuffer());if(bytes.length!==end-start+1)throw new Error('Incomplete model range.');break;}catch(error){if(attempt===2)throw error;}
        }
        await file.write(bytes,0,bytes.length,start);done++;if(done%8===0||done===total)console.log(`Model chunks ${done}/${total}`);
      }
    }));}finally{await file.close();}
  }else{
    const response=await fetch(url,{signal:AbortSignal.timeout(90000)});if(!response.ok)throw new Error(`Download failed ${response.status}: ${url}`);
    await streamPipeline(Readable.fromWeb(response.body),createWriteStream(temporary));
  }
  if(expected){const s=await stat(temporary);if(s.size!==expected.size||await hashFile(temporary)!==expected.sha256)throw new Error('Model size/SHA-256 mismatch; partial file retained, not activated.');}
  await rename(temporary,destination);console.log('Prepared '+path.relative(out,destination));
}
for(const name of ['config.json','generation_config.json','tokenizer.json','tokenizer_config.json',weight.name]){
  const destination=path.join(modelRoot,...name.split('/'));
  await download(`https://huggingface.co/${modelId}/resolve/${revision}/${name}`,destination,name===weight.name?weight:null);
  manifest.files.push({path:`models/${modelName}/${name}`,size:(await stat(destination)).size,sha256:await hashFile(destination)});
}
await download('https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/resolve/7ae557604adf67be50417f59c2c2f167def9a775/LICENSE',path.join(out,'LICENSE-QWEN.txt'));
await download('https://raw.githubusercontent.com/microsoft/onnxruntime/89f8206ba4f1c22c39e0297fb55272e8ce8cd7d0/LICENSE',path.join(out,'runtime','LICENSE-ONNXRUNTIME.txt'));
await download('https://raw.githubusercontent.com/microsoft/onnxruntime/89f8206ba4f1c22c39e0297fb55272e8ce8cd7d0/ThirdPartyNotices.txt',path.join(out,'runtime','THIRD-PARTY-ONNXRUNTIME.txt'));
for(const file of runtimeFiles)manifest.files.push({path:'runtime/'+file,size:(await stat(path.join(out,'runtime',file))).size,sha256:await hashFile(path.join(out,'runtime',file))});
await writeFile(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
await writeFile(path.join(out,'README.txt'),'Optional local language model: Qwen2.5-0.5B-Instruct q8\nAll inference runs locally. Apache-2.0 model/runtime licenses included.\nCopy this entire local-ai folder next to the game web shell only when enabling local LLM support.\nNot included in the small default build. Web/Android device inference still requires device QA.\n');
console.log('Ready: '+out);
