// Beat graphics for video 006: Lake Peigneur, low-poly anime style. Type is anime-title style
// (white/yellow fill, thick navy stroke, offset pink shadow); the host (scene_vtuber.py) sits bottom-left
// (x 0..640, y 1000..1920, head ~y 1040..1460), so graphics live in the band y 250..940 and captions at y 975.
const NAVY='#283272', PINK='#FF5FA2', AQUA='#7CF3FF', CREAM='rgba(255,250,246,0.95)', INKC='#1F1A33';
const HEAD_Y=318, HEAD2_Y=408;
function fade(tb,b,inAt=0,inDur=0.25,outPad=0.3){return smooth(inAt,inAt+inDur,tb)*(1-smooth(b.duration-outPad,b.duration-0.05,tb))}
function animeText(str,x,y,{size=78,fill=C.white,align='center',alpha=1,rot=0,shadow=PINK,stroke=NAVY,sw=null}={}){
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.rotate(rot); font(900,size); ctx.textAlign=align; ctx.textBaseline='middle'; ctx.lineJoin='round';
  const w=sw||Math.max(8,size*0.2), o=size*0.07;
  ctx.lineWidth=w; ctx.strokeStyle=shadow; ctx.strokeText(str,o,o); ctx.fillStyle=shadow; ctx.fillText(str,o,o);
  ctx.strokeStyle=stroke; ctx.strokeText(str,0,0); ctx.fillStyle=fill; ctx.fillText(str,0,0); ctx.restore(); }
function fitSz(parts,size,maxW=846){ font(900,size); const w=parts.reduce((a,p)=>a+ctx.measureText(p[0]).width,0)+size*0.3; return w>maxW?Math.floor(size*maxW/w):size; }
function animeLine(parts,y,size,alpha=1,pop=1){ size=fitSz(parts,size,846/Math.max(pop,1)); /* fit including the pop-in overshoot */ font(900,size); const ws=parts.map(p=>ctx.measureText(p[0]).width); const tot=ws.reduce((a,b)=>a+b,0);
  ctx.save(); ctx.translate(W/2,y); ctx.scale(pop,pop); let x=-tot/2; parts.forEach((p,i)=>{ animeText(p[0],x+ws[i]/2,0,{size,fill:p[1],alpha}); x+=ws[i]; }); ctx.restore(); }
function popIn(t,t0,d=0.22){ return t<t0?0:lerp(1.2,1,easeOutBack((t-t0)/d)); }
function tag(label,x,y,{alpha=1,bg=PINK,fg=C.white,size=36,align='left'}={}){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.shadowColor='rgba(40,50,114,0.55)'; ctx.shadowOffsetY=6; ctx.shadowBlur=0;
  pill(label,x,y,{bg,fg,size,weight:900,padX:26,align,border:'rgba(255,255,255,0.95)'}); ctx.restore(); }
// emotes next to the host's head (her face is ~x 120..520, y 1080..1440 in the final frame)
function emoteBang(t,t0,x=560,y=1090){ const k=t-t0; if(k<0||k>2.2)return; const a=smooth(0,0.08,k)*(1-smooth(1.8,2.2,k)); const s=lerp(1.6,1,easeOutBack(k/0.2)); const wob=0.08*Math.sin(k*30)*Math.exp(-k*4);
  ctx.save(); ctx.translate(x,y); ctx.rotate(0.18+wob); ctx.scale(s,s); animeText('!!',0,0,{size:110,fill:C.yellow,alpha:a}); ctx.restore(); }
function sparkle(x,y,r,a){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.translate(x,y); ctx.fillStyle='#FFF6A8'; ctx.strokeStyle=NAVY; ctx.lineWidth=4; ctx.beginPath();
  for(let i=0;i<8;i++){ const rr=i%2?r*0.28:r, an=i*Math.PI/4; ctx.lineTo(Math.cos(an)*rr,Math.sin(an)*rr); } ctx.closePath(); ctx.stroke(); ctx.fill(); ctx.restore(); }
function sparkles(t,t0,dur=2.0){ const k=t-t0; if(k<0||k>dur)return; const a=smooth(0,0.15,k)*(1-smooth(dur-0.4,dur,k));
  [[560,1120,34,0],[600,1230,22,1.3],[520,1030,18,2.1]].forEach(([x,y,r,ph])=>sparkle(x,y,r*(0.75+0.25*Math.sin(k*7+ph)),a)); }
