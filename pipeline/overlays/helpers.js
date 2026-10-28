// Shared canvas helpers for the overlay engine (overlay.html) and the
// carousel renderer (pipeline/carousel/panels.html). Classic script, loaded
// before the page's own script: everything here is a global, and the helpers
// draw into the page's global `ctx` (resolved at call time). Per-video
// beats.js / per-post panels.js may define their own top-level functions;
// a function with the same name silently replaces one here, a const with
// the same name is a SyntaxError, so new names here get a distinctive prefix.

const FONT = 'Inter';
const C = { yellow:'#FFD60A', orange:'#FF7A1A', red:'#FF3B3B', blue:'#4DB8FF', green:'#3DDC84', white:'#FFFFFF', ink:'rgba(8,10,16,0.82)' };

// ---------------------------------------------------------------- generic (moved verbatim from overlay.html)
const clamp = (x,a,b)=>Math.max(a,Math.min(b,x));
const lerp = (a,b,t)=>a+(b-a)*t;
const smooth = (e0,e1,x)=>{const t=clamp((x-e0)/(e1-e0),0,1);return t*t*(3-2*t)};
const easeOutBack = t=>{const c1=1.70158,c3=c1+1;t=clamp(t,0,1);return 1+c3*Math.pow(t-1,3)+c1*Math.pow(t-1,2)};
const easeOutCubic = t=>1-Math.pow(1-clamp(t,0,1),3);
const easeOutElastic = t=>{t=clamp(t,0,1);if(t===0||t===1)return t;return Math.pow(2,-10*t)*Math.sin((t*10-0.75)*(2*Math.PI/3))+1};
function mulberry(seed){return function(){let t=seed+=0x6D2B79F5;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296}}
function fmtNum(n){return Math.round(n).toLocaleString('en-US')}
function rr(x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath()}
function font(weight,size,family){ctx.font=`${weight} ${size}px "${family||FONT}", "Noto Color Emoji", sans-serif`}
function text(str,x,y,{size=72,weight=800,color=C.white,align='center',stroke=true,strokeW=null,shadow=true,alpha=1,family=null,baseline='middle'}={}){
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; font(weight,size,family); ctx.textAlign=align; ctx.textBaseline=baseline;
  if(shadow){ctx.shadowColor='rgba(0,0,0,0.55)';ctx.shadowBlur=size*0.18;ctx.shadowOffsetY=size*0.06}
  if(stroke){ctx.lineJoin='round';ctx.lineWidth=strokeW||Math.max(6,size*0.16);ctx.strokeStyle='rgba(0,0,0,0.9)';ctx.strokeText(str,x,y)}
  ctx.shadowColor='transparent'; ctx.fillStyle=color; ctx.fillText(str,x,y); ctx.restore();
}
function measure(str,size,weight){font(weight||800,size);return ctx.measureText(str).width}
function pill(label,x,y,{bg='rgba(10,12,18,0.78)',fg=C.white,size=40,weight=800,padX=28,h=null,border=null,alpha=1,align='center'}={}){
  const w=measure(label,size,weight)+padX*2, hh=h||size*1.7; let x0 = align==='center'?x-w/2:(align==='left'?x:x-w);
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; rr(x0,y-hh/2,w,hh,hh/2); ctx.fillStyle=bg; ctx.fill();
  if(border){ctx.lineWidth=4;ctx.strokeStyle=border;ctx.stroke()}
  text(label,x0+w/2,y+2,{size,weight,color:fg,stroke:false,shadow:false}); ctx.restore(); return w;
}

// ---------------------------------------------------------------- paper + marker + coins (carousels; usable by overlays too)
// Palette for the "textbook page attacked with a marker" look. One accent
// (red); blue is the second-series colour, answer posts only.
const PAPER = { bg:'#F4F0E6', ink:'#161616', red:'#E5261E', blue:'#1F5FE0', grid:'rgba(22,22,22,0.06)', grid2:'rgba(22,22,22,0.11)', soft:'rgba(22,22,22,0.55)' };
let MK_RNG = mulberry(1);              // stroke-seed stream; reset per panel with markerSeed(i)
function markerSeed(seed){ MK_RNG = mulberry(seed*7919+13); }
function mkNext(){ return Math.floor(MK_RNG()*1e9); }

