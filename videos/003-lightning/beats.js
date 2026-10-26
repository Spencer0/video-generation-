// Beat graphics for video 003: how lightning works. 2D explainer scenes are opaque (they paint their own sky).
function fadeInOut(tb,b,a0=0.2){return smooth(0,a0,tb)*(1-smooth(b.duration-0.3,b.duration-0.05,tb))}
const SKY_TOP='#070b16', SKY_HOR='#1d2740', GROUND_Y=1580;

// ---------------------------------------------------------------- storm scene primitives
function sky(){ const g=ctx.createLinearGradient(0,0,0,GROUND_Y); g.addColorStop(0,SKY_TOP); g.addColorStop(1,SKY_HOR); ctx.fillStyle=g; ctx.fillRect(0,0,W,H);
  ctx.fillStyle='#0b120d'; ctx.fillRect(0,GROUND_Y,W,H-GROUND_Y); ctx.fillStyle='rgba(120,160,120,0.15)'; ctx.fillRect(0,GROUND_Y,W,6); }
function cloudShape(){ ctx.beginPath(); ctx.ellipse(540,720,430,210,0,0,Math.PI*2); ctx.ellipse(330,560,190,150,0,0,Math.PI*2); ctx.ellipse(560,470,230,170,0,0,Math.PI*2);
  ctx.ellipse(780,580,180,140,0,0,Math.PI*2); ctx.rect(430,330,520,110); }
function cloudRain(t){ const rnd=mulberry(5); ctx.save(); ctx.strokeStyle='rgba(170,190,230,0.35)'; ctx.lineWidth=2;
  for(let i=0;i<90;i++){ const x=160+rnd()*760, sp=900+rnd()*500, ph=rnd()*700; const y=930+((t*sp+ph)%(GROUND_Y-930)); ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x-2,y-26); ctx.stroke(); } ctx.restore(); }
function cloudFlicker(t){ const k=Math.floor(t*2.3); const rnd=mulberry(k*7+1); const ph=(t*2.3)%1; return (rnd()<0.35 && ph<0.25) ? (1-ph/0.25)*0.6 : 0; }
function cloud(glow=0){ ctx.save(); cloudShape(); const g=ctx.createLinearGradient(0,320,0,930); g.addColorStop(0,'#6d7692'); g.addColorStop(0.5,'#3b4358'); g.addColorStop(1,'#1c2130');
  ctx.fillStyle=g; ctx.fill(); if(glow>0){ ctx.fillStyle=`rgba(190,200,255,${0.55*glow})`; ctx.fill(); } ctx.restore(); }
function rain(t,alpha=0.35){ const rnd=mulberry(99); ctx.save(); ctx.globalAlpha=alpha; ctx.strokeStyle='rgba(200,215,255,0.5)'; ctx.lineWidth=2;
  for(let i=0;i<160;i++){ const x0=rnd()*W*1.3-150, sp=1500+rnd()*900, ph=rnd()*H; const y=((t*sp+ph)%(H+200))-100; const x=x0+y*0.12;
    ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x-4,y-34); ctx.stroke(); } ctx.restore(); }
function sym(ch,x,y,size,col,alpha=1){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.beginPath(); ctx.arc(x,y,size*0.62,0,Math.PI*2); ctx.fillStyle='rgba(8,10,16,0.75)'; ctx.fill();
  ctx.lineWidth=3; ctx.strokeStyle=col; ctx.stroke(); text(ch,x,y+1,{size,weight:900,color:col,stroke:false,shadow:false}); ctx.restore(); }
function boltPath2D(x0,y0,x1,y1,seed,rough=0.22,levels=6){ const rnd=mulberry(seed); let pts=[[x0,y0],[x1,y1]];
  for(let lv=0;lv<levels;lv++){ const out=[pts[0]]; for(let i=0;i<pts.length-1;i++){ const a=pts[i],b=pts[i+1]; const mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2; const len=Math.hypot(b[0]-a[0],b[1]-a[1]);
      const nx=-(b[1]-a[1])/len, ny=(b[0]-a[0])/len; const d=(rnd()-0.5)*2*len*rough; out.push([mx+nx*d,my+ny*d],b); } pts=out; } return pts; }
