// Beat graphics for video 006: how tornadoes work (toy-diorama farm, blocky cow as the running gag).
// Bright set: white type with the usual black stroke, one yellow accent, cream explainer panels with dark ink.
// Labels can ride 3D objects via trackPos(name) (scene_tornado.py exports build/tracks/<shot>.json).
const HEAD_Y=300, HEAD2_Y=382, CAP_Y=485;
const INK='#1C1A22', CREAM='rgba(255,250,242,0.94)', GREY='#8E93A0', SKY_BLUE='#4DB8FF';
function fadeOut(tb,b,pad=0.3){return 1-smooth(b.duration-pad,b.duration-0.05,tb)}
function twoTone(parts,x,y,size,strokeW=12){ font(900,size); const ws=parts.map(p=>ctx.measureText(p[0]).width); const total=ws.reduce((a,b)=>a+b,0); let cx=x-total/2;
  parts.forEach((p,i)=>{ text(p[0],cx+ws[i]/2,y,{size,weight:900,color:p[1],strokeW}); cx+=ws[i]; }); }
function headline(parts,alpha,size=72){ // fitted to the 846 px readable width (pipeline/safe_area.json)
  if(alpha<=0) return; for(const line of parts){ if(!line) continue; font(900,size); const w=line.reduce((a,p)=>a+ctx.measureText(p[0]).width,0); if(w>846) size=Math.floor(size*846/w); }
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; twoTone(parts[0],W/2,HEAD_Y,size); if(parts[1]) twoTone(parts[1],W/2,HEAD2_Y,size); ctx.restore(); }
function popIn(k,dur=0.3){ return lerp(1.5,1,easeOutBack(k/dur)); }
function lightPanel(x,y,w,h,alpha=1){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.shadowColor='rgba(0,0,0,0.25)'; ctx.shadowBlur=30; ctx.shadowOffsetY=10; rr(x,y,w,h,36); ctx.fillStyle=CREAM; ctx.fill();
  ctx.shadowColor='transparent'; ctx.lineWidth=3; ctx.strokeStyle='rgba(28,26,34,0.12)'; ctx.stroke(); ctx.restore(); }
function inkText(str,x,y,{size=40,weight=800,align='center',alpha=1,color=INK}={}){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; text(str,x,y,{size,weight,color,align,stroke:false,shadow:false}); ctx.restore(); }
function thinLabel(txt,x,y,alpha,size=34,align='center',color=C.white){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; text(txt,x,y,{size,weight:800,color,align,strokeW:8}); ctx.restore(); }
function arrowLine(x0,y0,x1,y1,{color=C.white,width=8,head=26,alpha=1,dash=null}={}){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.strokeStyle=color; ctx.fillStyle=color; ctx.lineWidth=width; ctx.lineCap='round'; ctx.lineJoin='round';
  ctx.shadowColor='rgba(0,0,0,0.45)'; ctx.shadowBlur=8; if(dash) ctx.setLineDash(dash); ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x1,y1); ctx.stroke(); ctx.setLineDash([]);
  const a=Math.atan2(y1-y0,x1-x0); ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x1-head*Math.cos(a-0.5),y1-head*Math.sin(a-0.5)); ctx.lineTo(x1-head*Math.cos(a+0.5),y1-head*Math.sin(a+0.5)); ctx.closePath(); ctx.fill(); ctx.restore(); }

// ---- a label pinned to a tracked 3D object (pointer line + pill), kept inside the readable area
function tagAt(name,label,t0,t,{dx=-60,dy=-170,fg=C.yellow,bg='rgba(10,12,18,0.85)',size=32,out=1,instant=false}={}){
  const p=trackPos(name); if(!p||t<t0) return; const k=t-t0+(instant?0.3:0); const a=smooth(0,0.15,k)*out; if(a<=0) return;
  const hw=measure(label,size,900)/2+22; const y=clamp(p[1]+dy,560,1000), x=clamp(p[0]+dx,120+hw,(y+size>1040?850:960)-hw);   // whole pill inside the readable area (pipeline/safe_area.json), below the captions
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a;
  ctx.strokeStyle='rgba(255,255,255,0.95)'; ctx.lineWidth=4; ctx.shadowColor='rgba(0,0,0,0.5)'; ctx.shadowBlur=6; ctx.beginPath(); ctx.moveTo(x,y+size*0.85); ctx.lineTo(p[0],p[1]); ctx.stroke();
  ctx.shadowColor='transparent'; ctx.fillStyle=fg; ctx.beginPath(); ctx.arc(p[0],p[1],9,0,Math.PI*2); ctx.fill();
  const s=popIn(k); ctx.translate(x,y); ctx.scale(s,s); pill(label,0,0,{size,weight:900,bg,fg,padX:22}); ctx.restore(); }

