// Beat graphics for video 006 (v2): Roy Sullivan, struck 7 times -- and why he lived.
// Readable area per pipeline/safe_area.json: x 110..970 (846 px centred lines) above y=1040, x 110..860 below it.
// Characters fill y 850..1700, so headlines live in y 300..560, captions at y=680, panels (blurred beats) at y 750..1300.
// QA v2: nothing readable under 34 px; tags sit on the word they illustrate; the strike counter's year matches the story.
const HEAD_Y=320, HEAD2_Y=405, SUB_Y=480;
const ELEC='#8FD3FF';
// 3D event times (scene seconds) from pipeline/blender/scene_struck.py, mapped through script.json bg_plan:
//   hook = H 0 (strike 1), truck = T 0 (strike 2 at 1.15), hair = H from 10.5 (strikes 3-6 at 10.75/11.45/12.10/12.70), bear = B 0 (strike 7 at 0.80)
const T_STRIKE1=1.15, HAIR_STRIKES=[10.75,11.45,12.10,12.70], H_HAIR0=10.5, B_STRIKE=0.80, B_BONK=5.55;
const YEARS=[1942,1969,1970,1972,1973,1976,1977];
function strikeTimes(){ const B=BEATS; return [B.hook.start, B.truck.start+T_STRIKE1, ...HAIR_STRIKES.map(x=>B.hair.start+x-H_HAIR0), B.bear.start+B_STRIKE]; }
function twoTone(parts,x,y,size,strokeW=12){ font(900,size); const ws=parts.map(p=>ctx.measureText(p[0]).width); const total=ws.reduce((a,b)=>a+b,0); let cx=x-total/2;
  parts.forEach((p,i)=>{ text(p[0],cx+ws[i]/2,y,{size,weight:900,color:p[1],strokeW}); cx+=ws[i]; }); }
function headline(lines,alpha,size=74,y0=HEAD_Y,gap=85){
  for(const line of lines){ if(!line) continue; font(900,size); const w=line.reduce((a,p)=>a+ctx.measureText(p[0]).width,0); if(w>830) size=Math.floor(size*830/w); }
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; lines.forEach((l,i)=>{ if(l) twoTone(l,W/2,y0+i*gap,size); }); ctx.restore(); }
function label(txt,x,y,alpha,{size=38,align='center',color=C.white}={}){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; text(txt,x,y,{size,weight:900,color,align,strokeW:9}); ctx.restore(); }
function tag(txt,x,y,t,t0,{bg='rgba(10,12,18,0.85)',fg=C.white,size=44,align='center',rot=0}={}){ if(t<t0) return; const k=t-t0, s=lerp(1.5,1,easeOutBack(k/0.25));
  ctx.save(); ctx.translate(x,y); ctx.rotate(rot); ctx.scale(s,s); ctx.globalAlpha=ctx.globalAlpha*smooth(0,0.08,k); pill(txt,0,0,{size,weight:900,padX:26,bg,fg,align}); ctx.restore(); }
// a run of tags on spoken words, each giving way to the next (no stacking)
// an item's trigger is a spoken word, or a number = seconds into the beat (to sit on a 3D event, e.g. the bolt, in step with the counter)
function tagRun(beat,t,items,y,out=1){ const at=w=>typeof w==='number'?BEATS[beat].start+w:wordTime(beat,w);
  items.forEach(([w,txt,opts],i)=>{ const t0=at(w); if(t<t0) return; const nx=i<items.length-1?at(items[i+1][0]):1e9;
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*(1-smooth(nx-0.12,nx-0.02,t))*out; tag(txt,W/2,y,t,t0,opts||{}); ctx.restore(); }); }
function bolt(x,y,s,alpha=1,color=C.yellow){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s);
  ctx.beginPath(); ctx.moveTo(8,-40); ctx.lineTo(-18,6); ctx.lineTo(0,6); ctx.lineTo(-8,40); ctx.lineTo(20,-8); ctx.lineTo(2,-8); ctx.lineTo(12,-40); ctx.closePath();
  ctx.lineWidth=6; ctx.strokeStyle='rgba(0,0,0,0.9)'; ctx.lineJoin='round'; ctx.stroke(); ctx.fillStyle=color; ctx.fill(); ctx.restore(); }
