// Beat graphics for video 006: people who were struck by lightning and lived.
// Readable area per pipeline/safe_area.json: x 110..970 (846 px centred lines) above y=1040, x 110..860 below it.
// Characters stand in the middle/lower half of the frame, so headlines live in the band y 300..520 and captions at y=860.
const HEAD_Y=320, HEAD2_Y=405, SUB_Y=480;
const ELEC='#8FD3FF';
// 3D event times (scene seconds) from pipeline/blender/scene_struck.py; the roy/roymath beats show shot H from 3.25 s (frame 78)
const H_STRIKES=[0.0,3.62,4.55,5.78,6.72,7.36,8.30], H_ROY0=78/24;
const YEARS=[1942,1969,1970,1972,1973,1976,1977];
function fadeInOut(tb,b,inAt=0,inDur=0.25,outPad=0.3){return smooth(inAt,inAt+inDur,tb)*(1-smooth(b.duration-outPad,b.duration-0.05,tb))}
function twoTone(parts,x,y,size,strokeW=12){ font(900,size); const ws=parts.map(p=>ctx.measureText(p[0]).width); const total=ws.reduce((a,b)=>a+b,0); let cx=x-total/2;
  parts.forEach((p,i)=>{ text(p[0],cx+ws[i]/2,y,{size,weight:900,color:p[1],strokeW}); cx+=ws[i]; }); }
function headline(lines,alpha,size=74,y0=HEAD_Y,gap=85){
  for(const line of lines){ if(!line) continue; font(900,size); const w=line.reduce((a,p)=>a+ctx.measureText(p[0]).width,0); if(w>830) size=Math.floor(size*830/w); }
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; lines.forEach((l,i)=>{ if(l) twoTone(l,W/2,y0+i*gap,size); }); ctx.restore(); }
function popIn(t,t0,dur=0.22){ return t<t0?0:easeOutBack((t-t0)/dur); }
function label(txt,x,y,alpha,{size=36,align='center',color=C.white}={}){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; text(txt,x,y,{size,weight:900,color,align,strokeW:9}); ctx.restore(); }
function tag(txt,x,y,t,t0,{bg='rgba(10,12,18,0.82)',fg=C.white,size=38,align='center',rot=0}={}){ if(t<t0) return; const k=t-t0, s=lerp(1.5,1,easeOutBack(k/0.25));
  ctx.save(); ctx.translate(x,y); ctx.rotate(rot); ctx.scale(s,s); ctx.globalAlpha=ctx.globalAlpha*smooth(0,0.08,k); pill(txt,0,0,{size,weight:900,padX:26,bg,fg,align}); ctx.restore(); }
function bolt(x,y,s,alpha=1,color=C.yellow){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s);
  ctx.beginPath(); ctx.moveTo(8,-40); ctx.lineTo(-18,6); ctx.lineTo(0,6); ctx.lineTo(-8,40); ctx.lineTo(20,-8); ctx.lineTo(2,-8); ctx.lineTo(12,-40); ctx.closePath();
  ctx.lineWidth=6; ctx.strokeStyle='rgba(0,0,0,0.9)'; ctx.lineJoin='round'; ctx.stroke(); ctx.fillStyle=color; ctx.fill(); ctx.restore(); }
// strike counter, bottom-left (inside x 110..860 below y=1040)
function strikeCounter(t,times,alpha){ let n=0, last=-9; times.forEach((ts,i)=>{ if(t>=ts-0.02){ n=i+1; last=ts; } }); if(n===0) return;
  const k=t-last, s=lerp(1.35,1,easeOutBack(k/0.25)); const x=130, y=1450;
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s);
  rr(0,-62,330,124,30); ctx.fillStyle='rgba(10,12,18,0.85)'; ctx.fill(); ctx.lineWidth=4; ctx.strokeStyle=k<0.3?C.yellow:'rgba(255,255,255,0.18)'; ctx.stroke();
  bolt(52,-4,1.05); text('×'+n,108,-2,{size:84,weight:900,color:n===7?C.yellow:C.white,align:'left',stroke:false,shadow:false});
  text(String(YEARS[n-1]),245,8,{size:38,weight:800,color:'rgba(255,255,255,0.75)',align:'left',stroke:false,shadow:false}); ctx.restore(); }