// ---- figure skater (ink on cream): arms out (slow) -> arms in (fast). phase = spin angle; the two hands sit at +-r*cos(phase).
function skaterFig(x,y,s,armsIn,phase,alpha=1){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s); ctx.lineCap='round'; ctx.lineJoin='round';
  ctx.fillStyle='rgba(28,26,34,0.15)'; ctx.beginPath(); ctx.ellipse(0,6,lerp(70,40,armsIn),12,0,0,Math.PI*2); ctx.fill();   // shadow on the ice
  ctx.strokeStyle=INK; ctx.lineWidth=6; ctx.beginPath(); ctx.moveTo(-24,0); ctx.lineTo(24,0); ctx.stroke();                      // blade
  ctx.lineWidth=12; ctx.beginPath(); ctx.moveTo(0,-4); ctx.lineTo(0,-120); ctx.stroke();                                        // legs together
  const flare=lerp(52,76,armsIn); ctx.fillStyle=C.red; ctx.beginPath(); ctx.moveTo(-16,-168); ctx.lineTo(16,-168); ctx.lineTo(flare,-108); ctx.lineTo(-flare,-108); ctx.closePath(); ctx.fill();   // skirt
  ctx.fillStyle=C.red; rr(-20,-235,40,72,12); ctx.fill();                                                                       // torso
  ctx.fillStyle=INK; ctx.beginPath(); ctx.arc(0,-266,26,0,Math.PI*2); ctx.fill(); ctx.beginPath(); ctx.arc(-14,-284,12,0,Math.PI*2); ctx.fill();   // head + bun
  const r=lerp(118,16,armsIn), hy=lerp(-222,-308,armsIn), sy=-222;
  for(const sg of [1,-1]){ const hx=sg*r*Math.cos(phase); const depth=sg*Math.sin(phase); ctx.strokeStyle=INK; ctx.lineWidth=depth>0?12:9; ctx.globalAlpha=ctx.globalAlpha*(depth>0?1:0.75);
    ctx.beginPath(); ctx.moveTo(0,sy); ctx.quadraticCurveTo(hx*0.5,lerp(sy,hy,0.35)-10*armsIn,hx,hy); ctx.stroke(); ctx.globalAlpha=ctx.globalAlpha/(depth>0?1:0.75); }
  ctx.restore(); }
// spin lines around a figure: arcs that rotate with phase; count/alpha scale with speed
function spinLines(x,y,rx,ry,phase,speed,alpha=1,color=INK){ if(alpha<=0||speed<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha*clamp(speed,0,1); ctx.strokeStyle=color; ctx.lineWidth=5; ctx.lineCap='round';
  const n=3; for(let i=0;i<n;i++){ const a0=phase*2+i*2*Math.PI/n; ctx.beginPath(); ctx.ellipse(x,y,rx,ry,0,a0,a0+0.9); ctx.stroke(); } ctx.restore(); }
// a small tornado icon with rotating stripes (phase), ink on cream
function funnelIcon(x,y,s,phase,alpha=1){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s);
  ctx.fillStyle='rgba(28,26,34,0.15)'; ctx.beginPath(); ctx.ellipse(0,6,40,10,0,0,Math.PI*2); ctx.fill();
  const prof=u=>lerp(130,12,Math.pow(u,0.8));   // half-width from top (u=0) to ground (u=1)
  ctx.beginPath(); ctx.moveTo(-prof(0),-300); for(let i=1;i<=20;i++){ const u=i/20; ctx.lineTo(prof(u)*(1+0.06*Math.sin(u*7+phase*0.5)),lerp(-300,0,u)); } for(let i=20;i>=0;i--){ const u=i/20; ctx.lineTo(-prof(u)*(1+0.06*Math.sin(u*7+phase*0.5+1)),lerp(-300,0,u)); } ctx.closePath();
  ctx.fillStyle='#A9AEBB'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=5; ctx.stroke();
  ctx.save(); ctx.clip(); ctx.strokeStyle='rgba(28,26,34,0.5)'; ctx.lineWidth=6;   // stripes: front half of rotating ellipses
  for(let i=0;i<8;i++){ const u=(i+0.5)/8; const yy=lerp(-300,0,u); const rx=prof(u), ry=rx*0.25; const a0=phase*(1+u)+i*0.7; ctx.beginPath(); ctx.ellipse(0,yy,rx,ry,0,a0,a0+1.4); ctx.stroke(); } ctx.restore();
  ctx.fillStyle='rgba(120,95,60,0.6)'; ctx.beginPath(); ctx.ellipse(0,0,70,16,0,0,Math.PI*2); ctx.fill();   // dust
  ctx.restore(); }