// strike counter, bottom-left (inside x 110..860 below y=1040); counts the story's strikes on the absolute timeline
function strikeCounter(t,alpha=1){ const ts=strikeTimes(); let n=0, last=-9; ts.forEach((x,i)=>{ if(t>=x-0.02){ n=i+1; last=x; } }); if(n===0||alpha<=0) return;
  const k=t-last, s=lerp(1.35,1,easeOutBack(k/0.25)); const x=130, y=1450;
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s);
  rr(0,-62,330,124,30); ctx.fillStyle='rgba(10,12,18,0.85)'; ctx.fill(); ctx.lineWidth=4; ctx.strokeStyle=k<0.3?C.yellow:'rgba(255,255,255,0.18)'; ctx.stroke();
  bolt(52,-4,1.05); text('×'+n,108,-2,{size:84,weight:900,color:n===7?C.yellow:C.white,align:'left',stroke:false,shadow:false});
  text(String(YEARS[n-1]),245,8,{size:38,weight:800,color:'rgba(255,255,255,0.8)',align:'left',stroke:false,shadow:false}); ctx.restore(); }
function darkPanel(x,y,w,h,alpha=1){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; rr(x,y,w,h,36); ctx.fillStyle='rgba(8,10,18,0.82)'; ctx.fill(); ctx.lineWidth=3; ctx.strokeStyle='rgba(143,211,255,0.25)'; ctx.stroke(); ctx.restore(); }
function person(x,y,s,color,alpha=1){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s); ctx.fillStyle=color;
  ctx.beginPath(); ctx.arc(0,-62,18,0,Math.PI*2); ctx.fill(); rr(-22,-40,44,56,16); ctx.fill(); rr(-20,10,17,52,8); ctx.fill(); rr(3,10,17,52,8); ctx.fill(); ctx.restore(); }
const outOf=(tb,b)=>1-smooth(b.duration-0.3,b.duration-0.05,tb);

// ---- hook: the claim on frame 0; on 'lived' an open loop for the ending (strike 7 + the bear)
function beatHook(tb,t,b){ const tL=wordTime('hook','lived');
  headline([[['STRUCK BY LIGHTNING',C.white]],[['7 TIMES',C.yellow],['.',C.white]]],1,80);
  if(t>tL) tag('…and #7 involved a bear 🐻',W/2,SUB_Y+70,t,tL,{bg:C.yellow,fg:'#111',size:46,rot:-0.04});
  strikeCounter(t); }

// ---- roy: who he is, then strike one in pieces: year, the leg burn, the hole in the shoe (close-up)
function beatRoy(tb,t,b){ const out=outOf(tb,b), a=smooth(0.05,0.3,tb)*out;
  headline([[['ROY SULLIVAN',C.white]]],a,76); label('PARK RANGER · SHENANDOAH, VIRGINIA',W/2,HEAD2_Y-5,a,{size:36,color:ELEC});
  tagRun('roy',t,[['strike','STRIKE 1 · 1942'],['burned','BURN DOWN HIS LEG'],['hole','HOLE IN HIS SHOE',{bg:C.orange}]],SUB_Y+70,out);
  strikeCounter(t,out); }

