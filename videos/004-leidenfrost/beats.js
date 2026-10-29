// Beat graphics for video 004: Leidenfrost. Restrained: white type, a single yellow accent, three labels.
const CAP_Y=430;
function fade(tb,b,inAt=0,inDur=0.25,outPad=0.3){return smooth(inAt,inAt+inDur,tb)*(1-smooth(b.duration-outPad,b.duration-0.05,tb))}
function twoTone(parts,x,y,size){ // parts: [[text,color],...] rendered as one centred line
  font(900,size); const ws=parts.map(p=>ctx.measureText(p[0]).width); const total=ws.reduce((a,b)=>a+b,0); let cx=x-total/2;
  parts.forEach((p,i)=>{ text(p[0],cx+ws[i]/2,y,{size,weight:900,color:p[1],strokeW:12}); cx+=ws[i]; }); }
function thinLabel(txt,x,y,alpha,size=34,align='center'){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; text(txt,x,y,{size,weight:800,color:C.white,align,strokeW:8}); ctx.restore(); }
function annot(x0,y0,x1,y1,alpha){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.strokeStyle='rgba(255,255,255,0.9)'; ctx.lineWidth=3; ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x1,y1); ctx.stroke();
  ctx.fillStyle=C.yellow; ctx.beginPath(); ctx.arc(x1,y1,7,0,Math.PI*2); ctx.fill(); ctx.restore(); }

function beatHook(tb,t,b){ const a=1-smooth(b.duration-0.35,b.duration-0.05,tb);   // readable on frame 0 ctx.save(); ctx.globalAlpha=a;
  twoTone([['WATER ',C.white],['SHOULDN’T',C.yellow],[' DO THIS.',C.white]],W/2,CAP_Y-110,58)   // 58 px fits the 846 px readable width; 74 was cropped to 'VATER ... DO THI' on phones; ctx.restore(); }
function beatCompare(tb,t,b){ const tCool=wordTime('compare','cooler'), tHot=wordTime('compare','hot'); const splitEnd=b.start+150/TL.fps;
  const out=1-smooth(splitEnd-0.35,splitEnd-0.05,t);
  if(t>tCool){ thinLabel('COOLER SURFACE: SPREADS',W/2,300,smooth(0,0.25,t-tCool)*out,40); }
  if(t>tHot){ ctx.save(); ctx.globalAlpha=smooth(0,0.25,t-tHot)*out; twoTone([['VERY HOT SURFACE: ',C.white],['SKITTERS',C.yellow]],W/2,1300,40); ctx.restore(); } }
function beatReveal(tb,t,b){ const tSteam=wordTime('reveal','steam'); if(t>tSteam){ const a=smooth(0,0.3,t-tSteam);
    annot(470,1335,535,1238,a); thinLabel('INVISIBLE STEAM LAYER',340,1380,a,40); thinLabel('thickness exaggerated for clarity',340,1430,a*0.7,24); } }
function beatGlide(tb,t,b){ const tSep=wordTime('glide','separates'), tGl=wordTime('glide','glides');
  if(t<b.start+0.4){ const a=1-smooth(0,0.4,tb); annot(470,1335,535,1238,a); thinLabel('INVISIBLE STEAM LAYER',340,1380,a,40); }
  if(t>tSep){ thinLabel('LESS DIRECT CONTACT',W/2,1360,smooth(0,0.3,t-tSep)*(1-smooth(b.duration-0.4,b.duration-0.1,tb)),44); }
  if(t>tGl){ ctx.save(); ctx.globalAlpha=smooth(0,0.3,t-tGl)*(1-smooth(b.duration-0.4,b.duration-0.1,tb)); twoTone([['→ IT ',C.white],['GLIDES',C.yellow]],W/2,1420,36); ctx.restore(); } }
function beatName(tb,t,b){ const tL=wordTime('name','leidenfrost'), tE=wordTime('name','evaporating');
  if(t>tL){ const k=t-tL; const a=smooth(0,0.3,k)*(1-smooth(b.duration-0.4,b.duration-0.1,tb)); ctx.save(); ctx.globalAlpha=a;
    text('THE LEIDENFROST EFFECT',W/2,CAP_Y-110,{size:66,weight:900,strokeW:12}); ctx.strokeStyle=C.yellow; ctx.lineWidth=5; const w=lerp(0,420,easeOutCubic(k/0.6)); ctx.beginPath(); ctx.moveTo(W/2-w/2,CAP_Y-60); ctx.lineTo(W/2+w/2,CAP_Y-60); ctx.stroke(); ctx.restore(); }
  if(t>tE){ thinLabel('still evaporating — just slowly',W/2,1380,smooth(0,0.3,t-tE)*(1-smooth(b.duration-0.4,b.duration-0.1,tb)),32); } }
function beatPayoff(tb,t,b){ const tV=wordTime('payoff','vapor'); const cut0=3.0, cut1=6.4;
  if(tb>cut0+1.6 && tb<cut1-0.2){ const a=smooth(cut0+1.6,cut0+2.0,tb)*(1-smooth(cut1-0.5,cut1-0.2,tb));
    thinLabel('WATER',820,760,a,30,'left'); thinLabel('VAPOR',820,1225,a,30,'left'); thinLabel('HOT METAL',820,1400,a,30,'left');
    annot(805,760,700,800,a); annot(805,1225,640,1232,a); annot(805,1400,700,1380,a); }
  if(t>tV){ const k=t-tV; const a=smooth(0,0.35,k); ctx.save(); ctx.globalAlpha=a; twoTone([['RIDING ON ITS ',C.white],['OWN VAPOR.',C.yellow]],W/2,CAP_Y-110,62); ctx.restore(); } }
function beatLoop(tb,t,b){ const a=smooth(0,0.3,tb)*(1-smooth(b.duration-0.5,b.duration-0.1,tb)); thinLabel('FOLLOW FOR MORE PHYSICS THAT LOOKS IMPOSSIBLE',W/2,CAP_Y-110,a*0.8,28); }

window.BEATS = {
  draw: {hook:beatHook,compare:beatCompare,reveal:beatReveal,glide:beatGlide,name:beatName,payoff:beatPayoff,loop:beatLoop},
  cutFlash: [],
  keywords: [],
  caption: {y: CAP_Y, size: 64, pop: 1.04, keywordColor: '#FFFFFF'},
};
