// Beat graphics for video 006: how a forest is born (120-year succession timelapse on a cut-open block of land).
// Bright daylight set: white type with the black stroke, yellow accent, one green accent for "alive" labels,
// cream explainer panel. The YEAR counter is the spine of the video and is on screen in every frame; it reads the
// same year curve as the Blender scene (script.json "years" per beat, linear inside a beat, quintic rewind in ask+loop).
const COUNT_Y=330, RULER_Y=412, HEAD_Y=500, HEAD2_Y=582, CAP_Y=1430, TAG_Y=1290;
const INK='#1C1A22', CREAM='rgba(255,250,242,0.94)', LEAF='#3DDC84';
function smoother(u){u=clamp(u,0,1);return u*u*u*(u*(u*6-15)+10)}
function yearAt(t){ // mirror of scene_forest.py year_at(): the on-screen counter must match the footage
  const Y=(window.SCRIPT&&window.SCRIPT.years)||{}; const bs=TL.beats;
  for(let i=0;i<bs.length;i++){ const b=bs[i]; if(t<b.end||i===bs.length-1){ const yr=Y[b.id]||[0,0];
    if(b.id==='ask'){ const T1=BEATS.loop.end; return yr[0]*(1-smoother((t-b.start)/(T1-b.start))); }
    if(b.id==='loop') return 0;
    return yr[0]+(yr[1]-yr[0])*clamp((t-b.start)/b.duration,0,1); } }
  return 0; }
function fadeInOut(tb,b,inAt=0,inDur=0.25,outPad=0.3){return smooth(inAt,inAt+inDur,tb)*(1-smooth(b.duration-outPad,b.duration-0.05,tb))}
function twoTone(parts,x,y,size,strokeW=12){ font(900,size); const ws=parts.map(p=>ctx.measureText(p[0]).width); const total=ws.reduce((a,b)=>a+b,0); let cx=x-total/2;
  parts.forEach((p,i)=>{ text(p[0],cx+ws[i]/2,y,{size,weight:900,color:p[1],strokeW}); cx+=ws[i]; }); }
function headline(parts,alpha,size=72){ // fitted to the 846 px readable width above y=1040
  for(const line of parts){ if(!line) continue; font(900,size); const w=line.reduce((a,p)=>a+ctx.measureText(p[0]).width,0); if(w>846) size=Math.floor(size*846/w); }
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; twoTone(parts[0],W/2,HEAD_Y,size); if(parts[1]) twoTone(parts[1],W/2,HEAD2_Y,size); ctx.restore(); }
function lightPanel(x,y,w,h,alpha=1){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.shadowColor='rgba(0,0,0,0.25)'; ctx.shadowBlur=30; ctx.shadowOffsetY=10; rr(x,y,w,h,36); ctx.fillStyle=CREAM; ctx.fill();
  ctx.shadowColor='transparent'; ctx.lineWidth=3; ctx.strokeStyle='rgba(28,26,34,0.12)'; ctx.stroke(); ctx.restore(); }
function inkText(str,x,y,{size=40,weight=800,align='center',alpha=1,color=INK}={}){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; text(str,x,y,{size,weight,color,align,stroke:false,shadow:false}); ctx.restore(); }
// stage tag, bottom-left (x 120, inside the readable area; never bottom-right)
function stageTag(label,t0,t,{color=C.yellow,out=1,sub=null}={}){ if(t<t0) return; const k=t-t0; const a=smooth(0,0.2,k)*out; const s=lerp(0.9,1,easeOutBack(k/0.25));
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.translate(120,TAG_Y); ctx.scale(s,s); pill(label,0,0,{size:40,weight:900,padX:28,align:'left',bg:'rgba(10,12,18,0.80)',fg:color});
  if(sub) pill(sub,0,74,{size:30,weight:800,padX:22,align:'left',bg:'rgba(10,12,18,0.65)',fg:C.white}); ctx.restore(); }