function burst(x,y,t0,t,label){ const k=t-t0; if(k<0||k>1.1)return; const a=1-smooth(0.7,1.1,k); const R=lerp(80,260,easeOutCubic(k/0.35));
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.translate(x,y); const rng=mulberry(7); ctx.fillStyle='rgba(255,255,255,0.95)'; ctx.strokeStyle=NAVY; ctx.lineWidth=3;
  for(let i=0;i<22;i++){ const an=i/22*Math.PI*2+rng()*0.1, r0=R*0.45, r1=R*(0.85+0.4*rng()); ctx.beginPath(); ctx.moveTo(Math.cos(an-0.04)*r0,Math.sin(an-0.04)*r0); ctx.lineTo(Math.cos(an)*r1,Math.sin(an)*r1); ctx.lineTo(Math.cos(an+0.04)*r0,Math.sin(an+0.04)*r0); ctx.closePath(); ctx.fill(); ctx.stroke(); }
  ctx.restore(); if(label){ animeText(label,x,y,{size:96,fill:C.yellow,alpha:a,rot:-0.12}); } }

// ---------------------------------------------------------------- story
function beatHook(tb,t,b){ const a=1-smooth(b.duration-0.3,b.duration-0.05,tb);
  animeLine([['A DRILL PULLED',C.white]],HEAD_Y,84,a,popIn(t,0.0));
  animeLine([['THE ',C.white],['PLUG',C.yellow],[' ON A LAKE',C.white]],HEAD2_Y,84,a,popIn(t,0.15));
  const t80=wordTime('hook','1980'); if(t>=t80) tag('NOV 20, 1980 · LOUISIANA',W/2,505,{alpha:smooth(0,0.2,t-t80)*a,align:'center',bg:NAVY,size:34});
  emoteBang(t,0.25); }
function beatSetup(tb,t,b){ const a=fade(tb,b);
  animeLine([['LAKE ',C.white],['PEIGNEUR',C.yellow]],HEAD_Y,82,a,popIn(t,b.start+0.05));
  const tT=wordTime('setup','ten'), tR=wordTime('setup','rig');
  if(t>tT) tag('📏 ONLY 10 FT DEEP',130,470,{alpha:smooth(0,0.2,t-tT)*a});
  if(t>tR) tag('🛢️ TEXACO OIL RIG',130,556,{alpha:smooth(0,0.2,t-tR)*a,bg:NAVY}); }
function beatMine(tb,t,b){ const a=fade(tb,b,0,0.25,0.25); const tS=wordTime('mine','salt'), tF=wordTime('mine','fiftyfive'), tTw=wordTime('mine','twelve'), tP=wordTime('mine','punched');
  if(t>tS) animeLine([['A ',C.white],['SALT MINE',C.yellow],[' BELOW',C.white]],HEAD_Y,80,a*(1-smooth(tP-0.2,tP,t)),popIn(t,tS));
  if(t>tF) tag('⛑️ 55 MINERS INSIDE',130,445,{alpha:smooth(0,0.2,t-tF)*a*(1-smooth(tP-0.2,tP,t))});
  if(t>tTw){ const k=smooth(0,0.25,t-tTw)*a; animeLine([['1,228 FT',C.yellow],[' DOWN',C.white]],HEAD_Y,80,k*smooth(tP-0.2,tP,t),popIn(t,tP-0.2)); tag('1,228 FT',130,520,{alpha:k*(1-smooth(tP-0.2,tP,t)),bg:NAVY}); }
  if(t>tP) tag('drawn not to scale',130,470,{alpha:smooth(0,0.2,t-tP)*a*0.9,bg:'rgba(31,26,51,0.75)',size:26});
  burst(560,740,tP,t,'PUNCH!'); emoteBang(t,tP); }
