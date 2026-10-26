// Beat graphics for video 001 (loaded by render_overlays.py into overlay.html).
// Helpers available: ctx, W, H, C, text, pill, panel, stamp, stopwatch, flash, rr, font, smooth, lerp, easeOutBack, easeOutCubic, mulberry, fmtNum, wordTime, TL, BEATS.
// ---------------------------------------------------------------- beat graphics
function fadeInOut(tb,b,a0=0.2){return smooth(0,a0,tb)*(1-smooth(b.duration-0.3,b.duration-0.05,tb))}
function beatHook(tb,t,b){
  const out=1-smooth(b.duration-0.35,b.duration-0.05,tb);
  const k1=tb-0.25; if(k1>0){ const s=lerp(1.5,1,easeOutBack(k1/0.3)); ctx.save(); ctx.translate(W/2,360); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,k1)*out;
    text('FLAME 🔥 + PLASTIC BAG',0,0,{size:82,weight:900}); ctx.restore(); }
  const tIgn=2.45-(b.bg_offset||0)/TL.fps; const k2=tb-tIgn; if(k2>0){ const s=lerp(2.2,1,easeOutBack(k2/0.35))*(1+0.03*Math.sin(k2*8)); ctx.save(); ctx.translate(W/2,540); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,k2)*out;
    text('= ?',0,0,{size:150,weight:900,color:C.yellow}); ctx.restore(); flash(t,b.start+tIgn,{dur:0.3,peak:0.5,color:'255,170,60'}); }
}
const MELT_START=0.8, MELT_END=1.8; // must match scene_bag.py shot B
function beatEmpty(tb,t,b){
  const a=smooth(0,0.15,tb);
  pill('EMPTY BAG',120,250,{align:'left',size:40,bg:'rgba(120,125,140,0.85)',alpha:a});
  const sw = tb<MELT_START?0:Math.min(tb-MELT_START, MELT_END-MELT_START);
  stopwatch(sw,W-80,250,{color: sw>=MELT_END-MELT_START-0.001?C.red:C.white,alpha:a});
  stamp('MELTED',W/2,980,b.start+MELT_END+0.08,t,{color:C.red,size:150});
  const tInst=wordTime('empty','instantly'); if(t>tInst){ ctx.save(); ctx.globalAlpha=smooth(0,0.15,t-tInst); pill('1 SECOND',W/2,1150,{size:44,bg:'rgba(255,59,59,0.95)'}); ctx.restore(); }
}
function beatWater(tb,t,b){
  const a=smooth(0,0.15,tb);
  pill('WATER BAG',120,250,{align:'left',size:40,bg:'rgba(45,140,255,0.9)',alpha:a});
  stopwatch(Math.max(0,tb-0.2),W-80,250,{color: tb>2.5?C.green:C.white,alpha:a});
  const tImp=wordTime('water','impossible');
  stamp('WON’T MELT ✅',W/2,980,tImp+0.05,t,{color:C.green,size:110,rot:-0.08});
  const tHow=wordTime('water','how'); const kh=t-tHow; if(kh>0){ const s=lerp(2.4,1,easeOutBack(kh/0.35))*(1+0.04*Math.sin(kh*9));
    ctx.save(); ctx.translate(W/2,1180); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,kh); text('HOW?',0,0,{size:190,weight:900,color:C.yellow,strokeW:22}); ctx.restore(); flash(t,tHow,{dur:0.2,peak:0.3}); }
}
function bar(x,y,w,h,frac,color,label,value,alpha){
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; rr(x,y,w,h,h/2); ctx.fillStyle='rgba(255,255,255,0.08)'; ctx.fill();
  const fw=Math.max(h,w*frac); rr(x,y,fw,h,h/2); ctx.fillStyle=color; ctx.fill();
  text(label,x,y-44,{size:36,weight:800,color:'rgba(255,255,255,0.85)',align:'left',stroke:false});
  text(value,x+fw+24,y+h/2+2,{size:58,weight:900,color,align:'left',stroke:true,strokeW:8}); ctx.restore();
}
function beatTemps(tb,t,b){
  const a=fadeInOut(tb,b);
  const px=90,py=540,pw=900,ph=640; panel(px,py,pw,ph,a);
  text('HOW HOT?',W/2,py+70,{size:56,weight:900,alpha:a,stroke:false});
  const bx=px+60,bw=pw-120-220, bh=54, MAX=1150;
  const t1=wordTime('temps','flame'), t2=wordTime('temps','plastic'), t3=wordTime('temps','never');
  const rows=[
    {t0:t1,val:1000,color:C.orange,label:'FLAME',fmt:v=>fmtNum(v)+'°C+'},
    {t0:t2,val:120,color:C.red,label:'PLASTIC MELTS',fmt:v=>fmtNum(v)+'°C'},
    {t0:t3,val:100,color:C.blue,label:'PLASTIC ACTUALLY',fmt:v=>fmtNum(v)+'°C'},
  ];
  rows.forEach((r,i)=>{ const k=t-r.t0; if(k<0)return; const p=easeOutCubic(k/0.9); const y=py+200+i*160;
    bar(bx,y,bw,bh,r.val*p/MAX,r.color,r.label,r.fmt(r.val*p),a*smooth(0,0.1,k)); });
  const kq=t-t3; if(kq>0.5){ ctx.save(); ctx.globalAlpha=smooth(0.5,0.7,kq)*a; pill('NEVER ABOVE 100°C',W/2,py+ph+70,{size:46,bg:'rgba(61,220,132,0.95)',fg:'#06210f'}); ctx.restore(); }
}
function flameIcon(x,y,s,tt,alpha=1){
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s);
  for(let i=0;i<3;i++){ const w=[1,0.65,0.35][i], col=['#FF6A00','#FFB000','#FFF2B0'][i]; const fl=1+0.08*Math.sin(tt*9+i*2);
    ctx.beginPath(); ctx.moveTo(0,-110*w*fl); ctx.bezierCurveTo(60*w,-40*w,70*w,30*w,0,60*w); ctx.bezierCurveTo(-70*w,30*w,-60*w,-40*w,0,-110*w*fl); ctx.fillStyle=col; ctx.fill(); }
  ctx.restore();
}
function equationLine(x,y,size,hl){ // q = k · ΔT / d   (hl: which symbol to highlight)
  const parts=[['q','q'],[' = ',''],['k','k'],[' · ',''],['ΔT','dT'],[' / ',''],['d','d']];
  font(800,size); const widths=parts.map(p=>ctx.measureText(p[0]).width); const total=widths.reduce((a,b)=>a+b,0); let cx=x-total/2;
  parts.forEach((p,i)=>{ const on=hl&&p[1]===hl; const col=on?C.yellow:(p[1]?C.white:'rgba(255,255,255,0.7)');
    ctx.save(); if(on){ctx.translate(cx+widths[i]/2,y); ctx.scale(1.18,1.18); ctx.translate(-(cx+widths[i]/2),-y);} 
    text(p[0],cx+widths[i]/2,y,{size,weight:800,color:col,stroke:false,shadow:true}); ctx.restore(); cx+=widths[i]; });
}
function beatEquation(tb,t,b){
  const a=fadeInOut(tb,b);
  const px=70,py=430,pw=940,ph=860; panel(px,py,pw,ph,a);
  ctx.save(); ctx.globalAlpha=a;
  // equation header
  const tK=wordTime('equation','k'), tD=wordTime('equation','d'), tThin=wordTime('equation','thin'), tWater=wordTime('equation','water');
  const hl = t>tThin? 'd' : (t>tD ? 'd' : (t>tK ? 'k' : null));
  text('HEAT FLOW THROUGH THE FILM',W/2,py+60,{size:32,weight:700,color:'rgba(255,255,255,0.75)',stroke:false});
  equationLine(W/2,py+150,96,hl);
  const kthin=t-tThin; if(kthin>0){ ctx.save(); ctx.globalAlpha=smooth(0,0.2,kthin); pill('d = 0.03 mm  →  q is HUGE',W/2,py+250,{size:40,bg:'rgba(255,214,10,0.95)',fg:'#1a1500'}); ctx.restore(); }
  // zones: flame | film | water
  const filmX=px+400, filmW=14, top=py+370, bot=py+ph-70;
  const wg=ctx.createLinearGradient(filmX,0,px+pw,0); wg.addColorStop(0,'rgba(77,184,255,0.55)'); wg.addColorStop(1,'rgba(77,184,255,0.25)');
  ctx.fillStyle=wg; rr(filmX+filmW,top,px+pw-40-filmX-filmW,bot-top,24); ctx.fill();
  const fg=ctx.createRadialGradient(px+200,(top+bot)/2,10,px+200,(top+bot)/2,260); fg.addColorStop(0,'rgba(255,170,40,0.75)'); fg.addColorStop(1,'rgba(255,90,0,0)');
  ctx.fillStyle=fg; ctx.fillRect(px+20,top,filmX-px-20,bot-top);
  flameIcon(px+200,(top+bot)/2+40,1.0,t,0.95);
  ctx.fillStyle= (hl==='d') ? C.yellow : '#E8ECF2'; rr(filmX,top,filmW,bot-top,6); ctx.fill();
  text('FLAME',px+200,top+36,{size:36,weight:800,color:C.orange,stroke:false});
  text('WATER',filmX+280,top+36,{size:36,weight:800,color:C.blue,stroke:false});
  text('d',filmX+7,bot+40,{size:40,weight:800,color:(hl==='d')?C.yellow:'#E8ECF2',stroke:false});
  // heat particles
  const rnd=mulberry(42); const N=140;
  for(let i=0;i<N;i++){ const s0=i*0.045+rnd()*0.03, yy=lerp(top+40,bot-40,rnd()), spd=lerp(420,560,rnd()); const k=tb-s0-0.3; if(k<0)continue;
    let x=px+230+spd*k; if(x>px+pw-60)continue;
    const inWater=x>filmX; const life=inWater?(x-filmX)/300:0; if(life>1)continue;
    const r=inWater?lerp(9,3,life):9; const col=inWater?`rgba(120,210,255,${1-life})`:'rgba(255,150,40,0.95)';
    ctx.beginPath(); ctx.arc(x,yy+Math.sin(k*7+i)*6,r,0,Math.PI*2); ctx.fillStyle=col; ctx.fill();
    if(!inWater){ctx.beginPath();ctx.moveTo(x-26,yy+Math.sin(k*7+i)*6);ctx.lineTo(x-8,yy+Math.sin(k*7+i)*6);ctx.lineWidth=4;ctx.strokeStyle='rgba(255,150,40,0.5)';ctx.stroke()}
  }
  // film temperature gauge
  const gx=filmX+7, gy=bot-60; rr(gx-170,gy-46,340,92,46); ctx.fillStyle='rgba(8,10,16,0.9)'; ctx.fill(); ctx.lineWidth=3; ctx.strokeStyle=C.blue; ctx.stroke();
  const temp=100+2*Math.sin(t*5); text('FILM: '+temp.toFixed(0)+'°C',gx,gy+2,{size:40,weight:900,color:C.blue,stroke:false});
  if(t>tWater){ ctx.save(); ctx.globalAlpha=smooth(0,0.2,t-tWater); text('HEAT IN → HEAT OUT',W/2,py+ph+60,{size:50,weight:900,color:C.orange}); ctx.restore(); }
  ctx.restore();
}
function lockIcon(x,y,s,color){ctx.save();ctx.translate(x,y);ctx.scale(s,s);ctx.lineWidth=7;ctx.strokeStyle=color;ctx.fillStyle=color;
  ctx.beginPath();ctx.arc(0,-14,18,Math.PI,0);ctx.stroke(); rr(-26,-14,52,40,8);ctx.fill();ctx.restore()}