function strokePath(pts,frac,width,color,glow,glowCol){ const n=Math.max(2,Math.floor(pts.length*frac)); ctx.save(); ctx.lineCap='round'; ctx.lineJoin='round';
  if(glow>0){ ctx.shadowColor=glowCol||color; ctx.shadowBlur=glow; }
  ctx.strokeStyle=color; ctx.lineWidth=width; ctx.beginPath(); ctx.moveTo(pts[0][0],pts[0][1]); for(let i=1;i<n;i++) ctx.lineTo(pts[i][0],pts[i][1]);
  if(frac<1&&n<pts.length){ const a=pts[n-1],b=pts[n]; const u=pts.length*frac-(n-1); ctx.lineTo(a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u); } ctx.stroke(); ctx.restore(); }
function label(txt,x,y,col,alpha=1,size=34){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; pill(txt,x,y,{size,bg:'rgba(8,10,16,0.8)',fg:col,border:col,weight:800}); ctx.restore(); }

// ---------------------------------------------------------------- 3D-backed beats
function beatFlash(tb,t,b){ rain(t,0.3);
  const out=1-smooth(b.duration-0.25,b.duration-0.03,tb); const k=tb-0.55; if(k>0){ const s=lerp(1.5,1,easeOutBack(k/0.3)); ctx.save(); ctx.translate(W/2,420); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,k)*out;
    text('5× HOTTER THAN',0,-60,{size:84,weight:900}); text('THE SUN’S SURFACE',0,50,{size:92,weight:900,color:C.yellow}); ctx.restore(); }
  const tSun=wordTime('flash','sun'); if(t>tSun){ ctx.save(); ctx.globalAlpha=smooth(0,0.15,t-tSun)*out; pill('30,000 °C',W/2,640,{size:54,bg:'rgba(255,122,26,0.95)',padX:40}); ctx.restore(); } }
function beatHook(tb,t,b){ rain(t,0.3);
  const out=1-smooth(b.duration-0.35,b.duration-0.05,tb); const k=tb-0.1; if(k>0){ const s=lerp(1.6,1,easeOutBack(k/0.3)); ctx.save(); ctx.translate(W/2,400); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,k)*out;
    text('HOW DOES',0,-60,{size:84,weight:900}); text('LIGHTNING WORK?',0,50,{size:96,weight:900,color:C.yellow}); ctx.restore(); }
  const tUp=wordTime('hook','up'); const k2=t-tUp; if(k2>0){ const s=lerp(2.2,1,easeOutBack(k2/0.35)); ctx.save(); ctx.translate(W/2,700); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,k2)*out;
    text('⬆ UP?!',0,0,{size:150,weight:900,color:C.orange,strokeW:20}); ctx.restore(); } }
function beatStreamer(tb,t,b){ rain(t,0.3);
  const tS=wordTime('streamer','streamers'); if(t>tS&&tb<4.0){ ctx.save(); ctx.globalAlpha=smooth(0,0.15,t-tS)*(1-smooth(3.7,4.0,tb)); label('UPWARD STREAMERS  ⬆',W/2,1180,C.blue); ctx.restore(); }
  const tC=wordTime('streamer','connects'); if(t>tC&&tb<4.0){ ctx.save(); ctx.globalAlpha=smooth(0,0.1,t-tC); text('…',W/2,1330,{size:120,weight:900,color:C.yellow}); ctx.restore(); }
  if(tb>=4.0) flash(t,b.start+4.0,{dur:0.25,peak:0.8}); }
