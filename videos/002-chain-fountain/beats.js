// Beat graphics for video 002: the chain fountain.
function fadeInOut(tb,b,a0=0.2){return smooth(0,a0,tb)*(1-smooth(b.duration-0.3,b.duration-0.05,tb))}
function slowmoTag(alpha){ pill('SLOW MOTION  4×',W-70,250,{align:'right',size:32,bg:'rgba(8,10,16,0.75)',fg:'rgba(255,255,255,0.85)',alpha}); }

function beatFlash(tb,t,b){
  // flash-forward: the fountain fully up, with the hook quote
  const out=1-smooth(b.duration-0.25,b.duration-0.03,tb);
  const k1=tb-0.05; if(k1>0){ const s=lerp(1.4,1,easeOutBack(k1/0.3)); ctx.save(); ctx.translate(W/2,450); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,k1)*out;
    text('THIS CHAIN IS',0,-60,{size:84,weight:900}); text('STANDING UP',0,50,{size:112,weight:900,color:C.yellow}); ctx.restore(); }
  const tOwn=wordTime('flash','on'); const k2=t-tOwn; if(k2>0){ const s=lerp(1.8,1,easeOutBack(k2/0.3)); ctx.save(); ctx.translate(W/2,680); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,k2)*out;
    pill('ON ITS OWN.  NO HANDS.',0,0,{size:46,bg:'rgba(255,45,85,0.95)',padX:36}); ctx.restore(); }
  slowmoTag(out);
}
function beatHook(tb,t,b){
  const out=1-smooth(b.duration-0.35,b.duration-0.05,tb);
  const k1=tb-0.1; if(k1>0){ const s=lerp(1.8,1,easeOutBack(k1/0.3))*(1+0.02*Math.sin(k1*7)); ctx.save(); ctx.translate(W/2,360); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,k1)*out;
    text('WHY?',0,0,{size:170,weight:900,color:C.yellow,strokeW:20}); ctx.restore(); }
  const tW=wordTime('hook','watch'); if(t>tW){ ctx.save(); ctx.globalAlpha=smooth(0,0.15,t-tW)*out; pill('WATCH CLOSELY 👀',W/2,540,{size:42,bg:'rgba(8,10,16,0.8)',border:C.yellow}); ctx.restore(); }
  const tB=wordTime('hook','bucket'); if(t>tB){ ctx.save(); ctx.globalAlpha=smooth(0,0.15,t-tB)*out; pill('BEAD CHAIN + BUCKET',W/2,1180,{size:40,bg:'rgba(8,10,16,0.8)'}); ctx.restore(); }
  slowmoTag(smooth(0.3,0.6,tb));
}
function beatObvious(tb,t,b){
  slowmoTag(1);
  const tS=wordTime('obvious','slides'); if(t>tS){ const k=t-tS; ctx.save(); ctx.globalAlpha=smooth(0,0.15,k); pill('SLIDES OVER THE RIM  ↓',W/2,1180,{size:44,bg:'rgba(120,125,140,0.9)'}); ctx.restore(); }
}
function beatReversal(tb,t,b){
  slowmoTag(1-smooth(b.duration-0.4,b.duration-0.1,tb));
  const tLift=wordTime('reversal','lifts'); stamp('IT CLIMBS OUT ⬆️',W/2,1000,tLift+0.05,t,{color:C.green,size:104,rot:-0.08});
  const tHov=wordTime('reversal','floats'); if(t>tHov){ const k=t-tHov; ctx.save(); ctx.globalAlpha=smooth(0,0.15,k)*(1-smooth(b.duration-0.4,b.duration-0.1,tb));
    pill('A FLOATING LOOP  •  NO HANDS',W/2,1180,{size:42,bg:'rgba(8,10,16,0.8)',fg:C.blue,border:C.blue}); ctx.restore(); }
  const tHow=wordTime('reversal','how'); const kh=t-tHow; if(kh>0){ const s=lerp(2.4,1,easeOutBack(kh/0.35))*(1+0.04*Math.sin(kh*9));
    ctx.save(); ctx.translate(W/2,760); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.08,kh); text('HOW?',0,0,{size:190,weight:900,color:C.yellow,strokeW:22}); ctx.restore(); flash(t,tHow,{dur:0.2,peak:0.3}); }
}
function arrow(x0,y0,x1,y1,color,w=8,head=22){ ctx.save(); ctx.strokeStyle=color; ctx.fillStyle=color; ctx.lineWidth=w; ctx.lineCap='round';
  ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(x1,y1); ctx.stroke(); const a=Math.atan2(y1-y0,x1-x0);
  ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x1-head*Math.cos(a-0.5),y1-head*Math.sin(a-0.5)); ctx.lineTo(x1-head*Math.cos(a+0.5),y1-head*Math.sin(a+0.5)); ctx.closePath(); ctx.fill(); ctx.restore(); }
