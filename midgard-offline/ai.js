/* Offline decisions only: the game engine owns all movement, health and damage. */
(function(root){
  'use strict';
  const COMPANIONS=Object.freeze([
    Object.freeze({id:'guardian',name:'Bảo Hộ',role:'guardian',job:'knight',range:95,hp:120,description:'Giữ gần đội, cản quái và chiến đấu cận chiến.'}),
    Object.freeze({id:'ranger',name:'Phong Tiễn',role:'ranger',job:'archer',range:340,hp:85,description:'Giữ khoảng cách, bắn quái và né vùng nguy hiểm.'}),
    Object.freeze({id:'healer',name:'Ánh Dương',role:'healer',job:'mage',range:260,hp:80,description:'Ưu tiên hồi máu, hỗ trợ và cứu đồng đội.'})
  ]);
  const finite=(n,fallback=0)=>Number.isFinite(n)?n:fallback;
  const point=v=>({x:finite(v?.x),y:finite(v?.y)});
  const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
  const active=a=>a && a.hp>0 && !a.dead;
  const identity=a=>a.id??(a.isPlayer?'player':null);
  const ratio=a=>Math.max(0,Math.min(1,finite(a.hp)/Math.max(1,finite(a.maxHp,1))));
  const clamp=(n,a,b)=>Math.min(b,Math.max(a,n));

  function dangerAt(position,actor,enemies,hazards){
    let risk=0;
    for(const enemy of enemies){
      const d=distance(position,enemy),r=finite(enemy.r,13)+finite(actor.r,12)+45;
      if(d<r)risk+=((r-d)/r)**2*180;
    }
    for(const hazard of hazards){
      if(hazard.active===false || hazard.life<=0)continue;
      const r=finite(hazard.r,40)+finite(actor.r,12)+15,d=distance(position,hazard);
      if(d<r)risk+=220+(r-d)*3;
    }
    return risk;
  }
  function blocked(position,obstacles,radius=12){
    return obstacles.some(o=>distance(position,o)<finite(o.r,16)+radius);
  }
  function steer(actor,goal,enemies,hazards,obstacles){
    const pos=point(actor),target=point(goal),d=distance(pos,target),step=clamp(finite(actor.speed,160)*.3,24,64);
    const heading=Math.atan2(target.y-pos.y,target.x-pos.x),riskWeight=ratio(actor)<.4?1.65:1;
    const candidates=[{x:0,y:0}];
    for(let i=0;i<16;i++)candidates.push({x:Math.cos(heading+i*Math.PI/8),y:Math.sin(heading+i*Math.PI/8)});
    let best=candidates[0],bestCost=Infinity;
    for(const axis of candidates){
      const dest={x:pos.x+axis.x*Math.min(d||step,step),y:pos.y+axis.y*Math.min(d||step,step)};
      const middle={x:(dest.x+pos.x)/2,y:(dest.y+pos.y)/2};
      if(blocked(dest,obstacles,finite(actor.r,12))||blocked(middle,obstacles,finite(actor.r,12)))continue;
      const cost=distance(dest,target)*.65+dangerAt(dest,actor,enemies,hazards)*riskWeight;
      if(cost<bestCost){bestCost=cost;best=axis;}
    }
    return {x:Math.abs(best.x)<1e-10?0:best.x,y:Math.abs(best.y)<1e-10?0:best.y};
  }

  /** Pure deterministic policy. Inputs are never mutated; no damage is fabricated. */
  function decideCompanion(actor,snapshot={}){
    const idle={move:{x:0,y:0},targetId:null,healId:null,reviveId:null,dash:false,reason:'idle'};
    if(!active(actor))return {...idle,reason:'down'};
    const player=snapshot.player||snapshot.leader;
    if(!player)return idle;
    const enemies=(snapshot.enemies||[]).filter(active);
    const allies=[{...player,id:identity(player)??'player'},...(snapshot.allies||[]).filter(a=>identity(a)!==identity(actor))];
    const hazards=snapshot.hazards||[],obstacles=snapshot.obstacles||[];
    const pos=point(actor),leader=point(player),range=Math.max(50,finite(actor.range,250)),role=actor.role||'ranger';
    let target=null,best=Infinity;
    for(const enemy of enemies){
      const local=distance(pos,enemy),leaderDistance=distance(leader,enemy);
      if(local>range*1.5)continue;
      const priority=local+(role==='guardian'?leaderDistance*.7:0)+(enemy.type==='boss'?-25:0);
      if(priority<best){target=enemy;best=priority;}
    }
    const result={...idle,move:{x:0,y:0},targetId:target&&distance(pos,target)<=range?identity(target):null,reason:'follow'};
    let goal=leader;
    const fallen=allies.filter(a=>(a.dead||a.hp<=0)&&a.revivable!==false).sort((a,b)=>distance(pos,a)-distance(pos,b))[0];
    const wounded=allies.filter(active).filter(a=>ratio(a)<.7).sort((a,b)=>ratio(a)-ratio(b)||distance(pos,a)-distance(pos,b))[0];
    if(role==='healer' && wounded && finite(actor.healCooldown,finite(actor.cooldowns?.heal))<=0 && distance(pos,wounded)<=220){
      result.healId=identity(wounded);result.reason='heal';
    }
    if(fallen && (role==='healer'||enemies.every(e=>distance(pos,e)>140))){
      goal=point(fallen);result.reason='revive';
      if(distance(pos,fallen)<=56)result.reviveId=identity(fallen);
    }else if(distance(pos,leader)>300){
      goal=leader;result.reason='regroup';
    }else if(target){
      const td=distance(pos,target),ideal=role==='guardian'?65:role==='healer'?180:220;
      const dx=(pos.x-target.x)/(td||1),dy=(pos.y-target.y)/(td||1);
      goal={x:target.x+dx*ideal,y:target.y+dy*ideal};result.reason=td<ideal*.75?'kite':'engage';
    }else{
      const slot=finite(actor.slot)%3,angle=-Math.PI/2+slot*Math.PI*2/3;
      goal={x:leader.x+Math.cos(angle)*75,y:leader.y+Math.sin(angle)*75};
    }
    result.move=steer(actor,goal,enemies,hazards,obstacles);
    const presentDanger=dangerAt(pos,actor,enemies,hazards);
    const landing={x:pos.x+result.move.x*130,y:pos.y+result.move.y*130};
    result.dash=finite(actor.dashCooldown,finite(actor.cooldowns?.dash))<=0 && presentDanger>100 && Math.hypot(result.move.x,result.move.y)>.1 && dangerAt(landing,actor,enemies,hazards)<presentDanger*.5 && !blocked(landing,obstacles,finite(actor.r,12));
    if(presentDanger>150 && !result.reviveId)result.reason='evade';
    return result;
  }
  function scoreUpgrade(actor,card){
    if(!card||typeof card.id!=='string')return -Infinity;
    const low=ratio(actor)<.5;
    const values={vitality:low?120:35,regen:low?100:40,power:60,haste:58,multishot:65,orbit:actor.role==='guardian'?75:50,nova:55,speed:42,magnet:15};
    return values[card.id]??20;
  }
  function chooseUpgrade(actor,legalChoices=[]){
    let best=null,score=-Infinity;
    for(const choice of legalChoices){const next=scoreUpgrade(actor,choice);if(next>score){score=next;best=choice;}}
    return best;
  }
  function normalize(text){return String(text??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase().replace(/[^a-z0-9\s]/g,' ').replace(/\s+/g,' ').trim().slice(0,500);}
  const SUGGESTIONS=['Tôi nên nâng cấp gì?','Cách đánh boss?','Đồng đội AI làm được gì?'];
  function chat(input,context={}){
    const text=normalize(input),run=context.run,player=run?.player||context.player;
    const response=(intent,answer,suggestions=SUGGESTIONS)=>({intent,text:answer,suggestions:[...suggestions],mode:'offline-rules'});
    if(!text)return response('help','Mình là hướng dẫn viên ngoại tuyến, trả lời theo kiến thức và tình huống trong game. Bạn có thể hỏi về nghề, nâng cấp, boss, đồng đội hoặc lưu game.');
    if(/(chatgpt|llm|mo hinh|tri tue|ai that|internet|ket noi|online)/.test(text))return response('capability','Chat này dùng bộ luật và kiến thức có sẵn trên máy, không phải mô hình ngôn ngữ lớn và không gửi dữ liệu ra mạng. Đồng đội AI cũng quyết định ngay trong game.');
    if(/(save|luu|sang may|doi may|du lieu|sao luu)/.test(text))return response('save','Tiến trình nằm trong bộ nhớ trình duyệt hoặc ứng dụng trên máy này. Dùng Xuất lưu để giữ tệp JSON, rồi Nhập lưu ở máy khác. Hãy sao lưu trước khi gỡ ứng dụng hoặc xóa dữ liệu.');
    if(/(dieu khien|di chuyen|phim|choi sao|cach choi)/.test(text))return response('controls','Di chuyển bằng WASD, phím mũi tên hoặc cần ảo. Nhân vật tự đánh khi quái trong tầm. Space hoặc nút Lướt dùng để né; Escape/P tạm dừng. Nhặt tinh thể để lên cấp rồi chọn một nâng cấp.');
    if(/(dong doi|dong hanh|bot|nguoi ban|npc|hoi sinh|cuu)/.test(text))return response('companions','Bảo Hộ áp sát để bảo vệ đội, Phong Tiễn giữ khoảng cách và Ánh Dương ưu tiên hồi máu. AI né vùng nguy hiểm, bám đội và có thể tiếp cận người bị hạ để cứu nếu luật trận cho phép. Chúng dùng máu, tầm đánh và hồi chiêu do engine quản lý, nên vẫn có thể bị đánh gục.');
    if(/(boss|thu linh|vua co thu)/.test(text)){
      const late=run?.bossSpawned?'Thủ lĩnh đang có mặt: hãy tập trung sát thương, tránh đứng trong vòng cảnh báo. ':'Khi thủ lĩnh xuất hiện, giữ khoảng trống để di chuyển. ';
      return response('boss',late+'Lướt ra ngoài vùng cảnh báo trước khi đòn nổ, giữ tầm đánh phù hợp với nghề và nhặt đủ nâng cấp sát thương trước trận boss.');
    }
    if(/(nghe|class|kiem si|cung thu|phap su|nhan vat)/.test(text))return response('classes','Kiếm sĩ chịu đòn tốt và đánh lan gần người; Cung thủ di chuyển nhanh và bắn xa; Pháp sư mạnh về sát thương vùng. Chọn nghề hợp cách di chuyển của bạn, rồi phối hợp nâng cấp để bù điểm yếu.');
    if(/(nang cap|nen chon|build|ky nang|suc manh)/.test(text)){
      const low=player&&ratio(player)<.45;
      return response('upgrades',low?'Máu hiện dưới 45%: ưu tiên Sức sống hoặc Mầm hồi phục nếu có trong ba lựa chọn. Sau đó thêm Vòng băng để tạo khoảng trống và nâng sát thương.':'Ưu tiên một nguồn sát thương chính, thêm Nhịp chiến đấu rồi kỹ năng bảo vệ như Vòng băng hoặc Vệ tinh lửa. Chỉ chọn trong các thẻ game đang đưa ra; không cần dàn đều mọi nhánh.');
    }
    if(/(mau|hoi phuc|sap chet|chet|kho qua|thua)/.test(text))return response('survival',player?`Bạn còn ${Math.max(0,Math.ceil(finite(player.hp)))} / ${Math.max(1,Math.ceil(finite(player.maxHp,1)))} máu. Đừng lao xuyên đám đông; vòng theo rìa, dành Lướt để thoát hiểm và ưu tiên hồi phục khi lên cấp.`:'Đi vòng quanh rìa bầy quái, tránh quay ngược vào chỗ vừa đi qua. Giữ Lướt để thoát vòng vây; Sức sống và Mầm hồi phục giúp lượt sau dễ thở hơn.');
    if(/(vang|ren luyen|tien|chi phi)/.test(text))return response('training',`Bạn có ${Math.max(0,Math.floor(finite(context.save?.gold)))} vàng. Rèn luyện tạo sức mạnh giữa các lượt; tăng thể lực nếu hay bị hạ, võ nghệ nếu thiếu sát thương. Trước khi mua hãy xem đúng giá và hiệu ứng trên màn hình.`);
    if(/(ban do|khu vuc|mo khoa|di dau)/.test(text))return response('maps','Chọn vùng đất đã mở trong màn chuẩn bị. Mỗi khu vực có yêu cầu mở khóa và độ khó riêng; xem ngay trên thẻ bản đồ trước khi xuất phát. Nếu vùng mới quá khó, quay lại vùng cũ để tích lũy.');
    if(/(trang bi|vat pham|the bai|the|che tao|ren do)/.test(text))return response('equipment','Hãy xem hiệu ứng cụ thể trong túi đồ hoặc màn quản lý thẻ/trang bị nếu bản đang chơi đã mở các hệ thống đó. Ưu tiên hiệu ứng hỗ trợ nghề và kỹ năng chính; hướng dẫn viên không tự tạo vật phẩm hay thay đổi chỉ số.');
    if(/(xin chao|chao|hello|hi$|cam on)/.test(text))return response('greeting','Chào nhà thám hiểm! Mình sẵn sàng hướng dẫn ngay cả khi máy không có mạng. Hỏi mình về nghề, nâng cấp, boss hoặc cách đưa save sang máy khác nhé.');
    return response('unknown','Mình chưa có câu trả lời phù hợp cho câu này. Đây là hướng dẫn viên dùng luật ngoại tuyến; thử hỏi ngắn về nghề, nâng cấp, boss, đồng đội AI, điều khiển hoặc lưu game.');
  }
  const api={COMPANIONS,decideCompanion,dangerAt,scoreUpgrade,chooseUpgrade,chat,normalize};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MidgardAI=api;
})(typeof globalThis!=='undefined'?globalThis:this);