function beatReturn(tb,t,b){
  const tWave=wordTime('return','wave'), tThird=wordTime('return','third'), tUp=wordTime('return','going');
  if(t<tWave){ rain(t,0.3); flash(t,b.start+7/24,{dur:0.25,peak:0.8});
    const tR=wordTime('return','return'); if(t>tR){ ctx.save(); ctx.globalAlpha=smooth(0,0.15,t-tR); label('RETURN STROKE',W/2,1180,C.yellow,1,40); ctx.restore(); } return; }
  // 2D takeover: the wave races UP the channel
  sky(); cloud(0.15); const pts=boltPath2D(560,930,520,GROUND_Y,7,0.18,6);
  strokePath(pts,1,6,'rgba(150,130,255,0.55)',18,'rgba(140,120,255,0.8)');
  const k=((t-tWave)%1.1)/1.1; const front=1-easeOutCubic(Math.min(1,k/0.55)); // 1 = ground, 0 = cloud
  const n=pts.length; const lit=pts.slice(Math.floor(front*(n-1))); if(lit.length>1){ strokePath(lit,1,16,'#ffffff',40,'rgba(200,220,255,1)'); strokePath(lit,1,7,'#ffffff',0); }
  const fy=lerp(930,GROUND_Y,front); text('⬆',660,fy,{size:110,weight:900,color:C.yellow,align:'left'});
  // mast
  ctx.fillStyle='#2a2f3a'; ctx.fillRect(510,GROUND_Y-90,10,90); ctx.fillStyle='#ff3b3b'; ctx.beginPath(); ctx.arc(515,GROUND_Y-95,6,0,Math.PI*2); ctx.fill();
  label('CURRENT RACES UP',W/2,1110,C.yellow,smooth(0,0.2,t-tWave),40);
  if(t>tThird){ ctx.save(); const kk=t-tThird; const s=lerp(1.6,1,easeOutBack(kk/0.3)); ctx.translate(W/2,330); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,kk);
    text('⅓ THE SPEED OF LIGHT',0,0,{size:66,weight:900,color:C.white}); text('100,000,000 m/s  •  30,000 A',0,70,{size:36,weight:700,color:'rgba(255,255,255,0.8)'}); ctx.restore(); }
  if(t>tUp){ const kk=t-tUp; const s=lerp(2.2,1,easeOutBack(kk/0.35)); ctx.save(); ctx.translate(W/2,560); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,kk); text('GOING UP ⬆',0,0,{size:120,weight:900,color:C.yellow,strokeW:18}); ctx.restore(); }
}
function beatFlicker(tb,t,b){
  const tSame=wordTime('flicker','same'); const strokes=[3/24,3/24+0.6,3/24+1.0,3/24+1.3];
  if(t<tSame){ rain(t,0.3); let n=0; strokes.forEach(s=>{ if(tb>=s) n++; flash(t,b.start+s,{dur:0.2,peak:n===1?0.8:0.45}); });
    if(n>0){ ctx.save(); ctx.globalAlpha=1; pill('STROKE '+n,W/2,1180,{size:64,bg:'rgba(8,10,16,0.85)',fg:C.yellow,border:C.yellow,padX:40}); ctx.restore(); } return; }
  sky(); cloud(0.1); const pts=boltPath2D(560,930,520,GROUND_Y,7,0.18,6); strokePath(pts,1,5,'rgba(150,130,255,0.45)',14,'rgba(140,120,255,0.8)');
  const k=t-tSame; const per=0.55; const idx=Math.floor(k/per)%4; const ph=(k%per)/per;
  if(ph<0.45){ const a=1-ph/0.45; strokePath(pts,1,14*a+4,`rgba(255,255,255,${0.9*a+0.1})`,36*a,'rgba(200,220,255,1)'); }
  for(let i=0;i<4;i++){ sym(String(i+1),300+i*160,1150,36,i<=idx?C.yellow:'rgba(255,255,255,0.35)'); }
  label('SAME CHANNEL  •  ~40 ms APART',W/2,1250,C.blue,smooth(0,0.2,k),36);
  ctx.fillStyle='#2a2f3a'; ctx.fillRect(510,GROUND_Y-90,10,90);
}
function beatCta(tb,t,b){ rain(t,0.25);
  const tFollow=wordTime('cta','follow'); const kf=t-tFollow+0.1; if(kf>0){ const s=lerp(1.6,1,easeOutBack(kf/0.35))*(1+0.03*Math.sin(kf*6));
    ctx.save(); ctx.translate(W/2,860); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,kf); pill('＋ FOLLOW',0,0,{size:76,bg:'#FF2D55',fg:'#fff',padX:54}); ctx.restore();
    ctx.save(); ctx.globalAlpha=smooth(0.2,0.45,kf); text('more physics like this',W/2,980,{size:46,weight:700}); ctx.restore(); }
  const fo=smooth(b.duration-0.45,b.duration-0.02,tb); if(fo>0){ctx.fillStyle=`rgba(0,0,0,${fo})`; ctx.fillRect(0,0,W,H)} }