function beadRod(cx,cy,ang,len,color){ ctx.save(); ctx.translate(cx,cy); ctx.rotate(ang); ctx.strokeStyle=color; ctx.lineWidth=14; ctx.lineCap='round';
  ctx.beginPath(); ctx.moveTo(-len/2,0); ctx.lineTo(len/2,0); ctx.stroke(); ctx.fillStyle=color; for(const x of [-len/2,0,len/2]){ ctx.beginPath(); ctx.arc(x,0,26,0,Math.PI*2); ctx.fill(); } ctx.restore(); }
function beatKick(tb,t,b){
  const a=fadeInOut(tb,b);
  const px=70,py=470,pw=940,ph=820; panel(px,py,pw,ph,a);
  ctx.save(); ctx.globalAlpha=a;
  text('WHY IT LIFTS',W/2,py+60,{size:50,weight:900,stroke:false});
  // pile
  const pileTop=py+ph-250; ctx.fillStyle='rgba(255,255,255,0.08)'; rr(px+60,pileTop,pw-120,190,30); ctx.fill();
  const rnd=mulberry(5); ctx.fillStyle='rgba(200,205,215,0.55)';
  for(let i=0;i<90;i++){ const x=px+90+rnd()*(pw-180), y=pileTop+25+rnd()*140; ctx.beginPath(); ctx.arc(x,y,13,0,Math.PI*2); ctx.fill(); }
  text('THE PILE',W/2,pileTop+230,{size:34,weight:800,color:'rgba(255,255,255,0.7)',stroke:false});
  // the see-saw link, looping every 2.6 s
  const tRod=wordTime('kick','rod'), tYank=wordTime('kick','yanks'), tKick=wordTime('kick','kicks'), tBack=wordTime('kick','back');
  const cyc=((t-tYank)%2.6+2.6)%2.6; const live=t>tYank;
  const lift=live? smooth(0.0,0.9,cyc)*(1-smooth(1.9,2.5,cyc)) : 0;
  const cx=W/2, cy0=pileTop-20, len=360; const ang=-0.75*lift; const cy=cy0-90*lift;
  // highlight ring on "rod"
  if(t>tRod && t<tYank+0.4){ ctx.save(); ctx.globalAlpha=0.5+0.5*Math.sin(t*10); ctx.strokeStyle=C.yellow; ctx.lineWidth=6; ctx.setLineDash([16,12]); ctx.beginPath(); ctx.ellipse(cx,cy0,len/2+50,70,0,0,Math.PI*2); ctx.stroke(); ctx.restore(); }
  beadRod(cx,cy,ang,len,'#E8ECF2');
  const fx=cx+Math.cos(ang)*len/2, fy=cy+Math.sin(ang)*len/2, bx=cx-Math.cos(ang)*len/2, by=cy-Math.sin(ang)*len/2;
  if(t>tYank){ const top=Math.max(fy-200-60*lift, py+190); arrow(fx+10,fy-40,fx+10,top,C.orange,10,28); text('PULL',fx+60,top-10,{size:36,weight:900,color:C.orange,align:'left',stroke:false}); }
  if(t>tKick){ arrow(bx-10,by+40,bx-10,by+150,C.red,10,28); text('KICKS DOWN',bx-10,by+200,{size:32,weight:900,color:C.red,stroke:false}); }
  if(t>tBack){ const k=t-tBack; const s=lerp(1.6,1,easeOutBack(k/0.3)); arrow(bx+70,pileTop+150,bx+70,pileTop-10-40*lift,C.green,12,32);
    ctx.save(); ctx.translate(W/2,py+ph+60); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,k); pill('THE PILE KICKS BACK  •  NEWTON’S 3RD LAW',0,0,{size:38,bg:'rgba(61,220,132,0.95)',fg:'#06210f'}); ctx.restore(); }
  text('a rigid link = a tiny see-saw',W/2,py+120,{size:34,weight:700,color:'rgba(255,255,255,0.75)',stroke:false});
  ctx.restore();
}
function fraction(x,y,num,den,size,colNum,colDen){ font(800,size); const wn=ctx.measureText(num).width, wd=ctx.measureText(den).width, w=Math.max(wn,wd)+20;
  text(num,x,y-size*0.62,{size,weight:800,color:colNum,stroke:false}); text(den,x,y+size*0.66,{size,weight:800,color:colDen,stroke:false});
  ctx.save(); ctx.strokeStyle='rgba(255,255,255,0.85)'; ctx.lineWidth=6; ctx.beginPath(); ctx.moveTo(x-w/2,y); ctx.lineTo(x+w/2,y); ctx.stroke(); ctx.restore(); return w; }
