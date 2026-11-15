// Dependency-free, reproducible ZIP (stored entries, CRC-32, UTF-8 filenames).
import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';
const root=fileURLToPath(new URL('../',import.meta.url));
const output=path.join(root,'dist');
const files=['index.html','style.css','engine.js','game.js','icon.svg','CHOI_GAME.cmd','README.md'];
const bundle=path.join(output,'midgard-offline');
await mkdir(bundle,{recursive:true});
const table=Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
function crc32(bytes){let crc=0xffffffff;for(const b of bytes)crc=table[(crc^b)&255]^(crc>>>8);return (crc^0xffffffff)>>>0;}
const local=[],central=[],hashes=[];let offset=0;
for(const file of files){
  const data=await readFile(path.join(root,file));
  await copyFile(path.join(root,file),path.join(bundle,file));
  hashes.push(`${createHash('sha256').update(data).digest('hex')}  ${file}`);
  const name=Buffer.from(`midgard-offline/${file}`,'utf8'),crc=crc32(data);
  const header=Buffer.alloc(30);header.writeUInt32LE(0x04034b50,0);header.writeUInt16LE(20,4);header.writeUInt16LE(0x800,6);header.writeUInt16LE(0x21,12);header.writeUInt32LE(crc,14);header.writeUInt32LE(data.length,18);header.writeUInt32LE(data.length,22);header.writeUInt16LE(name.length,26);
  local.push(header,name,data);
  const dir=Buffer.alloc(46);dir.writeUInt32LE(0x02014b50,0);dir.writeUInt16LE(20,4);dir.writeUInt16LE(20,6);dir.writeUInt16LE(0x800,8);dir.writeUInt16LE(0x21,14);dir.writeUInt32LE(crc,16);dir.writeUInt32LE(data.length,20);dir.writeUInt32LE(data.length,24);dir.writeUInt16LE(name.length,28);dir.writeUInt32LE(offset,42);central.push(dir,name);offset+=header.length+name.length+data.length;
}
const directory=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50,0);end.writeUInt16LE(files.length,8);end.writeUInt16LE(files.length,10);end.writeUInt32LE(directory.length,12);end.writeUInt32LE(offset,16);
const zip=Buffer.concat([...local,directory,end]),zipName='midgard-offline-0.1.0.zip';
await writeFile(path.join(output,zipName),zip);
await writeFile(path.join(output,'SHA256SUMS.txt'),`${createHash('sha256').update(zip).digest('hex')}  ${zipName}\n${hashes.join('\n')}\n`);
console.log(`Built ${path.join(output,zipName)} (${zip.length} bytes, ${files.length} files)`);