function beatWhirl(tb,t,b){ const a=fade(tb,b); const tSw=wordTime('whirlpool','swallowed');
  const tSp=wordTime('whirlpool','spin'); if(t>tSp) animeLine([['IT ',C.white],['SPUN',C.yellow],[' INTO A WHIRLPOOL',C.white]],HEAD_Y,70,a*(1-smooth(tSw-0.15,tSw+0.1,t)),popIn(t,tSp));
  if(t>tSw){ animeLine([['SWALLOWED:',C.white]],HEAD_Y,80,a*smooth(tSw-0.1,tSw+0.1,t),popIn(t,tSw));
    const items=[['rig','1 OIL RIG',PINK],['barges','11 BARGES',NAVY],['tugboat','1 TUGBOAT',PINK]];
    items.forEach(([w,l,bg],i)=>{ const t0=wordTime('whirlpool',w); if(t<t0)return; ctx.save(); const s=popIn(t,t0); ctx.translate(130,450+i*86); ctx.scale(s,s); tag(l,0,0,{alpha:smooth(0,0.15,t-t0)*a,bg,size:40}); ctx.restore(); }); }
  emoteBang(t,b.start+0.2); }
function beatFall(tb,t,b){ const a=fade(tb,b); const tB=wordTime('waterfall','backwards'), t164=wordTime('waterfall','sixtyfour'), tE=wordTime('waterfall','every');
  if(t>tB && t<tE+0.2) animeLine([['THE CANAL RAN ',C.white],['BACKWARDS',C.yellow]],HEAD_Y,70,a*(1-smooth(tE-0.1,tE+0.15,t)),popIn(t,tB));
  if(t>t164){ const k=smooth(0,0.2,t-t164)*a*(1-smooth(tE-0.1,tE+0.15,t)); ctx.save(); ctx.globalAlpha*=k; animeLine([['164 FT',C.yellow],[' WATERFALL',C.white]],HEAD2_Y,70,1,popIn(t,t164)); ctx.restore();
    tag('tallest in Louisiana, for a few days',W/2,500,{alpha:k,bg:NAVY,size:30,align:'center'}); }
  if(t>tE){ animeLine([['ALL 55 MINERS',C.white]],HEAD_Y,80,a,popIn(t,tE)); animeLine([['GOT OUT ',C.white],['ALIVE',C.green]],HEAD2_Y,80,a,popIn(t,tE+0.2));
    tag('no human deaths',W/2,505,{alpha:smooth(0.3,0.5,t-tE)*a,bg:NAVY,size:32,align:'center'}); sparkles(t,tE,b.end-tE); } }
// ---------------------------------------------------------------- physics
function beatWhy(tb,t,b){ const a=fade(tb,b,0,0.2,0.2); const tW=wordTime('why','whirlpool');
  animeLine([['WHY A',C.white]],HEAD_Y,90,a,popIn(t,b.start+0.05)); if(t>tW) animeLine([['WHIRLPOOL',C.yellow],['?',C.white]],HEAD2_Y+10,96,a,popIn(t,tW)*(1+0.03*Math.sin(t*12)));
  const tD=wordTime('why','drain'); if(t>tD) tag('not just a drain',W/2,520,{alpha:smooth(0,0.2,t-tD)*a,bg:NAVY,align:'center'}); }
// top-down vortex (shot V): centre (540,700), 48 px/unit; buoys at r=9 and 4.5, theta = th0 + GAMMA/r^2 * t (scene_peigneur.py)
const VC={x:540,y:700,ppu:48,G:38.0}; const BUOYS=[{r:9.0,th0:0.6,label:'v',col:C.yellow},{r:4.5,th0:2.0,label:'2v',col:'#FF5A36'}];
function buoyPos(bu,ts){ const th=bu.th0+VC.G/(bu.r*bu.r)*ts; return {x:VC.x+VC.ppu*bu.r*Math.cos(th), y:VC.y-VC.ppu*bu.r*Math.sin(th), th}; }
function dashedCircle(r,col,a){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.setLineDash([18,14]); ctx.lineWidth=6; ctx.strokeStyle=col;
  ctx.beginPath(); ctx.arc(VC.x,VC.y,r,0,Math.PI*2); ctx.stroke(); ctx.restore(); }
