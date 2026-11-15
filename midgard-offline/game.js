/* Browser shell and original procedural pixel artwork. Runs over file://. */
(() => {
  'use strict';
  const {CLASSES,MAPS,UPGRADES,TRAINING,Run,emptySave,validateSave,cost,clamp}=Midgard;
  const $=id=>document.getElementById(id),canvas=$('world'),ctx=canvas.getContext('2d');
  const SAVE_KEY='votri.midgard.offline.v1';
  let save=emptySave(),storageOK=true,job='knight',map='meadow',run=null,mode='menu',last=0,ambient=0,sound=false,audio=null,shownState='',lastMove={x:1,y:0};
  let width=innerWidth,height=innerHeight,scale=1,uiStamp=0;
  const keys=new Set(),touch={active:false,id:null,x:0,y:0,dx:0,dy:0};
  try{const raw=localStorage.getItem(SAVE_KEY);if(raw)save=validateSave(JSON.parse(raw));}catch(e){storageOK=false;$('storage-message').textContent='Không đọc được lưu cục bộ. Bạn vẫn có thể chơi và xuất tệp lưu JSON.';}
  function persist(){try{localStorage.setItem(SAVE_KEY,JSON.stringify(save));storageOK=true;}catch(e){storageOK=false;$('storage-message').textContent='Trình duyệt chặn lưu. Hãy xuất tệp lưu JSON trước khi đóng game.';}}
  const clock=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${Math.floor(t%60).toString().padStart(2,'0')}`;
  const hash=(x,y)=>{const n=Math.sin(x*127.1+y*311.7)*43758.5453;return n-Math.floor(n);};
  function tone(freq=440,duration=.06,type='triangle',volume=.025){
    if(!sound)return;try{if(!audio)audio=new(window.AudioContext||window.webkitAudioContext)();if(audio.state==='suspended')audio.resume();const o=audio.createOscillator(),g=audio.createGain();o.type=type;o.frequency.setValueAtTime(freq,audio.currentTime);o.frequency.exponentialRampToValueAtTime(freq*.65,audio.currentTime+duration);g.gain.setValueAtTime(volume,audio.currentTime);g.gain.exponentialRampToValueAtTime(.001,audio.currentTime+duration);o.connect(g);g.connect(audio.destination);o.start();o.stop(audio.currentTime+duration);}catch(e){sound=false;}}
  function resize(){width=innerWidth;height=innerHeight;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);scale=clamp(Math.min(width/1100,height/720),.65,1.4);}
  addEventListener('resize',resize);resize();
  // Every sprite below is drawn here, with no dependency on a game installation.
  function character(c,x,y,id,face=1,step=0,size=1,hit=false){
    c.save();c.translate(Math.round(x),Math.round(y));c.scale(face*size,size);c.fillStyle='#0004';c.beginPath();c.ellipse(0,11,14,5,0,0,Math.PI*2);c.fill();
    const bob=Math.abs(Math.sin(step))*1.6;c.translate(0,-bob);const col=CLASSES.find(j=>j.id===id).color;
    c.fillStyle=hit?'#fff6b3':col;c.fillRect(-9,-7,18,16);c.fillStyle='#283b35';c.fillRect(-7,9,5,5+Math.sin(step)*2);c.fillRect(3,9,5,5-Math.sin(step)*2);
    c.fillStyle='#e9bc8c';c.fillRect(-7,-21,14,14);c.fillStyle='#513e32';c.fillRect(-8,-23,16,5);c.fillRect(-8,-21,4,7);c.fillStyle='#26392f';c.fillRect(2,-15,2,2);
    if(id==='knight'){c.fillStyle='#bcc7bb';c.fillRect(-9,-24,18,7);c.fillRect(-10,-19,4,7);c.fillStyle='#ddd4aa';c.fillRect(12,-13,3,26);c.fillStyle='#9da99a';c.fillRect(9,0,10,3);c.fillStyle='#7e5239';c.fillRect(-14,-4,8,13);c.fillStyle='#d4b57a';c.fillRect(-12,-2,3,9);}
    if(id==='archer'){c.fillStyle='#6f985f';c.fillRect(-9,-24,18,7);c.fillRect(-5,-28,11,6);c.fillStyle='#c9aa70';c.fillRect(14,-16,3,24);c.fillRect(17,-11,3,14);c.fillStyle='#ede2bf';c.fillRect(12,-13,1,20);c.fillStyle='#e0c99a';c.fillRect(-6,-6,4,16);}
    if(id==='mage'){c.fillStyle='#8780b7';c.fillRect(-12,-24,24,4);c.fillRect(-7,-30,14,7);c.fillRect(-4,-37,7,8);c.fillStyle='#d7bd85';c.fillRect(13,-18,3,31);c.fillStyle='#b8e1db';c.fillRect(10,-24,9,9);c.fillStyle='#c4bae7';c.fillRect(-5,1,10,10);}
    c.restore();
  }
  function tree(x,y,s=1,seed=0,palette=MAPS[0]){
    ctx.save();ctx.translate(x,y);ctx.scale(s,s);ctx.fillStyle='#071a1240';ctx.beginPath();ctx.ellipse(8,8,42,14,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#594b32';ctx.fillRect(-6,-47,12,47);ctx.fillStyle='#293e2a';ctx.fillRect(-28,-79,56,42);ctx.fillRect(-39,-64,78,30);ctx.fillStyle=palette.color;ctx.fillRect(-27,-87,54,37);ctx.fillRect(-37,-69,70,25);ctx.fillStyle=palette.accent;ctx.globalAlpha=.55;ctx.fillRect(-24,-81,22,12);ctx.fillRect(-32,-64,16,8);ctx.fillRect(4,-74,18,7);ctx.restore();
  }
  function enemy(e,time){
    ctx.save();ctx.translate(Math.round(e.x),Math.round(e.y));ctx.fillStyle='#0004';ctx.beginPath();ctx.ellipse(0,8,e.r,6,0,0,Math.PI*2);ctx.fill();ctx.translate(0,Math.sin(time*6+e.id)*2);
    if(e.type==='slime'){ctx.fillStyle=e.hit?'#e9ffc2':e.slow?'#95b9c2':'#c4a2aa';ctx.fillRect(-12,-7,24,14);ctx.fillRect(-8,-13,16,7);ctx.fillStyle='#f6ded5';ctx.fillRect(-7,-10,6,3);ctx.fillStyle='#4f4143';ctx.fillRect(-5,-4,2,3);ctx.fillRect(4,-4,2,3);}
    else if(e.type==='bat'){ctx.fillStyle=e.hit?'#f9dfb1':'#887c9c';const flap=Math.sin(time*15)*5;ctx.fillRect(-24,-9+flap,17,7);ctx.fillRect(7,-9+flap,17,7);ctx.fillRect(-8,-13,16,20);ctx.fillStyle='#e9b672';ctx.fillRect(-4,-8,2,3);ctx.fillRect(3,-8,2,3);}
    else if(e.type==='golem'){ctx.fillStyle=e.hit?'#fff4cc':'#8b9479';ctx.fillRect(-14,-22,28,28);ctx.fillRect(-20,-14,8,18);ctx.fillRect(12,-14,8,18);ctx.fillStyle='#b5b896';ctx.fillRect(-10,-19,10,7);ctx.fillStyle='#333c30';ctx.fillRect(-6,-10,4,3);ctx.fillRect(4,-10,4,3);}
    else{ctx.fillStyle=e.hit?'#ead6a7':'#795a3d';ctx.fillRect(-26,-56,52,63);ctx.fillRect(-39,-33,15,36);ctx.fillRect(25,-33,15,36);ctx.fillStyle='#48613e';ctx.fillRect(-45,-82,90,32);ctx.fillRect(-32,-100,64,28);ctx.fillStyle='#708452';ctx.fillRect(-27,-94,27,15);ctx.fillStyle='#edc66d';ctx.fillRect(-15,-41,9,7);ctx.fillRect(7,-41,9,7);ctx.fillStyle='#392e22';ctx.fillRect(-10,-19,21,6);}
    if(e.hp<e.maxHp && e.type!=='boss'){ctx.fillStyle='#13261c';ctx.fillRect(-16,-31,32,3);ctx.fillStyle='#ddb075';ctx.fillRect(-16,-31,32*Math.max(0,e.hp/e.maxHp),3);}
    ctx.restore();
  }
  function scenery(camera,palette,time,menu=false){
    ctx.fillStyle=palette.floor;ctx.fillRect(0,0,width,height);ctx.save();ctx.translate(width/2-camera.x*scale,height/2-camera.y*scale);ctx.scale(scale,scale);
    const left=camera.x-width/scale/2-120,right=camera.x+width/scale/2+120,top=camera.y-height/scale/2-100,bottom=camera.y+height/scale/2+170;
    for(let y=Math.floor(top/80)*80;y<bottom;y+=80)for(let x=Math.floor(left/80)*80;x<right;x+=80){
      const h=hash(x,y),h2=hash(y+13,x-7);ctx.fillStyle=h>.5?'#c0d59108':'#071b1209';ctx.fillRect(x,y,80,80);
      if(h<.14){ctx.fillStyle=palette.accent;ctx.globalAlpha=.4;ctx.fillRect(x+h2*55,y+h*200,3,5);ctx.fillRect(x+h2*55+5,y+h*200-2,2,7);ctx.globalAlpha=1;}
      if(h>.9){ctx.fillStyle='#e4cf9944';ctx.fillRect(x+25,y+45,3,3);ctx.fillStyle='#9eab7555';ctx.fillRect(x+24,y+48,2,4);}
      if(h>.64 && h<.7){ctx.fillStyle='#8d99714d';ctx.fillRect(x+21,y+39,14,8);ctx.fillStyle='#b2bc8a4d';ctx.fillRect(x+24,y+37,7,3);}
    }
    // A winding old road and scattered ruins establish direction without walls.
    ctx.strokeStyle=palette.id==='ruins'?'#b0a08022':'#b2a67d1a';ctx.lineWidth=72;ctx.beginPath();ctx.moveTo(-2000,-700);ctx.bezierCurveTo(-500,600,500,-300,2000,800);ctx.stroke();
    for(let y=Math.floor(top/200)*200;y<bottom;y+=200)for(let x=Math.floor(left/200)*200;x<right;x+=200){
      const h=hash(x+5,y-3);if(h>.67 && Math.hypot(x,y)>130){const tx=x+hash(y,x)*75,ty=y+hash(x+8,y)*65;if(palette.id==='ruins' && h>.85){ctx.fillStyle='#292e2780';ctx.fillRect(tx-20,ty+4,55,12);ctx.fillStyle='#8f8b71';ctx.fillRect(tx,ty-54,20,58);ctx.fillStyle='#b2aa8b';ctx.fillRect(tx-4,ty-60,28,10);ctx.fillStyle='#525b48';ctx.fillRect(tx+11,ty-45,4,32);}else tree(tx,ty,.7+h*.5,h,palette);}
    }
    if(menu){
      ctx.fillStyle='#d1c39330';ctx.beginPath();ctx.ellipse(250,120,160,58,-.2,0,Math.PI*2);ctx.fill();
      ctx.fillStyle='#383f32';ctx.fillRect(390,-130,88,45);ctx.fillStyle='#a7a487';ctx.fillRect(402,-191,20,73);ctx.fillRect(456,-202,20,85);ctx.fillRect(398,-204,83,13);ctx.fillStyle='#d2c5a0';ctx.fillRect(395,-208,89,5);ctx.fillStyle='#53684d';ctx.fillRect(437,-191,9,48);
      character(ctx,275,85,'knight',1,time*2,1.7);character(ctx,215,123,'mage',1,time*2+2,1.5);character(ctx,340,130,'archer',-1,time*2+1,1.5);
      for(let i=0;i<24;i++){const x=180+hash(i,3)*480,y=-250+hash(i,6)*550;ctx.fillStyle=`rgba(234,220,150,${.2+Math.sin(time+i)*.2})`;ctx.fillRect(x+Math.sin(time*.4+i)*14,y,2,2);}
    }
    ctx.restore();
    if(menu){const g=ctx.createRadialGradient(width*.73,height*.38,10,width*.73,height*.38,width*.7);g.addColorStop(0,'#d4c99709');g.addColorStop(1,'#06170f6b');ctx.fillStyle=g;ctx.fillRect(0,0,width,height);}
  }
  function draw(){
    const menu=mode==='menu';const palette=menu?MAPS.find(m=>m.id===map):run.map;
    const camera=menu?{x:0,y:0}:run.player;scenery(camera,palette,ambient,menu);if(menu)return;
    ctx.save();ctx.translate(width/2-camera.x*scale,height/2-camera.y*scale);ctx.scale(scale,scale);
    for(const g of run.gems){ctx.save();ctx.translate(g.x,g.y);ctx.rotate(Math.PI/4);ctx.fillStyle=g.value>4?'#e8c67b':'#b8d9b0';ctx.fillRect(-3,-3,6,6);ctx.restore();}
    const actors=[...run.enemies.map(e=>({y:e.y,draw:()=>enemy(e,run.time)})),{y:run.player.y,draw:()=>{if(run.player.invuln<=0||Math.floor(ambient*18)%2===0)character(ctx,run.player.x,run.player.y,job,run.player.face,(keys.size||touch.active)?run.time*11:0,1.15,run.player.invuln>0);}}];
    actors.sort((a,b)=>a.y-b.y);for(const a of actors)a.draw();
    for(const s of run.shots){ctx.save();ctx.translate(s.x,s.y);ctx.rotate(Math.atan2(s.vy,s.vx));ctx.fillStyle=s.kind==='fire'?'#efc37b':'#e7d7a3';ctx.fillRect(-12,-2,20,4);ctx.fillStyle=s.kind==='fire'?'#fff3bd':'#c4d2a0';ctx.fillRect(4,-4,6,8);ctx.restore();}
    for(const e of run.effects){const progress=1-e.life/e.max;ctx.save();ctx.globalAlpha=1-progress;ctx.strokeStyle=e.kind==='nova'?'#b3dfdf':e.kind==='hurt'?'#eaa18b':e.kind==='warning'?'#e6a26c':'#eee1ac';ctx.lineWidth=e.kind==='slash'?6:3;ctx.beginPath();ctx.arc(e.x,e.y,e.kind==='warning'?e.r:e.r*(.5+progress*.5),0,Math.PI*2);ctx.stroke();if(e.kind==='warning'){ctx.globalAlpha=.15;ctx.fillStyle='#ec9d65';ctx.fill();}ctx.restore();}
    const n=run.upgrades.orbit||0;for(let i=0;i<n;i++){const a=run.time*2.6+i*Math.PI*2/n,x=run.player.x+Math.cos(a)*82,y=run.player.y+Math.sin(a)*82;ctx.fillStyle='#ffde9a';ctx.fillRect(x-5,y-7,10,13);ctx.fillStyle='#ce7e59';ctx.fillRect(x-3,y-10,6,5);}
    ctx.font='bold 13px Segoe UI';ctx.textAlign='center';for(const t of run.texts){ctx.globalAlpha=Math.min(1,t.life*3);ctx.fillStyle='#f5e6b7';ctx.fillText(t.value,t.x,t.y);}ctx.globalAlpha=1;ctx.restore();
    const vignette=ctx.createRadialGradient(width/2,height/2,height*.2,width/2,height/2,width*.75);vignette.addColorStop(0,'#00140700');vignette.addColorStop(1,'#06150c88');ctx.fillStyle=vignette;ctx.fillRect(0,0,width,height);
  }
  function renderMenu(){
    $('gold-label').textContent=`· ${save.gold} vàng`;$('best-label').textContent=save.runs?`Kỷ lục ${clock(save.best)} · ${save.wins} chiến thắng`:'Cuộc phiêu lưu đầu tiên';
    $('classes').replaceChildren();
    for(const c of CLASSES){const b=document.createElement('button');b.className='class-card'+(c.id===job?' selected':'');b.setAttribute('aria-pressed',c.id===job);b.innerHTML=`<canvas width="48" height="64" aria-hidden="true"></canvas><div><span class="tag">${c.tag}</span><strong>${c.name}</strong><small>${c.desc}</small></div>`;const cctx=b.querySelector('canvas').getContext('2d');character(cctx,24,43,c.id,1,0,1.2);b.onclick=()=>{job=c.id;renderMenu();tone(430);};$('classes').append(b);}
    $('maps').replaceChildren();
    for(const m of MAPS){const locked=save.wins<m.unlock,b=document.createElement('button');b.className='map-card'+(m.id===map?' selected':'');b.disabled=locked;b.setAttribute('aria-pressed',m.id===map);b.innerHTML=`<span class="map-icon">${m.id==='ruins'?'♜':m.id==='forest'?'♠':'♧'}</span><div><strong>${m.name}</strong><small>${locked?`Mở sau ${m.unlock} chiến thắng`:m.desc}</small></div>`;b.onclick=()=>{map=m.id;renderMenu();tone(350);};$('maps').append(b);}
  }
  function modal(eyebrow,title,description){$('modal-eyebrow').textContent=eyebrow;$('modal-title').textContent=title;$('modal-description').textContent=description;$('modal-content').replaceChildren();$('modal-actions').replaceChildren();$('modal').hidden=false;}
  function action(label,fn,primary=false){const b=document.createElement('button');b.className=primary?'primary':'secondary';b.textContent=label;b.onclick=fn;$('modal-actions').append(b);return b;}
  function focusModal(){const b=$('modal').querySelector('button:not(:disabled)');if(b)b.focus();}
  function start(){
    run=new Run(job,map,save);mode='run';shownState='';keys.clear();releaseTouch();lastMove={x:1,y:0};$('menu').hidden=true;$('hud').hidden=false;$('modal').hidden=true;$('job-name').textContent=run.job.name+' · '+run.map.name;canvas.focus();tone(540,.18);updateHud();
  }
  function backToMenu(){mode='menu';run=null;keys.clear();releaseTouch();$('hud').hidden=true;$('modal').hidden=true;$('menu').hidden=false;renderMenu();$('start-button').focus();}
  function updateHud(){
    if(!run)return;const p=run.player;$('hp-fill').style.width=`${clamp(p.hp/p.maxHp*100,0,100)}%`;$('hp-label').textContent=`${Math.ceil(p.hp)} / ${p.maxHp}`;$('xp-fill').style.width=`${clamp(run.xp/run.nextXp*100,0,100)}%`;$('level-label').textContent=`Cấp ${run.level} · ${Math.floor(run.xp)} / ${run.nextXp} KN`;$('timer').textContent=clock(run.time);$('kill-label').textContent=`${run.kills} quái hạ gục · ${run.gold} vàng`;$('objective').textContent=run.bossSpawned?`Hạ thủ lĩnh trước ${clock(420)}`:'Sống sót đến 05:00';$('dash-button').disabled=run.dashCooldown>0;$('dash-button').textContent=run.dashCooldown>0?`Lướt · ${run.dashCooldown.toFixed(1)}s`:'Lướt · Space';
    const boss=run.enemies.find(e=>e.type==='boss');$('boss-hud').hidden=!boss;if(boss)$('boss-fill').style.width=`${clamp(boss.hp/boss.maxHp*100,0,100)}%`;
    const load=Object.entries(run.upgrades).map(([id,n])=>{const u=UPGRADES.find(x=>x.id===id);return `<span title="${u.name}">${u.icon} ${n}</span>`;}).join('');if($('loadout').innerHTML!==load)$('loadout').innerHTML=load;
  }
  function stateChanged(){
    if(!run || shownState===run.state)return;shownState=run.state;
    if(run.state==='playing'){$('modal').hidden=true;canvas.focus();return;}
    keys.clear();releaseTouch();
    if(run.state==='levelup'){
      tone(880,.2);modal(`CẤP ${run.level} · TIỀM NĂNG THỨC TỈNH`,'Chọn một sức mạnh.','Mỗi lựa chọn mở ra một cách chiến đấu mới.');const choices=document.createElement('div');choices.className='choices';
      for(const u of run.choices){const b=document.createElement('button');b.className='upgrade';b.innerHTML=`<span class="sigil">${u.icon}</span><strong>${u.name}</strong><small>${u.desc}<br>Bậc ${(run.upgrades[u.id]||0)+1} / ${u.max}</small>`;b.onclick=()=>{run.choose(u.id);shownState='';stateChanged();updateHud();tone(620);};choices.append(b);}$('modal-content').append(choices);
    }else if(run.state==='paused'){
      modal('DỪNG CHÂN MỘT CHÚT','Hành trình đang chờ.','Trận đấu đã tạm dừng. Tiến trình rèn luyện và vàng được lưu khi kết thúc trận.');action('Tiếp tục',resume,true);action('Kết thúc lượt',()=>{run.state='lost';stateChanged();});
    }else if(['won','lost'].includes(run.state)){
      save=run.settle(save);persist();tone(run.state==='won'?780:180,.35);
      modal(run.state==='won'?'THỦ LĨNH ĐÃ GỤC NGÃ':'MỘT BƯỚC GẦN HUYỀN THOẠI',run.state==='won'?'Bình minh trở lại.':'Hành trình chưa kết thúc.',run.state==='won'?'Chiến thắng mở thêm vùng đất mới. Mang chiến lợi phẩm về và tiếp tục rèn luyện.':run.time>=420?'Thời gian chinh phục đã hết. Hãy thử một cách phối hợp kỹ năng khác.':'Những kinh nghiệm hôm nay sẽ trở thành sức mạnh cho chuyến đi kế tiếp.');
      $('modal-content').innerHTML=`<div class="stat-grid"><div><b>${clock(run.time)}</b><small>Thời gian sinh tồn</small></div><div><b>${run.kills}</b><small>Quái đã hạ gục</small></div><div><b>+${run.gold}</b><small>Vàng nhận được</small></div></div>`;action('Thử lại',start,true);action('Về nơi chuẩn bị',backToMenu);
    }
    focusModal();
  }
  function pause(){if(run && run.state==='playing'){run.state='paused';stateChanged();}}
  function resume(){if(run && run.state==='paused'){run.state='playing';stateChanged();}}
  function training(){
    modal('SỨC MẠNH VĨNH VIỄN','Rèn luyện.',`Bạn có ${save.gold} vàng. Các bậc rèn luyện có hiệu lực trong mọi hành trình mới.`);
    for(const t of TRAINING){const level=save.training[t.id],price=cost(level),row=document.createElement('div');row.className='training-row';row.innerHTML=`<div><strong>${t.name} · ${level} / 10</strong><small>${t.desc}</small></div>`;const b=document.createElement('button');b.textContent=level>=10?'Đã tối đa':`${price} vàng`;b.disabled=level>=10||save.gold<price;b.onclick=()=>{if(save.gold<price || save.training[t.id]>=10)return;save.gold-=price;save.training[t.id]++;persist();renderMenu();training();tone(640);};row.append(b);$('modal-content').append(row);}
    action('Trở về',()=>{$('modal').hidden=true;$('training-button').focus();});focusModal();
  }
  function movement(){let x=(keys.has('d')||keys.has('arrowright')?1:0)-(keys.has('a')||keys.has('arrowleft')?1:0),y=(keys.has('s')||keys.has('arrowdown')?1:0)-(keys.has('w')||keys.has('arrowup')?1:0);if(touch.active){x=touch.dx;y=touch.dy;}if(Math.hypot(x,y)>.1)lastMove={x,y};return {x,y};}
  function dash(){if(run && run.dash(lastMove.x,lastMove.y))tone(230,.1,'sawtooth',.01);}
  function releaseTouch(){touch.active=false;touch.id=null;touch.dx=0;touch.dy=0;$('joystick').hidden=true;}
  canvas.addEventListener('pointerdown',e=>{if(!run || run.state!=='playing' || touch.active)return;touch.active=true;touch.id=e.pointerId;touch.x=e.clientX;touch.y=e.clientY;canvas.setPointerCapture(e.pointerId);$('joystick').hidden=false;$('joystick').style.transform=`translate(${touch.x-55}px,${touch.y-55}px)`;});
  canvas.addEventListener('pointermove',e=>{if(!touch.active||touch.id!==e.pointerId)return;const dx=e.clientX-touch.x,dy=e.clientY-touch.y,l=Math.hypot(dx,dy)||1,f=Math.min(1,l/42);touch.dx=dx/l*f;touch.dy=dy/l*f;$('joystick').firstElementChild.style.transform=`translate(${touch.dx*33}px,${touch.dy*33}px)`;});
  for(const evt of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(evt,e=>{if(touch.id===e.pointerId)releaseTouch();});
  addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey)return;const k=e.key.toLowerCase();if(mode==='run' && ['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright',' '].includes(k)){e.preventDefault();if(run.state==='playing')keys.add(k);}if(e.repeat)return;if(k==='escape'||k==='p'){if(run?.state==='paused')resume();else if(run?.state==='playing')pause();else if(mode==='menu'&&!$('modal').hidden)$('modal').hidden=true;}if(k===' ' && run?.state==='playing')dash();});
  addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));addEventListener('blur',()=>{keys.clear();releaseTouch();pause();});document.addEventListener('visibilitychange',()=>{if(document.hidden){keys.clear();releaseTouch();pause();}});
  // Keep tab focus inside the open game dialog.
  $('modal').addEventListener('keydown',e=>{if(e.key!=='Tab')return;const buttons=[...$('modal').querySelectorAll('button:not(:disabled)')];if(!buttons.length)return;const first=buttons[0],end=buttons[buttons.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();end.focus();}else if(!e.shiftKey&&document.activeElement===end){e.preventDefault();first.focus();}});
  $('start-button').onclick=start;$('pause-button').onclick=pause;$('dash-button').onclick=dash;$('training-button').onclick=training;
  $('sound-button').onclick=()=>{sound=!sound;$('sound-button').textContent='Âm thanh: '+(sound?'Bật':'Tắt');$('sound-button').setAttribute('aria-pressed',sound);tone(520,.15);};
  $('export-button').onclick=()=>{const blob=new Blob([JSON.stringify(save,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='midgard-save.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('storage-message').textContent='Đã xuất lưu. Giữ tệp JSON để mang tiến trình sang máy khác.';};
  $('import-button').onclick=()=>$('import-file').click();
  $('import-file').onchange=async e=>{const f=e.target.files[0];e.target.value='';if(!f)return;try{if(f.size>10000)throw new Error('Tệp quá lớn. Chỉ nhận tệp lưu JSON của game.');const incoming=validateSave(JSON.parse(await f.text()));modal('CHUYỂN TIẾN TRÌNH','Nhập bản lưu?',`Bản lưu có ${incoming.gold} vàng, ${incoming.runs} lượt và ${incoming.wins} chiến thắng. Xác nhận sẽ thay tiến trình hiện tại trên máy này.`);action('Nhập bản lưu',()=>{save=incoming;persist();if(save.wins<MAPS.find(m=>m.id===map).unlock)map='meadow';renderMenu();$('modal').hidden=true;$('storage-message').textContent=storageOK?'Đã nhập và lưu tiến trình.':'Đã nhập vào phiên chơi. Trình duyệt chặn lưu; hãy xuất JSON trước khi đóng.';},true);action('Giữ bản hiện tại',()=>{$('modal').hidden=true;});focusModal();}catch(err){$('storage-message').textContent='Không thể nhập: '+err.message;}};
  function frame(now){const dt=Math.min(.05,Math.max(0,(now-last)/1000));last=now;ambient+=dt;if(mode==='run' && run){const oldKills=run.kills;run.update(dt,movement());if(run.kills>oldKills)tone(130,.035,'triangle',.009);stateChanged();if(now-uiStamp>80){updateHud();uiStamp=now;}}draw();requestAnimationFrame(frame);}
  renderMenu();requestAnimationFrame(frame);
})();