// speedometer: 270-degree gauge, red zone, needle, digital readout
function gauge(x,y,r,value,max,alpha,{label='SPIN SPEED',unit='mph',red=200}={}){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha;
  ctx.shadowColor='rgba(0,0,0,0.35)'; ctx.shadowBlur=24; ctx.shadowOffsetY=8; ctx.fillStyle='rgba(255,250,242,0.95)'; ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.fill(); ctx.shadowColor='transparent';
  const a0=Math.PI*0.75, sweep=Math.PI*1.5, ang=v=>a0+sweep*clamp(v/max,0,1);
  ctx.lineWidth=r*0.14; ctx.lineCap='butt'; ctx.strokeStyle='rgba(28,26,34,0.12)'; ctx.beginPath(); ctx.arc(x,y,r*0.78,a0,a0+sweep); ctx.stroke();
  ctx.strokeStyle='rgba(255,59,59,0.85)'; ctx.beginPath(); ctx.arc(x,y,r*0.78,ang(red),a0+sweep); ctx.stroke();
  ctx.strokeStyle=C.yellow; ctx.beginPath(); ctx.arc(x,y,r*0.78,a0,ang(value)); ctx.stroke();
  ctx.strokeStyle=INK; ctx.lineWidth=3; for(let v=0;v<=max;v+=50){ const a=ang(v); ctx.beginPath(); ctx.moveTo(x+Math.cos(a)*r*0.64,y+Math.sin(a)*r*0.64); ctx.lineTo(x+Math.cos(a)*r*0.70,y+Math.sin(a)*r*0.70); ctx.stroke();
    if(v%100===0) inkText(String(v),x+Math.cos(a)*r*0.52,y+Math.sin(a)*r*0.52,{size:r*0.13,weight:800,color:'rgba(28,26,34,0.7)'}); }
  const a=ang(value); ctx.strokeStyle=C.red; ctx.lineWidth=r*0.05; ctx.lineCap='round'; ctx.beginPath(); ctx.moveTo(x-Math.cos(a)*r*0.1,y-Math.sin(a)*r*0.1); ctx.lineTo(x+Math.cos(a)*r*0.62,y+Math.sin(a)*r*0.62); ctx.stroke();
  ctx.fillStyle=INK; ctx.beginPath(); ctx.arc(x,y,r*0.07,0,Math.PI*2); ctx.fill();
  pill(fmtNum(value)+' '+unit,x,y+r*0.62,{size:r*0.16,weight:900,bg:INK,fg:C.yellow,padX:r*0.1}); inkText(label,x,y+r*0.88,{size:r*0.11,weight:900,color:'rgba(28,26,34,0.7)'}); ctx.restore(); }