// Smooth 1D value noise in [-1,1]: cosine-interpolated random knots every `step` px of arc length.
function valueNoise1(seed, n){ const r=mulberry(seed), k=[]; for(let i=0;i<n+2;i++) k.push(r()*2-1);
  return s=>{ s=Math.max(0,s); const i=Math.floor(s), f=s-i, u=(1-Math.cos(Math.PI*f))/2; return k[Math.min(i,n)]*(1-u)+k[Math.min(i+1,n+1)]*u; }; }

// Paper: flat warm off-white, faint grid (minor + major lines), low-frequency mottling,
// sparse fibre flecks and a warm corner vignette. Sparse grain instead of per-pixel
// noise keeps the PNGs ~1 MB (TikTok recompresses fine grain to mush anyway).
function paperBg(seed, {grid=54, major=5, vignette=0.16}={}){
  const r=mulberry(seed*31+7);
  ctx.save(); ctx.setTransform(1,0,0,1,0,0); ctx.globalAlpha=1; ctx.globalCompositeOperation='source-over';
  ctx.fillStyle=PAPER.bg; ctx.fillRect(0,0,W,H);
  for(let i=0;i<14;i++){ // mottling: big soft warm/cool blotches, a few % luminance
    const x=r()*W, y=r()*H, rad=180+r()*420, dark=r()<0.55;
    const g=ctx.createRadialGradient(x,y,0,x,y,rad); g.addColorStop(0, dark?'rgba(120,96,60,0.035)':'rgba(255,255,250,0.05)'); g.addColorStop(1,'rgba(0,0,0,0)');
    ctx.fillStyle=g; ctx.fillRect(x-rad,y-rad,rad*2,rad*2); }
  const ox=(W%grid)/2, oy=(H%grid)/2; ctx.lineWidth=2;
  for(let x=ox, i=0; x<=W; x+=grid, i++){ ctx.strokeStyle=(i%major===2)?PAPER.grid2:PAPER.grid; ctx.beginPath(); ctx.moveTo(x+0.5,0); ctx.lineTo(x+0.5,H); ctx.stroke(); }
  for(let y=oy, i=0; y<=H; y+=grid, i++){ ctx.strokeStyle=(i%major===2)?PAPER.grid2:PAPER.grid; ctx.beginPath(); ctx.moveTo(0,y+0.5); ctx.lineTo(W,y+0.5); ctx.stroke(); }
  paperGrain(seed);
  const v=ctx.createRadialGradient(W/2,H/2,H*0.36,W/2,H/2,H*0.62); v.addColorStop(0,'rgba(70,50,20,0)'); v.addColorStop(1,`rgba(70,50,20,${vignette})`);
  ctx.fillStyle=v; ctx.fillRect(0,0,W,H); ctx.restore();
}
function paperGrain(seed, {flecks=2600, fibres=90}={}){
  const r=mulberry(seed*131+3);
  for(let i=0;i<flecks;i++){ const d=r()<0.7; ctx.fillStyle=d?`rgba(60,45,25,${0.05+r()*0.08})`:`rgba(255,255,255,${0.25+r()*0.3})`;
    const s=1+r()*1.6; ctx.fillRect(r()*W, r()*H, s, s); }
  ctx.lineCap='round';
  for(let i=0;i<fibres;i++){ const x=r()*W, y=r()*H, a=r()*Math.PI, l=6+r()*16; ctx.strokeStyle=`rgba(90,70,40,${0.05+r()*0.06})`; ctx.lineWidth=0.8+r();
    ctx.beginPath(); ctx.moveTo(x,y); ctx.quadraticCurveTo(x+Math.cos(a)*l*0.5+r()*4, y+Math.sin(a)*l*0.5+r()*4, x+Math.cos(a)*l, y+Math.sin(a)*l); ctx.stroke(); }
}

