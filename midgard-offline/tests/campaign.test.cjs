'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),C=require('../campaign.js');
const rich=()=>{const p=C.createProfile();p.materials={ore:10000,essence:10000};return p;};
test('campaign schema roundtrips known fields and rejects malformed/equipped unowned data',()=>{
  const p=C.createProfile();assert.deepEqual(C.validateProfile(p),p);
  for(const modify of [p=>p.materials.ore=-1,p=>p.gear['iron-sword']=11,p=>p.cards.sprout.copies=0,p=>p.equipment.weapon='moon-staff',p=>p.equipment.charm='iron-sword',p=>p.cardSlots=['sprout','sprout'],p=>p.stats.wins=1,p=>p.claimedQuests=['not-a-quest'],p=>p.settledRuns=['<script>']]){const v=C.createProfile();modify(v);assert.throws(()=>C.validateProfile(v));}
});
test('craft/equip/refine transactions spend exact costs without mutating originals',()=>{
  const p=rich(),original=JSON.stringify(p);let next=C.craft(p,'hunting-bow');assert.equal(next.materials.ore,p.materials.ore-16);assert.equal(next.stats.crafted,1);assert.equal(JSON.stringify(p),original);
  next=C.equip(next,'hunting-bow');assert.equal(next.equipment.weapon,'hunting-bow');const ore=next.materials.ore;next=C.refine(next,'hunting-bow');assert.equal(next.gear['hunting-bow'],1);assert.equal(next.materials.ore,ore-C.refineCost(0).ore);assert.throws(()=>C.craft(next,'hunting-bow'));assert.throws(()=>C.craft(C.createProfile(),'dawn-axe'));assert.throws(()=>C.equip(next,'dawn-axe'));
});
test('cards require ownership, distinct slots and three copies for fusion',()=>{
  let p=rich();p.cards.sprout.copies=3;p.cards.ember={copies:1,rank:0};p=C.equipCards(p,['sprout','ember']);const before=C.bonuses(p).hp;p=C.fuseCard(p,'sprout');assert.equal(p.cards.sprout.copies,1);assert.equal(p.cards.sprout.rank,1);assert.ok(C.bonuses(p).hp>before);assert.throws(()=>C.fuseCard(p,'sprout'));assert.throws(()=>C.equipCards(p,['sprout','sprout']));assert.throws(()=>C.equipCards(p,['elder']));
});
test('settlement awards campaign materials once per recent run and tracks job/tower records',()=>{
  const result={id:'run-1',jobId:'knight',won:true,kills:80,time:360,mode:'tower',towerFloor:5};const p=C.settle(C.createProfile(),result),duplicate=C.settle(p,result);assert.deepEqual(duplicate,p);assert.equal(p.stats.runs,1);assert.equal(p.stats.bosses,1);assert.equal(p.materials.ore,24);assert.equal(p.towerBest,5);assert.equal(C.jobRank(p,'knight').level,1);assert.equal(p.jobs.knight.wins,1);assert.throws(()=>C.settle(p,{...result,id:'bad id'}));assert.throws(()=>C.settle(p,{...result,id:'run-2',time:Infinity}));
});
test('quest rewards cannot be claimed early or twice',()=>{
  const p=C.createProfile();assert.throws(()=>C.claimQuest(p,'first-run'));const after=C.settle(p,{id:'run-q',jobId:'mage',won:false,kills:4,time:20});assert.equal(C.questProgress(after,'first-run').complete,true);const paid=C.claimQuest(after,'first-run');assert.equal(paid.materials.ore,after.materials.ore+8);assert.throws(()=>C.claimQuest(paid,'first-run'));
});
test('rebirth has explicit wins/material prerequisites and increases persistent bonuses',()=>{
  const p=rich();assert.throws(()=>C.rebirth(p));p.stats.runs=3;p.stats.wins=3;const before=C.bonuses(p),next=C.rebirth(p);assert.equal(next.rebirth,1);assert.equal(next.materials.essence,p.materials.essence-10);assert.equal(C.bonuses(next).hp,before.hp+10);assert.equal(C.bonuses(next).power,before.power+.05);assert.throws(()=>C.rebirth(next));assert.equal(C.GEAR.length,12);assert.equal(C.CARDS.length,12);assert.equal(C.QUESTS.length,9);
});