function beatEquation(tb,t,b){
  const a=fadeInOut(tb,b);
  const px=70,py=430,pw=940,ph=900; panel(px,py,pw,ph,a);
  ctx.save(); ctx.globalAlpha=a;
  const tA=wordTime('equation','alpha'), tH=wordTime('equation','height'), tDrop=wordTime('equation','drop'), tE=wordTime('equation','eighth');
  text('FOUNTAIN HEIGHT',W/2,py+60,{size:32,weight:700,color:'rgba(255,255,255,0.75)',stroke:false});
  const hlA = t>tA && t<tDrop, hlH1 = t>tDrop && t<tE;
  const ey=py+200; const size=92;
  text('h  =',px+250,ey,{size,weight:800,color: t>tH&&t<tDrop? C.yellow:C.white,stroke:false});
  const fw=fraction(px+470,ey,'α','1 − α',size*0.8, hlA?C.yellow:C.white, hlA?C.yellow:C.white);
  text('·  h₁',px+470+fw/2+120,ey,{size,weight:800,color: hlH1? C.yellow:C.white,stroke:false});
  // legend
  const leg=[['h','fountain height',C.white],['h₁','drop height',C.white],['α','kick fraction',C.orange]];
  leg.forEach((l,i)=>{ const y=py+360+i*54; text(l[0],px+120,y,{size:38,weight:900,color:l[2],align:'left',stroke:false}); text('= '+l[1],px+200,y,{size:34,weight:700,color:'rgba(255,255,255,0.8)',align:'left',stroke:false}); });
  if(t>tE){ const k=t-tE; const s=lerp(1.6,1,easeOutBack(k/0.3)); ctx.save(); ctx.translate(px+700,py+410); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,k); pill('α ≈ 1/8',0,0,{size:54,bg:'rgba(255,214,10,0.95)',fg:'#1a1500',padX:34}); ctx.restore(); }
  // mini diagram: beaker on a stand, arch h above rim, drop h1 to floor
  const dx=px+pw/2+40, rimY=py+620, floorY=py+ph-60, bw=110;
  ctx.strokeStyle='rgba(255,255,255,0.55)'; ctx.lineWidth=5; ctx.strokeRect(dx-bw/2,rimY,bw,130);
  ctx.beginPath(); ctx.moveTo(dx-220,floorY); ctx.lineTo(dx+300,floorY); ctx.stroke();
  const hpx=120; ctx.strokeStyle='#E8ECF2'; ctx.lineWidth=7; ctx.beginPath(); ctx.moveTo(dx-20,rimY+60); ctx.bezierCurveTo(dx-20,rimY-hpx-40,dx+90,rimY-hpx-40,dx+90,rimY+10); ctx.lineTo(dx+90,floorY); ctx.stroke();
  // dimension lines
  const dim=(x,y0,y1,label,col)=>{ ctx.save(); ctx.strokeStyle=col; ctx.lineWidth=4; ctx.setLineDash([10,8]); ctx.beginPath(); ctx.moveTo(x,y0); ctx.lineTo(x,y1); ctx.stroke(); ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(x-14,y0); ctx.lineTo(x+14,y0); ctx.moveTo(x-14,y1); ctx.lineTo(x+14,y1); ctx.stroke(); text(label,x+30,(y0+y1)/2,{size:40,weight:900,color:col,align:'left',stroke:false}); ctx.restore(); };
  dim(dx+170,rimY-hpx,rimY,'h', t>tH&&t<tDrop? C.yellow:C.white);
  dim(dx+240,rimY,floorY,'h₁', hlH1? C.yellow:C.white);
  ctx.restore();
}
function person(x,baseY,hpx,alpha){ ctx.save(); ctx.globalAlpha=alpha; ctx.strokeStyle='#E8ECF2'; ctx.fillStyle='#E8ECF2'; ctx.lineWidth=hpx*0.06; ctx.lineCap='round';
  const headR=hpx*0.08; ctx.beginPath(); ctx.arc(x,baseY-hpx+headR,headR,0,Math.PI*2); ctx.fill();
  ctx.beginPath(); ctx.moveTo(x,baseY-hpx+2*headR); ctx.lineTo(x,baseY-hpx*0.42); ctx.moveTo(x,baseY-hpx*0.42); ctx.lineTo(x-hpx*0.16,baseY); ctx.moveTo(x,baseY-hpx*0.42); ctx.lineTo(x+hpx*0.16,baseY);
  ctx.moveTo(x-hpx*0.2,baseY-hpx*0.62); ctx.lineTo(x+hpx*0.2,baseY-hpx*0.62); ctx.stroke(); ctx.restore(); }