// Marker strokes are drawn opaque on an offscreen layer (so self-overlaps don't double up),
// then multiplied onto the page at ~90 % alpha, like ink soaking into paper.
let MK_LAYER = null;
function mkLayer(){ if(!MK_LAYER){ MK_LAYER=document.createElement('canvas'); MK_LAYER.width=W; MK_LAYER.height=H; }
  const m=MK_LAYER.getContext('2d'); m.setTransform(1,0,0,1,0,0); m.clearRect(0,0,W,H); m.setTransform(ctx.getTransform()); return m; }
function mkComposite(alpha){ ctx.save(); ctx.setTransform(1,0,0,1,0,0); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.globalCompositeOperation='multiply'; ctx.drawImage(MK_LAYER,0,0); ctx.restore(); }
// Resample a polyline to ~step px and push each point sideways by smooth noise.
function wobblePts(pts, {wobble=2.6, seed=mkNext(), step=6, freq=70}={}){
  const out=[]; for(let i=0;i<pts.length-1;i++){ const [x0,y0]=pts[i],[x1,y1]=pts[i+1]; const L=Math.hypot(x1-x0,y1-y0), n=Math.max(1,Math.ceil(L/step));
    for(let k=0;k<n;k++) out.push([lerp(x0,x1,k/n), lerp(y0,y1,k/n)]); }
  out.push(pts[pts.length-1]);
  let s=0; const tot=out.reduce((a,p,i)=>i?a+Math.hypot(p[0]-out[i-1][0],p[1]-out[i-1][1]):0,0);
  const nz=valueNoise1(seed, Math.ceil(tot/freq)+2);
  return out.map((p,i)=>{ if(i) s+=Math.hypot(p[0]-out[i-1][0],p[1]-out[i-1][1]);
    const a=out[Math.max(0,i-1)], b=out[Math.min(out.length-1,i+1)]; const dx=b[0]-a[0], dy=b[1]-a[1], l=Math.hypot(dx,dy)||1;
    const o=nz(s/freq)*wobble; return [p[0]-dy/l*o, p[1]+dx/l*o, s/(tot||1)]; });
}
// One marker stroke along pts ([[x,y],...]): width swells slightly mid-stroke and
// tapers at the ends; a few dry streaks are knocked out along the path.
function markerPath(pts, {color=PAPER.red, width=12, alpha=0.9, wobble=2.6, seed=mkNext(), streaks=true}={}){
  const m=mkLayer(), r=mulberry(seed), P=wobblePts(pts,{wobble,seed}), wn=valueNoise1(seed+1, 12);
  m.strokeStyle=color; m.fillStyle=color; m.lineCap='round'; m.lineJoin='round';
  for(let i=1;i<P.length;i++){ const u=P[i][2]; const w=width*(0.82+0.18*Math.sin(Math.PI*clamp(u*1.2,0,1)))*(1+0.08*wn(u*10));
    m.lineWidth=w; m.beginPath(); m.moveTo(P[i-1][0],P[i-1][1]); m.lineTo(P[i][0],P[i][1]); m.stroke(); }
  if(streaks && P.length>4){ m.globalCompositeOperation='destination-out'; m.lineCap='round';
    for(let k=0;k<3;k++){ const off=(r()-0.5)*width*0.55, a0=Math.floor(r()*P.length*0.5), a1=Math.min(P.length-1, a0+Math.floor(P.length*(0.2+r()*0.5)));
      m.globalAlpha=0.10+r()*0.12; m.lineWidth=1+r()*1.5; m.beginPath();
      for(let i=a0;i<=a1;i++){ const a=P[Math.max(0,i-1)], b=P[Math.min(P.length-1,i+1)], dx=b[0]-a[0], dy=b[1]-a[1], l=Math.hypot(dx,dy)||1;
        const x=P[i][0]-dy/l*off, y=P[i][1]+dx/l*off; i===a0?m.moveTo(x,y):m.lineTo(x,y); } m.stroke(); }
    m.globalAlpha=1; m.globalCompositeOperation='source-over'; }
  mkComposite(alpha);
}
function bezierPts(p0, c, p1, n=40){ const o=[]; for(let i=0;i<=n;i++){ const t=i/n, a=(1-t)*(1-t), b=2*(1-t)*t, d=t*t; o.push([a*p0[0]+b*c[0]+d*p1[0], a*p0[1]+b*c[1]+d*p1[1]]); } return o; }
function markerLine(x0,y0,x1,y1,o={}){ markerPath([[x0,y0],[x1,y1]],o); }
// Underline under [x0,x1] at y: a slight upward slope, overshooting the word a little.
function markerUnderline(x0,x1,y,{double=false,slope=-6,...o}={}){ const s=o.seed??mkNext(), w=o.width||12;
  markerPath([[x0-10,y+3],[x1+12,y+slope]],{...o,seed:s});
  if(double) markerPath([[x0+24,y+w*1.7+3],[x1-4,y+slope+w*1.5]],{...o,seed:s+5}); }