// ---- why: the physics, on Roy himself (slow motion)
function beatWhy(tb,t,b){ const out=outOf(tb,b);
  const tSp=wordTime('why','speed'), tM=wordTime('why','millionths'), tSk=wordTime('why','skims'), tF=wordTime('why','out');
  pill('SLOW-MO RE-ENACTMENT',130,1480,{size:36,weight:800,padX:24,align:'left',alpha:0.9*out});
  if(t<tSp) headline([[['HOW DID HE ',C.white],['LIVE?',C.yellow]]],smooth(0,0.2,tb)*(1-smooth(tSp-0.15,tSp,t)),84);
  if(t>tSp && t<tSk-0.1){ const a=smooth(tSp,tSp+0.15,t)*(1-smooth(tSk-0.4,tSk-0.1,t)); headline([[['SPEED.',C.yellow]]],a,96);
    if(t>tM){ const k=smooth(tM,tM+0.2,t); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k*a; darkPanel(230,430,620,150,1);
      text('0.00003 s',W/2,490,{size:72,weight:900,color:ELEC,stroke:false}); text('one current pulse',W/2,550,{size:38,weight:800,color:'rgba(255,255,255,0.85)',stroke:false}); ctx.restore(); } }
  if(t>tSk-0.1){ const a=smooth(tSk-0.1,tSk+0.15,t)*out; headline([[['FLASHOVER',ELEC]]],a,90);
    label('mostly OVER the skin, not through it',W/2,HEAD2_Y+20,a*(1-smooth(tF-0.25,tF,t)),{size:40});
    if(t>tF) tag('⚡ OUT THROUGH THE FEET',W/2,HEAD2_Y+40,t,tF,{bg:C.orange,size:46,rot:-0.04}); } }

// ---- truck: strike two through the open window, then why a closed car is safe
function beatTruck(tb,t,b){ const out=outOf(tb,b); const tW=wordTime('truck','windows');
  tagRun('truck',t,[[T_STRIKE1,'STRIKE 2 · 1969'],['took','EYEBROWS: GONE',{bg:C.orange}]],SUB_Y-120,1-smooth(tW-0.2,tW,t));
  if(t>=tW-0.05){ const k=smooth(tW-0.05,tW+0.2,t)*out; headline([[['WINDOWS UP',C.yellow],[' = SAFE',C.white]]],k,82);
    label('a hard-top car’s metal shell',W/2,HEAD2_Y+15,k,{size:40}); label('carries current AROUND you',W/2,HEAD2_Y+70,k,{size:40,color:ELEC}); }
  strikeCounter(t,out); }

// ---- hair: strikes 3-6 tick by; his fix was a can of water
function beatHair(tb,t,b){ const out=outOf(tb,b); const tF=wordTime('hair','fire'), tC=wordTime('hair','can');
  if(t>tF-0.1) headline([[['HAIR ON FIRE ',C.white],['AGAIN',C.orange]]],smooth(tF-0.1,tF+0.15,t)*out,80);
  if(t>tC) tag('💧 KEPT WATER HANDY',W/2,SUB_Y-20,t,tC,{size:46,rot:-0.03});
  strikeCounter(t,out); }

// ---- golf: name card, then his famous joke (it is a joke: holding a club up in a storm is a terrible idea)
function beatGolf(tb,t,b){ const out=outOf(tb,b); const tJ=wordTime('golf','joke'), tN=wordTime('golf','not'), tHit=wordTime('golf','hit');
  const a=smooth(0.1,0.35,tb)*(1-smooth(tJ-0.3,tJ,t));
  headline([[['LEE TREVINO',C.white]]],a,76); label('PRO GOLFER',W/2,HEAD2_Y-5,a,{size:38,color:ELEC});
  if(t>tHit && t<tJ) tag('⚡ 1975 WESTERN OPEN',W/2,SUB_Y+40,t,tHit,{size:44,rot:-0.03});
  if(t>tJ){ const k=smooth(tJ,tJ+0.25,t)*out; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k;
    darkPanel(130,250,820,300,1); text('“HOLD UP A 1-IRON.',W/2,335,{size:56,weight:900,color:C.white,stroke:false});
    if(t>tN){ ctx.globalAlpha=ctx.globalAlpha*smooth(tN,tN+0.2,t); text('NOT EVEN GOD',W/2,415,{size:60,weight:900,color:C.yellow,stroke:false}); text('CAN HIT A 1-IRON.”',W/2,485,{size:56,weight:900,color:C.yellow,stroke:false}); }
    ctx.restore(); label('— Lee Trevino (joking!)',850,590,k,{size:36,align:'right',color:'rgba(255,255,255,0.9)'}); } }

