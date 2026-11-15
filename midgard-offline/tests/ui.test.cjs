'use strict';
// A DOM/canvas contract smoke test, not a replacement for visual browser QA.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const engine=require('../engine.js');
const root=path.resolve(__dirname,'..');

function browser(initialSave=null,{storageBlocked=false}={}) {
  const ids=new Map(),events=new Map(),runs=[],storage=new Map(),draws={count:0};
  if(initialSave)storage.set('votri.midgard.offline.v1',JSON.stringify(initialSave));
  let callback=null,now=0,document;
  const context=new Proxy({}, {get(target,key) {
    if(key==='createRadialGradient')return ()=>({addColorStop(){}});
    if(!(key in target))target[key]=()=>{draws.count++;};
    return target[key];
  }});
  class Element {
    constructor(tag='div',id='') {
      this.tagName=tag.toUpperCase();this.id=id;this.children=[];this.style={};this.attributes={};this.listeners=new Map();this.hidden=false;this.disabled=false;this.textContent='';this._html='';
    }
    get innerHTML(){return this._html;}
    set innerHTML(value){this._html=value;this.children=[];if(/<canvas\b/.test(value))this.children.push(new Element('canvas'));}
    get firstElementChild(){return this.children[0];}
    append(...children){this.children.push(...children);}
    replaceChildren(...children){this._html='';this.children=[...children];}
    setAttribute(name,value){this.attributes[name]=String(value);}
    getAttribute(name){return this.attributes[name];}
    addEventListener(name,fn){this.listeners.set(name,fn);}
    focus(){document.activeElement=this;}
    click(){if(!this.disabled)this.onclick?.({target:this});}
    getContext(){return context;}
    setPointerCapture(){}
    querySelectorAll(selector){
      const results=[];
      const matches=e=>selector==='canvas'?e.tagName==='CANVAS':selector==='button:not(:disabled)'?e.tagName==='BUTTON'&&!e.disabled:false;
      function visit(e){for(const child of e.children){if(matches(child))results.push(child);visit(child);}}
      visit(this);return results;
    }
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  }
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  for(const match of html.matchAll(/<(\w+)\b([^>]*\bid="([^"]+)"[^>]*)>/g)) {
    const el=new Element(match[1],match[3]);el.hidden=/\bhidden\b/.test(match[2]);ids.set(el.id,el);
  }
  ids.get('modal').append(ids.get('modal-content'),ids.get('modal-actions'));
  ids.get('joystick').append(new Element('i'));
  document={hidden:false,activeElement:null,getElementById:id=>{
    assert.ok(ids.has(id),`HTML must declare #${id}`);return ids.get(id);
  },createElement:tag=>new Element(tag),addEventListener:(name,fn)=>events.set('document:'+name,fn)};
  class ObservedRun extends engine.Run {
    constructor(...args){super(...args);runs.push(this);}
  }
  const sandbox={document,innerWidth:1280,innerHeight:800,devicePixelRatio:1,console,Blob,
    Midgard:{...engine,Run:ObservedRun},
    localStorage:{getItem:key=>{if(storageBlocked)throw new Error('blocked');return storage.get(key)||null;},setItem:(key,value)=>{if(storageBlocked)throw new Error('blocked');storage.set(key,value);}},
    URL:{createObjectURL:()=> 'blob:offline-test',revokeObjectURL(){}},
    setTimeout:()=>0,requestAnimationFrame:fn=>{callback=fn;},
    addEventListener:(name,fn)=>events.set(name,fn),
    fetch:()=>{throw new Error('Offline game must not fetch');},
    XMLHttpRequest:class {constructor(){throw new Error('Offline game must not use XHR');}}
  };
  sandbox.window=sandbox;
  vm.runInNewContext(fs.readFileSync(path.join(root,'game.js'),'utf8'),sandbox,{filename:'game.js'});
  return {ids,runs,storage,draws,events,
    frame(ms=16){now+=ms;const next=callback;assert.equal(typeof next,'function');next(now);},
    key(key,kind='keydown'){events.get(kind)?.({key,repeat:false,preventDefault(){}});},
    modalButtons(){return ids.get('modal').querySelectorAll('button:not(:disabled)');}
  };
}

test('shell initializes from actual HTML and renders the menu canvas', () => {
  const b=browser();
  assert.equal(b.ids.get('classes').children.length,3);
  assert.equal(b.ids.get('maps').children.length,3);
  assert.deepEqual(b.ids.get('maps').children.map(e=>e.disabled),[false,true,true]);
  assert.equal(b.ids.get('hud').hidden,true);
  b.frame();assert.ok(b.draws.count>100);
  assert.equal(b.ids.get('storage-message').textContent,'');
});

