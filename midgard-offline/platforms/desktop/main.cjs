'use strict';
const {app,BrowserWindow,protocol,net,session}=require('electron');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
protocol.registerSchemesAsPrivileged([{scheme:'midgard',privileges:{standard:true,secure:true,supportFetchAPI:true,corsEnabled:true}}]);
app.setName('Bien nien Midgard');
app.setAppUserModelId('com.votrivalley.midgardoffline');
// Keep the save path independent of the folder holding the portable executable.
app.setPath('userData',path.join(app.getPath('appData'),'VotriValley','MidgardOffline'));
if(!app.requestSingleInstanceLock())app.quit();
let window;
app.on('second-instance',()=>{if(window){if(window.isMinimized())window.restore();window.focus();}});
app.whenReady().then(()=>{
  const gameRoot=path.resolve(__dirname,'game');
  protocol.handle('midgard',request=>{
    const url=new URL(request.url);
    if(url.hostname!=='game')return new Response('Not found',{status:404});
    const relative=decodeURIComponent(url.pathname).replace(/^\/+/,''),file=path.resolve(gameRoot,relative||'index.html');
    if(!file.startsWith(gameRoot+path.sep))return new Response('Forbidden',{status:403});
    return net.fetch(pathToFileURL(file).href);
  });
  session.defaultSession.webRequest.onBeforeRequest((details,callback)=>{
    callback({cancel:!['midgard:','file:','blob:','data:','devtools:'].some(scheme=>details.url.startsWith(scheme))});
  });
  session.defaultSession.setPermissionRequestHandler((_contents,_permission,callback)=>callback(false));
  window=new BrowserWindow({width:1280,height:800,minWidth:360,minHeight:480,backgroundColor:'#142b25',autoHideMenuBar:true,title:'Biên niên Midgard · Offline',webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true,webSecurity:true,devTools:!app.isPackaged}});
  window.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  window.webContents.on('will-navigate',(event,url)=>{if(!url.startsWith('midgard://game/'))event.preventDefault();});
  window.loadURL('midgard://game/index.html');
});
app.on('window-all-closed',()=>app.quit());