function stamp2(label,x,y,t0,t,{color=C.red,size=64,rot=-0.1}={}){ const k=t-t0; if(k<0)return; const s=lerp(1.6,1,easeOutBack(k/0.28)); const a=smooth(0,0.08,k);
  ctx.save(); ctx.translate(x,y); ctx.rotate(rot); ctx.scale(s,s); ctx.globalAlpha=ctx.globalAlpha*a; font(900,size); const w=ctx.measureText(label).width+60, h=size*1.4;
  rr(-w/2,-h/2,w,h,20); ctx.lineWidth=10; ctx.strokeStyle=color; ctx.stroke(); ctx.fillStyle='rgba(8,10,16,0.55)'; ctx.fill();
  ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillStyle=color; ctx.fillText(label,0,size*0.06); ctx.restore(); if(k<0.3) flash(t,t0,{dur:0.16,peak:0.18}); }

// ---------------------------------------------------------------- the year counter + ruler (every frame)
const STAGES=[[0,'dirt'],[1.5,'weeds'],[4.5,'grass'],[12,'shrubs'],[25,'pioneers'],[60,'climax'],[120,'forest']];
function counter(t){ const Y=yearAt(t); const rewind=t>=BEATS.ask.start-0.001; const yi=Math.floor(Y+1e-6);
  // "YEAR 37" with tabular numerals; pops a little on each integer change
  const frac=Y-yi; const pop=rewind?1:(1+0.05*(1-smooth(0,0.35,frac)));
  ctx.save(); ctx.translate(W/2,COUNT_Y); ctx.scale(pop,pop); font(900,96); ctx.fontVariantNumeric='tabular-nums';
  const lab='YEAR '; const num=String(yi); const wl=ctx.measureText(lab).width, wn=ctx.measureText(num).width; const x0=-(wl+wn)/2;
  text(lab,x0+wl/2,0,{size:96,weight:900,strokeW:16}); text(num,x0+wl+wn/2,0,{size:96,weight:900,color:C.yellow,strokeW:16}); ctx.restore();
  if(rewind){ pill('◀◀ REWIND',120,COUNT_Y,{size:26,weight:900,padX:18,align:'left',bg:'rgba(255,214,10,0.95)',fg:INK,alpha:smooth(0,0.3,t-BEATS.ask.start)}); }   // left of the counter (whose left edge is ~x 330)
  // ruler 0..120 with stage ticks; the readable band is x 110..970
  const x0r=150,x1r=930; ctx.save(); ctx.lineCap='round'; ctx.shadowColor='rgba(0,0,0,0.6)'; ctx.shadowBlur=8;
  ctx.strokeStyle='rgba(255,255,255,0.55)'; ctx.lineWidth=6; ctx.beginPath(); ctx.moveTo(x0r,RULER_Y); ctx.lineTo(x1r,RULER_Y); ctx.stroke();
  const xx=lerp(x0r,x1r,clamp(Y/120,0,1)); ctx.strokeStyle=C.yellow; ctx.lineWidth=8; ctx.beginPath(); ctx.moveTo(x0r,RULER_Y); ctx.lineTo(xx,RULER_Y); ctx.stroke();
  for(const [y,n] of STAGES){ const x=lerp(x0r,x1r,y/120); ctx.fillStyle=Y>=y?C.yellow:'rgba(255,255,255,0.7)'; ctx.beginPath(); ctx.arc(x,RULER_Y,Y>=y?9:6,0,Math.PI*2); ctx.fill(); }
  ctx.fillStyle=C.white; ctx.beginPath(); ctx.arc(xx,RULER_Y,15,0,Math.PI*2); ctx.fill(); ctx.restore();
  text('0',x0r,RULER_Y+38,{size:24,weight:800,strokeW:6}); text('120 YEARS',x1r,RULER_Y+38,{size:24,weight:800,strokeW:6,align:'right'}); }

