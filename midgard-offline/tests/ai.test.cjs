'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {COMPANIONS,decideCompanion,chooseUpgrade,chat,dangerAt}=require('../ai.js');
const actor=(extra={})=>({id:'ally-1',x:0,y:0,hp:80,maxHp:100,range:300,role:'ranger',speed:160,...extra});
const player=(extra={})=>({id:'player',x:70,y:0,hp:100,maxHp:100,...extra});

test('companion decision is pure, deterministic and normalized',()=>{
  const a=actor(),snapshot={player:player({x:500}),enemies:[],allies:[]};
  const original=JSON.stringify({a,snapshot});
  const result=decideCompanion(a,snapshot);
  assert.equal(result.reason,'regroup');assert.ok(result.move.x>.9);
  assert.ok(Math.hypot(result.move.x,result.move.y)<=1.000001);
  assert.deepEqual(result,decideCompanion(a,snapshot));
  assert.equal(JSON.stringify({a,snapshot}),original);
});
test('downed companions never attack or move',()=>{
  const result=decideCompanion(actor({hp:0}),{player:player(),enemies:[{id:'e',x:10,y:0,hp:100}]});
  assert.equal(result.reason,'down');assert.equal(result.targetId,null);assert.deepEqual(result.move,{x:0,y:0});
});
test('healer chooses lowest relative health and obeys cooldown',()=>{
  const snapshot={player:player({hp:60}),allies:[actor({id:'other',x:60,hp:10})]};
  assert.equal(decideCompanion(actor({role:'healer'}),snapshot).healId,'other');
  assert.equal(decideCompanion(actor({role:'healer',healCooldown:1}),snapshot).healId,null);
});
test('healer can approach and request revive but cannot revive an ineligible actor',()=>{
  const snapshot={player:player({hp:0,x:30}),allies:[]};
  assert.equal(decideCompanion(actor({role:'healer'}),snapshot).reviveId,'player');
  snapshot.player.revivable=false;
  assert.equal(decideCompanion(actor({role:'healer'}),snapshot).reviveId,null);
});
test('ranged AI kites nearby enemies and targets only in legal range',()=>{
  const enemies=[{id:'e',x:60,y:0,hp:100,r:13}];
  const result=decideCompanion(actor(),{player:player(),enemies});
  assert.equal(result.targetId,'e');assert.ok(result.move.x<0);
  assert.equal(decideCompanion(actor({range:50}),{player:player(),enemies:[{...enemies[0],x:100}]}).targetId,null);
});
test('hazard evasion reduces danger and does not dash into a solid obstacle',()=>{
  const a=actor(),hazards=[{x:0,y:0,r:80,life:1}];
  const result=decideCompanion(a,{player:player(),hazards});
  assert.equal(result.reason,'evade');assert.equal(result.dash,true);
  const landing={x:a.x+result.move.x*130,y:a.y+result.move.y*130};
  assert.ok(dangerAt(landing,a,[],hazards)<dangerAt(a,a,[],hazards));
  const wall={...landing,r:150};
  assert.equal(decideCompanion(a,{player:player(),hazards,obstacles:[wall]}).dash,false);
});
test('AI upgrades choose only from legal offers and prioritize survival',()=>{
  const choices=[{id:'power'},{id:'vitality'}];
  assert.strictEqual(chooseUpgrade(actor({hp:20}),choices),choices[1]);
  assert.strictEqual(chooseUpgrade(actor(),choices),choices[0]);
  assert.equal(chooseUpgrade(actor(),[]),null);
});
test('Vietnamese offline chat handles diacritics, context, storage and honest limits',()=>{
  assert.equal(chat('Tôi nên nâng cấp gì?',{player:actor({hp:20})}).intent,'upgrades');
  assert.match(chat('Tôi nên nâng cấp gì?',{player:actor({hp:20})}).text,/45%/);
  assert.equal(chat('cach danh boss').intent,'boss');
  assert.equal(chat('Tôi đổi máy thì lưu sao?').intent,'save');
  assert.equal(chat('Đồng đội AI làm được gì?').intent,'companions');
  assert.match(chat('có dùng ChatGPT không?').text,/không phải mô hình/);
  assert.equal(chat('nói về thiên văn lượng tử').intent,'unknown');
  assert.equal(chat('hồi phục',{player:actor({hp:13})}).mode,'offline-rules');
  assert.match(chat('hồi phục',{player:actor({hp:13})}).text,/13 \/ 100/);
  assert.equal(COMPANIONS.length,3);
});
