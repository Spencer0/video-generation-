// Beat graphics for video 006: the Odyssey with cats, dressed as a PS2-era game HUD.
// Everything readable stays inside pipeline/safe_area.json: x 110..970, y 250..1040 (wide things), nothing bottom-right.
const HUD_Y=292, CARD_Y=384, GOLD='#FFD23F', HUDBG='rgba(12,16,40,0.82)';
function io(tb,b,inAt=0,inDur=0.2,outPad=0.25){return smooth(inAt,inAt+inDur,tb)*(1-smooth(b.duration-outPad,b.duration-0.04,tb))}
// YEAR n/10 on the left, CREW bar on the right
function hud(year,crew,alpha=1,crewFlash=0){
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha;
  pill('YEAR '+year+'/10',122,HUD_Y,{size:34,weight:900,padX:22,bg:HUDBG,fg:GOLD,align:'left',border:'rgba(255,255,255,0.25)'});
  const n=5,w=34,g=8,h=30,x1=952,x0=x1-n*w-(n-1)*g; font(900,30); const lw=ctx.measureText('CREW').width;
  rr(x0-lw-40,HUD_Y-31,x1-x0+lw+58,62,31); ctx.fillStyle=HUDBG; ctx.fill(); ctx.lineWidth=3; ctx.strokeStyle='rgba(255,255,255,0.25)'; ctx.stroke();
  text('CREW',x0-lw/2-14,HUD_Y+1,{size:30,weight:900,color:'#FFFFFF',stroke:false,shadow:false});
  for(let i=0;i<n;i++){ const on=i<crew; rr(x0+i*(w+g),HUD_Y-h/2,w,h,7); ctx.fillStyle=on?'#4BE36B':(crewFlash>0&&i<crew+crewFlash?'#FF4D4D':'rgba(255,255,255,0.16)'); ctx.fill(); }
  ctx.restore(); }
// level / boss card under the HUD: small tag + big name, slides in from the left
function card(tag,name,tb,b,{hold=1.7,color=GOLD}={}){
  const a=smooth(0.05,0.25,tb)*(1-smooth(hold,hold+0.25,tb)); if(a<=0) return; const dx=lerp(-60,0,easeOutCubic(Math.min(1,tb/0.3)));
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a; ctx.translate(dx,0);
  text(tag,W/2,CARD_Y,{size:34,weight:900,color:'#FFFFFF',strokeW:8}); let size=70; font(900,size); const w=ctx.measureText(name).width; if(w>830) size=Math.floor(size*830/w);
  text(name,W/2,CARD_Y+72,{size,weight:900,color,strokeW:12}); ctx.restore(); }
function tagAt(str,x,y,alpha,{size=36,color='#FFFFFF',rot=0}={}){ if(alpha<=0)return; ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.rotate(rot); text(str,0,0,{size,weight:900,color,strokeW:9}); ctx.restore(); }

function beatHook(tb,t,b){ const a=1-smooth(b.duration-0.25,b.duration-0.04,tb); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*a;
  text('THE ODYSSEY',W/2,300,{size:96,weight:900,color:GOLD,strokeW:14});
  const tc=wordTime('hook','but'); if(t>=tc){ const s=lerp(1.25,1,easeOutBack(Math.min(1,(t-tc)/0.2))); ctx.translate(W/2,392); ctx.scale(s,s); text('BUT EVERYONE IS A CAT',0,0,{size:58,weight:900,color:'#FFFFFF',strokeW:11}); }
  ctx.restore(); }
function beatHome(tb,t,b){ hud(0,5,smooth(0.1,0.3,tb)); card('QUEST','GET HOME TO ITHACA',tb,b,{hold:2.6});
  const tt=wordTime('home','ten'); tagAt('10 YEARS',W/2,430,smooth(0,0.15,t-tt)*(1-smooth(b.duration-0.3,b.duration-0.05,tb)),{size:92,color:GOLD}); }
function beatCyclops(tb,t,b){ hud(1,4,1,tb<0.8?1:0); card('BOSS','THE CYCLOPS',tb,b);
  const ts=wordTime('cyclops','hiding'); tagAt('STEALTH SECTION',W/2,410,smooth(0,0.15,t-ts)*(1-smooth(b.duration-0.3,b.duration-0.05,tb)),{size:56,color:'#7CF29A'}); }
function beatWinds(tb,t,b){ hud(1,4,1); card('ITEM GET','BAG OF EVERY STORM',tb,b);
  const to=wordTime('winds','opens'), th=wordTime('winds','they'); tagAt('DO NOT OPEN',W/2,410,smooth(0,0.12,t-to+0.6)*(1-smooth(0,0.15,t-to)),{size:60,color:'#FF5A5A',rot:-0.05});
  tagAt('SO CLOSE.',W/2,410,smooth(0,0.15,t-th)*(1-smooth(b.duration-0.3,b.duration-0.05,tb)),{size:76,color:'#FF5A5A'}); }