// ---------------------------------------------------------------- small glyphs for annotations and the explainer
function windSeeds(t,x,y,alpha){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.strokeStyle='rgba(255,255,255,0.9)'; ctx.lineWidth=5; ctx.lineCap='round'; ctx.shadowColor='rgba(0,0,0,0.5)'; ctx.shadowBlur=6;
  for(let i=0;i<3;i++){ const yy=y-30+i*30, ph=t*3+i; ctx.beginPath(); for(let k=0;k<=24;k++){ const u=k/24; const xx=x+u*260; const yo=Math.sin(u*6+ph)*8*(1-u*0.3); k?ctx.lineTo(xx,yy+yo):ctx.moveTo(xx,yy+yo);} ctx.stroke(); }
  const rnd=mulberry(11); ctx.fillStyle=C.white; for(let i=0;i<9;i++){ const sp=70+rnd()*60, yy=y-50+rnd()*100; const xx=x+((t*sp+rnd()*300)%300); ctx.beginPath(); ctx.arc(xx,yy+Math.sin(t*4+i)*6,5,0,Math.PI*2); ctx.fill(); }
  ctx.restore(); }
function sunGlyph(x,y,r,alpha){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.fillStyle=C.yellow; ctx.strokeStyle=C.yellow; ctx.lineWidth=6; ctx.lineCap='round'; ctx.shadowColor='rgba(0,0,0,0.5)'; ctx.shadowBlur=8;
  ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.fill(); for(let i=0;i<8;i++){ const a=i/8*Math.PI*2; ctx.beginPath(); ctx.moveTo(x+Math.cos(a)*r*1.4,y+Math.sin(a)*r*1.4); ctx.lineTo(x+Math.cos(a)*r*1.9,y+Math.sin(a)*r*1.9); ctx.stroke(); } ctx.restore(); }
function bird(t,t0,alpha){ // a bird crosses left to right over the footage and drops a seed
  const k=t-t0; if(k<0||k>2.2) return; const u=k/2.2; const x=lerp(160,900,u), y=640+Math.sin(u*9)*18-u*40;   // stays inside x 110..970 (side crops)
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha*(1-smooth(0.85,1,u)); text('🐦',x,y,{size:72,stroke:false,shadow:true});
  if(u>0.3){ const d=(u-0.3)/0.5; const sy=y+20+d*d*560; ctx.fillStyle='#8B2E5A'; ctx.beginPath(); ctx.arc(x-40,Math.min(sy,1200),8,0,Math.PI*2); ctx.fill(); } ctx.restore(); }
// explainer icons (ink on cream), each ~110 px tall, centred at (x, y = baseline)
function icoWeed(x,y,s,col){ ctx.strokeStyle=col; ctx.lineWidth=5; ctx.lineCap='round'; for(let i=-2;i<=2;i++){ ctx.beginPath(); ctx.moveTo(x,y); ctx.quadraticCurveTo(x+i*14*s,y-40*s,x+i*26*s,y-70*s); ctx.stroke(); } }
function icoGrass(x,y,s,col){ ctx.strokeStyle=col; ctx.lineWidth=4; ctx.lineCap='round'; for(let i=-4;i<=4;i++){ ctx.beginPath(); ctx.moveTo(x+i*9*s,y); ctx.quadraticCurveTo(x+i*9*s+4,y-30*s,x+i*13*s,y-55*s); ctx.stroke(); } }
function icoShrub(x,y,s,col){ ctx.fillStyle=col; for(const [dx,dy,r] of [[0,-40,34],[-28,-26,24],[28,-28,24],[0,-16,26]]){ ctx.beginPath(); ctx.arc(x+dx*s,y+dy*s,r*s,0,Math.PI*2); ctx.fill(); } }
function icoPine(x,y,s,col,trunk){ ctx.fillStyle=trunk; ctx.fillRect(x-5*s,y-30*s,10*s,30*s); ctx.fillStyle=col; for(let i=0;i<3;i++){ const yy=y-30*s-i*28*s, w=(40-i*9)*s; ctx.beginPath(); ctx.moveTo(x-w,yy); ctx.lineTo(x+w,yy); ctx.lineTo(x,yy-40*s); ctx.closePath(); ctx.fill(); } }
function icoBirch(x,y,s,col,trunk){ ctx.fillStyle='#E8E4DA'; ctx.fillRect(x-5*s,y-70*s,10*s,70*s); ctx.fillStyle=trunk; for(let i=0;i<3;i++) ctx.fillRect(x-5*s,y-62*s+i*18*s,10*s,3*s); ctx.fillStyle=col; ctx.beginPath(); ctx.ellipse(x,y-88*s,26*s,34*s,0,0,Math.PI*2); ctx.fill(); }
function icoOak(x,y,s,col,trunk){ ctx.fillStyle=trunk; ctx.fillRect(x-9*s,y-60*s,18*s,60*s); ctx.fillStyle=col; for(const [dx,dy,r] of [[0,-95,42],[-36,-75,30],[36,-75,30],[-20,-110,26],[20,-110,26]]){ ctx.beginPath(); ctx.arc(x+dx*s,y+dy*s,r*s,0,Math.PI*2); ctx.fill(); } }
function crossOut(x,y,s,alpha){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.strokeStyle=C.red; ctx.lineWidth=9; ctx.lineCap='round'; ctx.beginPath(); ctx.moveTo(x-34*s,y-34*s); ctx.lineTo(x+34*s,y+34*s); ctx.moveTo(x+34*s,y-34*s); ctx.lineTo(x-34*s,y+34*s); ctx.stroke(); ctx.restore(); }

