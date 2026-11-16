/* Validated in-progress snapshots; separate from account progression. */
(function(root){
  'use strict';
  const Engine=typeof module!=='undefined'&&module.exports?require('./engine.js'):root.Midgard;
  const bounded=(n,min,max,label)=>{if(!Number.isFinite(n)||n<min||n>max)throw new Error('Bản lưu trận lỗi: '+label);return n;};
  const integer=(n,min,max,label)=>{bounded(n,min,max,label);if(!Number.isInteger(n))throw new Error('Bản lưu trận lỗi: '+label);return n;};
  const position=v=>({x:bounded(v.x,-1e7,1e7,'x'),y:bounded(v.y,-1e7,1e7,'y')});
  function capture(run){
    if(!run||!['playing','paused','levelup'].includes(run.state))return null;
    return {version:1,id:run.id,jobId:run.job.id,mapId:run.map.id,mode:run.mode,time:run.time,kills:run.kills,level:run.level,xp:run.xp,nextXp:run.nextXp,player:{...run.player},upgrades:{...run.upgrades},basePower:run.basePower,fortune:run.fortune,bonusSpeed:run.bonusSpeed,bonusRegen:run.bonusRegen,bonusFortune:run.bonusFortune,floor:run.floor,floorKills:run.floorKills,bossSpawned:run.bossSpawned,nextId:run.nextId,enemies:run.enemies.map(e=>({...e})),gems:run.gems.map(g=>({...g})),effects:run.effects.map(e=>({...e})),companions:run.companions.map(a=>({...a,cooldowns:{...a.cooldowns}})),choices:run.choices.map(c=>c.id),state:run.state};
  }
  function restore(raw,save){
    if(!raw||raw.version!==1||typeof raw.id!=='string'||!/^[a-zA-Z0-9_-]{1,100}$/.test(raw.id))throw new Error('Không nhận dạng được bản lưu trận.');
    if(!['playing','paused','levelup'].includes(raw.state)||!['survival','tower'].includes(raw.mode))throw new Error('Trạng thái trận không hợp lệ.');
    if(!Array.isArray(raw.companions)||raw.companions.length>3)throw new Error('Đội hình không hợp lệ.');
    const roles=raw.companions.map(a=>a.role);if(roles.some((r,i)=>!['guardian','ranger','healer'].includes(r)||roles.indexOf(r)!==i))throw new Error('Đồng đội không hợp lệ.');
    const run=new Engine.Run(raw.jobId,raw.mapId,save,Math.random,{runId:raw.id,mode:raw.mode,companions:roles});
    run.time=bounded(raw.time,0,3600,'time');run.kills=integer(raw.kills,0,1e6,'kills');run.level=integer(raw.level,1,1000,'level');run.xp=bounded(raw.xp,0,1e9,'xp');run.nextXp=integer(raw.nextXp,1,1e9,'nextXp');
    const maxHp=bounded(raw.player.maxHp,1,5000,'maxHp');run.player={...position(raw.player),maxHp,hp:bounded(raw.player.hp,.001,maxHp,'hp'),invuln:0,face:raw.player.face===-1?-1:1};
    run.upgrades={};if(!raw.upgrades||typeof raw.upgrades!=='object')throw new Error('Nâng cấp không hợp lệ.');
    for(const [id,value]of Object.entries(raw.upgrades)){const card=Engine.UPGRADES.find(c=>c.id===id);if(!card)throw new Error('Nâng cấp lạ.');run.upgrades[id]=integer(value,1,card.max,'upgrade');}
    run.basePower=bounded(raw.basePower,.1,20,'power');run.fortune=integer(raw.fortune,0,20,'fortune');run.bonusSpeed=bounded(raw.bonusSpeed??0,0,.5,'speed');run.bonusRegen=bounded(raw.bonusRegen??0,0,8,'regen');run.bonusFortune=bounded(raw.bonusFortune??0,0,2,'fortune bonus');
    run.floor=integer(raw.floor,1,21,'floor');run.floorKills=integer(raw.floorKills,0,1e6,'floor kills');run.bossSpawned=raw.bossSpawned===true;run.nextId=integer(raw.nextId,1,1e8,'nextId');
    if(!Array.isArray(raw.enemies)||raw.enemies.length>201)throw new Error('Số quái không hợp lệ.');
    const enemyIds=new Set();
    run.enemies=raw.enemies.map(e=>{if(!['slime','bat','golem','boss'].includes(e.type))throw new Error('Loại quái lạ.');const id=integer(e.id,1,1e8,'enemy id');if(enemyIds.has(id)||id>=run.nextId)throw new Error('ID quái không hợp lệ.');enemyIds.add(id);const maxHp=bounded(e.maxHp,.001,1e8,'enemy maxHP');return {...position(e),id,type:e.type,maxHp,hp:bounded(e.hp,.001,maxHp,'enemy HP'),r:bounded(e.r,1,100,'radius'),speed:bounded(e.speed,0,1000,'enemy speed'),damage:bounded(e.damage,0,10000,'damage'),hit:0,slow:bounded(e.slow??0,0,10,'slow'),pulse:0,attack:bounded(e.attack??3,-1,10,'attack')};});
    if(run.enemies.filter(e=>e.type==='boss').length>1)throw new Error('Trùng thủ lĩnh.');
    if(!Array.isArray(raw.gems)||raw.gems.length>450)throw new Error('Tinh thể không hợp lệ.');
    run.gems=raw.gems.map(g=>({...position(g),value:integer(g.value,1,1e8,'gem'),pulling:g.pulling===true}));
    if(!Array.isArray(raw.effects)||raw.effects.length>300)throw new Error('Hiệu ứng không hợp lệ.');
    run.effects=raw.effects.map(e=>{if(!['warning','slash','fire','nova','heal','hurt'].includes(e.kind))throw new Error('Hiệu ứng lạ.');return {...position(e),r:bounded(e.r,0,1000,'effect radius'),kind:e.kind,life:bounded(e.life,0,2,'effect life'),max:bounded(e.max,.001,2,'effect max'),...(e.damage?{damage:bounded(e.damage,0,10000,'effect damage')}:{})};});
    for(let i=0;i<run.companions.length;i++){const a=run.companions[i],r=raw.companions[i];a.x=position(r).x;a.y=r.y;a.hp=bounded(r.hp,0,a.maxHp,'ally HP');a.face=r.face===-1?-1:1;}
    if(!Array.isArray(raw.choices)||raw.choices.length>3)throw new Error('Lựa chọn không hợp lệ.');
    run.choices=raw.choices.map(id=>{const u=Engine.UPGRADES.find(x=>x.id===id);if(!u||(run.upgrades[id]||0)>=u.max)throw new Error('Thẻ lựa chọn không hợp lệ.');return u;});
    if(new Set(raw.choices).size!==raw.choices.length||raw.state==='levelup'&&!run.choices.length)throw new Error('Lựa chọn lặp hoặc rỗng.');
    run.state=raw.state==='levelup'?'levelup':'paused';return run;
  }
  const api={capture,restore};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MidgardRunSave=api;
})(typeof globalThis!=='undefined'?globalThis:this);
