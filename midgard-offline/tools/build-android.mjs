// Build a small native WebView APK using existing JDK + Android SDK, without Gradle.
import {mkdir,writeFile,access,mkdtemp,copyFile,cp} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import os from 'node:os';
import {root,version,copyGame,option} from './bundle.mjs';
const javaHome=option('java-home',process.env.JAVA_HOME),sdk=option('android-sdk',process.env.ANDROID_SDK_ROOT||process.env.ANDROID_HOME);
if(!javaHome||!sdk)throw new Error('Provide --java-home and --android-sdk (or JAVA_HOME / ANDROID_SDK_ROOT). JDK 17+ and Android SDK 36/build-tools 36.0.0 are required.');
const exe=process.platform==='win32'?'.exe':'',java=path.join(javaHome,'bin','java'+exe),javac=path.join(javaHome,'bin','javac'+exe),jar=path.join(javaHome,'bin','jar'+exe),keytool=path.join(javaHome,'bin','keytool'+exe);
const tools=path.join(sdk,'build-tools',option('build-tools','36.0.0')),androidJar=path.join(sdk,'platforms','android-36','android.jar');
// Android native executables can reject Unicode project paths on Windows.
const stage=await mkdtemp(path.join(os.tmpdir(),'midgard-android-'));
const output=path.join(root,'dist','android'),classes=path.join(stage,'classes'),assets=path.join(stage,'assets'),dex=path.join(stage,'dex'),keys=path.join(root,'work','android-debug');
for(const directory of [output,classes,assets,dex,keys])await mkdir(directory,{recursive:true});
function run(command,args){const result=spawnSync(command,args,{stdio:'inherit',env:{...process.env,JAVA_HOME:javaHome}});if(result.error)throw result.error;if(result.status!==0)throw new Error(`${path.basename(command)} failed (${result.status}).`);}
await copyGame(assets);
const manifest=path.join(stage,'AndroidManifest.xml'),source=path.join(stage,'MainActivity.java');
await copyFile(path.join(root,'platforms','android','AndroidManifest.xml'),manifest);
await copyFile(path.join(root,'platforms','android','MainActivity.java'),source);
const resources=path.join(stage,'res'),compiledResources=path.join(stage,'resources.zip');
await cp(path.join(root,'platforms','android','res'),resources,{recursive:true});
run(path.join(tools,'aapt2'+exe),['compile','--dir',resources,'-o',compiledResources]);
const unsigned=path.join(stage,'unsigned.apk'),aligned=path.join(stage,'aligned.apk'),apk=path.join(stage,`MidgardOffline-${version}-Android-DEBUG-TEST.apk`);
run(path.join(tools,'aapt2'+exe),['link','-o',unsigned,'--manifest',manifest,'-I',androidJar,'-A',assets,'--min-sdk-version','26','--target-sdk-version','36','--version-code',option('version-code','200'),'--version-name',version,compiledResources]);
run(javac,['-encoding','UTF-8','--release','8','-classpath',androidJar,'-d',classes,source]);
const classJar=path.join(stage,'classes.jar');run(jar,['--create','--file',classJar,'-C',classes,'.']);
run(java,['-cp',path.join(tools,'lib','d8.jar'),'com.android.tools.r8.D8','--min-api','26','--lib',androidJar,'--output',dex,classJar]);
// jar updates the ZIP container; zipalign and apksigner run after this last mutation.
run(jar,['--update','--file',unsigned,'-C',dex,'classes.dex']);
run(path.join(tools,'zipalign'+exe),['-f','4',unsigned,aligned]);
const persistentKey=path.join(keys,'midgard-debug.keystore'),debugKey=path.join(stage,'midgard-debug.keystore');
try{await access(persistentKey);await copyFile(persistentKey,debugKey);}catch(error){
  if(error.code!=='ENOENT')throw error;
  run(keytool,['-genkeypair','-keystore',debugKey,'-storepass','android','-keypass','android','-alias','androiddebugkey','-keyalg','RSA','-keysize','2048','-validity','10000','-dname','CN=Midgard Local Debug,O=Votri Valley,C=VN','-noprompt']);
  await copyFile(debugKey,persistentKey);
}
run(java,['-jar',path.join(tools,'lib','apksigner.jar'),'sign','--ks',debugKey,'--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned]);
run(java,['-jar',path.join(tools,'lib','apksigner.jar'),'verify','--verbose',apk]);
run(path.join(tools,'aapt'+exe),['dump','badging',apk]);
const finalApk=path.join(output,path.basename(apk));await copyFile(apk,finalApk);
await writeFile(path.join(output,'BUILD-INFO.json'),JSON.stringify({product:'Biên niên Midgard',version,versionCode:Number(option('version-code','200')),applicationId:'com.votrivalley.midgardoffline',platform:'android',minSdk:26,targetSdk:36,releaseStatus:'local-debug-test-only',deviceQA:false,releaseSigningConfigured:false},null,2));
console.log(`Android test APK: ${finalApk}`);
console.log('Local debug certificate only. No permanent release signing identity has been enrolled; do not distribute this as a stable player-update release.');