// ---------------------------------------------------------------- beats
const HOOK_HEAD=[[['BARE DIRT ',C.white],['→',C.yellow],[' FOREST',C.white]],[['BY ITSELF.',C.yellow]]];
function beatHook(tb,t,b){ headline(HOOK_HEAD,1-smooth(b.duration-0.3,b.duration-0.05,tb)); }

function beatWeeds(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tW=wordTime('weeds','weeds'), tWind=wordTime('weeds','wind'), tSun=wordTime('weeds','sun');
  stageTag('ANNUAL WEEDS',tW,t,{out,sub:'year 1 to 3'});
  if(t>tWind){ const a=smooth(0,0.2,t-tWind)*out; windSeeds(t,120,720,a); pill('SEEDS ON THE WIND',120,820,{size:30,weight:800,padX:22,align:'left',alpha:a}); }
  if(t>tSun){ const a=smooth(0,0.2,t-tSun)*out; sunGlyph(820,700,36,a); pill('FULL SUN',870,790,{size:30,weight:800,padX:22,align:'right',alpha:a,bg:'rgba(255,214,10,0.95)',fg:INK}); } }

function beatGrass(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tG=wordTime('grass','grasses'), tS=wordTime('grass','soil'), tD=wordTime('grass','dead');
  stageTag('GRASSES',tG,t,{out,sub:'year 5 to 12'});
  if(t>tD){ const a=smooth(0,0.2,t-tD)*out; pill('DEAD LEAVES ↓',W/2,700,{size:34,weight:900,padX:26,alpha:a}); }
  if(t>tS){ const a=smooth(0,0.25,t-tS)*out; // bracket on the dark topsoil band of the section (the G camera puts the lawn edge ~y 820)
    ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.strokeStyle=C.yellow; ctx.lineWidth=6; ctx.lineCap='round'; ctx.shadowColor='rgba(0,0,0,0.6)'; ctx.shadowBlur=8;
    ctx.beginPath(); ctx.moveTo(150,838); ctx.lineTo(130,838); ctx.lineTo(130,900); ctx.lineTo(150,900); ctx.stroke(); ctx.restore();
    pill('TOPSOIL BUILDS',170,869,{size:34,weight:900,padX:24,align:'left',alpha:a,bg:'rgba(255,214,10,0.95)',fg:INK}); } }

function beatShrubs(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tB=wordTime('shrubs','birds'), tS=wordTime('shrubs','shrubs'), tSh=wordTime('shrubs','shade');
  bird(t,tB,out); if(t>tB) pill('BIRDS BRING BERRY SEEDS',W/2,760,{size:30,weight:800,padX:22,alpha:smooth(0,0.2,t-tB)*out});
  stageTag('SHRUBS',tS,t,{out,sub:'year 15 to 25'});
  if(t>tSh){ const a=smooth(0,0.2,t-tSh)*out; pill('THE FIRST SHADE',W/2,860,{size:36,weight:900,padX:26,alpha:a,bg:'rgba(10,12,18,0.85)',fg:C.white,border:C.yellow}); } }

