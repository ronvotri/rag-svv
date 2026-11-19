/* Independent game rules. No network, game-client code, or third-party assets. */
(function (root) {
  'use strict';
  const CLASSES = [
    {id:'knight',name:'Kiếm sĩ',tag:'CẬN CHIẾN',desc:'Bền bỉ · Chém lan',hp:140,speed:170,damage:28,rate:.72,range:108,color:'#bd7957'},
    {id:'archer',name:'Cung thủ',tag:'TẦM XA',desc:'Linh hoạt · Xuyên giáp',hp:95,speed:200,damage:22,rate:.55,range:440,color:'#9bb875'},
    {id:'mage',name:'Pháp sư',tag:'PHÉP THUẬT',desc:'Bùng nổ · Sát thương vùng',hp:85,speed:175,damage:38,rate:1.1,range:350,color:'#a79ac8'}
  ];
  const MAPS = [
    {id:'meadow',name:'Đồng cỏ bình minh',desc:'Khởi đầu · Quái chậm',unlock:0,color:'#567648',floor:'#334a32',accent:'#79985d',difficulty:1},
    {id:'forest',name:'Rừng sương cổ',desc:'Thử thách · Quái đông',unlock:1,color:'#436e60',floor:'#203f36',accent:'#618f72',difficulty:1.25},
    {id:'ruins',name:'Phế tích hoàng hôn',desc:'Hiểm nguy · Quái mạnh',unlock:2,color:'#8e775a',floor:'#4a4538',accent:'#a38e68',difficulty:1.5}
  ];
  const UPGRADES = [
    {id:'power',name:'Ý chí chiến binh',icon:'⚔',desc:'Tăng 20% sát thương mọi kỹ năng.',max:8},
    {id:'haste',name:'Nhịp chiến đấu',icon:'»',desc:'Giảm 10% thời gian giữa các đòn đánh.',max:6},
    {id:'vitality',name:'Sức sống',icon:'♡',desc:'+25 máu tối đa, hồi 35 máu.',max:6},
    {id:'speed',name:'Bước chân gió',icon:'⌁',desc:'Tăng 10% tốc độ di chuyển.',max:5},
    {id:'magnet',name:'Lực hút linh hồn',icon:'◇',desc:'Tăng 55% tầm nhặt kinh nghiệm.',max:4},
    {id:'orbit',name:'Vệ tinh lửa',icon:'✦',desc:'Thêm một ngọn lửa quay quanh, thiêu đốt kẻ địch.',max:4},
    {id:'nova',name:'Vòng băng',icon:'❄',desc:'Bùng nổ mỗi 5 giây, làm chậm quái. Thêm cấp tăng sức mạnh.',max:4},
    {id:'regen',name:'Mầm hồi phục',icon:'✚',desc:'Hồi thêm 1,5 máu mỗi giây.',max:4},
    {id:'multishot',name:'Dư ảnh',icon:'⋈',desc:'Thêm một đòn phụ. Kiếm sĩ tăng tầm chém.',max:3}
  ];
  const TRAINING = [
    {id:'hp',name:'Thể lực',desc:'+10 máu tối đa mỗi bậc'},
    {id:'power',name:'Võ nghệ',desc:'+5% sát thương mỗi bậc'},
    {id:'fortune',name:'Tích lũy',desc:'+10% vàng sau trận mỗi bậc'}
  ];
  const emptySave = () => ({version:1,gold:0,runs:0,wins:0,best:0,kills:0,training:{hp:0,power:0,fortune:0}});
  function validateSave(value) {
    if (!value || value.version!==1 || !value.training) throw new Error('Tệp lưu không đúng định dạng phiên bản 1.');
    const result=emptySave();
    for(const k of ['gold','runs','wins','best','kills']) {
      if(!Number.isSafeInteger(value[k]) || value[k]<0 || value[k]>1e9) throw new Error('Dữ liệu lưu không hợp lệ: '+k);
      result[k]=value[k];
    }
    for(const k of ['hp','power','fortune']) {
      if(!Number.isInteger(value.training[k]) || value.training[k]<0 || value.training[k]>10) throw new Error('Bậc rèn luyện không hợp lệ.');
      result.training[k]=value.training[k];
    }
    if(result.wins>result.runs || result.best>3600) throw new Error('Thống kê lưu không hợp lệ.');
    return result;
  }
  const dist = (a,b) => Math.hypot(a.x-b.x,a.y-b.y);
  const clamp = (v,a,b) => Math.max(a,Math.min(v,b));
  const cost = level => 60+level*60;
  class Run {
    constructor(jobId,mapId,save=emptySave(),random=Math.random,options={}) {
      this.job=CLASSES.find(x=>x.id===jobId);this.map=MAPS.find(x=>x.id===mapId);
      if(!this.job || !this.map) throw new Error('Nghề hoặc bản đồ không tồn tại.');
      if(save.wins<this.map.unlock) throw new Error('Bản đồ chưa mở khóa.');
      this.random=random;this.state='playing';this.time=0;this.kills=0;this.earned=0;this.level=1;this.xp=0;this.nextXp=12;
      this.player={x:0,y:0,hp:this.job.hp+save.training.hp*10,maxHp:this.job.hp+save.training.hp*10,invuln:0,face:1};
      this.basePower=1+save.training.power*.05;this.fortune=save.training.fortune;
      this.upgrades={};this.enemies=[];this.gems=[];this.shots=[];this.effects=[];this.texts=[];this.choices=[];
      this.spawnClock=0;this.attackClock=0;this.novaClock=4;this.dashCooldown=0;this.dashTime=0;this.bossSpawned=false;this.nextId=1;
      this.id=options.runId||`run-${Date.now()}-${Math.floor(random()*1e9)}`;
      this.mode=options.mode==='tower'?'tower':'survival';this.floor=1;this.floorKills=0;
      this.companions=(options.companions||[]).filter((role,i,a)=>['guardian','ranger','healer'].includes(role)&&a.indexOf(role)===i).slice(0,3).map((role,i)=>({id:`ally-${role}`,name:role==='healer'?'Linh':role==='ranger'?'Phong':'Thạch',role,job:role==='healer'?'mage':role==='ranger'?'archer':'knight',x:-45-i*35,y:40,hp:role==='guardian'?180:105,maxHp:role==='guardian'?180:105,range:role==='guardian'?95:350,damage:role==='guardian'?17:role==='ranger'?15:11,face:1,invuln:0,cooldowns:{attack:0,heal:0,revive:0,dash:0},dashTime:0,reviveProgress:0,reason:'Bám đội'}));
      const b=options.bonuses||{};
      this.player.maxHp+=clamp(Number(b.hp)||0,0,500);this.player.hp=this.player.maxHp;
      this.basePower*=1+clamp(Number(b.power)||0,0,2);this.bonusSpeed=clamp(Number(b.speed)||0,0,.5);this.bonusRegen=clamp(Number(b.regen)||0,0,8);this.bonusFortune=clamp(Number(b.fortune)||0,0,2);
    }
    get power(){return this.basePower*(1+.2*(this.upgrades.power||0));}
    get speed(){return this.job.speed*(1+.1*(this.upgrades.speed||0)+(this.bonusSpeed||0));}
    get gold(){return Math.floor((this.kills*.55+this.time*.12+(this.state==='won'?120:0))*(1+this.fortune*.1+(this.bonusFortune||0)));}
    dash(dx,dy){
      if(this.state!=='playing' || this.dashCooldown>0 || Math.hypot(dx,dy)<.1) return false;
      const d=Math.hypot(dx,dy);this.dashDirection={x:dx/d,y:dy/d};this.dashTime=.19;this.dashCooldown=3;this.player.invuln=.3;return true;
    }
    spawn(boss=false) {
      if(!boss && this.enemies.length>=200)return;
      const angle=this.random()*Math.PI*2, radius=boss?470:610+this.random()*120;
      const type=boss?'boss':this.random()<.2+this.time/1400?'bat':this.random()<.3?'golem':'slime';
      const mult=this.map.difficulty, stage=1+this.time/110;
      const hp=(boss?2300:type==='golem'?58:type==='bat'?23:33)*stage*mult;
      this.enemies.push({id:this.nextId++,type,x:this.player.x+Math.cos(angle)*radius,y:this.player.y+Math.sin(angle)*radius,hp,maxHp:hp,r:boss?39:type==='golem'?17:13,speed:(boss?67:type==='bat'?108:type==='golem'?43:61)*mult*(1+this.time/900),damage:(boss?28:9)*mult,hit:0,slow:0,pulse:0,attack:3});
    }
    damage(enemy,value) {
      if(enemy.hp<=0)return;
      enemy.hp-=value;enemy.hit=.12;
      if(this.texts.length<60)this.texts.push({x:enemy.x+(this.random()-.5)*16,y:enemy.y-20,value:Math.round(value),life:.65});
      if(enemy.hp<=0){this.kills++;this.floorKills++;this.gems.push({x:enemy.x,y:enemy.y,value:enemy.type==='boss'?100:enemy.type==='golem'?4:2});if(enemy.type==='boss'){if(this.mode==='tower'){this.floor++;this.floorKills=0;this.bossSpawned=false;this.player.hp=Math.min(this.player.maxHp,this.player.hp+this.player.maxHp*.25);}else this.state='won';}}
    }
    area(x,y,radius,damage,kind='slash') {
      this.effects.push({x,y,r:radius,kind,life:.28,max:.28});
      for(const e of this.enemies)if(e.hp>0 && Math.hypot(e.x-x,e.y-y)<radius+e.r){this.damage(e,damage);if(kind==='nova')e.slow=2;}
    }
    attack() {
      const extra=this.upgrades.multishot||0;
      let target=null,nearest=this.job.range+(this.job.id==='knight'?extra*18:0);
      for(const e of this.enemies){const d=dist(e,this.player);if(e.hp>0 && d<nearest){nearest=d;target=e;}}
      if(!target)return false;
      const p=this.player,damage=this.job.damage*this.power;
      if(this.job.id==='knight')this.area(p.x,p.y,this.job.range+extra*18,damage);
      else {
        const angle=Math.atan2(target.y-p.y,target.x-p.x);
        for(let i=0;i<=extra;i++) {
          // Keep the first shot aimed at the target; extras fan out around it.
          const a=angle+(i===0?0:Math.ceil(i/2)*.15*(i%2?1:-1));
          this.shots.push({x:p.x,y:p.y,vx:Math.cos(a)*440,vy:Math.sin(a)*440,damage,life:1.5,kind:this.job.id==='mage'?'fire':'arrow',pierce:this.job.id==='archer'?2:1,hit:new Set()});
        }
      }
      return true;
    }
    gainXp(amount){this.xp+=amount;this.checkLevel();}
    checkLevel(){
      if(this.state!=='playing' || this.xp<this.nextXp)return;
      this.xp-=this.nextXp;this.level++;this.nextXp=Math.floor(12+this.level*6+this.level*this.level*.25);
      const available=UPGRADES.filter(x=>(this.upgrades[x.id]||0)<x.max);
      if(!available.length){this.player.hp=Math.min(this.player.maxHp,this.player.hp+30);return;}
      for(let i=available.length-1;i>0;i--){const j=Math.floor(this.random()*(i+1));[available[i],available[j]]=[available[j],available[i]];}
      this.choices=available.slice(0,3);this.state='levelup';
    }
    choose(id){
      if(this.state!=='levelup' || !this.choices.some(x=>x.id===id))return false;
      this.upgrades[id]=(this.upgrades[id]||0)+1;
      if(id==='vitality'){this.player.maxHp+=25;this.player.hp=Math.min(this.player.maxHp,this.player.hp+35);}
      this.choices=[];this.state='playing';this.checkLevel();return true;
    }
    updateCompanions(dt){
      if(!this.companions.length)return;
      const ai=root.MidgardAI||(typeof require==='function'?require('./ai.js'):null);
      if(!ai)return;
      const allies=[{...this.player,id:'player'},...this.companions];
      const hazards=this.effects.filter(e=>e.damage&&e.life>0).map(e=>({...e,radius:e.r}));
      for(const a of this.companions){
        if(a.hp<=0)continue;
        a.invuln=Math.max(0,a.invuln-dt);for(const k of Object.keys(a.cooldowns))a.cooldowns[k]=Math.max(0,a.cooldowns[k]-dt);
        const decision=ai.decideCompanion(a,{player:{...this.player,id:'player'},enemies:this.enemies.filter(e=>e.hp>0),allies,hazards});
        a.reason=decision.reason;const move=decision.move||{x:0,y:0};const l=Math.hypot(move.x,move.y)||1;
        if(decision.dash&&a.cooldowns.dash<=0){a.dashTime=.18;a.cooldowns.dash=3;a.invuln=.25;}
        a.dashTime=Math.max(0,a.dashTime-dt);const speed=this.speed*.93*(a.dashTime>0?3:1);
        a.x+=move.x/Math.max(1,l)*speed*dt;a.y+=move.y/Math.max(1,l)*speed*dt;if(move.x)a.face=move.x<0?-1:1;
        // Catch up after a long sprint; no repeated attacks or healing during teleport.
        if(dist(a,this.player)>900){a.x=this.player.x-45;a.y=this.player.y+35;continue;}
        const target=this.enemies.find(e=>e.id===decision.targetId&&e.hp>0);
        if(target&&a.cooldowns.attack<=0&&dist(a,target)<=a.range+target.r){
          a.cooldowns.attack=a.role==='ranger'?.8:1.15;
          if(a.role==='guardian')this.area(a.x,a.y,95,a.damage*this.power,'slash');
          else{const angle=Math.atan2(target.y-a.y,target.x-a.x);this.shots.push({x:a.x,y:a.y,vx:Math.cos(angle)*440,vy:Math.sin(angle)*440,damage:a.damage*this.power,life:1.5,kind:a.role==='healer'?'fire':'arrow',pierce:1,hit:new Set()});}
        }
        const heal=decision.healId==='player'?this.player:this.companions.find(e=>e.id===decision.healId);
        if(a.role==='healer'&&heal&&heal.hp>0&&a.cooldowns.heal<=0&&dist(a,heal)<260){heal.hp=Math.min(heal.maxHp,heal.hp+24);a.cooldowns.heal=5;this.effects.push({x:heal.x,y:heal.y,r:32,kind:'heal',life:.5,max:.5});}
        const down=this.companions.find(e=>e.id===decision.reviveId&&e.hp<=0);
        if(down&&dist(a,down)<60&&a.cooldowns.revive<=0){a.reviveProgress+=dt;if(a.reviveProgress>=2){down.hp=down.maxHp*.35;down.invuln=2;a.cooldowns.revive=12;a.reviveProgress=0;}}
        else a.reviveProgress=0;
        for(const e of this.enemies){if(e.hp>0&&dist(a,e)<e.r+12&&a.invuln<=0){a.hp=Math.max(0,a.hp-e.damage);a.invuln=.8;}}
      }
    }
    update(dt,input={x:0,y:0}) {
      if(this.state!=='playing')return;
      dt=clamp(dt,0,.05);this.time+=dt;const p=this.player;
      this.dashCooldown=Math.max(0,this.dashCooldown-dt);p.invuln=Math.max(0,p.invuln-dt);
      const l=Math.hypot(input.x,input.y),move=l>1?{x:input.x/l,y:input.y/l}:input;
      if(this.dashTime>0){this.dashTime-=dt;p.x+=this.dashDirection.x*this.speed*4*dt;p.y+=this.dashDirection.y*this.speed*4*dt;}
      else{p.x+=move.x*this.speed*dt;p.y+=move.y*this.speed*dt;}
      if(move.x)p.face=move.x<0?-1:1;
      p.hp=Math.min(p.maxHp,p.hp+((this.upgrades.regen||0)*1.5+this.bonusRegen)*dt);
      this.spawnClock-=dt;
      if(this.spawnClock<=0 && !this.bossSpawned){this.spawnClock=Math.max(.18,1.1-this.time/310)/this.map.difficulty;this.spawn();if(this.time>90)this.spawn();}
      if((this.mode==='tower'?this.floorKills>=15+this.floor*5:this.time>=300) && !this.bossSpawned){this.bossSpawned=true;this.spawn(true);this.effects.push({x:p.x,y:p.y,r:400,kind:'warning',life:1,max:1});}
      if((this.mode==='survival'&&this.time>=420)||this.time>=3600){this.state='lost';return;}
      if(this.mode==='tower'&&this.floor>20){this.state='won';return;}
      this.updateCompanions(dt);
      this.attackClock-=dt;if(this.attackClock<=0){if(this.attack())this.attackClock=this.job.rate*Math.pow(.9,this.upgrades.haste||0);else this.attackClock=.08;}
      this.novaClock-=dt;if(this.upgrades.nova && this.novaClock<=0){this.novaClock=5;this.area(p.x,p.y,145+this.upgrades.nova*20,(25+this.upgrades.nova*18)*this.power,'nova');}
      const orbits=this.upgrades.orbit||0;
      for(const e of this.enemies){
        if(e.hp<=0)continue;
        e.hit=Math.max(0,e.hit-dt);e.slow=Math.max(0,e.slow-dt);e.pulse=Math.max(0,e.pulse-dt);
        const d=dist(e,p)||1,slow=e.slow>0?.45:1;
        e.x+=(p.x-e.x)/d*e.speed*slow*dt;e.y+=(p.y-e.y)/d*e.speed*slow*dt;
        if(d<e.r+12 && p.invuln<=0){p.hp-=e.damage;p.invuln=.65;this.effects.push({x:p.x,y:p.y,r:28,kind:'hurt',life:.18,max:.18});}
        if(e.type==='boss'){
          e.attack-=dt;
          if(e.attack<=0){e.attack=3.5;this.effects.push({x:e.x,y:e.y,r:145,kind:'warning',life:.85,max:.85,damage:e.damage});}
        }
        for(let i=0;i<orbits;i++){
          const a=this.time*2.6+i*Math.PI*2/orbits;
          if(Math.hypot(e.x-p.x-Math.cos(a)*82,e.y-p.y-Math.sin(a)*82)<e.r+16 && e.pulse<=0){this.damage(e,18*this.power);e.pulse=.35;break;}
        }
      }
      for(const s of this.shots){
        s.life-=dt;s.x+=s.vx*dt;s.y+=s.vy*dt;
        for(const e of this.enemies){
          if(s.life<=0)break;
          if(e.hp>0 && !s.hit.has(e.id) && dist(s,e)<e.r+8){s.hit.add(e.id);if(s.kind==='fire'){this.area(s.x,s.y,60,s.damage,'fire');s.life=0;}else{this.damage(e,s.damage);if(--s.pierce<=0)s.life=0;}}
        }
      }
      const magnet=65*(1+.55*(this.upgrades.magnet||0));
      for(const g of this.gems){const d=dist(g,p);if(d<magnet || g.pulling){g.pulling=true;const speed=360;g.x+=(p.x-g.x)/Math.max(1,d)*Math.min(d,speed*dt);g.y+=(p.y-g.y)/Math.max(1,d)*Math.min(d,speed*dt);}if(dist(g,p)<15){g.collected=true;this.xp+=g.value;}}
      // Only merge uncollected drops: collected values are already in player XP.
      this.gems=this.gems.filter(x=>!x.collected);
      while(this.gems.length>450){const a=this.gems.shift();this.gems[0].value+=a.value;}
      for(const effect of this.effects){effect.life-=dt;if(effect.damage&&effect.life<=0){if(dist(effect,p)<effect.r+12&&p.invuln<=0){p.hp-=effect.damage;p.invuln=.65;}for(const a of this.companions)if(a.hp>0&&dist(effect,a)<effect.r+12&&a.invuln<=0){a.hp=Math.max(0,a.hp-effect.damage);a.invuln=.8;}}}
      for(const t of this.texts){t.life-=dt;t.y-=25*dt;}
      this.enemies=this.enemies.filter(x=>x.hp>0 && (x.type==='boss'||dist(x,p)<1500));this.gems=this.gems.filter(x=>!x.collected);
      this.shots=this.shots.filter(x=>x.life>0);this.effects=this.effects.filter(x=>x.life>0);this.texts=this.texts.filter(x=>x.life>0);
      if(p.hp<=0){p.hp=0;this.state='lost';}else this.checkLevel();
    }
    settle(save){
      if(this.earned || !['won','lost'].includes(this.state))return save;
      const next=validateSave(save);next.gold+=this.gold;next.runs++;next.kills+=this.kills;next.wins+=this.state==='won'?1:0;next.best=Math.max(next.best,Math.floor(this.time));this.earned=1;return next;
    }
  }
  const api={CLASSES,MAPS,UPGRADES,TRAINING,Run,emptySave,validateSave,cost,clamp};
  if(typeof module!=='undefined' && module.exports)module.exports=api;else root.Midgard=api;
})(typeof globalThis!=='undefined'?globalThis:this);