function darkPanel(x,y,w,h,alpha=1){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; rr(x,y,w,h,36); ctx.fillStyle='rgba(8,10,18,0.80)'; ctx.fill(); ctx.lineWidth=3; ctx.strokeStyle='rgba(143,211,255,0.25)'; ctx.stroke(); ctx.restore(); }
function arrow(x0,y0,x1,y1,alpha,color=C.yellow,w=8){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.strokeStyle=color; ctx.fillStyle=color; ctx.lineWidth=w; ctx.lineCap='round';
  ctx.shadowColor='rgba(0,0,0,0.6)'; ctx.shadowBlur=8; ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x1,y1); ctx.stroke();
  const a=Math.atan2(y1-y0,x1-x0); ctx.beginPath(); ctx.moveTo(x1+Math.cos(a)*10,y1+Math.sin(a)*10); ctx.lineTo(x1-Math.cos(a-0.5)*30,y1-Math.sin(a-0.5)*30); ctx.lineTo(x1-Math.cos(a+0.5)*30,y1-Math.sin(a+0.5)*30); ctx.closePath(); ctx.fill(); ctx.restore(); }
function person(x,y,s,color,alpha=1,down=false){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s); ctx.fillStyle=color;
  if(down){ ctx.rotate(Math.PI/2); ctx.translate(30,-20); }
  ctx.beginPath(); ctx.arc(0,-62,18,0,Math.PI*2); ctx.fill(); rr(-22,-40,44,56,16); ctx.fill(); rr(-20,10,17,52,8); ctx.fill(); rr(3,10,17,52,8); ctx.fill(); ctx.restore(); }

// ---- hook: the claim on frame 0, strike counter from frame 0
function beatHook(tb,t,b){ const tL=wordTime('hook','lived');
  headline([[['STRUCK BY LIGHTNING',C.white]],[['7 TIMES',C.yellow],['.',C.white]]],1,80);
  if(t>tL){ ctx.save(); const s=lerp(1.6,1,easeOutBack((t-tL)/0.25)); ctx.translate(W/2,SUB_Y+40); ctx.scale(s,s); ctx.rotate(-0.05); pill('AND LIVED.',0,0,{size:56,weight:900,padX:34,bg:C.yellow,fg:'#111'}); ctx.restore(); }
  strikeCounter(tb,[0],1); }

// ---- roy: name card, the counter runs to 7 in sync with the footage, injury tags on their words
function beatRoy(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb);
  const a=smooth(0.05,0.3,tb)*out;
  headline([[['ROY SULLIVAN',C.white]]],a,76); label('PARK RANGER · VIRGINIA',W/2,HEAD2_Y-5,a,{size:38,color:ELEC});
  const ts=H_STRIKES.map(x=>b.start+(x-H_ROY0)); strikeCounter(t,ts.map((x,i)=>i===0?b.start-5:x),out);
  const tags=[['eyebrows','EYEBROWS: GONE',-0.05],['fire','HAIR ON FIRE 🔥',0.04],['twice','…TWICE',-0.04],['hole','HOLE IN HIS SHOE',0.05]];
  tags.forEach(([w,txt,rot],i)=>{ const t0=wordTime('roy',w); if(t<t0) return; const nx=i<3?wordTime('roy',tags[i+1][0]):1e9; const al=(1-smooth(nx-0.12,nx-0.02,t));   // each tag gives way to the next
    ctx.save(); ctx.globalAlpha=ctx.globalAlpha*al*out; tag(txt,W/2,SUB_Y+60,t,t0,{bg:i===1||i===2?C.orange:'rgba(10,12,18,0.85)',size:46,rot}); ctx.restore(); });
  if(tb>b.duration-1.0) { /* hand-off */ } }