function beatPioneers(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tB=wordTime('pioneers','birch'), tL=wordTime('pioneers','light'), tC=wordTime('pioneers',"can't"), tO=wordTime('pioneers','own');
  flash(t,b.start+90/TL.fps,{dur:0.2,peak:0.45});   // the mid-beat cut to the low angle (bg_plan cuts P2 at frame 90)
  stageTag('PIONEER TREES',tB,t,{out,sub:'birch & pine · year 30 to 60'});
  if(t>tL) pill('RACE FOR THE LIGHT ↑',W/2,700,{size:36,weight:900,padX:26,alpha:smooth(0,0.2,t-tL)*out,bg:'rgba(255,214,10,0.95)',fg:INK});
  if(t>tC){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*out; stamp2("CAN'T GROW IN SHADE",W/2,860,tC,t,{size:56}); ctx.restore(); }
  if(t>tO) pill('not even their own',W/2,960,{size:30,weight:800,padX:22,alpha:smooth(0,0.2,t-tO)*out}); }

function beatClimax(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tO=wordTime('climax','oaks'), tU=wordTime('climax','underneath'), tT=wordTime('climax','take'), tB=wordTime('climax','born');
  flash(t,b.start+84/TL.fps,{dur:0.2,peak:0.45});   // mid-beat cut to the high wide (C2 at frame 84)
  if(t<tB) stageTag('OAK & MAPLE',tO,t,{out,sub:'shade-tolerant · year 60 to 120'});
  if(t>tU&&t<tB) pill('GROW IN THE SHADE ✓',W/2,700,{size:36,weight:900,padX:26,alpha:smooth(0,0.2,t-tU),bg:'rgba(61,220,132,0.95)',fg:INK});
  if(t>tT&&t<tB) pill('PIONEERS DIE OUT',W/2,790,{size:32,weight:800,padX:22,alpha:smooth(0,0.2,t-tT)});
  if(t>tB){ const k=t-tB; const s=lerp(1.15,1,easeOutBack(k/0.3)); ctx.save(); ctx.translate(W/2,HEAD_Y+40); ctx.scale(s,s); ctx.globalAlpha=ctx.globalAlpha*smooth(0,0.08,k)*out;
    twoTone([['A FOREST ',C.white],['IS BORN',C.yellow]],0,0,76,14);   // 722 px wide x 1.15 pop stays under the 846 px readable width ctx.restore(); if(k<0.4) flash(t,tB,{dur:0.3,peak:0.5}); } }

// why: cream explainer on blurred footage: the five stages in a row, each one changing the ground and crossing out the last
function beatWhy(tb,t,b){ const a=fadeInOut(tb,b,0,0.3,0.35); const tEach=wordTime('why','each'), tChg=wordTime('why','changes'), tKill=wordTime('why','kills'), tRoom=wordTime('why','room'), tSucc=wordTime('why','succession');
  const px=110,py=610,pw=750,ph=740,pcx=px+pw/2; lightPanel(px,py,pw,ph,a); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a;
  inkText('WHY IT HAPPENS',pcx,py+62,{size:40,weight:900});
  const ink=INK, green='#2E7D32', brown='#7A4A1E'; const xs=[0,1,2,3,4].map(i=>px+90+i*142); const yb=py+330;
  const draw=[(x,s,c)=>icoWeed(x,yb,s,c),(x,s,c)=>icoGrass(x,yb,s,c),(x,s,c)=>icoShrub(x,yb,s,c),(x,s,c)=>icoBirch(x,yb,s,c,brown),(x,s,c)=>icoOak(x,yb,s,c,brown)];
  const names=['WEEDS','GRASS','SHRUBS','PIONEERS','OAKS']; const n=t<tEach?0:5;
  // stage k becomes "current" in turn after 'kills' (each ~0.45 s); the one before it is crossed out
  const cur=t<tKill?-1:Math.min(4,Math.floor((t-tKill)/0.45)+1);
  for(let i=0;i<n;i++){ const live=i===cur||cur<0; const col=i<cur?'rgba(28,26,34,0.28)':(live?green:'rgba(28,26,34,0.55)'); ctx.save(); draw[i](xs[i],live?1.05:0.95,col); ctx.restore();
    inkText(names[i],xs[i],yb+42,{size:20,weight:800,color:i<cur?'rgba(28,26,34,0.35)':ink}); if(i<cur) crossOut(xs[i],yb-60,0.9,smooth(0,0.2,t-(tKill+(i)*0.45)));
    if(i<4){ ctx.fillStyle=ink; ctx.beginPath(); const ax=xs[i]+71; ctx.moveTo(ax-12,yb-70); ctx.lineTo(ax+6,yb-62); ctx.lineTo(ax-12,yb-54); ctx.closePath(); ctx.fill(); } }
  // the ground changes under them: soil band thickening + shade bar
  if(t>tChg){ const k=smooth(0,0.6,t-tChg); const gy=yb+90; ctx.fillStyle='#5A3A1E'; ctx.fillRect(px+60,gy,pw-120,14+40*k); inkText('MORE SOIL',px+70,gy+36+40*k,{size:22,weight:800,align:'left',color:'#5A3A1E'});
    ctx.fillStyle='rgba(28,26,34,0.75)'; ctx.fillRect(px+60,gy+70+40*k,(pw-120)*k,10); inkText('MORE SHADE',px+pw-70,gy+96+40*k,{size:22,weight:800,align:'right'}); }
  if(t>tRoom) inkText('each stage makes room for the next',pcx,py+ph-150,{size:28,weight:700,color:'rgba(28,26,34,0.7)',alpha:smooth(0,0.2,t-tRoom)});
  if(t>tSucc){ const k=t-tSucc; const s=lerp(1.4,1,easeOutBack(k/0.3)); ctx.save(); ctx.translate(pcx,py+ph-78); ctx.scale(s,s); ctx.globalAlpha=ctx.globalAlpha*smooth(0,0.08,k); pill('SUCCESSION',0,0,{size:48,weight:900,padX:40,bg:INK,fg:C.yellow}); ctx.restore(); }
  ctx.restore(); }

function beatAsk(tb,t,b){ const tW=wordTime('ask',"what's"), tC=wordTime('ask','cracks'), tE=wordTime('ask','every');
  if(t>tE&&t<tW) pill('EVERY EMPTY LOT IS ON THIS CLOCK',W/2,HEAD_Y,{size:34,weight:900,padX:26,alpha:smooth(0,0.2,t-tE)});
  if(t>tW) headline([[["WHAT'S ",C.white],['GROWING',C.yellow]],[['NEAR YOU?',C.white]]],smooth(0,0.25,t-tW),72);
  if(t>tC){ const a=smooth(0,0.25,t-tC); pill('comment what you found ↓',W/2,1150,{size:36,weight:800,padX:30,alpha:a}); pill('follow for the next one',W/2,1230,{size:28,weight:800,padX:24,alpha:a*0.85,bg:'rgba(10,12,18,0.6)'}); } }
function beatLoop(tb,t,b){ headline([[["WHAT'S ",C.white],['GROWING',C.yellow]],[['NEAR YOU?',C.white]]],1-smooth(0,0.3,tb),72); headline(HOOK_HEAD,smooth(b.duration-0.5,b.duration-0.1,tb)); }

window.BEATS = {
  draw: {hook:beatHook,weeds:beatWeeds,grass:beatGrass,shrubs:beatShrubs,pioneers:beatPioneers,climax:beatClimax,why:beatWhy,ask:beatAsk,loop:beatLoop},
  cutFlash: ['weeds','grass','shrubs','pioneers','climax','why','ask'],
  keywords: ['dirt','forest','weeds','wind','sun','grasses','soil','birds','shrubs','shade','birch','pine','light','oaks','maples','born','succession','clock','cracks','itself'],
  caption: {y: CAP_Y, size: 58, pop: 1.06, keywordColor: '#FFB020'},
  vignette: 0.12,
  every: counter,
};