test('start, pause, resume, level-up, loss, persistence and return to menu', () => {
  const b=browser();b.ids.get('start-button').click();b.frame();
  const run=b.runs[0];
  assert.equal(b.ids.get('menu').hidden,true);assert.equal(b.ids.get('hud').hidden,false);
  assert.equal(run.state,'playing');
  const x=run.player.x;b.key('d');b.frame(40);b.key('d','keyup');assert.ok(run.player.x>x);
  b.ids.get('pause-button').click();
  assert.equal(run.state,'paused');assert.equal(b.ids.get('modal').hidden,false);
  const time=run.time;b.frame(40);assert.equal(run.time,time);
  assert.equal(b.modalButtons()[0].textContent,'Tiếp tục');b.modalButtons()[0].click();
  assert.equal(run.state,'playing');assert.equal(b.ids.get('modal').hidden,true);
  run.gainXp(run.nextXp);b.frame();
  assert.equal(run.state,'levelup');assert.equal(b.modalButtons().length,3);
  b.modalButtons()[0].click();assert.equal(run.state,'playing');assert.equal(b.ids.get('modal').hidden,true);
  run.kills=12;run.time=30;run.state='lost';b.frame();
  assert.equal(b.ids.get('modal').hidden,false);
  const saved=JSON.parse(b.storage.get('votri.midgard.offline.v1'));
  assert.equal(saved.runs,1);assert.equal(saved.kills,12);assert.equal(saved.gold,run.gold);
  b.frame();assert.equal(JSON.parse(b.storage.get('votri.midgard.offline.v1')).runs,1);
  b.modalButtons().find(e=>e.textContent==='Về nơi chuẩn bị').click();
  assert.equal(b.ids.get('menu').hidden,false);assert.equal(b.ids.get('hud').hidden,true);assert.equal(b.ids.get('modal').hidden,true);
  assert.equal(b.ids.get('gold-label').textContent,`· ${saved.gold} vàng`);
  b.frame();
});

test('training spends once and applies to a new run; focus loss pauses', () => {
  const save=engine.emptySave();save.gold=100;
  const b=browser(save);b.ids.get('training-button').click();
  b.modalButtons()[0].click();
  const saved=JSON.parse(b.storage.get('votri.midgard.offline.v1'));
  assert.equal(saved.gold,40);assert.equal(saved.training.hp,1);
  b.modalButtons().find(e=>e.textContent==='Trở về').click();
  b.ids.get('start-button').click();b.frame();assert.equal(b.runs[0].player.maxHp,150);
  b.events.get('blur')();assert.equal(b.runs[0].state,'paused');
  b.key('Escape');assert.equal(b.runs[0].state,'playing');
  b.events.get('document:visibilitychange')();assert.equal(b.runs[0].state,'playing');
});

test('blocked storage keeps the game playable and warns about JSON export', () => {
  const b=browser(null,{storageBlocked:true});
  assert.match(b.ids.get('storage-message').textContent,/JSON/);
  b.ids.get('start-button').click();b.runs[0].state='lost';b.frame();
  assert.match(b.ids.get('storage-message').textContent,/xuất tệp lưu JSON/);
  assert.equal(b.modalButtons().length,2);
  b.ids.get('export-button').click();
  assert.match(b.ids.get('storage-message').textContent,/Đã xuất lưu/);
});

test('malformed import is rejected and a valid import waits for confirmation', async () => {
  const b=browser(),input=b.ids.get('import-file');
  await input.onchange({target:{files:[{size:10,text:async()=>'{invalid'}],value:''}});
  assert.match(b.ids.get('storage-message').textContent,/Không thể nhập/);
  const save=engine.emptySave();save.gold=456;save.runs=2;save.wins=2;
  await input.onchange({target:{files:[{size:300,text:async()=>JSON.stringify(save)}],value:''}});
  assert.equal(b.ids.get('modal').hidden,false);assert.equal(b.storage.size,0);
  b.modalButtons().find(e=>e.textContent==='Nhập bản lưu').click();
  assert.equal(JSON.parse(b.storage.get('votri.midgard.offline.v1')).gold,456);
  assert.deepEqual(b.ids.get('maps').children.map(e=>e.disabled),[false,false,false]);
});