function beatCeiling(tb,t,b){
  const a=fadeInOut(tb,b);
  const px=70,py=480,pw=940,ph=780; panel(px,py,pw,ph,a);
  ctx.save(); ctx.globalAlpha=a;
  const tx=px+230, top=py+110, bot=py+ph-110, tw=70;
  const yOf=v=>lerp(bot,top,v/130);
  rr(tx-tw/2,top-20,tw,bot-top+20,tw/2); ctx.fillStyle='rgba(255,255,255,0.1)'; ctx.fill();
  ctx.beginPath(); ctx.arc(tx,bot+40,70,0,Math.PI*2); ctx.fillStyle='rgba(255,255,255,0.1)'; ctx.fill();
  const tLock=wordTime('ceiling','boils'); const rise=smooth(b.start+0.3,tLock,t); let temp=lerp(20,100,rise);
  if(t>tLock){ const k=t-tLock; temp=100+ 3*Math.exp(-k*4)*Math.sin(k*18); }
  const col = temp<60? C.blue : (temp<95? C.orange : C.red);
  const hy=yOf(temp); rr(tx-tw/2+14,hy,tw-28,bot+40-hy,20); ctx.fillStyle=col; ctx.fill();
  ctx.beginPath(); ctx.arc(tx,bot+40,52,0,Math.PI*2); ctx.fill();
  text(Math.round(temp)+'°C',tx,bot+44,{size:40,weight:900,color:'#0a0c12',stroke:false,shadow:false});
  const mark=(v,label,color,dash)=>{ const y=yOf(v); ctx.save(); ctx.setLineDash(dash?[14,12]:[]); ctx.lineWidth=5; ctx.strokeStyle=color;
    ctx.beginPath(); ctx.moveTo(tx-tw/2-30,y); ctx.lineTo(px+pw-60,y); ctx.stroke(); ctx.restore();
    text(label,tx+tw/2+40,y-34,{size:34,weight:800,color,align:'left',stroke:false}); };
  mark(120,'PLASTIC MELTS  120°C',C.red,true);
  mark(100,'BOILING POINT  100°C',C.yellow,false);
  if(t>tLock){ const k=t-tLock; const s=lerp(2.2,1,easeOutBack(k/0.35)); lockIcon(px+pw-130,yOf(100),s,C.yellow);
    ctx.save(); ctx.globalAlpha=smooth(0.1,0.3,k); text('HARD CEILING',px+pw-130,yOf(100)+70,{size:34,weight:900,color:C.yellow,stroke:false}); ctx.restore(); }
  const tJ=wordTime('ceiling','joule'); if(t>tJ){ const k=t-tJ; const s=lerp(1.5,1,easeOutBack(k/0.3)); ctx.save(); ctx.translate(px+640,yOf(100)+260); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,k);
    text('Q = m · L',0,0,{size:84,weight:800,color:C.white,stroke:false}); text('latent heat → steam',0,70,{size:30,weight:700,color:'rgba(255,255,255,0.75)',stroke:false}); ctx.restore(); }
  const tSteam=wordTime('ceiling','steam'); const rnd=mulberry(7);
  for(let i=0;i<40;i++){ const s0=rnd()*2.5, x0=lerp(px+520,px+840,rnd()), sp=lerp(90,160,rnd()); const k=t-tSteam-s0+1.0; if(k<0)continue;
    const life=(k%2.2)/2.2; const y=yOf(100)-20-life*260, x=x0+Math.sin(k*2+i)*18; const r=lerp(10,34,life);
    ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.fillStyle=`rgba(255,255,255,${0.55*(1-life)*smooth(0,0.3,k)})`; ctx.fill(); }
  if(t>tSteam){ ctx.save(); ctx.globalAlpha=smooth(0,0.2,t-tSteam); text('EXTRA ENERGY → STEAM',W/2,py+ph+70,{size:50,weight:900,color:C.white}); ctx.restore(); }
  if(t>tLock){ for(let i=0;i<5;i++){ const k=((t-tLock)*1.4+i*0.2)%1; const y=lerp(bot+120,bot-40,k), x=px+560+i*60; ctx.save(); ctx.globalAlpha=(1-k)*0.9;
      ctx.strokeStyle=C.orange; ctx.lineWidth=6; ctx.beginPath(); ctx.moveTo(x,y+40); ctx.lineTo(x,y); ctx.moveTo(x-12,y+14); ctx.lineTo(x,y); ctx.lineTo(x+12,y+14); ctx.stroke(); ctx.restore(); } }
  ctx.restore();
}
function hud(label,value,x,y,color,alpha,align){
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; const w=400,h=150; const x0=align==='left'?x:x-w; rr(x0,y-h/2,w,h,28); ctx.fillStyle='rgba(8,10,16,0.8)'; ctx.fill(); ctx.lineWidth=4; ctx.strokeStyle=color; ctx.stroke();
  text(label,x0+w/2,y-38,{size:30,weight:700,color:'rgba(255,255,255,0.8)',stroke:false}); text(value,x0+w/2,y+26,{size:62,weight:900,color,stroke:false}); ctx.restore();
}
function beatPunch(tb,t,b){
  const a=smooth(0,0.25,tb)*(1-smooth(b.duration-0.3,b.duration-0.05,tb));
  const tHundred=wordTime('punch','hundred'), tTwenty=wordTime('punch','twenty'), tCannot=wordTime('punch','cannot');
  const temp=lerp(20,100,smooth(b.start,tHundred+0.3,t));
  hud('PLASTIC',Math.round(temp)+'°C',70,300,C.blue,a,'left');
  hud('MELTS AT','120°C',W-70,300,C.red,a*smooth(0.6,0.9,tb),'right');
  ctx.save(); ctx.globalAlpha=a*0.8; ctx.strokeStyle=C.blue; ctx.lineWidth=4; ctx.setLineDash([10,10]); ctx.beginPath(); ctx.moveTo(270,375); ctx.lineTo(430,1000); ctx.stroke(); ctx.restore();
  const k=t-tTwenty; if(k>0){ const s=lerp(1.6,1,easeOutBack(k/0.3)); ctx.save(); ctx.translate(W/2,520); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,k)*a;
    pill('20°C TO SPARE  ✅',0,0,{size:48,bg:'rgba(61,220,132,0.95)',fg:'#06210f'}); ctx.restore(); }
  stamp('CANNOT MELT',W/2,1000,tCannot+0.02,t,{color:C.red,size:120,rot:-0.1});
}
function beatNoodles(tb,t,b){
  const a=fadeInOut(tb,b,0.15);
  const k=tb-0.1; if(k>0){ const s=lerp(1.5,1,easeOutBack(k/0.35)); ctx.save(); ctx.translate(W/2,420); ctx.scale(s,s); ctx.globalAlpha=a;
    panel(-470,-170,940,340,1); text('🍜',-300,0,{size:150,stroke:false,shadow:false}); text('YOU CAN BOIL',-150,-50,{size:44,weight:800,align:'left',stroke:false});
    text('NOODLES IN A BAG',-150,30,{size:54,weight:900,color:C.yellow,align:'left',stroke:false}); ctx.restore(); }
  const tBag=wordTime('noodles','bag'); if(t>tBag){ const kk=t-tBag; const s=lerp(1.8,1,easeOutBack(kk/0.3)); ctx.save(); ctx.translate(W/2,1000); ctx.rotate(-0.08); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,kk)*a;
    pill('YES. REALLY.',0,0,{size:60,bg:'rgba(255,45,85,0.95)',padX:40}); ctx.restore(); }
}
function beatCta(tb,t,b){
  const tFollow=wordTime('cta','follow'); const kf=t-tFollow+0.1; if(kf>0){ const s=lerp(1.6,1,easeOutBack(kf/0.35))*(1+0.03*Math.sin(kf*6));
    ctx.save(); ctx.translate(W/2,860); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,kf); pill('＋ FOLLOW',0,0,{size:76,bg:'#FF2D55',fg:'#fff',padX:54}); ctx.restore();
    ctx.save(); ctx.globalAlpha=smooth(0.2,0.45,kf); text('more physics like this',W/2,980,{size:46,weight:700}); ctx.restore(); }
  const fo=smooth(b.duration-0.45,b.duration-0.02,tb); if(fo>0){ctx.fillStyle=`rgba(0,0,0,${fo})`; ctx.fillRect(0,0,W,H)}
}
const DRAW={hook:beatHook,empty:beatEmpty,water:beatWater,temps:beatTemps,equation:beatEquation,ceiling:beatCeiling,punch:beatPunch,noodles:beatNoodles,cta:beatCta};
const CUT_FLASH=['empty','water','temps','equation','punch','noodles','cta'];


window.BEATS = {draw: DRAW, cutFlash: CUT_FLASH, keywords: ['water','flame','boil','boils','boiling','melts','melting','melt','instantly','impossible','obviously','thousand','twenty','hundred','steam','never','noodles','hotter','plastic','joule','cannot','physics']};