function speedArrow(p,len,col,a){ const tx=-Math.sin(p.th), ty=-Math.cos(p.th); // screen tangent (CCW in world = CCW on screen with y flipped)
  const x1=p.x+tx*len, y1=p.y+ty*len; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.lineCap='round'; ctx.strokeStyle=NAVY; ctx.lineWidth=16; ctx.beginPath(); ctx.moveTo(p.x,p.y); ctx.lineTo(x1,y1); ctx.stroke();
  ctx.strokeStyle=col; ctx.lineWidth=9; ctx.stroke(); const an=Math.atan2(y1-p.y,x1-p.x); ctx.fillStyle=col; ctx.strokeStyle=NAVY; ctx.lineWidth=4; ctx.beginPath(); ctx.moveTo(x1+Math.cos(an)*22,y1+Math.sin(an)*22);
  ctx.lineTo(x1+Math.cos(an+2.4)*24,y1+Math.sin(an+2.4)*24); ctx.lineTo(x1+Math.cos(an-2.4)*24,y1+Math.sin(an-2.4)*24); ctx.closePath(); ctx.stroke(); ctx.fill(); ctx.restore(); }
function eqPanel(x,y,w,h,a,hl){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.shadowColor='rgba(40,50,114,0.6)'; ctx.shadowOffsetY=8; rr(x,y,w,h,30); ctx.fillStyle=CREAM; ctx.fill(); ctx.shadowColor='transparent'; ctx.lineWidth=5; ctx.strokeStyle=NAVY; ctx.stroke();
  const parts=[['v','speed'],[' × ',null],['r','radius'],[' = ',null],['constant',null]]; font(900,64); const ws=parts.map(p=>ctx.measureText(p[0]).width); let cx=x+w/2-ws.reduce((a,b)=>a+b,0)/2;
  parts.forEach((p,i)=>{ const on=p[1]&&hl[p[1]]; ctx.save(); font(900,64); ctx.textAlign='left'; ctx.textBaseline='middle'; if(on){ ctx.fillStyle='rgba(255,95,162,0.25)'; rr(cx-8,y+h/2-44,ws[i]+16,84,16); ctx.fill(); }
    ctx.fillStyle=on?PINK:INKC; ctx.fillText(p[0],cx,y+h/2+2); ctx.restore(); cx+=ws[i]; }); ctx.restore(); }
function beatSpin(tb,t,b){ const a=fade(tb,b); const tLs=wordTime('spin','little'), tPu=wordTime('spin','pulled'), tSp=wordTime('spin','speed'), tRa=wordTime('spin','radius'), tH=wordTime('spin','half'), tD=wordTime('spin','double');
  const ts=tb;   // shot V starts at this beat (bg_plan spin: V 0)
  // rings + buoy arrows on the footage
  if(t>tLs){ const k=smooth(0,0.3,t-tLs)*a; BUOYS.forEach((bu,i)=>{ if(i===1 && t<tPu) return; const kk=i?smooth(0,0.3,t-tPu)*a:k; dashedCircle(VC.ppu*bu.r,bu.col,kk*0.42); const p0=buoyPos(bu,ts); const p={...p0,x:clamp(p0.x,180,900),y:clamp(p0.y,330,1500)};   /* faint guide ring (footage may cross the side crops); arrow + label kept in the readable area */
      const show=i===0?(t>tLs):(t>tH); if(show){ speedArrow(p,i===0?80:160,bu.col,kk); animeText(bu.label,p.x+(i?-10:10),p.y+(p.y<380?70:-62),{size:56,fill:bu.col,alpha:kk}); } }); }
  // equation panel up top on 'speed'
  if(t>tSp-0.15) eqPanel(150,262,780,120,smooth(0,0.25,t-tSp+0.15)*a,{speed:t>tSp-0.05&&t<tH, radius:t>tRa-0.05&&t<tH});
  if(t>tH) tag('½ the distance',150,440,{alpha:smooth(0,0.2,t-tH)*a,bg:'#FF5A36'});
  if(t>tD) tag('= 2× the speed',150,526,{alpha:smooth(0,0.2,t-tD)*a,bg:NAVY});
  if(t<tSp-0.15) animeLine([['SPIN ',C.yellow],['GETS FASTER',C.white]],HEAD_Y,80,a*(1-smooth(tSp-0.4,tSp-0.15,t)),popIn(t,b.start+0.05)); }
