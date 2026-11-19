'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const os=require('node:os');

test('offline bundles include each HTML asset and exclude development/client material',async()=>{
  const {gameFiles,root}=await import(pathToFileURL(path.resolve(__dirname,'../tools/bundle.mjs')).href);
  const files=await gameFiles(),html=await fs.readFile(path.join(root,'index.html'),'utf8');
  for(const match of html.matchAll(/(?:src|href)="([^"#]+)"/g)){
    const name=match[1].replace(/^\.\//,'');
    if(name==='index.html')continue;
    assert.ok(!/^https?:/.test(name),'runtime assets must be local');
    assert.ok(files.includes(name),`missing packaged dependency: ${name}`);
  }
  assert.ok(files.includes('engine.js')&&files.includes('game.js'));
  assert.ok(files.every(file=>!/(^|\/)(work|private|platforms|reference|tests)\//.test(file)));
  assert.ok(files.every(file=>!file.includes('.private.')&&!/\.(exe|pck|dll|keystore|jks)$/.test(file)));
});

test('ZIP writer preserves UTF-8 names and exact bytes without external libraries',async()=>{
  const {writeZip}=await import(pathToFileURL(path.resolve(__dirname,'../tools/bundle.mjs')).href);
  const folder=await fs.mkdtemp(path.join(os.tmpdir(),'midgard-zip-test-'));
  const entry={name:'midgard/tiếng-Việt.txt',data:Buffer.from('Lưu tiến trình · offline','utf8')};
  const zip=await writeZip(path.join(folder,'test.zip'),[entry]);
  assert.equal(zip.readUInt32LE(0),0x04034b50);
  assert.equal(zip.readUInt16LE(6),0x800);
  const nameLength=zip.readUInt16LE(26),size=zip.readUInt32LE(18);
  assert.equal(zip.subarray(30,30+nameLength).toString('utf8'),entry.name);
  assert.deepEqual(zip.subarray(30+nameLength,30+nameLength+size),entry.data);
  assert.equal(zip.readUInt32LE(zip.length-22),0x06054b50);
  assert.equal(zip.readUInt16LE(zip.length-12),1);
});

test('fresh packaging removes stale modules and refuses to clear the source directory',async()=>{
  const {copyGame,root}=await import(pathToFileURL(path.resolve(__dirname,'../tools/bundle.mjs')).href);
  await assert.rejects(copyGame(root),/destination must be inside dist/);
  const destination=path.resolve(root,'dist','package-test-'+process.pid);
  assert.ok(destination.startsWith(path.resolve(root,'dist')+path.sep));
  await fs.mkdir(destination,{recursive:true});
  await fs.writeFile(path.join(destination,'removed-module.js'),'old module');
  try{
    await copyGame(destination);
    await assert.rejects(fs.access(path.join(destination,'removed-module.js')),{code:'ENOENT'});
    assert.deepEqual(await fs.readFile(path.join(destination,'engine.js')),await fs.readFile(path.join(root,'engine.js')));
  }finally{await fs.rm(destination,{recursive:true,force:true});}
});

test('native Android wrapper needs no Internet or broad storage permissions',async()=>{
  const manifest=await fs.readFile(path.resolve(__dirname,'../platforms/android/AndroidManifest.xml'),'utf8');
  assert.ok(!/<uses-permission\b/.test(manifest));
  assert.ok(manifest.includes('com.votrivalley.midgardoffline'));
  const source=await fs.readFile(path.resolve(__dirname,'../platforms/android/MainActivity.java'),'utf8');
  assert.ok(source.includes('Intent.ACTION_CREATE_DOCUMENT'));
  assert.ok(source.includes('Intent.ACTION_OPEN_DOCUMENT'));
  assert.ok(!source.includes('setAllowUniversalAccessFromFileURLs(true)'));
  assert.ok(!source.includes('setAllowFileAccess(true)'));
});