function beatCirce(tb,t,b){ const tp=wordTime('circe','pigs'), td=wordTime('circe','dogs'); hud(2,t>tp?3:4,1,(t>tp&&t<tp+0.8)?1:0); card('BOSS','CIRCE THE WITCH',tb,b,{hold:1.3});
  const a=1-smooth(b.duration-0.3,b.duration-0.05,tb);
  if(t>=tp&&t<td){ tagAt('PIGS',W/2,420,smooth(0,0.1,t-tp),{size:90,color:'#FF9BC2'}); }
  if(t>=td){ ctx.save(); ctx.globalAlpha=a; tagAt('PIGS',W/2-190,420,1,{size:70,color:'rgba(255,255,255,0.55)'}); ctx.strokeStyle='#FF4D4D'; ctx.lineWidth=12; ctx.beginPath(); ctx.moveTo(W/2-300,424); ctx.lineTo(W/2-80,416); ctx.stroke();
    const s=lerp(1.4,1,easeOutBack(Math.min(1,(t-td)/0.2))); ctx.translate(W/2+150,420); ctx.scale(s,s); text('DOGS',0,0,{size:100,weight:900,color:GOLD,strokeW:14}); ctx.restore(); } }
function beatSirens(tb,t,b){ hud(3,2,1,tb<0.8?1:0); card('BOSS','THE SIRENS',tb,b,{hold:1.5});
  const ts=wordTime('sirens','song'), t2=wordTime('sirens','so'); tagAt('*shakes the treat tin*',W/2,1010,smooth(0,0.15,t-ts)*(1-smooth(0,0.12,t-t2+0.1)),{size:46,color:'#FFFFFF',rot:-0.03});
  tagAt('MUST. HAVE. TREATS.',W/2,410,smooth(0,0.15,t-t2-0.4)*(1-smooth(b.duration-0.3,b.duration-0.05,tb)),{size:62,color:GOLD}); }
function beatCalypso(tb,t,b){ const ts=wordTime('calypso','seven'); const k=clamp((t-ts)/(b.end-0.5-ts),0,1); const yr=t<ts?3:Math.min(10,3+Math.floor(k*7.99));
  hud(yr,0,1,tb<0.9?2:0); card('BOSS?','CALYPSO',tb,b,{hold:1.3});
  if(t>=ts){ const n=Math.min(7,1+Math.floor(k*7)); tagAt('+'+n+(n===1?' YEAR':' YEARS'),W/2,420,1-smooth(b.duration-0.3,b.duration-0.05,tb),{size:92,color:GOLD}); } }
function beatSuitors(tb,t,b){ hud(10,0,1); card('FINAL BOSS','108 SUITORS',tb,b,{hold:2.2});
  const th=wordTime('suitors','he',1); tagAt('HE HANDLES IT.',W/2,410,smooth(0,0.12,t-th-0.2)*(1-smooth(b.duration-0.3,b.duration-0.05,tb)),{size:72,color:'#FF5A5A'}); }
function beatDoor(tb,t,b){ const tw=wordTime('door','and'); hud(10,0,smooth(0,0.2,tb));
  if(t<tw) card('QUEST COMPLETE','HOME AT LAST',tb,b,{hold:9,color:'#7CF29A'});
  else { const s=lerp(1.3,1,easeOutBack(Math.min(1,(t-tw)/0.22))); text('NEW QUEST',W/2,CARD_Y,{size:34,weight:900,color:'#FFFFFF',strokeW:8}); ctx.save(); ctx.translate(W/2,CARD_Y+76); ctx.scale(s,s); text('GO BACK OUTSIDE',0,0,{size:62,weight:900,color:GOLD,strokeW:12}); ctx.restore(); }
  const to=wordTime('door','out'); tagAt('meow.',330,760,smooth(0,0.12,t-to-0.25),{size:64,color:'#FFFFFF',rot:-0.08}); }
window.BEATS={ vignette:0.22, caption:{y:1150},
  draw:{hook:beatHook,home:beatHome,cyclops:beatCyclops,winds:beatWinds,circe:beatCirce,sirens:beatSirens,calypso:beatCalypso,suitors:beatSuitors,door:beatDoor},
  cutFlash:['home','cyclops','winds','circe','sirens','calypso','suitors','door'],
  keywords:['odyssey','cat','ten','giant','sheep','storm','pigs','dogs','sirens','mast','seven','hundred','out'] };