// ---- fern: the marks, named; they usually fade within a day (the 3D fern fades on 'fade')
function beatFern(tb,t,b){ const out=outOf(tb,b); const tL=wordTime('fern','lichtenberg'), tF=wordTime('fern','fade');
  headline([[['FERN-SHAPED MARKS',C.white]]],smooth(0.1,0.35,tb)*out*(1-smooth(tL-0.2,tL,t)),70);
  if(t>tL-0.1) headline([[['LICHTENBERG',C.yellow]],[['FIGURES',C.white]]],smooth(tL-0.1,tL+0.15,t)*out,86);
  if(t>tF) tag('⏱ USUALLY FADES WITHIN A DAY',W/2,SUB_Y+90,t,tF,{size:42}); }

// ---- heart: ECG flatlines on 'stopped', comes back after 'CPR'
function beatHeart(tb,t,b){ const out=outOf(tb,b); const tS=wordTime('heart','stopped'), tC=wordTime('heart','cpr');
  const a=smooth(0.05,0.35,tb)*out; const stopped=t>tS&&t<tC+0.3;
  headline([[['WHAT KILLS?',C.white]]],a,80);
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; darkPanel(130,750,820,290,1);
  const beat=!stopped?1+0.08*Math.max(0,Math.sin(t*9)):1;
  ctx.save(); ctx.translate(250,820); ctx.scale(beat*1.4,beat*1.5); ctx.fillStyle=stopped?'#666':C.red; ctx.beginPath(); ctx.moveTo(0,18); ctx.bezierCurveTo(-40,-8,-24,-40,0,-22); ctx.bezierCurveTo(24,-40,40,-8,0,18); ctx.fill(); ctx.restore();
  text(stopped?'CARDIAC ARREST':'HEART',W/2+70,820,{size:50,weight:900,color:stopped?C.red:C.white,stroke:false});
  ctx.strokeStyle=ELEC; ctx.lineWidth=6; ctx.lineJoin='round'; ctx.beginPath(); const x0=170, x1=910, yb=960;
  for(let x=x0;x<=x1;x+=4){ const tt=t-(x1-x)/700; let y=yb; const ph=(tt*1.6)%1;
    const alive=tt<tS||tt>tC+0.2; if(alive && tt>b.start-1){ if(ph>0.30&&ph<0.34) y=yb-80*Math.sin((ph-0.30)/0.04*Math.PI); else if(ph>0.34&&ph<0.37) y=yb+30*Math.sin((ph-0.34)/0.03*Math.PI); }
    if(x===x0) ctx.moveTo(x,y); else ctx.lineTo(x,y); }
  ctx.stroke(); ctx.restore();
  if(t>tC){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; tag('CPR SAVES LIVES ✓',490,1110,t,tC,{bg:C.green,fg:'#05210f',size:46}); ctx.restore(); } }

// ---- odds: per year, then 9 in 10 survive
function beatOdds(tb,t,b){ const out=outOf(tb,b); const tA=wordTime('odds','about'), tN=wordTime('odds','nine'), tSv=wordTime('odds','survive');
  headline([[['YOUR ODDS?',C.white]]],smooth(0.05,0.3,tb)*out,80);
  if(t>tA){ const k=smooth(tA,tA+0.2,t)*out; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; darkPanel(130,750,820,210,1);
    text('≈1 in 1.2 million',W/2,825,{size:76,weight:900,color:C.yellow,stroke:false}); text('per year · USA',W/2,905,{size:40,weight:800,color:'rgba(255,255,255,0.85)',stroke:false}); ctx.restore(); }
  if(t>tN-0.1){ const k=smooth(tN-0.1,tN+0.15,t)*out; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; darkPanel(130,985,720,290,1);
    for(let i=0;i<10;i++){ const x=185+i*67, dead=i===9; const up=dead?0:smooth(tSv+i*0.04,tSv+0.2+i*0.04,t);
      person(x,1140,0.95,dead?'rgba(150,150,160,0.8)':(up>0.5?C.green:'rgba(255,255,255,0.85)'),1); }
    text('9 in 10 people struck SURVIVE',490,1235,{size:38,weight:900,color:t>tSv?C.green:C.white,stroke:false}); ctx.restore(); }
  label('source: US National Weather Service',490,1320,smooth(tA,tA+0.3,t)*out,{size:34}); }