function beatSalt(tb,t,b){ const a=fade(tb,b); const tE=wordTime('salt','eats'), tN=wordTime('salt','three'), tG=wordTime('salt','growing');
  animeLine([['FRESH WATER ',C.white],['EATS SALT',C.yellow]],HEAD_Y,74,a,popIn(t,b.start+0.05));
  const px=150,py=400,pw=780,ph=520; const pa=smooth(0.1,0.4,tb)*a;
  ctx.save(); ctx.globalAlpha*=pa; ctx.shadowColor='rgba(40,50,114,0.6)'; ctx.shadowOffsetY=8; rr(px,py,pw,ph,34); ctx.fillStyle=CREAM; ctx.fill(); ctx.shadowColor='transparent'; ctx.lineWidth=5; ctx.strokeStyle=NAVY; ctx.stroke(); ctx.restore();
  // feedback loop: four nodes around a circle, lit in order, arrow chasing around once 'growing' is spoken
  const cx=px+pw/2, cy=py+ph/2+10, R=170; const nodes=[['💧 water pours in',-Math.PI/2],['🧂 salt dissolves',0],['🕳️ hole widens',Math.PI/2],['⏩ faster flow',Math.PI]];
  const lit=[tE, tE+0.6, tG-0.2, tG+0.3];
  ctx.save(); ctx.globalAlpha*=pa; ctx.lineWidth=8; ctx.strokeStyle='rgba(40,50,114,0.25)'; ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); ctx.stroke();
  if(t>tG){ const sp=(t-tG)*2.4; ctx.strokeStyle=PINK; ctx.lineWidth=10; ctx.lineCap='round'; ctx.beginPath(); ctx.arc(cx,cy,R,sp-1.2-Math.PI/2,sp-Math.PI/2); ctx.stroke(); }
  nodes.forEach(([l,an],i)=>{ const on=t>lit[i]; const x=cx+Math.cos(an)*R, y=cy+Math.sin(an)*R; const s=on?popIn(t,lit[i]):1;
    ctx.save(); ctx.translate(x,y); ctx.scale(s,s); pill(l,0,0,{bg:on?(i%2?NAVY:PINK):'rgba(40,50,114,0.18)',fg:on?C.white:'rgba(31,26,51,0.5)',size:30,weight:900,padX:20,alpha:1}); ctx.restore(); });
  ctx.restore();
  if(t>tN) tag('~350 kg of salt per m³ of water',W/2,py+ph+60,{alpha:smooth(0,0.2,t-tN)*a,bg:NAVY,size:32,align:'center'}); }
function beatPayoff(tb,t,b){ const a=fade(tb,b); const tB=wordTime('payoff','bathtub'), tM=wordTime('payoff','mine');
  if(t>tB) animeLine([['= YOUR ',C.white],['BATHTUB DRAIN',C.yellow]],HEAD_Y,80,a,popIn(t,tB));
  if(t>tM) tag('...with a salt mine at the bottom',W/2,430,{alpha:smooth(0,0.2,t-tM)*a,bg:NAVY,size:34,align:'center'});
  sparkles(t,b.start+0.1,b.duration-0.2); }
function beatCta(tb,t,b){ const a=smooth(0,0.2,tb);
  animeLine([['FOLLOW',C.yellow],[' FOR MORE',C.white]],HEAD_Y,86,a,popIn(t,b.start+0.05)); animeLine([['DISASTERS, EXPLAINED',C.white]],HEAD2_Y,72,a,popIn(t,b.start+0.2));
  const k=tb; ctx.save(); ctx.globalAlpha*=a; animeText('♥',560+6*Math.sin(k*6),1110-10*Math.abs(Math.sin(k*4)),{size:80,fill:PINK,shadow:C.white}); ctx.restore(); }

window.BEATS = {
  draw: {hook:beatHook,setup:beatSetup,mine:beatMine,whirlpool:beatWhirl,waterfall:beatFall,why:beatWhy,spin:beatSpin,salt:beatSalt,payoff:beatPayoff,cta:beatCta},
  cutFlash: ['setup','mine','whirlpool','waterfall','why','spin','salt','payoff','cta'],
  keywords: ['drill','plug','lake','peigneur','salt','mine','miners','punched','whirlpool','spin','rig','barges','tugboat','backwards','waterfall','alive','speed','radius','double','dissolve','growing','bathtub','drain','disasters'],
  caption: {y: 975, size: 66, pop: 1.08, keywordColor: '#FF8FC4'},
  vignette: 0.18,
};
