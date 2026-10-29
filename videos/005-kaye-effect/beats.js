// Beat graphics for video 005: the Kaye effect. Bright set, so: white type with the usual black stroke,
// one yellow accent, light (cream) explainer panels with dark ink, no black anywhere.
const HEAD_Y=300, HEAD2_Y=382, CAP_Y=485;
const INK='#1C1A22', CREAM='rgba(255,250,242,0.94)';
function fadeInOut(tb,b,inAt=0,inDur=0.25,outPad=0.3){return smooth(inAt,inAt+inDur,tb)*(1-smooth(b.duration-outPad,b.duration-0.05,tb))}
function twoTone(parts,x,y,size,strokeW=12){ font(900,size); const ws=parts.map(p=>ctx.measureText(p[0]).width); const total=ws.reduce((a,b)=>a+b,0); let cx=x-total/2;
  parts.forEach((p,i)=>{ text(p[0],cx+ws[i]/2,y,{size,weight:900,color:p[1],strokeW}); cx+=ws[i]; }); }
function thinLabel(txt,x,y,alpha,size=34,align='center',color=C.white){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; text(txt,x,y,{size,weight:800,color,align,strokeW:8}); ctx.restore(); }
function annot(x0,y0,x1,y1,alpha){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.strokeStyle='rgba(255,255,255,0.95)'; ctx.lineWidth=4; ctx.shadowColor='rgba(0,0,0,0.5)'; ctx.shadowBlur=6;
  ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x1,y1); ctx.stroke(); ctx.fillStyle=C.yellow; ctx.beginPath(); ctx.arc(x1,y1,8,0,Math.PI*2); ctx.fill(); ctx.restore(); }
// slow-mo tag: right edge at 850, left of TikTok's like/comment column (pipeline/safe_area.json)
function slowmoTag(alpha){ pill('SLOW MOTION 4x',850,1470,{size:28,weight:800,padX:22,alpha:alpha*0.9,align:'right'}); }
function headline(parts,alpha,size=72){ // fitted to the 846 px readable width (pipeline/safe_area.json): 72 px 'SHAMPOO CAN BOUNCE' was 896 wide and cropped on phones
  for(const line of parts){ if(!line) continue; font(900,size); const w=line.reduce((a,p)=>a+ctx.measureText(p[0]).width,0); if(w>846) size=Math.floor(size*846/w); }
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; twoTone(parts[0],W/2,HEAD_Y,size); if(parts[1]) twoTone(parts[1],W/2,HEAD2_Y,size); ctx.restore(); }
const HOOK_HEAD=[[['SHAMPOO CAN ',C.white],['BOUNCE',C.yellow]],[['OFF ITSELF.',C.white]]];
function lightPanel(x,y,w,h,alpha=1){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.shadowColor='rgba(0,0,0,0.25)'; ctx.shadowBlur=30; ctx.shadowOffsetY=10; rr(x,y,w,h,36); ctx.fillStyle=CREAM; ctx.fill();
  ctx.shadowColor='transparent'; ctx.lineWidth=3; ctx.strokeStyle='rgba(28,26,34,0.12)'; ctx.stroke(); ctx.restore(); }
function inkText(str,x,y,{size=40,weight=800,align='center',alpha=1,color=INK}={}){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; text(str,x,y,{size,weight,color,align,stroke:false,shadow:false}); ctx.restore(); }

// ---- hook: the claim on frame 0, for the whole beat
function beatHook(tb,t,b){ headline(HOOK_HEAD,1-smooth(b.duration-0.3,b.duration-0.05,tb)); slowmoTag(1); }

// ---- compare: three stacked panels (honey / water / shampoo), label each on its spoken word
function beatCompare(tb,t,b){ const stackEnd=b.start+150/TL.fps; const out=1-smooth(stackEnd-0.3,stackEnd-0.05,t);
  const rows=[['honey','coils','HONEY',' → COILS',590],['water','splashes','WATER',' → SPLASHES',1230],['shampoo','leaps','SHAMPOO',' → LEAPS',1440]];
  for(const [n,v,N,V,y] of rows){ const tn=wordTime('compare',n), tv=wordTime('compare',v); if(t<tn) continue; const a=smooth(0,0.2,t-tn)*out;
    ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; font(900,44); const w1=ctx.measureText(N).width; text(N,120,y,{size:44,weight:900,align:'left',strokeW:10});
    if(t>tv){ ctx.globalAlpha=ctx.globalAlpha*smooth(0,0.15,t-tv); text(V,120+w1,y,{size:44,weight:900,align:'left',color:C.yellow,strokeW:10}); } ctx.restore(); }
  slowmoTag(out); }

