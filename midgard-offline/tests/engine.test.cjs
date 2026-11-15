'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {Run, emptySave, validateSave, CLASSES, MAPS, UPGRADES} = require('../engine.js');

function seeded(seed=1729) {
  return () => {
    seed=(Math.imul(seed,1664525)+1013904223)>>>0;
    return seed/0x100000000;
  };
}
function enemy(run,x=40,y=0,type='slime') {
  run.spawn(type==='boss');
  const e=run.enemies.at(-1);
  Object.assign(e,{x,y,type,hp:100,maxHp:100});
  return e;
}
function allMapsSave() {
  return {...emptySave(),runs:2,wins:2};
}

test('save validation rejects malformed imports and copies known fields only', () => {
  const original=emptySave();
  original.ignored={script:'anything'};
  const clean=validateSave(original);
  assert.deepEqual(clean,emptySave());
  clean.training.hp=5;
  assert.equal(original.training.hp,0);
  for(const bad of [null,{}, {...emptySave(),version:2}, {...emptySave(),gold:-1}, {...emptySave(),gold:NaN}, {...emptySave(),runs:1.5}, {...emptySave(),wins:1}, {...emptySave(),best:3601}, {...emptySave(),training:{hp:11,power:0,fortune:0}}, {...emptySave(),training:{hp:0,power:0,fortune:'1'}}]) {
    assert.throws(()=>validateSave(bad));
  }
});

test('map progression enforces unlocks and permanent training applies to runs', () => {
  assert.throws(()=>new Run('knight','forest'),/mở khóa/);
  assert.throws(()=>new Run('knight','ruins',{...emptySave(),runs:1,wins:1}),/mở khóa/);
  assert.throws(()=>new Run('unknown','meadow'),/tồn tại/);
  const save=allMapsSave();save.training={hp:3,power:2,fortune:4};
  const run=new Run('knight','ruins',save);
  assert.equal(run.player.maxHp,170);
  assert.equal(run.power,1.1);
  run.kills=100;run.time=100;
  assert.equal(run.gold,Math.floor(67*1.4));
});

test('damage drops XP once and XP choices pause simulation until chosen', () => {
  const run=new Run('knight','meadow',emptySave(),seeded());
  const e=enemy(run);
  run.damage(e,100);run.damage(e,100);
  assert.equal(run.kills,1);assert.equal(run.gems.length,1);
  run.gainXp(100);
  assert.equal(run.level,2);assert.equal(run.state,'levelup');
  assert.equal(new Set(run.choices.map(x=>x.id)).size,3);
  const before=run.time;
  run.update(.05,{x:1,y:0});
  assert.equal(run.time,before);
  assert.equal(run.choose('invalid'),false);
  assert.equal(run.choose(run.choices[0].id),true);
  assert.equal(run.level,3); // XP carries through chained level-ups.
  assert.equal(run.state,'levelup');
});

test('vitality heals and increases max HP; capped upgrades never reappear', () => {
  const run=new Run('mage','meadow',emptySave(),seeded());
  run.player.hp=10;run.state='levelup';run.choices=[UPGRADES.find(x=>x.id==='vitality')];
  assert.equal(run.choose('vitality'),true);
  assert.equal(run.player.maxHp,110);assert.equal(run.player.hp,45);
  for(const u of UPGRADES)run.upgrades[u.id]=u.max;
  run.upgrades.regen--;
  run.gainXp(run.nextXp);
  assert.deepEqual(run.choices.map(x=>x.id),['regen']);
  run.choose('regen');run.player.hp=1;
  run.gainXp(run.nextXp);
  assert.equal(run.state,'playing');assert.equal(run.player.hp,31);
});

test('melee range upgrade acquires enemies at its expanded reach', () => {
  const run=new Run('knight','meadow');
  run.upgrades.multishot=2;
  const e=enemy(run,130);
  assert.equal(run.attack(),true);
  assert.equal(e.hp,72);
});

test('ranged multishot preserves the aimed shot and adds projectiles', () => {
  for(const job of ['archer','mage']) {
    const run=new Run(job,'meadow');run.upgrades.multishot=3;
    const e=enemy(run,300);
    assert.equal(run.attack(),true);assert.equal(run.shots.length,4);
    assert.equal(run.shots[0].vy,0);assert.equal(run.shots[0].vx,440);
    run.spawnClock=100;run.attackClock=100;e.speed=0;
    for(let i=0;i<16;i++)run.update(.05);
    assert.ok(e.hp<100,`${job} aimed projectile should hit`);
  }
});