function fountainIcon(x,baseY,hpx,wpx,col){ ctx.save(); ctx.strokeStyle=col; ctx.lineWidth=7; ctx.beginPath(); ctx.moveTo(x-wpx/2,baseY); ctx.bezierCurveTo(x-wpx/2,baseY-hpx*1.33,x+wpx/2,baseY-hpx*1.33,x+wpx/2,baseY); ctx.stroke(); ctx.restore(); }
function beatScale(tb,t,b){
  const a=fadeInOut(tb,b);
  const px=70,py=470,pw=940,ph=840; panel(px,py,pw,ph,a);
  ctx.save(); ctx.globalAlpha=a;
  text('BIGGER DROP, TALLER FOUNTAIN',W/2,py+60,{size:44,weight:900,stroke:false});
  const t1=wordTime('scale','meters'), t2=wordTime('scale','balcony'), t3=wordTime('scale','tall');
  const baseY=py+ph-120, scale=330/1.7; // px per metre, person = 1.7 m
  // left: 1.5 m drop -> 0.20 m
  const k1=easeOutCubic((t-t1)/0.8); if(t>t1){ const x=px+240; const h=0.20*scale*k1; fountainIcon(x,baseY,h,70,C.blue);
    text('1.5 m drop',x,baseY+50,{size:32,weight:700,color:'rgba(255,255,255,0.8)',stroke:false}); text(Math.round(20*k1)+' cm',x,baseY-h-40,{size:44,weight:900,color:C.blue,stroke:false}); }
  // right: 12 m drop -> 1.6 m next to a person
  const k2=easeOutCubic((t-t2)/1.2); if(t>t2){ const x=px+640; const h=1.6*scale*k2; fountainIcon(x,baseY,h,140,C.orange);
    text('12 m drop',x,baseY+50,{size:32,weight:700,color:'rgba(255,255,255,0.8)',stroke:false}); text((1.6*k2).toFixed(1)+' m',x,baseY-h-40,{size:44,weight:900,color:C.orange,stroke:false}); }
  person(px+830,baseY,1.7*scale,smooth(0,0.3,t-t3+0.2)); if(t>t3) text('you',px+830,baseY+50,{size:32,weight:700,color:'rgba(255,255,255,0.8)',stroke:false});
  ctx.restore();
}
function beatCta(tb,t,b){
  const tFollow=wordTime('cta','follow'); const kf=t-tFollow+0.1; if(kf>0){ const s=lerp(1.6,1,easeOutBack(kf/0.35))*(1+0.03*Math.sin(kf*6));
    ctx.save(); ctx.translate(W/2,860); ctx.scale(s,s); ctx.globalAlpha=smooth(0,0.1,kf); pill('＋ FOLLOW',0,0,{size:76,bg:'#FF2D55',fg:'#fff',padX:54}); ctx.restore();
    ctx.save(); ctx.globalAlpha=smooth(0.2,0.45,kf); text('more physics like this',W/2,980,{size:46,weight:700}); ctx.restore(); }
  const fo=smooth(b.duration-0.45,b.duration-0.02,tb); if(fo>0){ctx.fillStyle=`rgba(0,0,0,${fo})`; ctx.fillRect(0,0,W,H)}
}
window.BEATS = {
  draw: {flash:beatFlash,hook:beatHook,obvious:beatObvious,reversal:beatReversal,kick:beatKick,equation:beatEquation,scale:beatScale,cta:beatCta},
  cutFlash: ['hook','kick','equation','scale','cta'],
  keywords: ['chain','bucket','standing','own','why','watch','pull','trick','hands','slides','drops','lifts','hovers','loop','empty','rigid','rod','yanks','kicks','back','alpha','eighth','height','meters','twenty','balcony','tall','obviously','falls'],
};