// ---- golf: name card, then the quote as a stamped card
function beatGolf(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tA=wordTime('golf','advice'), tN=wordTime('golf','not'), tHit=wordTime('golf','hit');
  const a=smooth(0.1,0.35,tb)*(1-smooth(tA-0.3,tA,t));
  headline([[['LEE TREVINO',C.white]]],a,76); label('PRO GOLFER · 1975',W/2,HEAD2_Y-5,a,{size:38,color:ELEC});
  if(t>tHit && t<tA) tag('⚡ HIT AT A TOURNAMENT',W/2,SUB_Y+60,t,tHit,{size:40,rot:-0.03});
  if(t>tA){ const k=smooth(tA,tA+0.25,t)*out; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k;
    darkPanel(130,250,820,300,1); text('“HOLD UP A 1-IRON.',W/2,335,{size:56,weight:900,color:C.white,stroke:false});
    if(t>tN){ ctx.globalAlpha=ctx.globalAlpha*smooth(tN,tN+0.2,t); text('NOT EVEN GOD',W/2,415,{size:60,weight:900,color:C.yellow,stroke:false}); text('CAN HIT A 1-IRON.”',W/2,485,{size:56,weight:900,color:C.yellow,stroke:false}); }
    ctx.restore(); }
  if(t>tA) label('— Lee Trevino',780,590,smooth(tA,tA+0.3,t)*out,{size:32,align:'right',color:'rgba(255,255,255,0.85)'}); }

// ---- how: one big question
function beatHow(tb,t,b){ const tS=wordTime('how','survive'); const k=popIn(t,b.start+0.1);
  ctx.save(); ctx.translate(W/2,HEAD_Y+40); ctx.scale(k,k); text('SO HOW DO',0,-50,{size:70,weight:900}); text('PEOPLE SURVIVE?',0,40,{size:84,weight:900,color:t>tS?C.yellow:C.white,strokeW:14}); ctx.restore(); }

// ---- flash: speed (timer), flashover over the skin, shoes off
function beatFlash(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb);
  const tSp=wordTime('flash','speed'), tM=wordTime('flash','millionths'), tSk=wordTime('flash','skims'), tSh=wordTime('flash','shoes');
  pill('EXTREME SLOW MOTION',130,1480,{size:30,weight:800,padX:22,align:'left',alpha:0.9*out});
  if(t>tSp && t<tSk-0.1){ const a=smooth(tSp,tSp+0.15,t)*(1-smooth(tSk-0.4,tSk-0.1,t)); headline([[['SPEED.',C.yellow]]],a,96);
    if(t>tM){ const k=smooth(tM,tM+0.2,t); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k*a; darkPanel(270,450,540,130,1);
      text('0.00003 s',W/2,505,{size:70,weight:900,color:ELEC,stroke:false}); text('one strike pulse',W/2,560,{size:28,weight:700,color:'rgba(255,255,255,0.7)',stroke:false}); ctx.restore(); } }
  if(t>tSk-0.1){ const a=smooth(tSk-0.1,tSk+0.15,t)*out; headline([[['FLASHOVER',ELEC]]],a,90);
    label('current skims OVER the skin',W/2,HEAD2_Y+20,a*(1-smooth(tSh-0.3,tSh,t)),{size:40});
    label('not through you',W/2,HEAD2_Y+75,a*(1-smooth(tSh-0.3,tSh,t)),{size:40,color:C.yellow}); }
  if(t>tSh) tag('👟 BLOWN OFF',W/2,HEAD2_Y+50,t,tSh,{bg:C.orange,size:52,rot:-0.05}); }

// ---- ground: how strikes actually reach people, then the leg path labels
function beatGround(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb);
  const tD=wordTime('ground','directly'), tC=wordTime('ground','current'), tU=wordTime('ground','up'), tDn=wordTime('ground','down');
  const a=smooth(0.1,0.35,tb)*out;
  headline([[['NOT A ',C.white],['DIRECT HIT',C.yellow]]],a*(1-smooth(tC-0.25,tC,t)),74);
  if(t>tD && t<tC) tag('only ~5% of cases',W/2,SUB_Y-30,t,tD,{size:42});
  if(t>tC-0.1){ const k=smooth(tC-0.1,tC+0.15,t)*out; headline([[['GROUND CURRENT',ELEC]]],k,80); label('the most common way people get hit',W/2,HEAD2_Y,k,{size:36}); }
  if(t>tU){ const k=smooth(tU,tU+0.2,t)*out; arrow(330,1420,450,1250,k,C.yellow); label('UP ONE LEG',300,1470,k,{size:42,color:C.yellow}); }
  if(t>tDn){ const k=smooth(tDn,tDn+0.2,t)*out; arrow(700,1180,770,1360,k,ELEC); label('DOWN THE OTHER',640,1430,k,{size:42,color:ELEC}); } }