// Hand-drawn loop around a thing: ~1.15 turns so the ends overshoot instead of closing.
function markerCircle(cx,cy,rx,ry,{turns=1.13,start=null,tilt=-0.06,...o}={}){ const s=o.seed??mkNext(), r=mulberry(s);
  const a0=start??(-2.2+r()*0.6), ph=r()*6, n=90, pts=[];
  for(let i=0;i<=n;i++){ const a=a0+turns*2*Math.PI*i/n, grow=1+0.06*(i/n)+0.025*Math.sin(i*0.21+ph);
    const x=Math.cos(a)*rx*grow, y=Math.sin(a)*ry*grow; pts.push([cx+x*Math.cos(tilt)-y*Math.sin(tilt), cy+x*Math.sin(tilt)+y*Math.cos(tilt)]); }
  markerPath(pts,{wobble:3,...o,seed:s}); }
// Arrow from p0 to p1 bowing by `bend` (fraction of length, + = left of travel); head = two strokes.
function markerArrow(x0,y0,x1,y1,{bend=0.15,head=38,headAngle=0.5,...o}={}){ const s=o.seed??mkNext();
  const mx=(x0+x1)/2, my=(y0+y1)/2, dx=x1-x0, dy=y1-y0; const c=[mx+dy*bend, my-dx*bend];
  const pts=bezierPts([x0,y0],c,[x1,y1]); markerPath(pts,{...o,seed:s});
  markerArrowHead(pts[pts.length-1], pts[pts.length-4], {head,headAngle,...o,seed:s+3}); return c; }
function markerArrowHead(tip, from, {head=38,headAngle=0.5,...o}={}){ const a=Math.atan2(tip[1]-from[1], tip[0]-from[0]);
  markerPath([[tip[0]-Math.cos(a-headAngle)*head, tip[1]-Math.sin(a-headAngle)*head], tip, [tip[0]-Math.cos(a+headAngle)*head, tip[1]-Math.sin(a+headAngle)*head]],{wobble:1.2,streaks:false,...o}); }
function markerCross(cx,cy,r,o={}){ const s=o.seed??mkNext(); markerLine(cx-r,cy-r*0.9,cx+r,cy+r*0.95,{...o,seed:s}); markerLine(cx+r*0.92,cy-r,cx-r*0.95,cy+r*0.9,{...o,seed:s+2}); }
// Hand-lettered text in Permanent Marker (pipeline/carousel/fonts), multiplied like the strokes.
function markerText(str,x,y,{size=72,color=PAPER.red,align='center',rot=-0.03,alpha=0.92,baseline='middle'}={}){
  const m=mkLayer(); m.translate(x,y); m.rotate(rot); m.font=`${size}px "Permanent Marker"`; m.textAlign=align; m.textBaseline=baseline; m.fillStyle=color;
  if(window.TEXT_HOOK) window.TEXT_HOOK(m,str,0,0,'fill'); m.fillText(str,0,0); mkComposite(alpha);
  m.font=`${size}px "Permanent Marker"`; return m.measureText(str).width; }

// Ink text on paper: no stroke, no shadow. Returns the drawn width.
function ink(str,x,y,{size=64,weight=700,color=PAPER.ink,align='center',baseline='middle',alpha=1,family=null}={}){
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; font(weight,size,family); ctx.textAlign=align; ctx.textBaseline=baseline; ctx.fillStyle=color;
  ctx.fillText(str,x,y); const w=ctx.measureText(str).width; ctx.restore(); return w; }
