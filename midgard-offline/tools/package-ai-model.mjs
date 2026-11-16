// Explicit optional large bundle. Does not alter or expand the normal game build.
import {open,readFile,stat,mkdir,writeFile} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url)),source=path.join(root,'work/local-ai'),out=path.join(root,'dist');
const manifest=JSON.parse(await readFile(path.join(source,'manifest.json'),'utf8'));
if(manifest.revision!=='516c8d04add8a80c5228f32102b57953b8d421a9'||manifest.runtimeVersion!=='3.8.1')throw new Error('Unexpected optional model/runtime version.');
const allowed=new Set(['models/Qwen2.5-0.5B-Instruct/config.json','models/Qwen2.5-0.5B-Instruct/generation_config.json','models/Qwen2.5-0.5B-Instruct/tokenizer.json','models/Qwen2.5-0.5B-Instruct/tokenizer_config.json','models/Qwen2.5-0.5B-Instruct/onnx/model_quantized.onnx','runtime/transformers.min.js','runtime/ort-wasm-simd-threaded.jsep.mjs','runtime/ort-wasm-simd-threaded.jsep.wasm']);
if(!Array.isArray(manifest.files)||manifest.files.length!==allowed.size||new Set(manifest.files.map(f=>f.path)).size!==allowed.size||manifest.files.some(f=>!allowed.has(f.path)))throw new Error('Optional model file whitelist mismatch.');
const weight=manifest.files.find(f=>f.path.endsWith('/model_quantized.onnx'));
if(weight.size!==512096557||weight.sha256!=='41834041ab1b29eff9fc592f1a29a1844133aea35832ea9fa91682be13016100')throw new Error('Unexpected model weight size/SHA-256.');
const table=Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
for(const item of manifest.files){
  if(!/^(models\/Qwen2\.5-0\.5B-Instruct\/|runtime\/)[a-zA-Z0-9_./-]+$/.test(item.path)||item.path.includes('..'))throw new Error('Unsafe manifest path.');
  const h=createHash('sha256');let size=0;for await(const bytes of createReadStream(path.join(source,item.path))){h.update(bytes);size+=bytes.length;}
  if(size!==item.size||h.digest('hex')!==item.sha256)throw new Error('Optional AI manifest verification failed: '+item.path);
}
const required=['manifest.json','README.txt','LICENSE-QWEN.txt','runtime/LICENSE-TRANSFORMERS.txt','runtime/LICENSE-ONNXRUNTIME.txt','runtime/LICENSE-JINJA.txt','runtime/THIRD-PARTY-ONNXRUNTIME.txt'];
const entries=[...manifest.files.map(x=>({name:'local-ai/'+x.path,file:path.join(source,x.path)})),...required.map(name=>({name:'local-ai/'+name,file:path.join(source,name)})),{name:'llm.js',file:path.join(root,'llm.js')},{name:'LOCAL_LLM.md',file:path.join(root,'docs/LOCAL_LLM.md')}].sort((a,b)=>a.name.localeCompare(b.name,'en'));
if(new Set(entries.map(x=>x.name)).size!==entries.length)throw new Error('Duplicate optional bundle entry.');
await mkdir(out,{recursive:true});
const destination=path.join(out,'midgard-local-ai-qwen-0.5b-q8-experimental.zip'),handle=await open(destination,'w'),central=[],archiveHash=createHash('sha256');let offset=0;
async function write(bytes){let done=0;while(done<bytes.length){const result=await handle.write(bytes,done,bytes.length-done);if(!result.bytesWritten)throw new Error('Short ZIP write.');done+=result.bytesWritten;}offset+=bytes.length;archiveHash.update(bytes);}
try{
  for(const item of entries){
    const info=await stat(item.file);if(!info.isFile()||info.size>=0xffffffff)throw new Error('Unsupported ZIP entry.');
    const start=offset,name=Buffer.from(item.name,'utf8'),header=Buffer.alloc(30);header.writeUInt32LE(0x04034b50,0);header.writeUInt16LE(20,4);header.writeUInt16LE(0x808,6);header.writeUInt16LE(0x21,12);header.writeUInt16LE(name.length,26);await write(header);await write(name);
    let crc=0xffffffff,size=0;
    for await(const bytes of createReadStream(item.file)){for(const byte of bytes)crc=table[(crc^byte)&255]^(crc>>>8);size+=bytes.length;await write(bytes);}
    crc=(crc^0xffffffff)>>>0;const descriptor=Buffer.alloc(16);descriptor.writeUInt32LE(0x08074b50,0);descriptor.writeUInt32LE(crc,4);descriptor.writeUInt32LE(size,8);descriptor.writeUInt32LE(size,12);await write(descriptor);
    const record=Buffer.alloc(46);record.writeUInt32LE(0x02014b50,0);record.writeUInt16LE(20,4);record.writeUInt16LE(20,6);record.writeUInt16LE(0x808,8);record.writeUInt16LE(0x21,14);record.writeUInt32LE(crc,16);record.writeUInt32LE(size,20);record.writeUInt32LE(size,24);record.writeUInt16LE(name.length,28);record.writeUInt32LE(start,42);central.push(record,name);
  }
  const directoryStart=offset,directory=Buffer.concat(central);await write(directory);const end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50,0);end.writeUInt16LE(entries.length,8);end.writeUInt16LE(entries.length,10);end.writeUInt32LE(directory.length,12);end.writeUInt32LE(directoryStart,16);await write(end);
}finally{await handle.close();}
const hash=archiveHash.digest('hex');await writeFile(destination+'.sha256',`${hash}  ${path.basename(destination)}\n`);console.log(JSON.stringify({path:destination,bytes:offset,files:entries.length,sha256:hash,scope:'experimental optional browser LLM bundle; not complete Godot native integration'},null,2));
