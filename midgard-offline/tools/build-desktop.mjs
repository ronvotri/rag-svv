import {cp,mkdir,readFile,writeFile,rename,access} from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {root,version,copyGame,option} from './bundle.mjs';
const electron=option('electron-dir',process.env.MIDGARD_ELECTRON_DIR);
if(!electron)throw new Error('Set MIDGARD_ELECTRON_DIR or --electron-dir to an existing Windows x64 Electron runtime directory.');
await access(path.join(electron,'electron.exe'));
const output=path.join(root,'dist',`MidgardOffline-${version}-Windows-x64`);
await mkdir(output,{recursive:true});
await cp(electron,output,{recursive:true});
const app=path.join(output,'resources','app');await mkdir(app,{recursive:true});
await cp(path.join(root,'platforms','desktop','main.cjs'),path.join(app,'main.cjs'));
await writeFile(path.join(app,'package.json'),JSON.stringify({name:'midgard-offline',version,main:'main.cjs',private:true}));
const files=await copyGame(path.join(app,'game'));
await rename(path.join(output,'electron.exe'),path.join(output,'MidgardOffline.exe'));
const runtimeVersion=(await readFile(path.join(electron,'version'),'utf8')).trim();
await writeFile(path.join(output,'BUILD-INFO.json'),JSON.stringify({product:'Biên niên Midgard',version,platform:'windows-x64',electron:runtimeVersion,runtimeFiles:files,releaseStatus:'unsigned-test-build',visualQA:false},null,2));
console.log(`Windows portable folder: ${output}`);
console.log('Run MidgardOffline.exe. Keep every adjacent runtime file. This build is unsigned and awaits device QA.');
if(process.argv.includes('--zip')){
  const zip=output+'.zip';
  // Native tar builds may mangle Unicode arguments; use ASCII relative paths.
  const result=spawnSync('tar',['-a','-cf',path.basename(zip),path.basename(output)],{stdio:'inherit',cwd:path.dirname(output)});
  if(result.error)throw result.error;
  if(result.status!==0)throw new Error('System tar could not create the Windows ZIP. The portable folder remains available.');
  console.log(`Windows ZIP: ${zip}`);
}