// office chair with a seated figure, side view; arms via the skater trick
function chairFig(x,y,s,armsIn,phase,alpha=1){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.scale(s,s); ctx.lineCap='round'; ctx.lineJoin='round'; ctx.strokeStyle=INK; ctx.fillStyle=INK;
  ctx.lineWidth=8; for(let i=0;i<5;i++){ const a=i*2*Math.PI/5+phase; const ex=Math.cos(a)*90, ey=Math.sin(a)*26; ctx.beginPath(); ctx.moveTo(0,-20); ctx.lineTo(ex,ey-20); ctx.stroke(); ctx.beginPath(); ctx.arc(ex,ey-12,9,0,Math.PI*2); ctx.fill(); }   // star base + casters
  ctx.lineWidth=12; ctx.beginPath(); ctx.moveTo(0,-24); ctx.lineTo(0,-120); ctx.stroke();                                       // column
  ctx.fillStyle='#3A6FD8'; rr(-70,-150,140,30,12); ctx.fill(); rr(40,-300,26,160,10); ctx.fill();                                // seat + backrest
  ctx.fillStyle=C.red; rr(-26,-290,52,140,14); ctx.fill();                                                                       // torso
  ctx.strokeStyle=INK; ctx.lineWidth=12; ctx.beginPath(); ctx.moveTo(-10,-150); ctx.lineTo(-60,-120); ctx.lineTo(-60,-40); ctx.stroke();   // legs
  ctx.fillStyle=INK; ctx.beginPath(); ctx.arc(0,-322,28,0,Math.PI*2); ctx.fill();                                                 // head
  const r=lerp(120,18,armsIn), hy=lerp(-270,-360,armsIn), sy=-272;
  for(const sg of [1,-1]){ const hx=sg*r*Math.cos(phase); const depth=sg*Math.sin(phase); ctx.lineWidth=depth>0?12:9; ctx.beginPath(); ctx.moveTo(0,sy); ctx.quadraticCurveTo(hx*0.5,lerp(sy,hy,0.4),hx,hy); ctx.stroke(); }
  ctx.restore(); }
// layered-atmosphere diagram for the recipe beat
function layersPanel(x,y,w,h,st,alpha){ if(alpha<=0)return; lightPanel(x,y,w,h,alpha); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y);
  inkText('THE RECIPE',w/2,52,{size:38,weight:900});
  const top=100, gy=h-90; const g=ctx.createLinearGradient(0,top,0,gy); g.addColorStop(0,'rgba(77,184,255,0.55)'); g.addColorStop(0.5,'rgba(255,255,255,0)'); g.addColorStop(1,'rgba(255,122,26,0.5)');
  rr(30,top,w-60,gy-top,24); ctx.fillStyle=g; ctx.fill();
  ctx.fillStyle='#5B9B3C'; rr(30,gy-8,w-60,40,10); ctx.fill();                       // ground
  ctx.fillStyle='#F2EDE3'; ctx.fillRect(w/2-40,gy-60,80,56); ctx.fillStyle=C.red; ctx.beginPath(); ctx.moveTo(w/2-52,gy-60); ctx.lineTo(w/2,gy-100); ctx.lineTo(w/2+52,gy-60); ctx.closePath(); ctx.fill();   // tiny house
  if(st.warm>0){ ctx.globalAlpha=ctx.globalAlpha*st.warm; inkText('WARM, WET AIR',w/2,gy-150,{size:40,weight:900,color:'#D14A00'}); 
    for(let i=0;i<5;i++){ const xx=90+i*(w-180)/4; ctx.strokeStyle='rgba(209,74,0,0.7)'; ctx.lineWidth=5; ctx.beginPath(); for(let k=0;k<=12;k++){ const yy=gy-20-k*8; const xo=Math.sin(k*0.9+st.t*4+i)*8; k?ctx.lineTo(xx+xo,yy):ctx.moveTo(xx+xo,yy);} ctx.stroke(); }   // steam squiggles
    ctx.globalAlpha=ctx.globalAlpha/st.warm; }
  if(st.cold>0){ ctx.globalAlpha=ctx.globalAlpha*st.cold; inkText('COLD, DRY AIR',w/2,top+70,{size:40,weight:900,color:'#1F6FC0'}); text('❄',110,top+70,{size:40,stroke:false,shadow:false}); text('❄',w-110,top+70,{size:40,stroke:false,shadow:false}); ctx.globalAlpha=ctx.globalAlpha/st.cold; }
  if(st.wind>0){ ctx.globalAlpha=ctx.globalAlpha*st.wind;   // wind arrows turning (and growing) with height, drawn in a flattened plan view
    for(let i=0;i<5;i++){ const u=i/4; const yy=lerp(gy-200,top+140,u); const ang=lerp(0.15,-1.35,u)*st.twist; const L=lerp(90,190,u); const dx=Math.cos(ang)*L, dy=Math.sin(ang)*L*0.4;
      arrowLine(w/2-dx/2,yy-dy/2,w/2+dx/2,yy+dy/2,{color:INK,width:9,head:24}); }
    inkText('WIND TWISTS WITH HEIGHT',w/2,gy-230,{size:30,weight:900,alpha:st.twist}); ctx.globalAlpha=ctx.globalAlpha/st.wind; }
  ctx.restore(); }