// ---- fern: name it, then 'fades in days'
function beatFern(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tL=wordTime('fern','lichtenberg'), tF=wordTime('fern','fade');
  const a=smooth(0.1,0.35,tb)*out; headline([[['FERN-SHAPED SCARS',C.white]]],a*(1-smooth(tL-0.2,tL,t)),70);
  if(t>tL-0.1){ const k=smooth(tL-0.1,tL+0.15,t)*out; headline([[['LICHTENBERG',C.yellow]],[['FIGURES',C.white]]],k,86); }
  if(t>tF){ const d=Math.min(3,1+Math.floor((t-tF)/0.45)); tag(`FADES IN DAYS · DAY ${d}`,W/2,SUB_Y+90,t,tF,{size:42}); } }

// ---- heart: dark panel with an ECG trace that flatlines and comes back with CPR; then the safety line
function beatHeart(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tK=wordTime('heart','kills'), tS=wordTime('heart','stopped'), tC=wordTime('heart','cpr'), tW=wordTime('heart','when');
  const a=smooth(0.05,0.35,tb)*out*(1-smooth(tW-0.3,tW,t));
  headline([[['WHAT KILLS?',C.white]]],a,80);
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; darkPanel(130,750,820,290,1);
  // heart icon
  const beat=t<tS?1+0.08*Math.max(0,Math.sin(t*9)):(t>tC+0.3?1+0.08*Math.max(0,Math.sin(t*9)):1);
  ctx.save(); ctx.translate(250,820); ctx.scale(beat*1.4,beat*1.5); ctx.fillStyle=(t>tS&&t<tC+0.3)?'#666':C.red; ctx.beginPath(); ctx.moveTo(0,18); ctx.bezierCurveTo(-40,-8,-24,-40,0,-22); ctx.bezierCurveTo(24,-40,40,-8,0,18); ctx.fill(); ctx.restore();
  text(t>tS&&t<tC+0.3?'HEART STOPS':'HEART',W/2+70,820,{size:52,weight:900,color:t>tS&&t<tC+0.3?C.red:C.white,stroke:false});
  // ECG: beats, flat after 'stopped', beats again after 'CPR'
  ctx.strokeStyle=ELEC; ctx.lineWidth=6; ctx.lineJoin='round'; ctx.beginPath(); const x0=170, x1=910, yb=960;
  for(let x=x0;x<=x1;x+=4){ const tt=t-(x1-x)/700; let y=yb; const ph=(tt*1.6)%1;
    const alive=tt<tS||tt>tC+0.2; if(alive && tt>b.start-1){ if(ph>0.30&&ph<0.34) y=yb-80*Math.sin((ph-0.30)/0.04*Math.PI); else if(ph>0.34&&ph<0.37) y=yb+30*Math.sin((ph-0.34)/0.03*Math.PI); }
    if(x===x0) ctx.moveTo(x,y); else ctx.lineTo(x,y); }
  ctx.stroke(); ctx.restore();
  if(t>tC){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; tag('CPR SAVES LIVES ✓',490,1110,t,tC,{bg:C.green,fg:'#05210f',size:46}); ctx.restore(); }
  if(t>tW-0.1){ const k=smooth(tW-0.1,tW+0.15,t)*out; headline([[['WHEN THUNDER ROARS,',C.white]],[['GO INDOORS',C.yellow]]],k,78,HEAD_Y+60,95); } }

