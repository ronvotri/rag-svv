/* Original offline campaign content. Pure transactions; no network or storage. */
(function(root){
  'use strict';
  const GEAR=[
    {id:'iron-sword',name:'Kiếm sắt',slot:'weapon',desc:'Lưỡi kiếm cân bằng cho người mới.',cost:{ore:12,essence:0},effects:{power:.08}},
    {id:'hunting-bow',name:'Cung săn',slot:'weapon',desc:'Cánh cung nhẹ giúp giữ nhịp di chuyển.',cost:{ore:16,essence:2},effects:{power:.06,speed:.04}},
    {id:'moon-staff',name:'Trượng nguyệt',slot:'weapon',desc:'Dòng phép dịu giúp hồi phục bền bỉ.',cost:{ore:20,essence:4},effects:{power:.1,regen:.2}},
    {id:'dawn-axe',name:'Rìu rạng đông',slot:'weapon',desc:'Vũ khí nặng dành cho trận đánh dài.',cost:{ore:40,essence:8},effects:{power:.15,hp:8}},
    {id:'traveler-coat',name:'Áo lữ hành',slot:'armor',desc:'Tấm áo đầu tiên trên đường phiêu lưu.',cost:{ore:10,essence:0},effects:{hp:12}},
    {id:'iron-mail',name:'Giáp mắt xích',slot:'armor',desc:'Tăng sức chịu đựng trước bầy quái.',cost:{ore:20,essence:2},effects:{hp:25}},
    {id:'wind-robe',name:'Áo gió',slot:'armor',desc:'Vải nhẹ và bùa gió giúp giữ khoảng cách.',cost:{ore:25,essence:4},effects:{hp:10,speed:.06}},
    {id:'dragon-mail',name:'Giáp long vảy',slot:'armor',desc:'Giáp rèn từ tinh chất cổ thụ.',cost:{ore:50,essence:12},effects:{hp:40,regen:.2}},
    {id:'amber-pendant',name:'Mặt dây hổ phách',slot:'charm',desc:'Một chút may mắn trên đường về.',cost:{ore:15,essence:2},effects:{fortune:.08}},
    {id:'wind-ring',name:'Nhẫn phong hành',slot:'charm',desc:'Bước chân nhẹ hơn giữa vòng vây.',cost:{ore:20,essence:4},effects:{speed:.06}},
    {id:'moon-talisman',name:'Bùa trăng',slot:'charm',desc:'Bồi đắp sinh lực theo thời gian.',cost:{ore:25,essence:6},effects:{regen:.35,hp:5}},
    {id:'dawn-crown',name:'Ấn rạng đông',slot:'charm',desc:'Biểu tượng chiến công trước thủ lĩnh.',cost:{ore:60,essence:15},effects:{power:.08,fortune:.1}}
  ];
  const CARDS=[
    {id:'sprout',name:'Mầm xanh',desc:'Sức sống nhỏ giữa hoang dã.',rarity:'common',effects:{hp:6}},
    {id:'slime',name:'Chất nhờn',desc:'Sức bền kiên trì qua từng lượt.',rarity:'common',effects:{regen:.12}},
    {id:'bat',name:'Cánh đêm',desc:'Giữ bước chân linh hoạt.',rarity:'common',effects:{speed:.025}},
    {id:'stone',name:'Thạch vệ',desc:'Thân thể vững như đá.',rarity:'common',effects:{hp:9}},
    {id:'ember',name:'Than hồng',desc:'Tập trung vào một đòn mạnh.',rarity:'common',effects:{power:.03}},
    {id:'dew',name:'Giọt sương',desc:'Hơi thở hồi phục dịu nhẹ.',rarity:'common',effects:{regen:.18}},
    {id:'falcon',name:'Ưng xanh',desc:'Tầm nhìn và bước chạy của thợ săn.',rarity:'rare',effects:{speed:.04,power:.02}},
    {id:'tortoise',name:'Huyền quy',desc:'Sống sót để tiếp tục cuộc chiến.',rarity:'rare',effects:{hp:15}},
    {id:'fox',name:'Hồ ly',desc:'May mắn thường đến với kẻ kiên nhẫn.',rarity:'rare',effects:{fortune:.06}},
    {id:'wisp',name:'Linh hỏa',desc:'Ngọn lửa nuôi dưỡng ý chí.',rarity:'rare',effects:{power:.05}},
    {id:'elder',name:'Cổ thụ',desc:'Phần thưởng của người hạ thủ lĩnh.',rarity:'epic',effects:{hp:14,regen:.18}},
    {id:'phoenix',name:'Phượng hỏa',desc:'Bình minh sau những lần gục ngã.',rarity:'epic',effects:{power:.06,fortune:.04}}
  ];
  const QUESTS=[
    {id:'first-run',name:'Bước chân đầu',desc:'Hoàn thành một lượt sinh tồn.',stat:'runs',target:1,reward:{ore:8,essence:1}},
    {id:'hundred-kills',name:'Người dọn đường',desc:'Hạ tổng cộng 100 quái.',stat:'kills',target:100,reward:{ore:15,essence:3}},
    {id:'three-wins',name:'Ba bình minh',desc:'Giành ba chiến thắng.',stat:'wins',target:3,reward:{ore:20,essence:5}},
    {id:'ten-minutes',name:'Bền bỉ',desc:'Tích lũy 10 phút trong đấu trường.',stat:'seconds',target:600,reward:{ore:15,essence:2}},
    {id:'craftsman',name:'Thợ rèn tập sự',desc:'Chế tạo ba trang bị.',stat:'crafted',target:3,reward:{ore:25,essence:4}},
    {id:'refiner',name:'Bàn tay tinh luyện',desc:'Tinh luyện tổng cộng năm lần.',stat:'refined',target:5,reward:{ore:30,essence:6}},
    {id:'boss-hunter',name:'Thợ săn thủ lĩnh',desc:'Hạ ba thủ lĩnh.',stat:'bosses',target:3,reward:{ore:25,essence:8}},
    {id:'tower-climber',name:'Bước lên tháp',desc:'Đạt tầng 5 trong Tháp vô tận.',stat:'towerBest',target:5,reward:{ore:35,essence:10}},
    {id:'new-life',name:'Khởi đầu khác',desc:'Tái sinh một lần.',stat:'rebirth',target:1,reward:{ore:40,essence:12}}
  ];
  const safeId=id=>typeof id==='string'&&/^[a-z0-9][a-z0-9_-]{0,63}$/i.test(id);
  const count=(n,max=1e9)=>Number.isSafeInteger(n)&&n>=0&&n<=max;
  const definition=(catalog,id)=>catalog.find(item=>item.id===id);
  const fail=message=>{throw new Error(message);};
  const createProfile=()=>({version:1,materials:{ore:0,essence:0},gear:{'iron-sword':0,'traveler-coat':0},equipment:{weapon:'iron-sword',armor:'traveler-coat',charm:null},cards:{sprout:{copies:1,rank:0}},cardSlots:['sprout'],stats:{runs:0,wins:0,kills:0,seconds:0,bosses:0,crafted:0,refined:0},rebirth:0,jobs:{},towerBest:0,claimedQuests:[],settledRuns:[]});
  function validateProfile(raw){
    if(!raw||raw.version!==1)fail('Bản lưu hành trình không đúng phiên bản.');
    const p=createProfile();
    for(const key of ['ore','essence']){if(!count(raw.materials?.[key]))fail('Nguyên liệu không hợp lệ.');p.materials[key]=raw.materials[key];}
    p.gear={};
    if(!raw.gear||Object.keys(raw.gear).length>GEAR.length)fail('Túi trang bị không hợp lệ.');
    for(const [id,level] of Object.entries(raw.gear)){if(!definition(GEAR,id)||!count(level,10))fail('Trang bị hoặc cấp tinh luyện không hợp lệ.');p.gear[id]=level;}
    p.equipment={};
    for(const slot of ['weapon','armor','charm']){const id=raw.equipment?.[slot];if(id!==null&&(!definition(GEAR,id)||definition(GEAR,id).slot!==slot||!Object.hasOwn(p.gear,id)))fail('Trang bị đang mặc không hợp lệ.');p.equipment[slot]=id;}
    p.cards={};
    if(!raw.cards||Object.keys(raw.cards).length>CARDS.length)fail('Bộ thẻ không hợp lệ.');
    for(const [id,c] of Object.entries(raw.cards)){if(!definition(CARDS,id)||!c||!count(c.copies,1e6)||c.copies<1||!count(c.rank,5))fail('Thẻ hoặc bậc thẻ không hợp lệ.');p.cards[id]={copies:c.copies,rank:c.rank};}
    if(!Array.isArray(raw.cardSlots)||raw.cardSlots.length>3||new Set(raw.cardSlots).size!==raw.cardSlots.length||raw.cardSlots.some(id=>!Object.hasOwn(p.cards,id)))fail('Ô thẻ không hợp lệ.');p.cardSlots=[...raw.cardSlots];
    for(const key of Object.keys(p.stats)){if(!count(raw.stats?.[key]))fail('Thống kê hành trình không hợp lệ.');p.stats[key]=raw.stats[key];}
    if(p.stats.wins>p.stats.runs||!count(raw.rebirth,10)||!count(raw.towerBest,10000))fail('Tiến trình không hợp lệ.');p.rebirth=raw.rebirth;p.towerBest=raw.towerBest;
    if(!Array.isArray(raw.claimedQuests)||raw.claimedQuests.length>QUESTS.length||new Set(raw.claimedQuests).size!==raw.claimedQuests.length||raw.claimedQuests.some(id=>!definition(QUESTS,id)))fail('Nhiệm vụ đã nhận không hợp lệ.');p.claimedQuests=[...raw.claimedQuests];
    if(!Array.isArray(raw.settledRuns)||raw.settledRuns.length>4096||new Set(raw.settledRuns).size!==raw.settledRuns.length||raw.settledRuns.some(id=>!safeId(id)))fail('Lịch sử lượt không hợp lệ.');p.settledRuns=[...raw.settledRuns];
    if(!raw.jobs||Object.keys(raw.jobs).length>64)fail('Tiến trình nghề không hợp lệ.');p.jobs={};
    for(const [id,j] of Object.entries(raw.jobs)){if(!safeId(id)||!j||!count(j.runs)||!count(j.wins)||j.wins>j.runs)fail('Thống kê nghề không hợp lệ.');p.jobs[id]={runs:j.runs,wins:j.wins};}
    return p;
  }
  function spend(p,price){for(const [id,n] of Object.entries(price))if(p.materials[id]<n)fail('Chưa đủ nguyên liệu.');for(const [id,n] of Object.entries(price))p.materials[id]-=n;}
  function grant(p,reward){for(const id of ['ore','essence'])p.materials[id]=Math.min(1e9,p.materials[id]+(reward[id]||0));}
  function craft(profile,id){const p=validateProfile(profile),item=definition(GEAR,id);if(!item)fail('Không có công thức này.');if(Object.hasOwn(p.gear,id))fail('Đã sở hữu trang bị này.');spend(p,item.cost);p.gear[id]=0;p.stats.crafted++;return p;}
  function equip(profile,id){const p=validateProfile(profile),item=definition(GEAR,id);if(!item||!Object.hasOwn(p.gear,id))fail('Bạn chưa sở hữu trang bị này.');p.equipment[item.slot]=id;return p;}
  const refineCost=level=>({ore:6+(Number.isInteger(level)?level:0)*5,essence:1+Math.floor((Number.isInteger(level)?level:0)/3)});
  function refine(profile,id){const p=validateProfile(profile);if(!Object.hasOwn(p.gear,id))fail('Bạn chưa sở hữu trang bị này.');if(p.gear[id]>=10)fail('Trang bị đã tinh luyện tối đa.');spend(p,refineCost(p.gear[id]));p.gear[id]++;p.stats.refined++;return p;}
  function equipCards(profile,ids){const p=validateProfile(profile);if(!Array.isArray(ids)||ids.length>3||new Set(ids).size!==ids.length||ids.some(id=>!Object.hasOwn(p.cards,id)))fail('Chỉ trang bị tối đa ba thẻ khác nhau đã sở hữu.');p.cardSlots=[...ids];return p;}
  function fuseCard(profile,id){const p=validateProfile(profile),card=p.cards[id];if(!card||card.copies<3)fail('Cần ba bản sao cùng thẻ để hợp nhất.');if(card.rank>=5)fail('Thẻ đã đạt bậc tối đa.');card.copies-=2;card.rank++;return p;}
  function questProgress(profile,quest){const q=typeof quest==='string'?definition(QUESTS,quest):quest;if(!q)fail('Nhiệm vụ không tồn tại.');const current=q.stat==='towerBest'?profile.towerBest:q.stat==='rebirth'?profile.rebirth:profile.stats[q.stat];return {current,target:q.target,complete:current>=q.target,claimed:profile.claimedQuests.includes(q.id)};}
  function claimQuest(profile,id){const p=validateProfile(profile),q=definition(QUESTS,id);if(!q)fail('Nhiệm vụ không tồn tại.');const progress=questProgress(p,q);if(progress.claimed)fail('Đã nhận thưởng nhiệm vụ này.');if(!progress.complete)fail('Chưa hoàn thành nhiệm vụ.');grant(p,q.reward);p.claimedQuests.push(id);return p;}
  const rebirthCost=profile=>({wins:3*(profile.rebirth+1),essence:10*(profile.rebirth+1)});
  function rebirth(profile){const p=validateProfile(profile),price=rebirthCost(p);if(p.rebirth>=10)fail('Đã đạt tái sinh tối đa.');if(p.stats.wins<price.wins)fail('Chưa đủ chiến thắng để tái sinh.');spend(p,{essence:price.essence});p.rebirth++;return p;}
  function jobRank(profile,id){const wins=profile.jobs[id]?.wins||0,level=wins>=10?3:wins>=3?2:wins>=1?1:0;return {level,name:['Tập sự','Chuyển nghề','Tinh anh','Bậc thầy'][level],wins,nextWins:[1,3,10,null][level]};}
  function bonuses(profile){const p=validateProfile(profile),result={hp:p.rebirth*10,power:p.rebirth*.05,speed:0,regen:0,fortune:0};const add=(effects,mult=1)=>{for(const [id,n]of Object.entries(effects))result[id]+=n*mult;};for(const id of Object.values(p.equipment))if(id)add(definition(GEAR,id).effects,1+p.gear[id]*.12);for(const id of p.cardSlots)add(definition(CARDS,id).effects,1+p.cards[id].rank*.3);return result;}
  function settle(profile,result){
    const p=validateProfile(profile);
    if(!result||!safeId(result.id)||!safeId(result.jobId)||!count(result.kills,1e7)||!Number.isFinite(result.time)||result.time<0||result.time>7200||typeof result.won!=='boolean')fail('Kết quả lượt chơi không hợp lệ.');
    if(p.settledRuns.includes(result.id))return p;
    p.settledRuns.push(result.id);if(p.settledRuns.length>4096)p.settledRuns.shift();
    p.stats.runs=Math.min(1e9,p.stats.runs+1);p.stats.wins=Math.min(1e9,p.stats.wins+(result.won?1:0));p.stats.kills=Math.min(1e9,p.stats.kills+result.kills);p.stats.seconds=Math.min(1e9,p.stats.seconds+Math.floor(result.time));p.stats.bosses=Math.min(1e9,p.stats.bosses+(result.won?1:0));
    const j=p.jobs[result.jobId]||{runs:0,wins:0};j.runs=Math.min(1e9,j.runs+1);j.wins=Math.min(1e9,j.wins+(result.won?1:0));p.jobs[result.jobId]=j;
    if(result.mode==='tower'&&count(result.towerFloor,10000))p.towerBest=Math.max(p.towerBest,result.towerFloor);
    grant(p,{ore:Math.floor(result.kills/8+result.time/60)+(result.won?8:0),essence:result.won?3:result.kills>=50?1:0});
    if(result.won||result.kills>=40){let hash=2166136261;for(const ch of result.id)hash=Math.imul(hash^ch.charCodeAt(0),16777619)>>>0;const pool=result.won?CARDS:CARDS.filter(c=>c.rarity==='common');const card=pool[hash%pool.length];if(p.cards[card.id])p.cards[card.id].copies=Math.min(1e6,p.cards[card.id].copies+1);else p.cards[card.id]={copies:1,rank:0};}
    return p;
  }
  const api={GEAR,CARDS,QUESTS,createProfile,validateProfile,settle,craft,equip,refine,refineCost,equipCards,fuseCard,questProgress,claimQuest,rebirth,rebirthCost,jobRank,bonuses};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MidgardCampaign=api;
})(typeof globalThis!=='undefined'?globalThis:this);