const HOOK_HEAD=[[['THIS COW IS DOING',C.white]],[['200 MPH',C.yellow]]];
// ---- hook: claim on frame 0, tag riding the cow, two more debris gags
function beatHook(tb,t,b){ const out=fadeOut(b,b,0.3); const o=fadeOut(tb,b); headline(HOOK_HEAD,o); 
  tagAt('cow','COW · 200 MPH',b.start,t,{out:o,instant:true}); tagAt('trampoline','TRAMPOLINE (obviously)',b.start+0.9,t,{fg:C.white,dx:-40,dy:-130,size:28,out:o}); tagAt('gnome','GNOME (not ok)',b.start+1.6,t,{fg:C.white,dx:40,dy:-120,size:28,out:o});
  thinLabel('toy cow. real physics.',W/2,1300,smooth(1.2,1.5,tb)*o,30); }
// ---- skater: thesis panel, funnel = skater, both spinning
function beatSkater(tb,t,b){ const o=fadeOut(tb,b); const tS=wordTime('skater','skater'), tG=wordTime('skater','giant');
  if(t>tG) headline([[['A TORNADO IS A',C.white]],[['GIANT FIGURE SKATER',C.yellow]]],smooth(0,0.25,t-tG)*o,68);
  const a=smooth(0.05,0.35,tb)*o; const px=110,py=600,pw=750,ph=820; lightPanel(px,py,pw,ph,a);
  const k=t>tS?smooth(0,0.5,t-tS):0;   // arms come in on 'skater', spin speeds up
  const spin=lerp(2.0,7.0,k); const phase=tb*spin*Math.PI;
  funnelIcon(px+205,py+ph-120,1.0,tb*6,a); inkText('=',px+pw/2,py+ph/2+40,{size:120,weight:900,alpha:a,color:'rgba(28,26,34,0.55)'});
  spinLines(px+560,py+ph-250,lerp(150,80,k),30,phase,lerp(0.3,1,k),a*0.8); skaterFig(px+560,py+ph-120,1.0,k,phase,a);
  inkText('same trick',px+pw/2,py+70,{size:36,weight:900,alpha:a,color:'rgba(28,26,34,0.65)'}); }
// ---- recipe: layered atmosphere panel, pieces on the spoken words
function beatRecipe(tb,t,b){ const o=fadeOut(tb,b); const tW=wordTime('recipe','warm'), tC=wordTime('recipe','cold'), tWi=wordTime('recipe','wind'), tT=wordTime('recipe','twists');
  const a=smooth(0.05,0.35,tb)*o; const st={t:tb, warm:t>tW?smooth(0,0.3,t-tW):0, cold:t>tC?smooth(0,0.3,t-tC):0, wind:t>tWi?smooth(0,0.3,t-tWi):0, twist:t>tT?easeOutCubic((t-tT)/0.8):0};
  layersPanel(110,600,750,900,st,a); }