// ---------------------------------------------------------------- 2D explainer beats
function particles(t,showCharge){ const rnd=mulberry(3);
  for(let i=0;i<70;i++){ const x=200+rnd()*680, ph=rnd()*6, sp=90+rnd()*70, big=rnd()<0.35; const y0=420+rnd()*480;
    if(big){ const y=((y0+ (t*sp*0.9)-400)%520)+400; ctx.beginPath(); ctx.arc(x,y,13,0,Math.PI*2); ctx.fillStyle='#9aa3b5'; ctx.fill(); if(showCharge) text('−',x,y+1,{size:22,weight:900,color:'#0b1020',stroke:false,shadow:false}); }
    else { const y=920-(((y0+t*sp)-400)%520); ctx.save(); ctx.translate(x,y); ctx.rotate(t*2+ph); ctx.beginPath(); for(let k=0;k<6;k++){ const a=k*Math.PI/3; ctx.lineTo(9*Math.cos(a),9*Math.sin(a)); } ctx.closePath(); ctx.fillStyle='#e8f0ff'; ctx.fill(); ctx.restore();
      if(showCharge) text('+',x,y+1,{size:20,weight:900,color:'#1a1500',stroke:false,shadow:false}); } }
  // collision sparks
  for(let i=0;i<14;i++){ const x=230+rnd()*620, y=460+rnd()*420, per=1.3+rnd()*1.2, ph=rnd()*per; const k=((t+ph)%per)/per; if(k<0.18){ const a=1-k/0.18; ctx.save(); ctx.globalAlpha=a; ctx.strokeStyle='#fff6b0'; ctx.lineWidth=3;
      for(let s=0;s<6;s++){ const an=s*Math.PI/3; ctx.beginPath(); ctx.moveTo(x+8*Math.cos(an),y+8*Math.sin(an)); ctx.lineTo(x+22*Math.cos(an),y+22*Math.sin(an)); ctx.stroke(); } ctx.restore(); } }
}
function updrafts(t){ ctx.save(); ctx.strokeStyle='rgba(255,255,255,0.35)'; ctx.lineWidth=5; ctx.lineCap='round';
  for(let i=0;i<6;i++){ const x=260+i*110; for(let j=0;j<5;j++){ const y=930-(((j*110)+t*220)%520); ctx.beginPath(); ctx.moveTo(x,y+30); ctx.lineTo(x,y); ctx.moveTo(x-10,y+12); ctx.lineTo(x,y); ctx.lineTo(x+10,y+12); ctx.stroke(); } } ctx.restore(); }
function beatCloud(tb,t,b){ sky(); cloud(cloudFlicker(t)); cloudRain(t); const tUp=wordTime('cloud','updrafts'), tCol=wordTime('cloud','collision'), tSteal=wordTime('cloud','steals');
  if(t>tUp) updrafts(t); particles(t, t>tSteal);
  if(t>tUp){ label('UPDRAFT ⬆',260,1010,C.white,smooth(0,0.2,t-tUp),32); }
  if(t>tUp+0.8){ label('ICE CRYSTALS',740,1010,'#e8f0ff',smooth(0,0.2,t-tUp-0.8),32); label('HAIL (graupel)',500,1090,'#9aa3b5',smooth(0,0.2,t-tUp-1.3),32); }
  if(t>tCol){ ctx.save(); ctx.globalAlpha=smooth(0,0.2,t-tCol); pill('EVERY COLLISION TRANSFERS CHARGE',W/2,1240,{size:36,bg:'rgba(255,214,10,0.95)',fg:'#1a1500'}); ctx.restore(); }
  text('INSIDE A THUNDERCLOUD',W/2,240,{size:46,weight:900,alpha:fadeInOut(tb,b)}); }