// ---- roymath: honest naive odds for 7 strikes, then the real reason (exposure)
function beatRoymath(tb,t,b){ const out=outOf(tb,b); const tO=wordTime('roymath','one'), tH=wordTime('roymath','he');
  headline([[['SO WHY ',C.white],['ROY?',C.yellow]]],smooth(0.05,0.3,tb)*out,84);
  if(t>tO && t<tH+0.1){ const k=smooth(tO,tO+0.2,t)*(1-smooth(tH-0.2,tH+0.1,t)); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; darkPanel(130,750,820,250,1);
    text('PURE LUCK: 1 in 10³³',W/2,840,{size:66,weight:900,color:C.yellow,stroke:false});
    text('naive math, average American',W/2,925,{size:38,weight:800,color:'rgba(255,255,255,0.85)',stroke:false}); ctx.restore(); }
  if(t>tH-0.1){ const k=smooth(tH-0.1,tH+0.15,t)*out; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; darkPanel(130,750,820,250,1);
    text('NOT LUCK. EXPOSURE.',W/2,835,{size:62,weight:900,color:C.yellow,stroke:false}); text('decades outdoors in storm country',W/2,920,{size:40,weight:800,color:C.white,stroke:false}); ctx.restore(); } }

// ---- bear: strike seven, then the bear (his story)
function beatBear(tb,t,b){ const out=outOf(tb,b); const tB=wordTime('bear','bear'), tS=b.start+B_BONK, tSays=wordTime('bear','says');   // BONK lands with the 3D hit
  tagRun('bear',t,[[B_STRIKE,'STRIKE 7 · 1977'],['hair','HAIR SMOKING 💨']],SUB_Y-120,1-smooth(tB-0.2,tB,t));
  if(t>tB-0.05) headline([[['A ',C.white],['BEAR',C.orange],['?!',C.white]]],smooth(tB-0.05,tB+0.15,t)*out*(1-smooth(tS-0.2,tS,t)),96);
  if(t>tS){ ctx.save(); const k=t-tS, s=lerp(1.45,1,easeOutBack(k/0.25)); ctx.translate(W/2,HEAD_Y+80);   // the pop stays below the top bar (y>250) ctx.rotate(-0.08); ctx.scale(s,s); ctx.globalAlpha=ctx.globalAlpha*out;
    text('BONK.',0,0,{size:120,weight:900,color:C.yellow,strokeW:16}); ctx.restore(); }
  if(t>tSays) label('(his story)',W/2,SUB_Y+70,smooth(tSays,tSays+0.2,t)*out,{size:36,color:'rgba(255,255,255,0.9)'});
  strikeCounter(t,out); }

// ---- cta: the comment question, then the safety line
function beatCta(tb,t,b){ const tW=wordTime('cta','when');
  headline([[['WOULD YOU GO',C.white]],[['FISHING WITH ',C.white],['ROY?',C.yellow]]],smooth(0.0,0.25,tb)*(1-smooth(tW-0.2,tW,t)),82);
  if(t>tW-0.1) headline([[['WHEN THUNDER ROARS,',C.white]],[['GO INDOORS',C.yellow]]],smooth(tW-0.1,tW+0.15,t),80);
  pill('comment 💬 · follow for more',W/2,SUB_Y+90,{size:38,weight:800,padX:30,alpha:smooth(0.6,0.9,tb)}); }

window.BEATS = {
  draw: {hook:beatHook, roy:beatRoy, why:beatWhy, truck:beatTruck, hair:beatHair, golf:beatGolf, fern:beatFern, heart:beatHeart, odds:beatOdds, roymath:beatRoymath, bear:beatBear, cta:beatCta},
  cutFlash: ['why','truck','hair','golf','fern','heart','roymath','bear'],
  keywords: ['lightning','seven','lived','1942','leg','shoe','speed','millionths','skims','skin','feet','truck','window','eyebrows','windows','metal','fire','water','1-iron','god','fern-shaped','lichtenberg','fade','day','heart','cpr','million','nine','survive','luck','thirty-three','decades','storm','bear','trout','stick','fishing','indoors'],
  caption: {y: 680, size: 66, keywordColor: '#FFB020', cutAtBeat: true},
  vignette: 0.3,
};