// Rich line: segs = [[text, {weight,color,size,family}], ...] laid out left to right, aligned as a whole.
// Returns per-segment boxes {x0,x1,y,size} so callers can underline/circle a word.
function inkLine(segs,x,y,{size=56,weight=700,color=PAPER.ink,align='center'}={}){
  const parts=segs.map(([t,s={}])=>{ const st={size,weight,color,...s}; font(st.weight,st.size,st.family); return {t,st,w:ctx.measureText(t).width}; });
  const tot=parts.reduce((a,p)=>a+p.w,0); let cx=align==='center'?x-tot/2:(align==='right'?x-tot:x); const boxes=[];
  for(const p of parts){ ink(p.t,cx,y,{...p.st,align:'left',baseline:'alphabetic'}); boxes.push({t:p.t,x0:cx,x1:cx+p.w,y,size:p.st.size}); cx+=p.w; }
  return boxes; }
// Largest size <= max at which every line fits maxW.
function fitSize(lines,maxW,{weight=900,max=200,family=null}={}){ let s=max; for(const l of lines){ font(weight,100,family); s=Math.min(s, 100*maxW/ctx.measureText(l).width); } return Math.floor(s); }

// A coin seen face-on: soft drop shadow, milled rim, radial-gradient face, raised
// inner ring and an embossed letter. Gold for heads, silver for tails by default.
const COIN_METAL = {
  gold:  {hi:'#FFF1B8', mid:'#E9B949', lo:'#A9761C', edge:'#7A5212', letter:'#C8902C'},
  silver:{hi:'#FFFFFF', mid:'#C9CDD3', lo:'#8A9099', edge:'#5D636C', letter:'#A3A9B2'} };
function coin(cx,cy,r,face='H',{metal=null,alpha=1,shadow=true,rot=0}={}){
  const M=COIN_METAL[metal||(face==='T'?'silver':'gold')];
  ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(cx,cy); ctx.rotate(rot);
  if(shadow){ ctx.save(); ctx.shadowColor='rgba(40,28,10,0.38)'; ctx.shadowBlur=r*0.28; ctx.shadowOffsetX=r*0.07; ctx.shadowOffsetY=r*0.12;
    ctx.beginPath(); ctx.arc(0,0,r,0,Math.PI*2); ctx.fillStyle=M.lo; ctx.fill(); ctx.restore(); }
  let g=ctx.createLinearGradient(-r,-r,r,r); g.addColorStop(0,M.hi); g.addColorStop(0.45,M.mid); g.addColorStop(1,M.edge);
  ctx.beginPath(); ctx.arc(0,0,r,0,Math.PI*2); ctx.fillStyle=g; ctx.fill();
  ctx.lineWidth=Math.max(1,r*0.018); ctx.strokeStyle=M.edge; // milled edge: radial ticks
  const n=Math.round(r*1.15); ctx.beginPath(); for(let i=0;i<n;i++){ const a=i/n*Math.PI*2; ctx.moveTo(Math.cos(a)*r*0.9,Math.sin(a)*r*0.9); ctx.lineTo(Math.cos(a)*r*0.985,Math.sin(a)*r*0.985); }
  ctx.globalAlpha*=0.55; ctx.stroke(); ctx.globalAlpha/=0.55;
  g=ctx.createRadialGradient(-r*0.35,-r*0.4,r*0.05,0,0,r*0.9); g.addColorStop(0,M.hi); g.addColorStop(0.55,M.mid); g.addColorStop(1,M.lo);
  ctx.beginPath(); ctx.arc(0,0,r*0.86,0,Math.PI*2); ctx.fillStyle=g; ctx.fill();
  ctx.lineWidth=r*0.035; ctx.strokeStyle='rgba(255,255,255,0.55)'; ctx.beginPath(); ctx.arc(-r*0.012,-r*0.012,r*0.78,Math.PI*0.75,Math.PI*1.75); ctx.stroke();
  ctx.strokeStyle='rgba(0,0,0,0.22)'; ctx.beginPath(); ctx.arc(r*0.012,r*0.012,r*0.78,-Math.PI*0.25,Math.PI*0.75); ctx.stroke();
  ctx.fillStyle='rgba(0,0,0,0.18)'; for(let i=0;i<24;i++){ const a=i/24*Math.PI*2; ctx.beginPath(); ctx.arc(Math.cos(a)*r*0.7,Math.sin(a)*r*0.7,r*0.016,0,Math.PI*2); ctx.fill(); }
  const KIND=window.TEXT_KIND; window.TEXT_KIND='glyph';
  font(900,r*1.02); ctx.textAlign='center'; ctx.textBaseline='middle'; const dy=r*0.04, e=Math.max(1.5,r*0.03);
  ctx.fillStyle='rgba(255,255,255,0.8)'; ctx.fillText(face,-e,dy-e);
  ctx.fillStyle='rgba(0,0,0,0.55)'; ctx.fillText(face,e*1.4,dy+e*1.4);
  g=ctx.createLinearGradient(0,-r*0.5,0,r*0.5); g.addColorStop(0,M.letter); g.addColorStop(1,M.lo); ctx.fillStyle=g; ctx.fillText(face,0,dy);
  window.TEXT_KIND=KIND; ctx.restore();
}
// A row of coins centred on cx; returns the centres so callers can circle a run.
function coinRow(faces,cx,cy,{r=70,gap=16,...o}={}){ const n=faces.length, tot=n*2*r+(n-1)*gap; const xs=[];
  for(let i=0;i<n;i++){ const x=cx-tot/2+r+i*(2*r+gap); xs.push(x); coin(x,cy,r,faces[i],o); } return xs; }