function chargeSymbols(t,tTop,tBot,tGround){ const rnd=mulberry(8);
  for(let i=0;i<22;i++){ const x=300+rnd()*480, y=400+rnd()*150, d=rnd()*1.2; if(t>tTop+d) sym('+',x,y,30,C.yellow,smooth(0,0.2,t-tTop-d)); }
  for(let i=0;i<22;i++){ const x=220+rnd()*640, y=800+rnd()*110, d=rnd()*1.2; if(t>tBot+d) sym('−',x,y,30,C.blue,smooth(0,0.2,t-tBot-d)); }
  for(let i=0;i<16;i++){ const x=120+rnd()*840, d=rnd()*1.0; if(t>tGround+d) sym('+',x,GROUND_Y+60,30,C.yellow,smooth(0,0.2,t-tGround-d)); } }
function fieldLines(alpha){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.setLineDash([14,14]); ctx.strokeStyle='rgba(255,214,10,0.45)'; ctx.lineWidth=3;
  for(let i=0;i<7;i++){ const x=200+i*113; ctx.beginPath(); ctx.moveTo(x,950); ctx.lineTo(x+(i-3)*25,GROUND_Y-10); ctx.stroke(); } ctx.restore(); }
function beatCharge(tb,t,b){ sky(); cloud(cloudFlicker(t)); cloudRain(t); const tTop=wordTime('charge','positive'), tBot=wordTime('charge','negative'), tG=wordTime('charge','ground'), tP2=wordTime('charge','positive',1);
  chargeSymbols(t,tTop,tBot,tP2); if(t>tP2) fieldLines(smooth(0,0.4,t-tP2));
  if(t>tTop) label('+ TOP',W/2,300,C.yellow,smooth(0,0.2,t-tTop)); if(t>tBot) label('− BOTTOM',W/2,1010,C.blue,smooth(0,0.2,t-tBot));
  if(t>tP2) label('GROUND GOES +',W/2,1700,C.yellow,smooth(0,0.2,t-tP2));
  text('CHARGE SEPARATES',W/2,240,{size:46,weight:900,alpha:fadeInOut(tb,b)}); }
function beatField(tb,t,b){ sky(); cloud(cloudFlicker(t)*0.5); cloudRain(t); const tV=wordTime('field','volts'), tIns=wordTime('field','insulator'), tNot=wordTime("field","isn't");
  chargeSymbols(t,b.start-5,b.start-5,b.start-5); fieldLines(1);
  // voltmeter
  const v=300e6*easeOutCubic(smooth(b.start+0.3,tV+0.6,t)); panel(90,1040,900,230,1);
  text('CLOUD ↔ GROUND',W/2,1085,{size:30,weight:700,color:'rgba(255,255,255,0.75)',stroke:false});
  text(fmtNum(v)+' V',W/2,1160,{size:72,weight:900,color:C.yellow,stroke:false});
  const bw=760; ctx.fillStyle='rgba(255,255,255,0.1)'; rr(160,1215,bw,22,11); ctx.fill(); ctx.fillStyle=C.yellow; rr(160,1215,bw*v/300e6,22,11); ctx.fill();
  if(t>tIns){ ctx.save(); ctx.globalAlpha=smooth(0,0.2,t-tIns); pill('AIR BREAKS DOWN AT ~3,000,000 V/m',W/2,1340,{size:34,bg:'rgba(8,10,16,0.85)',fg:C.orange,border:C.orange}); ctx.restore();
    // nervous sparks at the cloud base
    const rnd=mulberry(Math.floor(t*12)); for(let i=0;i<4;i++){ const x=380+rnd()*320, y=930+rnd()*30; const p=boltPath2D(x,y,x+(rnd()-0.5)*60,y+40+rnd()*50,i+Math.floor(t*12),0.3,3); strokePath(p,1,2,'rgba(200,190,255,0.7)',10,'rgba(170,150,255,1)'); } }
  if(t>tNot){ const p=boltPath2D(560,930,540,1180,11,0.25,5); strokePath(p,smooth(0,0.25,t-tNot),4,'#d8d0ff',22,'rgba(170,150,255,1)'); flash(t,tNot,{dur:0.2,peak:0.3}); }
  text('THE FIELD BUILDS',W/2,240,{size:46,weight:900,alpha:fadeInOut(tb,b)}); }
