// Dependency-free offline web package. Does not read original game client files.
import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {root,version,copyGame,writeZip} from './bundle.mjs';
const output=path.join(root,'dist'),bundle=path.join(output,'midgard-offline');
await mkdir(bundle,{recursive:true});
const files=await copyGame(bundle);
for(const file of ['CHOI_GAME.cmd','README.md']){await copyFile(path.join(root,file),path.join(bundle,file));files.push(file);}
const entries=[],hashes=[];
for(const file of files.sort()){const data=await readFile(path.join(root,file));entries.push({name:`midgard-offline/${file}`,data});hashes.push(`${createHash('sha256').update(data).digest('hex')}  ${file}`);}
const zipName=`midgard-offline-${version}.zip`,zip=await writeZip(path.join(output,zipName),entries);
await writeFile(path.join(output,'SHA256SUMS.txt'),`${createHash('sha256').update(zip).digest('hex')}  ${zipName}\n${hashes.join('\n')}\n`);
console.log(`Built ${path.join(output,zipName)} (${zip.length} bytes, ${files.length} files)`);
