import http from 'node:http';
import {stat} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const mime={'.html':'text/html; charset=utf-8','.js':'application/javascript; charset=utf-8','.mjs':'application/javascript; charset=utf-8','.wasm':'application/wasm','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.json':'application/json; charset=utf-8','.onnx':'application/octet-stream'};
const server=http.createServer(async(req,res)=>{
  try{
    if(!['GET','HEAD'].includes(req.method)){res.writeHead(405).end();return;}
    const url=new URL(req.url,'http://localhost');
    const file=path.resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));
    const relative=path.relative(root,file),parts=relative.split(path.sep);
    if(!file.startsWith(root)||path.isAbsolute(relative)||parts.some(x=>x.startsWith('.'))||['work','private','imported','tools','tests','platforms'].includes(parts[0])){res.writeHead(403).end();return;}
    const info=await stat(file);if(!info.isFile()){res.writeHead(404).end();return;}
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Content-Length':info.size,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
    if(req.method==='HEAD'){res.end();return;}
    const stream=createReadStream(file);stream.on('error',()=>res.destroy());res.on('close',()=>stream.destroy());stream.pipe(res);
  }catch{res.writeHead(404).end('Not found');}
});
server.listen(8765,'127.0.0.1',()=>console.log('Local: http://127.0.0.1:8765/'));