const LEADER=(()=>{ const rnd=mulberry(17); const steps=[]; let x=560,y=930; for(let i=0;i<34;i++){ const ang=Math.PI/2+(rnd()-0.5)*1.2; const len=38+rnd()*22; const nx=x+Math.cos(ang)*len, ny=y+Math.sin(ang)*len; steps.push({x0:x,y0:y,x1:nx,y1:ny,branch: rnd()<0.3 ? {dx:(rnd()-0.5)*160, dy:40+rnd()*90, seed:i} : null}); x=nx; y=ny; if(y>GROUND_Y-230) break; } return steps; })();
function beatLeader(tb,t,b){ sky(); cloud(0.05); cloudRain(t); chargeSymbols(t,b.start-5,b.start-5,b.start-5);
  const tStep=wordTime('leader','steps'), tBranch=wordTime('leader','branching'), tName=wordTime('leader','stepped');
  const per=0.13; const n=Math.min(LEADER.length, Math.floor((tb-0.4)/per)); 
  for(let i=0;i<n;i++){ const s=LEADER[i]; const age=tb-0.4-i*per; const fresh=age<0.12; ctx.save(); ctx.lineCap='round'; ctx.shadowColor='rgba(170,150,255,1)'; ctx.shadowBlur=fresh?30:12;
    ctx.strokeStyle=fresh?'#ffffff':'rgba(200,190,255,0.8)'; ctx.lineWidth=fresh?7:4; ctx.beginPath(); ctx.moveTo(s.x0,s.y0); ctx.lineTo(s.x1,s.y1); ctx.stroke(); ctx.restore();
    if(s.branch&&age>0.1){ const p=boltPath2D(s.x1,s.y1,s.x1+s.branch.dx,s.y1+s.branch.dy,s.branch.seed,0.3,4); strokePath(p,Math.min(1,(age-0.1)/0.4),2.5,'rgba(190,180,255,0.6)',10,'rgba(170,150,255,1)'); } }
  if(n>0&&n<LEADER.length){ const s=LEADER[n-1]; const age=tb-0.4-(n-1)*per; if(age<0.06){ ctx.save(); ctx.globalAlpha=1-age/0.06; ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(s.x1,s.y1,14,0,Math.PI*2); ctx.fill(); ctx.restore(); } }
  if(t>tStep){ label('~50 m PER STEP',W/2,1060,'#d8d0ff',smooth(0,0.2,t-tStep),34); }
  if(t>tName){ ctx.save(); const k=t-tName; const s=lerp(1.5,1,easeOutBack(k/0.3)); ctx.translate(W/2,1200); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,k); pill('THE STEPPED LEADER',0,0,{size:48,bg:'rgba(120,100,255,0.95)',padX:40}); ctx.restore(); }
  ctx.fillStyle='#2a2f3a'; ctx.fillRect(510,GROUND_Y-90,10,90);
  text('A PATH FORMS',W/2,240,{size:46,weight:900,alpha:fadeInOut(tb,b)}); }