// A lateral-flow test cassette (sample well + C/T window); positive = both lines.
function testStrip(cx,cy,{rot=0,positive=true,scale=1}={}){
  ctx.save(); ctx.translate(cx,cy); ctx.rotate(rot); ctx.scale(scale,scale);
  ctx.save(); ctx.shadowColor='rgba(40,28,10,0.3)'; ctx.shadowBlur=24; ctx.shadowOffsetY=10;
  rr(-330,-95,660,190,40); ctx.fillStyle='#FFFFFF'; ctx.fill(); ctx.restore();
  ctx.lineWidth=4; ctx.strokeStyle='rgba(22,22,22,0.25)'; rr(-330,-95,660,190,40); ctx.stroke();
  rr(-90,-42,230,84,18); ctx.fillStyle='#ECE8E0'; ctx.fill(); ctx.strokeStyle='rgba(22,22,22,0.3)'; ctx.stroke();
  ctx.beginPath(); ctx.arc(-230,0,46,0,Math.PI*2); ctx.fillStyle='#ECE8E0'; ctx.fill(); ctx.stroke();
  ctx.fillStyle='rgba(200,30,30,0.85)'; ctx.fillRect(-30,-36,16,72); if(positive) ctx.fillRect(70,-36,16,72);
  const KIND=window.TEXT_KIND; window.TEXT_KIND='glyph';
  font(800,26); ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillStyle=PAPER.soft; ctx.fillText('C',-22,70); ctx.fillText('T',78,70);
  window.TEXT_KIND=KIND; ctx.restore();
}
// cols x rows dots (a population); `mark` = indices drawn in `markColor`. Returns dot centres by index.
function dotGrid(x0,y0,cols,rows,step,{r=1.8,color='rgba(22,22,22,0.55)',mark=[],markColor=PAPER.red,markR=null}={}){
  const pos=i=>[x0+(i%cols)*step+step/2, y0+Math.floor(i/cols)*step+step/2];
  ctx.save(); ctx.fillStyle=color; ctx.beginPath();
  for(let i=0;i<cols*rows;i++){ const [x,y]=pos(i); ctx.moveTo(x+r,y); ctx.arc(x,y,r,0,Math.PI*2); } ctx.fill();
  ctx.fillStyle=markColor; for(const i of mark){ const [x,y]=pos(i); ctx.beginPath(); ctx.arc(x,y,markR||r*2.2,0,Math.PI*2); ctx.fill(); }
  ctx.restore(); return pos;
}