// ---- why1: shear-thinning. Light panel with a two-bar viscosity graphic, bars lit on 'slowly' / 'fast'
function beatWhy1(tb,t,b){ const tS=wordTime('why1','shearthinning'), tSlow=wordTime('why1','slowly'), tTen=wordTime('why1','ten'), tFast=wordTime('why1','fast');
  const out=1-smooth(b.duration-0.35,b.duration-0.05,tb);
  if(t>tS) headline([[['SHEAR-',C.white],['THINNING',C.yellow]]],smooth(0,0.25,t-tS)*out,70);
  const a=smooth(0.1,0.45,tb)*out; const px=110,py=600,pw=750,ph=760,pcx=px+pw/2; lightPanel(px,py,pw,ph,a);   // 110..860: clear of the side crop and the like/comment column
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a;
  inkText('HOW THICK IS SHAMPOO?',pcx,py+70,{size:40,weight:900});
  inkText('(viscosity, not to scale)',pcx,py+118,{size:26,weight:700,color:'rgba(28,26,34,0.6)'});
  const base=py+ph-150, maxH=440; const bars=[[tSlow,'MOVING SLOWLY','THICK',1.0,C.orange,px+150],[tFast,'SHEARED FAST','THIN',0.1,C.yellow,px+pw-150]];
  for(const [t0,lab,word,h,col,cx] of bars){ const k=t>t0?easeOutCubic((t-t0)/0.5):0; const bw=250, bh=Math.max(12,maxH*h*k);
    ctx.save(); ctx.fillStyle='rgba(28,26,34,0.08)'; rr(cx-bw/2,base-maxH,bw,maxH,18); ctx.fill();
    ctx.fillStyle=col; rr(cx-bw/2,base-bh,bw,bh,14); ctx.fill(); ctx.restore();
    inkText(lab,cx,base+46,{size:30,weight:800,alpha:t>t0?1:0.35});
    if(k>0.6) inkText(word,cx,base-bh-34,{size:40,weight:900,alpha:smooth(0.6,1,k)}); }
  if(t>tTen){ const k=smooth(0,0.3,t-tTen); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*k; pill('≈ 10× THINNER',pcx,base-maxH*0.55,{size:36,weight:900,bg:INK,fg:C.yellow,padX:30}); ctx.restore(); }
  ctx.restore(); }

// ---- why2: labels over the close-up footage + a cutaway inset (cross-section of the heap) that builds on the spoken words
function crossSection(x,y,w,h,st,alpha){ // st: {dimple, layer, slide, jet} in 0..1
  lightPanel(x,y,w,h,alpha); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y);
  inkText('CROSS-SECTION',w/2,44,{size:26,weight:900,color:'rgba(28,26,34,0.65)'});
  const gy=h-60, cx=w*0.52; // ground line
  ctx.fillStyle='rgba(28,26,34,0.10)'; ctx.fillRect(30,gy,w-60,12);
  // heap profile with a dimple on its left slope
  const heap=new Path2D(); heap.moveTo(40,gy); heap.bezierCurveTo(cx-170,gy-10,cx-120,gy-150,cx-60,gy-170);
  const dim=st.dimple; heap.bezierCurveTo(cx-40,gy-176,cx-30,gy-150+40*dim,cx-10,gy-150+70*dim); heap.bezierCurveTo(cx+10,gy-150+40*dim,cx+20,gy-200,cx+70,gy-190);
  heap.bezierCurveTo(cx+150,gy-170,cx+200,gy-40,w-40,gy); heap.closePath(); ctx.fillStyle='#7FC9CF'; ctx.fill(heap); ctx.strokeStyle='rgba(28,26,34,0.35)'; ctx.lineWidth=3; ctx.stroke(heap);
  // incoming stream into the dimple
  ctx.strokeStyle='#167F8C'; ctx.lineWidth=16; ctx.lineCap='round'; ctx.beginPath(); ctx.moveTo(cx-10,70); ctx.lineTo(cx-10,gy-150+62*dim); ctx.stroke();
  if(st.layer>0){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*st.layer; ctx.strokeStyle=C.yellow; ctx.lineWidth=7; ctx.setLineDash([14,10]); ctx.beginPath();
    ctx.moveTo(cx-34,gy-150+30*dim); ctx.quadraticCurveTo(cx-10,gy-150+84*dim,cx+22,gy-150+30*dim); ctx.stroke(); ctx.restore(); }
  if(st.jet>0){ ctx.save(); ctx.strokeStyle='#167F8C'; ctx.lineWidth=12; ctx.lineCap='round'; ctx.beginPath(); const n=40; for(let i=0;i<=n*st.jet;i++){ const u=i/n; const jx=cx+22+u*170, jy=gy-150+30*dim-u*260+u*u*300; if(i===0)ctx.moveTo(jx,jy); else ctx.lineTo(jx,jy);} ctx.stroke(); ctx.restore(); }
  if(st.slide>0){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*st.slide; ctx.fillStyle=INK; const ax=cx+40, ay=gy-150+36*dim; ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(ax-18,ay+14); ctx.lineTo(ax-6,ay+24); ctx.closePath(); ctx.fill(); ctx.restore(); }
  ctx.restore(); }