function beatHeat(tb,t,b){ sky(); cloud(0.08); cloudRain(t);
  const tDeg=wordTime('heat','degrees'), tExp=wordTime('heat','explodes'), tTh=wordTime('heat','thunder');
  const pts=boltPath2D(560,930,520,GROUND_Y,7,0.18,6); strokePath(pts,1,10,'#ffffff',30,'rgba(200,220,255,1)');
  // shock rings
  if(t>tExp){ for(let i=0;i<5;i++){ const k=((t-tExp)*0.9+i*0.22)%1.1; if(k<1){ const r=60+k*700; ctx.save(); ctx.globalAlpha=(1-k)*0.7; ctx.strokeStyle='#fff'; ctx.lineWidth=10*(1-k)+2; ctx.beginPath(); ctx.ellipse(540,1250,r,r*0.55,0,0,Math.PI*2); ctx.stroke(); ctx.restore(); } } }
  // temperature gauge
  const temp=30000*easeOutCubic(smooth(b.start+0.2,tDeg+0.5,t)); panel(90,1040,900,250,1);
  text('CHANNEL TEMPERATURE',W/2,1085,{size:30,weight:700,color:'rgba(255,255,255,0.75)',stroke:false});
  text(fmtNum(temp)+' °C',W/2,1160,{size:76,weight:900,color:C.orange,stroke:false});
  const bw=760; ctx.fillStyle='rgba(255,255,255,0.1)'; rr(160,1215,bw,24,12); ctx.fill(); const g=ctx.createLinearGradient(160,0,920,0); g.addColorStop(0,C.yellow); g.addColorStop(1,'#ff3b3b'); ctx.fillStyle=g; rr(160,1215,bw*temp/30000,24,12); ctx.fill();
  const sx=160+bw*5500/30000; ctx.strokeStyle=C.yellow; ctx.lineWidth=4; ctx.beginPath(); ctx.moveTo(sx,1200); ctx.lineTo(sx,1255); ctx.stroke(); text('☀ SUN 5,500 °C',sx+10,1270,{size:26,weight:800,color:C.yellow,align:'left',stroke:false});
  if(t>tExp) label('AIR EXPLODES OUTWARD',W/2,1360,C.white,smooth(0,0.2,t-tExp),36);
  stamp('THUNDER',W/2,700,tTh,t,{color:C.white,size:140,rot:-0.06});
  text('IN MICROSECONDS',W/2,240,{size:46,weight:900,alpha:fadeInOut(tb,b)}); }
function beatThunder(tb,t,b){ const a=fadeInOut(tb,b); const px=70,py=430,pw=940,ph=900; panel(px,py,pw,ph,a); ctx.save(); ctx.globalAlpha=a;
  const tCount=wordTime('thunder','count'), tThree=wordTime('thunder','three'), tKm=wordTime('thunder','kilometers');
  text('HOW FAR AWAY WAS IT?',W/2,py+60,{size:40,weight:900,stroke:false});
  text('d  =  343 m/s  ×  t',W/2,py+160,{size:70,weight:800,stroke:false});
  text('speed of sound  ×  seconds you counted',W/2,py+225,{size:28,weight:700,color:'rgba(255,255,255,0.7)',stroke:false});
  // scene: bolt left, person right, sound arcs travel
  const bx=px+180, personX=px+760, baseY=py+640; const p=boltPath2D(bx,py+300,bx-20,baseY,5,0.2,5); strokePath(p,1,5,'#fff',20,'rgba(200,220,255,1)');
  ctx.save(); ctx.strokeStyle='#E8ECF2'; ctx.fillStyle='#E8ECF2'; ctx.lineWidth=8; ctx.lineCap='round'; ctx.beginPath(); ctx.arc(personX,baseY-150,22,0,Math.PI*2); ctx.fill();
  ctx.beginPath(); ctx.moveTo(personX,baseY-128); ctx.lineTo(personX,baseY-50); ctx.lineTo(personX-30,baseY); ctx.moveTo(personX,baseY-50); ctx.lineTo(personX+30,baseY); ctx.moveTo(personX-35,baseY-100); ctx.lineTo(personX+35,baseY-100); ctx.stroke(); ctx.restore();
  ctx.strokeStyle='rgba(255,255,255,0.3)'; ctx.lineWidth=3; ctx.beginPath(); ctx.moveTo(px+60,baseY+10); ctx.lineTo(px+pw-60,baseY+10); ctx.stroke();
  const k=t-tCount; if(k>0){ const sec=Math.min(3,k/0.75); for(let i=1;i<=3;i++){ const r=(sec/3)*(personX-bx)-i*60; if(r>0&&r<personX-bx+40){ ctx.save(); ctx.globalAlpha=0.6; ctx.strokeStyle=C.blue; ctx.lineWidth=5; ctx.beginPath(); ctx.arc(bx,baseY-120,r,-0.6,0.6); ctx.stroke(); ctx.restore(); } }
    for(let i=1;i<=3;i++){ if(sec>=i-0.02) text(String(i),bx+((personX-bx)*i/3)-60,baseY-240,{size:70,weight:900,color:i===Math.ceil(sec)?C.yellow:C.white,stroke:false}); } }
  if(t>tThree){ ctx.save(); ctx.globalAlpha=smooth(0,0.2,t-tThree); pill('3 s  ≈  1 km',px+pw/2-170,py+ph-70,{size:40,bg:'rgba(77,184,255,0.95)',fg:'#06182a'}); ctx.restore(); }
  if(t>tKm){ ctx.save(); ctx.globalAlpha=smooth(0,0.2,t-tKm); pill('5 s  ≈  1 mile',px+pw/2+170,py+ph-70,{size:40,bg:'rgba(255,214,10,0.95)',fg:'#1a1500'}); ctx.restore(); }
  ctx.restore(); }