// ---- roll: labels + a rotation arrow around the live tube
function beatRoll(tb,t,b){ const o=fadeOut(tb,b); const tTw=wordTime('roll','twist'), tTube=wordTime('roll','tube'), tRp=wordTime('roll','rolling');
  if(t>tTw){ const a=smooth(0,0.25,t-tTw)*o; arrowLine(150,1290,330,1290,{alpha:a,width:9}); thinLabel('SLOW WIND',240,1340,a,30); arrowLine(150,760,540,760,{alpha:a,width:12,color:C.yellow}); thinLabel('FAST WIND',345,810,a,30,'center',C.yellow); }
  if(t>tTube){ const a=smooth(0,0.3,t-tTube)*o; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.strokeStyle=C.yellow; ctx.lineWidth=10; ctx.lineCap='round'; ctx.shadowColor='rgba(0,0,0,0.5)'; ctx.shadowBlur=8;
    const ph=(t*1.2)%1; const a0=-0.4+ph*0.6; ctx.beginPath(); ctx.ellipse(560,1040,230,105,0,a0,a0+2.3); ctx.stroke();   // front arc of a loop around the tube
    const ex=560+230*Math.cos(a0+2.3), ey=1040+105*Math.sin(a0+2.3); const ta=a0+2.3+Math.PI/2; ctx.fillStyle=C.yellow; ctx.beginPath(); ctx.moveTo(ex+22*Math.cos(ta),ey+22*Math.sin(ta)); ctx.lineTo(ex+22*Math.cos(ta+2.5),ey+22*Math.sin(ta+2.5)); ctx.lineTo(ex+22*Math.cos(ta-2.5),ey+22*Math.sin(ta-2.5)); ctx.closePath(); ctx.fill(); ctx.restore();
    headline([[['IT ',C.white],['ROLLS',C.yellow]]],a,70); }
  if(t>tRp){ const k=t-tRp; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*smooth(0,0.15,k)*o; ctx.translate(W/2,1380); ctx.scale(popIn(k),popIn(k)); pill('LIKE A ROLLING PIN',0,0,{size:38,weight:900,bg:'rgba(255,214,10,0.95)',fg:INK,padX:30}); ctx.restore(); } }
// ---- tilt: updraft chevrons rising around the tube
function beatTilt(tb,t,b){ const o=fadeOut(tb,b); const tU=wordTime('tilt','updraft'), tS=wordTime('tilt','stands');
  if(t>tU){ const a=smooth(0,0.3,t-tU)*o; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a;
    for(let i=0;i<5;i++){ const x=[240,390,540,690,800][i]; for(let j=0;j<4;j++){ const y=1450-(((j*190)+(t-tU)*380+i*60)%760); const fa=Math.sin(Math.PI*(1450-y)/760); ctx.globalAlpha=ctx.globalAlpha*fa; text('⬆',x,y,{size:64,weight:900,color:C.yellow,strokeW:10}); ctx.globalAlpha=ctx.globalAlpha/fa; } }
    ctx.restore(); headline([[['UPDRAFT',C.yellow]]],a,70); }
  if(t>tS){ const a=smooth(0,0.25,t-tS)*o; headline([[['UPDRAFT',C.yellow]],[['STANDS IT UP',C.white]]],a,70); } }
// ---- squeeze: the live funnel narrows; gauge climbs; skater pops in on 'arms'
function squeezeSpeed(tb){ return lerp(60,250,smooth(0.6,4.4,tb)); }
function beatSqueeze(tb,t,b){ const o=fadeOut(tb,b); const tSq=wordTime('squeeze','squeeze'), tF=wordTime('squeeze','faster'), tA=wordTime('squeeze','arms');
  const g=smooth(0.3,0.7,tb)*o; gauge(330,1300,190,squeezeSpeed(tb),300,g);
  if(t>tSq) headline([[['SQUEEZE THE SPIN',C.white]]],smooth(0,0.25,t-tSq)*o,70);
  if(t>tF) headline([[['SQUEEZE THE SPIN',C.white]],[['= FASTER',C.yellow]]],smooth(0,0.25,t-tF)*o,70);
  if(t>tA){ const k=t-tA; const a=smooth(0,0.2,k)*o; const armsIn=smooth(0.1,0.6,k); const phase=k*lerp(3,8,armsIn)*Math.PI; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.translate(700,1480); ctx.scale(popIn(k),popIn(k));
    ctx.fillStyle='rgba(255,250,242,0.9)'; ctx.beginPath(); ctx.ellipse(0,-150,140,200,0,0,Math.PI*2); ctx.fill(); spinLines(0,-120,lerp(110,60,armsIn),24,phase,1,0.8); skaterFig(0,-20,0.72,armsIn,phase,1); ctx.restore(); } }