test('pickup compaction conserves XP and bounds uncollected drops', () => {
  const run=new Run('knight','meadow');run.spawnClock=100;run.attackClock=100;
  run.gems=[{x:0,y:0,value:1}];
  for(let i=0;i<600;i++)run.gems.push({x:2000+i,y:2000,value:1});
  run.update(.01);
  assert.equal(run.xp,1);
  assert.equal(run.gems.length,450);
  assert.equal(run.gems.reduce((sum,g)=>sum+g.value,0)+run.xp,601);
});

test('movement is normalized, dash has cooldown, pause freezes rules', () => {
  const run=new Run('knight','meadow');run.spawnClock=100;
  run.update(.05,{x:1,y:1});
  assert.ok(Math.abs(Math.hypot(run.player.x,run.player.y)-run.speed*.05)<1e-8);
  assert.equal(run.dash(0,0),false);
  assert.equal(run.dash(1,0),true);assert.equal(run.dash(1,0),false);
  const x=run.player.x;run.update(.05);
  assert.ok(run.player.x-x>run.speed*.05);
  run.state='paused';const time=run.time;run.update(.05,{x:1,y:0});
  assert.equal(run.time,time);
});

test('boss spawns once, defeat wins, and settlement pays exactly once', () => {
  const save=emptySave(),run=new Run('knight','meadow',save,seeded());
  run.time=299.99;run.spawnClock=100;run.update(.02);
  assert.equal(run.enemies.filter(e=>e.type==='boss').length,1);
  run.update(.05);assert.equal(run.enemies.filter(e=>e.type==='boss').length,1);
  const boss=run.enemies.find(e=>e.type==='boss');
  run.damage(boss,boss.hp);
  assert.equal(run.state,'won');
  const result=run.settle(save);
  assert.equal(result.wins,1);assert.equal(result.runs,1);assert.equal(result.best,300);
  assert.equal(result.gold,run.gold);assert.ok(result.gold>=156);
  assert.deepEqual(save,emptySave());
  assert.equal(run.settle(result),result);
});

test('death and boss timeout lose; unfinished runs do not settle', () => {
  const run=new Run('mage','meadow');const save=emptySave();
  assert.equal(run.settle(save),save);
  const e=enemy(run,0,0);e.damage=1000;run.update(.01);
  assert.equal(run.state,'lost');assert.equal(run.player.hp,0);
  const settled=run.settle(save);
  assert.equal(settled.runs,1);assert.equal(settled.wins,0);
  const expired=new Run('mage','meadow');expired.time=419.99;expired.update(.05);
  assert.equal(expired.state,'lost');
});

test('full-duration seeded runs remain finite and collections stay bounded', () => {
  for(const job of CLASSES)for(const map of MAPS) {
    const run=new Run(job.id,map.id,allMapsSave(),seeded());
    // Keep the player alive to exercise an entire 7-minute session on each map.
    run.upgrades.regen=4;run.upgrades.orbit=4;run.upgrades.nova=4;
    const maxima={enemies:0,gems:0,shots:0,effects:0,texts:0};
    for(let step=0;step<9000 && !['lost','won'].includes(run.state);step++) {
      if(run.state==='levelup')run.choose(run.choices[0].id);
      run.player.hp=run.player.maxHp;run.player.invuln=.1;
      const a=step*.003;
      run.update(.05,{x:Math.cos(a),y:Math.sin(a)});
      for(const name of Object.keys(maxima))maxima[name]=Math.max(maxima[name],run[name].length);
      for(const value of [run.time,run.player.x,run.player.y,run.player.hp,run.xp])assert.ok(Number.isFinite(value));
      for(const e of run.enemies)assert.ok(Number.isFinite(e.x+e.y+e.hp));
    }
    assert.ok(['lost','won'].includes(run.state),`${job.id}/${map.id} must terminate`);
    assert.ok(maxima.enemies<=201);assert.ok(maxima.gems<=450);
    assert.ok(maxima.shots<100);assert.ok(maxima.effects<100);assert.ok(maxima.texts<=60);
    validateSave(run.settle(allMapsSave()));
  }
});