function beatPayoff(tb,t,b){ sky(); const tFifty=wordTime('payoff','fifty'), tSec=wordTime('payoff','second');
  const cx=540,cy=900,R=380; ctx.save(); ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); const g=ctx.createRadialGradient(cx-120,cy-120,40,cx,cy,R); g.addColorStop(0,'#28406a'); g.addColorStop(1,'#0c1830'); ctx.fillStyle=g; ctx.fill();
  ctx.clip(); ctx.strokeStyle='rgba(120,170,255,0.25)'; ctx.lineWidth=2; for(let i=-3;i<=3;i++){ ctx.beginPath(); ctx.ellipse(cx,cy,R,Math.abs(R*Math.sin(i*0.4)),0,0,Math.PI*2); ctx.stroke(); ctx.beginPath(); ctx.ellipse(cx,cy,Math.abs(R*Math.cos(i*0.4)),R,0,0,Math.PI*2); ctx.stroke(); }
  // blobby continents
  const rnd=mulberry(31); ctx.fillStyle='rgba(90,140,90,0.55)'; for(let i=0;i<9;i++){ const x=cx+(rnd()-0.5)*560, y=cy+(rnd()-0.5)*560; for(let j=0;j<5;j++){ ctx.beginPath(); ctx.arc(x+(rnd()-0.5)*120,y+(rnd()-0.5)*120,30+rnd()*50,0,Math.PI*2); ctx.fill(); } }
  // flashes: ~50 per second rendered as random pops
  const r2=mulberry(Math.floor(t*24)); for(let i=0;i<4;i++){ const a=r2()*Math.PI*2, rr0=Math.sqrt(r2())*R*0.95; const x=cx+rr0*Math.cos(a), y=cy+rr0*Math.sin(a); ctx.save(); ctx.globalAlpha=0.9; ctx.fillStyle='#fff'; ctx.shadowColor='#fff'; ctx.shadowBlur=20; ctx.beginPath(); ctx.arc(x,y,5+r2()*6,0,Math.PI*2); ctx.fill(); ctx.restore(); }
  ctx.restore();
  const cnt=Math.floor(50*tb*(t>tFifty?1:0)); if(t>tFifty){ text(fmtNum(cnt),W/2,330,{size:110,weight:900,color:C.yellow}); text('bolts since this beat started',W/2,420,{size:34,weight:700,color:'rgba(255,255,255,0.8)'}); }
  if(t>tSec){ ctx.save(); ctx.globalAlpha=smooth(0,0.2,t-tSec); pill('~50 PER SECOND  •  4,000,000 A DAY',W/2,1400,{size:38,bg:'rgba(255,214,10,0.95)',fg:'#1a1500'}); ctx.restore(); }
  text('RIGHT NOW, ON EARTH',W/2,240,{size:46,weight:900,alpha:fadeInOut(tb,b)}); }

window.BEATS = {
  draw: {flash:beatFlash,hook:beatHook,cloud:beatCloud,charge:beatCharge,field:beatField,leader:beatLeader,streamer:beatStreamer,return:beatReturn,heat:beatHeat,thunder:beatThunder,flicker:beatFlicker,payoff:beatPayoff,cta:beatCta},
  cutFlash: ['hook','cloud','streamer','return','heat','thunder','flicker','payoff','cta'],
  keywords: ['lightning','up','down','sun','cloud','updrafts','ice','hail','collision','charge','positive','negative','ground','volts','insulator',"isn't",'channel','leader','steps','branching','streamers','connects','boom','return','stroke','third','light','flash','thirty','thousand','explodes','thunder','seconds','three','kilometers','flicker','strokes','fifty','second','bolts'],
};