// ---- speed: the record on the gauge
function beatSpeed(tb,t,b){ const o=fadeOut(tb,b); const tO=wordTime('speed','over'), tThree=wordTime('speed','three');
  const v=t>tThree?lerp(250,302,easeOutCubic((t-tThree)/0.5)):250; gauge(330,1300,190,v,320,o,{red:200});
  if(t>tO) headline([[['OVER ',C.white],['300 MPH',C.yellow]]],smooth(0,0.25,t-tO)*o,72);
  if(t>tThree){ const k=t-tThree; const a=smooth(0.2,0.5,k)*o; thinLabel('fastest wind ever measured on Earth',W/2,990,a,30); thinLabel('Doppler radar · Oklahoma, 1999',W/2,1035,a,26,'center','rgba(255,255,255,0.85)'); if(k<0.4) flash(t,tThree,{dur:0.3,peak:0.3,color:'255,59,59'}); } }
// ---- tryit: chair panel with steps
function beatTryit(tb,t,b){ const o=fadeOut(tb,b); const tT=wordTime('tryit','try'), tSp=wordTime('tryit','spin'), tArms=wordTime('tryit','arms');
  if(t>tT) headline([[['TRY IT',C.yellow],[' AT HOME',C.white]]],smooth(0,0.25,t-tT)*o,70);
  const a=smooth(0.05,0.35,tb)*o; const px=110,py=600,pw=750,ph=880; lightPanel(px,py,pw,ph,a);
  const armsIn=t>tArms?smooth(0,0.5,t-tArms):0; const spinning=t>tSp; const phase=spinning?(t-tSp)*lerp(2.2,7,armsIn)*Math.PI:0;
  spinLines(px+pw/2,py+620,lerp(170,90,armsIn),40,phase,spinning?lerp(0.4,1,armsIn):0,a*0.8); chairFig(px+pw/2,py+ph-130,1.0,armsIn,phase,a);
  const steps=[[tSp,'1. SPIN ON A CHAIR'],[tArms,'2. PULL YOUR ARMS IN'],[tArms+0.7,'3. WHEEEEE']];
  steps.forEach(([t0,lab],i)=>{ if(t<t0) return; const k=t-t0; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*smooth(0,0.2,k)*a; ctx.translate(px+40,py+80+i*74); ctx.scale(popIn(k),popIn(k)); pill(lab,0,0,{size:34,weight:900,bg:i<2?INK:'rgba(255,214,10,0.95)',fg:i<2?C.white:INK,padX:24,align:'left'}); ctx.restore(); }); }
// ---- ask: name the cow
function beatAsk(tb,t,b){ const tN=wordTime('ask','name'), tC=wordTime('ask','cow');
  if(t>tN) headline([[['NAME ',C.white],['THE COW',C.yellow]]],smooth(0,0.25,t-tN),76);
  tagAt('cow','???',b.start,t,{dx:0,dy:-240,size:44});
  if(t>tC){ const a=smooth(0,0.25,t-tC); pill('comment her name ↓',W/2,1340,{size:38,weight:900,padX:30,alpha:a}); thinLabel('follow for more chaos',W/2,1420,a*0.85,28); } }
// ---- loop: footage runs into frame 0; bring the hook headline + cow tag back so the wrap is seamless
function beatLoop(tb,t,b){ const a=smooth(b.duration-0.6,b.duration-0.1,tb); headline([[['NAME ',C.white],['THE COW',C.yellow]]],1-smooth(0,0.3,tb),76); headline(HOOK_HEAD,a); tagAt('cow','COW · 200 MPH',b.start+b.duration-0.5,t,{instant:true}); }

window.BEATS = {
  draw: {hook:beatHook,skater:beatSkater,recipe:beatRecipe,roll:beatRoll,tilt:beatTilt,squeeze:beatSqueeze,speed:beatSpeed,tryit:beatTryit,ask:beatAsk,loop:beatLoop},
  cutFlash: ['roll','squeeze','speed','ask'],
  keywords: ['cow','tornado','skater','warm','wet','cold','dry','wind','twists','tube','rolling','updraft','squeeze','spin','spins','faster','arms','chair','name','record','stretches'],
  caption: {y: CAP_Y, size: 60, pop: 1.06, keywordColor: '#FFB020'},
  vignette: 0.15,
};