function beatWhy2(tb,t,b){ const tD=wordTime('why2','dimple'), tL=wordTime('why2','layer'), tSl=wordTime('why2','slippery'), tJ=wordTime('why2','jet');
  const out=1-smooth(b.duration-0.35,b.duration-0.05,tb); const st={dimple:t>tD?smooth(0,0.5,t-tD):0, layer:t>tL?smooth(0,0.4,t-tL):0, slide:t>tSl?smooth(0,0.3,t-tSl):0, jet:t>tJ?easeOutCubic((t-tJ)/0.7):0};
  if(t>tD) headline([[['WHY IT ',C.white],['LEAPS',C.yellow]]],smooth(0,0.25,t-tD)*out,70);
  crossSection(120,570,400,370,st,smooth(0.1,0.4,tb)*out);   // top-left: clear of the stream (x~745) and the jet (goes up-right)
  // labels on the real footage; the impact point / dimple sits at ~(745,1270) in the X camera (see scene_kaye.py)
  const L=[[tD,'DIMPLE',120,1290,705,1262],[tL,'THIN, FAST LAYER',120,1350,735,1290],[tSl,'SLIPPERY → IT SKIDS',120,1410,null,null],[tJ,'JET',520,1060,790,1150]];
  for(const [t0,lab,x,y,ax,ay] of L){ if(t<t0) continue; const a=smooth(0,0.25,t-t0)*out; thinLabel(lab,x,y,a,40,'left'); if(ax!==null){ font(800,40); annot(x+ctx.measureText(lab).width+16,y,ax,ay,a); } }
  slowmoTag(out); }

// ---- tryit: a checklist that fills in on the spoken words
function beatTryit(tb,t,b){ const out=1-smooth(b.duration-0.3,b.duration-0.05,tb); const tT=wordTime('tryit','try');
  if(t>tT) headline([[['TRY IT',C.yellow],[' AT HOME',C.white]]],smooth(0,0.25,t-tT)*out,70);
  const items=[['plate','A PLATE'],['stream','A THIN STREAM'],['handspan','A HAND-SPAN UP'],['tries','TAKES A FEW TRIES']];
  items.forEach(([w,lab],i)=>{ const t0=wordTime('tryit',w); if(t<t0) return; const k=t-t0; const a=smooth(0,0.2,k)*out; const y=1180+i*86;
    ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; const s=lerp(0.9,1,easeOutBack(k/0.25)); ctx.translate(120,y); ctx.scale(s,s);
    pill((i<3?'✓  ':'↻  ')+lab,0,0,{size:36,weight:800,padX:26,align:'left',bg:i<3?'rgba(10,12,18,0.78)':'rgba(255,214,10,0.92)',fg:i<3?C.white:INK}); ctx.restore(); });
  slowmoTag(out); }

// ---- ask: the question on screen + a small follow line; no separate CTA beat
function beatAsk(tb,t,b){ const tD=wordTime('ask','does'), tTell=wordTime('ask','tell');
  if(t>tD) headline([[['DOES ',C.white],['YOURS',C.yellow],[' BOUNCE?',C.white]]],smooth(0,0.25,t-tD),72);
  if(t>tTell){ const a=smooth(0,0.25,t-tTell); pill('comment the brand ↓',W/2,1340,{size:36,weight:800,padX:30,alpha:a}); thinLabel('follow for the next one',W/2,1420,a*0.85,28); }
  slowmoTag(1); }
// ---- loop: footage runs into frame 0; bring the headline back so the wrap is seamless
function beatLoop(tb,t,b){ const a=smooth(b.duration-0.6,b.duration-0.1,tb); headline([[['DOES ',C.white],['YOURS',C.yellow],[' BOUNCE?',C.white]]],1-smooth(0,0.3,tb),72); headline(HOOK_HEAD,a); slowmoTag(1); }

window.BEATS = {
  draw: {hook:beatHook,compare:beatCompare,why1:beatWhy1,why2:beatWhy2,tryit:beatTryit,ask:beatAsk,loop:beatLoop},
  cutFlash: ['compare','why2','tryit'],
  keywords: ['shampoo','bounce','coils','splashes','leaps','dimple','slippery','jet','thinner','slowly','fast'],
  caption: {y: CAP_Y, size: 60, pop: 1.06, keywordColor: '#FFB020'},
  vignette: 0.15,
};