// ---- odds: per year, then 9 in 10 survive (ten figures, nine stand up)
function beatOdds(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tA=wordTime('odds','about'), tN=wordTime('odds','nine'), tSv=wordTime('odds','survive');
  headline([[['YOUR ODDS?',C.white]]],smooth(0.05,0.3,tb)*out,80);
  if(t>tA){ const k=smooth(tA,tA+0.2,t)*out; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; darkPanel(130,750,820,210,1);
    text('1 in 1,222,000',W/2,825,{size:76,weight:900,color:C.yellow,stroke:false}); text('chance of being struck in a given year (US)',W/2,905,{size:30,weight:700,color:'rgba(255,255,255,0.8)',stroke:false}); ctx.restore(); }
  if(t>tN-0.1){ const k=smooth(tN-0.1,tN+0.15,t)*out; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; darkPanel(130,985,720,290,1);
    for(let i=0;i<10;i++){ const x=185+i*67, dead=i===9; const up=dead?0:smooth(tSv+i*0.04,tSv+0.2+i*0.04,t);
      person(x,1140,0.95,dead?'rgba(150,150,160,0.8)':(up>0.5?C.green:'rgba(255,255,255,0.85)'),1); }
    text('9 in 10 people struck SURVIVE',490,1235,{size:38,weight:900,color:t>tSv?C.green:C.white,stroke:false}); ctx.restore(); }
  label('source: US National Weather Service',490,1310,smooth(tA,tA+0.3,t)*out*0.9,{size:26}); }

// ---- roymath: naive odds for 7 strikes, then why it isn't luck
function beatRoymath(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tO=wordTime('roymath','one'), tR=wordTime('roymath','roy');
  headline([[['7 STRIKES BY ',C.white],['PURE LUCK?',C.yellow]]],smooth(0.05,0.3,tb)*out,72);
  if(t>tO){ const k=smooth(tO,tO+0.2,t)*out*(1-smooth(tR-0.2,tR+0.1,t)); const z=Math.min(29,Math.floor((t-tO)*30));
    ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; darkPanel(130,750,820,250,1);
    font(900,60); text('1 in 1'+'0'.repeat(Math.min(z,12))+(z>12?'…':''),W/2,830,{size:60,weight:900,color:C.yellow,stroke:false});
    text(z>=29?'= 1 in 10²⁹ (29 zeros!)':'',W/2,920,{size:44,weight:900,color:C.white,stroke:false});
    text('(1 in 15,300 lifetime odds, seven times)',W/2,970,{size:26,weight:700,color:'rgba(255,255,255,0.7)',stroke:false}); ctx.restore(); }
  if(t>tR-0.1){ const k=smooth(tR-0.1,tR+0.15,t)*out; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; darkPanel(130,750,820,250,1);
    text('NOT LUCK. EXPOSURE.',W/2,830,{size:58,weight:900,color:C.yellow,stroke:false}); text('35 years outdoors on the Blue Ridge',W/2,910,{size:36,weight:800,color:C.white,stroke:false}); ctx.restore(); }
  strikeCounter(t,H_STRIKES.map((x,i)=>i===0?b.start-5:b.start+(x-H_ROY0)),out); }

// ---- cta: the comment question
function beatCta(tb,t,b){ const tF=wordTime('cta','follow');
  headline([[['WOULD YOU GOLF',C.white]],[['IN A ',C.white],['STORM?',C.yellow]]],smooth(0.0,0.25,tb),82);
  if(t>tF){ const a=smooth(tF,tF+0.25,t); pill('comment ↓',W/2,SUB_Y+70,{size:40,weight:800,padX:30,alpha:a}); label('follow for more',W/2,SUB_Y+150,a*0.9,{size:32}); } }

window.BEATS = {
  draw: {hook:beatHook, roy:beatRoy, golf:beatGolf, how:beatHow, flash:beatFlash, ground:beatGround, fern:beatFern, heart:beatHeart, odds:beatOdds, roymath:beatRoymath, cta:beatCta},
  cutFlash: ['golf','how','ground','fern','heart','roymath','cta'],
  keywords: ['lightning','seven','lived','eyebrows','fire','twice','shoe','one-iron','god','survive','speed','millionths','skims','skin','shoes','directly','ground','leg','other','fern-shaped','lichtenberg','fade','heart','cpr','indoors','million','nine','luck','mountaintops','storm'],
  caption: {y: 680, size: 66, keywordColor: '#FFB020'},
  vignette: 0.3,
};
