import {readFile,readdir,mkdir,copyFile,writeFile,rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import os from 'node:os';
export const root=fileURLToPath(new URL('../',import.meta.url));
export const version=JSON.parse(await readFile(path.join(root,'package.json'),'utf8')).version;
// Explicit file types and directories: private/work/client dumps never enter a build.
export async function gameFiles(){
  const allowedName=name=>!name.startsWith('.') && !name.includes('.private.') && !['package.json','package-lock.json','private','work','imported'].includes(name);
  const files=(await readdir(root,{withFileTypes:true})).filter(x=>x.isFile() && allowedName(x.name) && /\.(html|js|css|svg|json)$/.test(x.name)).map(x=>x.name);
  async function walk(relative){
    let entries;try{entries=await readdir(path.join(root,relative),{withFileTypes:true});}catch(error){if(error.code==='ENOENT')return;throw error;}
    for(const entry of entries){if(!allowedName(entry.name))continue;const name=path.posix.join(relative,entry.name);if(entry.isDirectory())await walk(name);else if(entry.isFile() && /\.(png|jpg|jpeg|webp|svg|ogg|mp3|wav|woff2?|ttf|json)$/.test(name))files.push(name);}
  }
  await walk('assets');
  return files.sort();
}
export async function copyGame(destination){
  const files=await gameFiles();
  const targetRoot=path.resolve(destination),distRoot=path.resolve(root,'dist')+path.sep,tempRoot=path.resolve(os.tmpdir())+path.sep;
  const tempStage=targetRoot.startsWith(tempRoot)?targetRoot.slice(tempRoot.length).split(path.sep)[0]:'';
  if(!targetRoot.startsWith(distRoot) && !tempStage.startsWith('midgard-android-'))throw new Error('Game copy destination must be inside dist or its dedicated Android staging directory.');
  // Clear only this validated generated target; removed modules cannot linger in a build.
  await rm(targetRoot,{recursive:true,force:true});
  for(const file of files){const target=path.join(destination,file);await mkdir(path.dirname(target),{recursive:true});await copyFile(path.join(root,file),target);}
  return files;
}
const crcTable=Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
function crc32(bytes){let crc=0xffffffff;for(const b of bytes)crc=crcTable[(crc^b)&255]^(crc>>>8);return (crc^0xffffffff)>>>0;}
export async function writeZip(output,entries){
  const local=[],central=[];let offset=0;
  for(const {name:filename,data} of entries){
    const name=Buffer.from(filename,'utf8'),crc=crc32(data);
    const header=Buffer.alloc(30);header.writeUInt32LE(0x04034b50,0);header.writeUInt16LE(20,4);header.writeUInt16LE(0x800,6);header.writeUInt16LE(0x21,12);header.writeUInt32LE(crc,14);header.writeUInt32LE(data.length,18);header.writeUInt32LE(data.length,22);header.writeUInt16LE(name.length,26);local.push(header,name,data);
    const dir=Buffer.alloc(46);dir.writeUInt32LE(0x02014b50,0);dir.writeUInt16LE(20,4);dir.writeUInt16LE(20,6);dir.writeUInt16LE(0x800,8);dir.writeUInt16LE(0x21,14);dir.writeUInt32LE(crc,16);dir.writeUInt32LE(data.length,20);dir.writeUInt32LE(data.length,24);dir.writeUInt16LE(name.length,28);dir.writeUInt32LE(offset,42);central.push(dir,name);offset+=header.length+name.length+data.length;
  }
  const directory=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50,0);end.writeUInt16LE(entries.length,8);end.writeUInt16LE(entries.length,10);end.writeUInt32LE(directory.length,12);end.writeUInt32LE(offset,16);
  const zip=Buffer.concat([...local,directory,end]);await writeFile(output,zip);return zip;
}
export function option(name,fallback){const index=process.argv.indexOf('--'+name);return index<0?fallback:process.argv[index+1];}
