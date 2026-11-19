const test=require('node:test'),assert=require('node:assert/strict');
const {Run,emptySave}=require('../engine.js');
const {capture,restore}=require('../run-save.js');
test('resume preserves progression, hazards and companions while pausing the fight',()=>{
  const r=new Run('archer','meadow',emptySave(),Math.random,{companions:['healer','ranger'],mode:'tower'});
  r.time=41;r.kills=10;r.upgrades.power=2;r.player.hp=40;r.spawn();r.effects.push({x:2,y:3,r:140,kind:'warning',life:.5,max:.8,damage:30});
  const s=capture(r),restored=restore(JSON.parse(JSON.stringify(s)),emptySave());
  assert.equal(restored.id,r.id);assert.equal(restored.state,'paused');assert.equal(restored.mode,'tower');assert.equal(restored.kills,10);assert.equal(restored.player.hp,40);assert.equal(restored.companions.length,2);assert.equal(restored.effects[0].damage,30);assert.equal(restored.enemies.length,1);
  restored.player.hp=1;assert.equal(s.player.hp,40);
});
test('resume preserves legal level choices and rejects corrupted or oversized input',()=>{
  const r=new Run('knight','meadow');r.gainXp(12);const s=capture(r);assert.equal(restore(s,emptySave()).state,'levelup');
  for(const edit of [v=>v.time=Infinity,v=>v.player.hp=-1,v=>v.enemies=Array(250).fill({}),v=>v.companions=[{role:'unknown'}],v=>v.choices=['unknown'],v=>v.id='../oops',v=>v.upgrades={power:99}]){
    const v=JSON.parse(JSON.stringify(s));edit(v);assert.throws(()=>restore(v,emptySave()));
  }
  r.state='lost';assert.equal(capture(r),null);
});
