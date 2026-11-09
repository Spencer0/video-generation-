// Beat graphics for video 006: Mount St. Helens, May 18 1980 (David Johnston's last radio call).
// Fully 2D, anime / cel look: flat fills, hard two- or three-tone shading, ink outlines, impact frames,
// speed lines, eye cut-ins. Every beat paints its own opaque frame; "shots": {} in script.json.
// Scenery goes through S(fn) so `--eval "window.READABLE_ONLY=true"` renders only the readable layer
// (titles, pills, bubbles, captions) for checks.py --only-safe-area.
(function(){
const INK='#1b1730', SKIN='#f4c7a1', SKIN_SH='#d99a7a', BLOND='#f0c659', BLOND_SH='#c38d36';
const TAU=Math.PI*2;
function S(fn){ if(!window.READABLE_ONLY) fn(); }
const wt=(b,w,n)=>wordTime(b,w,n||0);

// ---------------------------------------------------------------- drawing primitives
function vgrad(y0,y1,stops){ const g=ctx.createLinearGradient(0,y0,0,y1); stops.forEach(([o,c])=>g.addColorStop(o,c)); return g; }
function fillAll(style){ ctx.fillStyle=style; ctx.fillRect(-200,-200,W+400,H+400); }
function pathOf(pts,close=true){ ctx.beginPath(); pts.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1])); if(close) ctx.closePath(); }
function poly(pts,fill,stroke,lw=6){ pathOf(pts); if(fill){ctx.fillStyle=fill;ctx.fill()} if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lw;ctx.lineJoin='round';ctx.stroke()} }
function circ(x,y,r,fill,stroke,lw=6){ ctx.beginPath(); ctx.arc(x,y,Math.max(0,r),0,TAU); if(fill){ctx.fillStyle=fill;ctx.fill()} if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lw;ctx.stroke()} }
function ell(x,y,rx,ry,rot,fill,stroke,lw=6){ ctx.beginPath(); ctx.ellipse(x,y,Math.max(0,rx),Math.max(0,ry),rot||0,0,TAU); if(fill){ctx.fillStyle=fill;ctx.fill()} if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lw;ctx.stroke()} }
function line(pts,color,lw,cap='round'){ pathOf(pts,false); ctx.strokeStyle=color; ctx.lineWidth=lw; ctx.lineCap=cap; ctx.lineJoin='round'; ctx.stroke(); }
function shakeXY(t,amp){ return [amp*(Math.sin(t*83.1)+Math.sin(t*47.3+1.3))/2, amp*(Math.sin(t*71.7+2.1)+Math.sin(t*39.9))/2]; }
// Cel-shaded cloud made of circles: ink silhouette, dark base, mid tone and highlight offset toward the light.
function blobs(list,{dark,mid,lite,outline=INK,ow=7,lx=-0.3,ly=-0.38}){
  if(outline){ ctx.fillStyle=outline; ctx.beginPath(); for(const [x,y,r] of list){ if(r>1){ ctx.moveTo(x+r+ow,y); ctx.arc(x,y,r+ow,0,TAU); } } ctx.fill(); }
  ctx.fillStyle=dark; ctx.beginPath(); for(const [x,y,r] of list){ if(r>1){ ctx.moveTo(x+r,y); ctx.arc(x,y,r,0,TAU); } } ctx.fill();
  if(mid){ ctx.fillStyle=mid; ctx.beginPath(); for(const [x,y,r] of list){ if(r>1){ const X=x+lx*r*0.45,Y=y+ly*r*0.45; ctx.moveTo(X+r*0.78,Y); ctx.arc(X,Y,r*0.78,0,TAU); } } ctx.fill(); }
  if(lite){ ctx.fillStyle=lite; ctx.beginPath(); for(const [x,y,r] of list){ if(r>1){ const X=x+lx*r*0.92,Y=y+ly*r*0.92; ctx.moveTo(X+r*0.5,Y); ctx.arc(X,Y,r*0.5,0,TAU); } } ctx.fill(); }
}
function cumulus(cx,cy,s,seed,pal=['#a9c8f4','#e2eeff','#ffffff']){ const r=mulberry(seed), n=7, list=[];
  for(let i=0;i<n;i++){ const k=1-Math.abs(i-(n-1)/2)/n*1.5; const rad=(48+r()*40)*s*Math.max(0.35,k); list.push([cx+(i-(n-1)/2)*62*s+(r()-0.5)*26*s, cy-rad*0.55, rad]); }
  ctx.save(); ctx.beginPath(); ctx.rect(cx-500*s,cy-400*s,1000*s,400*s+8*s); ctx.clip(); blobs(list,{dark:pal[0],mid:pal[1],lite:pal[2],outline:null}); ctx.restore(); }
function glow(x,y,r,color,alpha=1){ ctx.save(); ctx.globalCompositeOperation='lighter'; ctx.globalAlpha=ctx.globalAlpha*alpha; const g=ctx.createRadialGradient(x,y,0,x,y,r); g.addColorStop(0,color); g.addColorStop(1,'rgba(0,0,0,0)'); ctx.fillStyle=g; ctx.fillRect(x-r,y-r,r*2,r*2); ctx.restore(); }
// Radial speed lines (thin wedges pointing at the focus); reseeded every other frame so they flicker.
function speedLines(cx,cy,t,{n=46,inner=420,outer=1500,color='#ffffff',alpha=0.8,seed=1,wid=0.022}={}){ const r=mulberry(seed*977+Math.floor(t*15)); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.fillStyle=color;
  for(let i=0;i<n;i++){ const a=r()*TAU, w=wid*(0.4+r()), r0=inner*(0.75+r()*0.6); ctx.beginPath(); ctx.moveTo(cx+Math.cos(a)*r0,cy+Math.sin(a)*r0); ctx.lineTo(cx+Math.cos(a-w)*outer,cy+Math.sin(a-w)*outer); ctx.lineTo(cx+Math.cos(a+w)*outer,cy+Math.sin(a+w)*outer); ctx.fill(); } ctx.restore(); }
function streaks(t,{n=26,y0=300,y1=1500,color='#ffffff',alpha=0.7,seed=3,len=420,dir=1}={}){ const r=mulberry(seed*131+Math.floor(t*15)); ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.fillStyle=color;
  for(let i=0;i<n;i++){ const y=y0+r()*(y1-y0), x=r()*W*1.2-100, l=len*(0.4+r()), h=3+r()*7; ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x+l*dir,y-h/2); ctx.lineTo(x+l*dir,y+h/2); ctx.fill(); } ctx.restore(); }
function pine(x,y,h,col='#1f5b4a',rot=0,sh='#17463b'){ ctx.save(); ctx.translate(x,y); ctx.rotate(rot); const w=h*0.42;
  for(let k=0;k<3;k++){ const yy=-h*(0.18+k*0.26), ww=w*(1-k*0.24); ctx.beginPath(); ctx.moveTo(-ww/2,yy); ctx.lineTo(0,yy-h*0.42); ctx.lineTo(ww/2,yy); ctx.closePath(); ctx.fillStyle=col; ctx.fill(); ctx.beginPath(); ctx.moveTo(0,yy); ctx.lineTo(0,yy-h*0.42); ctx.lineTo(ww/2,yy); ctx.closePath(); ctx.fillStyle=sh; ctx.fill(); }
  ctx.fillStyle='#4a3326'; ctx.fillRect(-h*0.03,-h*0.2,h*0.06,h*0.2); ctx.restore(); }
function ridgeLine(seed,y,amp,n=28){ const nz=valueNoise1(seed,n+2), pts=[]; for(let i=0;i<=n;i++) pts.push([-40+i*(W+80)/n, y+nz(i*0.55)*amp]); return pts; }
function ridge(pts,fill,stroke){ poly([...pts,[W+60,H+60],[-60,H+60]],fill,stroke,5); }
function yOn(pts,x){ for(let i=1;i<pts.length;i++){ if(x<=pts[i][0]){ const a=pts[i-1],b=pts[i]; return lerp(a[1],b[1],(x-a[0])/(b[0]-a[0])); } } return pts[pts.length-1][1]; }
// Manga-style title: hard offset shadow + thick ink stroke + fill, slanted like hand lettering.
function title(str,x,y,{size=96,color='#fff',rot=0,slant=-0.14,sw=null,alpha=1,scale=1,weight=900}={}){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; ctx.translate(x,y); ctx.rotate(rot); ctx.scale(scale,scale); ctx.transform(1,0,slant,1,0,0);
  font(weight,size); ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.lineJoin='round'; const w=sw||Math.max(10,size*0.17);
  ctx.fillStyle=INK; ctx.strokeStyle=INK; ctx.lineWidth=w; ctx.strokeText(str,size*0.05,size*0.08); ctx.strokeText(str,0,0); ctx.fillStyle=color; ctx.fillText(str,0,0); ctx.restore(); }
function pop(t,t0,d=0.28){ return t<t0?0:lerp(1.3,1,easeOutBack((t-t0)/d)); }
function tag(str,x,y,{size=38,bg=INK,fg='#fff',border='#fff',align='center',alpha=1}={}){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; pill(str,x,y,{size,bg,fg,border,weight:800,align,padX:26}); ctx.restore(); }

// ---------------------------------------------------------------- the mountain (exterior, seen from the north ridge)
const PAL_DAY={snow:'#ffffff',snowSh:'#b7c9f2',rock:'#5a6a9e',rockSh:'#44518a',line:'#8ea6e6'};
const PAL_FIRE={snow:'#ffe2cf',snowSh:'#a37fb6',rock:'#5b4775',rockSh:'#3f3260',line:'#c79ad0'};
const PAL_DUSK={snow:'#ffe9dc',snowSh:'#b79ad2',rock:'#6b5a8e',rockSh:'#4f4276',line:'#d2b4e0'};
function coneProfile(cx,baseY,w,h,seed=4,crater=0){ const nz=valueNoise1(seed,40), pts=[]; const n=64;
  for(let i=0;i<=n;i++){ const u=-1+2*i/n, a=Math.abs(u); let f=Math.pow(1-a,1.55); if(a<0.07) f=Math.pow(0.93,1.55)+0.012*Math.cos(a/0.07*Math.PI/2);
    if(crater>0){ const c=0.62-0.20*Math.exp(-u*u/0.02)+0.06*Math.exp(-(u-0.02)*(u-0.02)/0.0012); f=Math.min(f, lerp(f,c+0.03*nz(i*0.9+7),crater)); }   // 1980 collapse: horseshoe crater with the lava dome
    f+=0.012*nz(i*0.6)*(1-a); pts.push([cx+u*w/2, baseY-h*f]); } return pts; }
function cone(cx,baseY,w,h,{pal=PAL_DAY,seed=4,crater=0,outline=true,jag=0.16}={}){
  const P=coneProfile(cx,baseY,w,h,seed,crater), r=mulberry(seed*13+1);
  ctx.save(); pathOf([...P,[cx+w/2,baseY+40],[cx-w/2,baseY+40]]); if(outline){ ctx.strokeStyle=INK; ctx.lineWidth=7; ctx.lineJoin='round'; ctx.stroke(); } ctx.fillStyle=pal.snow; ctx.fill(); ctx.clip();
  // shaded east side: a zigzag ridge line down from the summit
  const top=baseY-h*(crater?0.6:0.95), sh=[[cx+w*0.02,top-30]]; for(let k=1;k<=9;k++){ sh.push([cx+w*(0.02+0.05*k*(0.6+0.4*(k%2)))+ (r()-0.5)*w*0.03, top+(baseY-top)*k/9]); }
  poly([...sh,[cx+w/2+20,baseY+40],[cx+w/2+20,top-60]],pal.snowSh);
  for(let k=0;k<7;k++){ const u=-0.42+k*0.11+(r()-0.5)*0.05, x0=cx+u*w*0.16, y0=top+h*0.06, x1=cx+u*w*0.95, y1=baseY-h*0.2; poly([[x0,y0],[lerp(x0,x1,0.5)+w*0.007,lerp(y0,y1,0.5)],[x1+w*0.016,y1],[x1,y1]],u<0?pal.snowSh:pal.line); }
  // rock below a ragged snowline
  const rock=[[cx-w/2-20,baseY+40]]; const nt=22; for(let k=0;k<=nt;k++){ const x=cx-w/2+k*w/nt; rock.push([x, baseY-h*(0.2+(k%2?jag:0.0)+0.07*r())]); } rock.push([cx+w/2+20,baseY+40]);
  poly(rock,pal.rock); ctx.save(); pathOf(rock); ctx.clip(); poly([[cx+w*0.08,baseY-h*0.5],[cx+w/2+20,baseY-h*0.5],[cx+w/2+20,baseY+40],[cx+w*0.2,baseY+40]],pal.rockSh); ctx.restore();
  if(crater>0){ poly([[cx-w*0.085,baseY-h*0.585],[cx+w*0.01,baseY-h*0.47],[cx+w*0.10,baseY-h*0.585],[cx+w*0.17,baseY-h*0.25],[cx-w*0.15,baseY-h*0.25]],pal.rockSh); }
  ctx.restore(); return P; }

// ---------------------------------------------------------------- David, always seen from behind (no invented likeness of a real face)
function davidBack(cx,cy,s,t,{radio=0,chair=false,wind=0}={}){ ctx.save(); ctx.translate(cx,cy); ctx.scale(s,s);
  const J='#d8502a', JS='#a53a22';
  const jacket=()=>{ ctx.beginPath(); ctx.moveTo(-380,700); ctx.lineTo(-335,220); ctx.quadraticCurveTo(-315,95,-175,52); ctx.lineTo(-60,12); ctx.lineTo(60,12); ctx.lineTo(175,52); ctx.quadraticCurveTo(315,95,335,220); ctx.lineTo(380,700); ctx.closePath(); };
  jacket(); ctx.fillStyle=J; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=8; ctx.lineJoin='round'; ctx.stroke();
  ctx.save(); jacket(); ctx.clip(); poly([[70,0],[420,0],[420,720],[150,720],[110,330]],JS); line([[-150,330],[-190,700]],JS,10); line([[0,90],[0,700]],JS,8); ctx.restore();
  rr(-46,-110,92,150,10); ctx.fillStyle=SKIN_SH; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=6; ctx.stroke(); ell(0,44,150,54,0,'#b8421f',INK,7);
  ell(-182,-190,22,40,0,SKIN,INK,6); ell(182,-190,22,40,0,SKIN_SH,INK,6);
  // hair from behind: rounded mass, crescent shadow on the east side, highlight band, short nape spikes, wind flicks
  const hp=[]; for(let i=0;i<=30;i++){ const a=Math.PI*(2.13-1.26*i/30); const rr2=186+((i%2)?5:0); hp.push([Math.cos(a)*rr2, -215+Math.sin(a)*rr2*1.04]); }   // right-lower -> over the top -> left-lower
  const sway=wind*Math.sin(t*9)*10; const nape=[[-172,-138],[-140,-84+sway*0.4],[-112,-128],[-80,-70+sway*0.5],[-48,-124],[-14,-62+sway*0.5],[20,-124],[52,-70+sway*0.5],[84,-128],[116,-84+sway*0.4],[150,-134],[172,-138]];
  const tufts=wind?[[-180,-262],[-226-wind*14,-270+sway],[-184,-234],[-238-wind*18,-222+sway*1.2],[-184,-200],[-222-wind*12,-176+sway],[-176,-166]]:[];
  const hair=[...hp,...tufts,...nape];
  poly(hair,BLOND_SH,INK,8); ctx.save(); pathOf(hair); ctx.clip(); ell(-46,-262,168,176,0,BLOND);
  line([[-126,-318],[-92,-296],[-58,-328],[-20,-300],[18,-332],[50,-306]],'#fff3bd',15);
  for(const q of [-70,10,80]){ ctx.beginPath(); ctx.moveTo(q*0.3,-392); ctx.quadraticCurveTo(q*1.5,-270,q*1.2,-130); ctx.strokeStyle='rgba(120,80,20,0.55)'; ctx.lineWidth=5; ctx.stroke(); } ctx.restore();
  if(chair){ rr(-235,150,470,330,22); ctx.fillStyle='#2f7d6b'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=8; ctx.stroke(); ctx.fillStyle='#256457'; ctx.fillRect(-225,330,450,140); line([[-250,120],[-250,700]],INK,22); line([[250,120],[250,700]],INK,22); line([[-250,120],[-250,700]],'#c9ccd6',10); line([[250,120],[250,700]],'#c9ccd6',10); }
  if(radio){ const lift=radio; const sh=[262,175], el=[385,330-40*lift], wr=[lerp(330,238,lift),lerp(250,-70,lift)];
    line([sh,el,wr],INK,116); line([sh,el,wr],JS,100); ctx.save(); ctx.translate(wr[0],wr[1]-50); ctx.rotate(-0.12);
    line([[26,-150],[40,-330]],INK,12); rr(-44,-160,88,200,14); ctx.fillStyle='#2b2b36'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=7; ctx.stroke();
    for(let k=0;k<4;k++) line([[-24,-130+k*16],[24,-130+k*16]],'#6b6b7c',5); circ(-20,-50,7,(Math.floor(t*6)%2)?'#ff3b3b':'#7a1f1f'); ctx.restore();
    circ(wr[0]-4,wr[1]-8,50,SKIN,INK,7); line([[wr[0]-38,wr[1]-28],[wr[0]+30,wr[1]-34]],SKIN_SH,6); line([[wr[0]-40,wr[1]-6],[wr[0]+32,wr[1]-12]],SKIN_SH,6); }
  ctx.restore(); }

// ---------------------------------------------------------------- blast cloud (exterior), shared by hook + radio
function blastBlobs(cx,cy,R,t,seed,{n=44,a0=-Math.PI*1.05,a1=Math.PI*0.05,down=0.55}={}){ const r=mulberry(seed), out=[];
  for(let i=0;i<n;i++){ const a=lerp(a0,a1,r()), d=Math.pow(r(),0.6), ph=r()*TAU, big=0.5+r()*0.6; const rad=R*(0.16+0.3*d)*big*(1+0.05*Math.sin(t*5+ph));
    out.push([cx+Math.cos(a)*R*d*0.95, cy+Math.sin(a)*R*d*0.62+R*down*d*d, rad]); }
  return out.sort((a,b)=>a[1]-b[1]); }
function ejecta(cx,cy,t,seed,n=16,speed=620){ const r=mulberry(seed); ctx.save(); ctx.lineCap='round';
  for(let i=0;i<n;i++){ const a=-Math.PI*(0.08+0.84*r()), v=speed*(0.6+r()*0.9), ph=r()*1.2, k=((t+ph)%1.4), x=cx+Math.cos(a)*v*k, y=cy+Math.sin(a)*v*k+260*k*k, x0=cx+Math.cos(a)*v*(k-0.09), y0=cy+Math.sin(a)*v*(k-0.09)+260*(k-0.09)*(k-0.09);
    if(k<0.1) continue; line([[x0,y0],[x,y]],'#ff7a1a',9); line([[lerp(x0,x,0.5),lerp(y0,y,0.5)],[x,y]],'#ffe27a',5); circ(x,y,7,'#2a1c2c'); } ctx.restore(); }
function lightning(x0,y0,x1,y1,seed){ const r=mulberry(seed), pts=[[x0,y0]]; for(let i=1;i<7;i++){ pts.push([lerp(x0,x1,i/7)+(r()-0.5)*70, lerp(y0,y1,i/7)+(r()-0.5)*40]); } pts.push([x1,y1]); line(pts,'#ffffff',9); line(pts,'#c9b8ff',3); }

function eruptionWide(t,g,{mx=540,my=1060,shake=1}={}){
  fillAll(vgrad(0,1200,[[0,'#2a1846'],[0.45,'#8e2f5a'],[0.8,'#ff7a3a'],[1,'#ffc46a']]));
  speedLines(mx,my-420,t,{n:34,inner:520,outer:1700,color:'#ffe9b0',alpha:0.22,seed:5});
  cone(mx,my,980,600,{pal:PAL_FIRE,jag:0.05});
  const R=lerp(330,720,g), cx=mx+20, cy=my-500;
  glow(cx,cy+40,R*1.5,'rgba(255,150,60,0.55)');
  const B=blastBlobs(cx,cy,R,t,11,{down:0.1});
  blobs(B,{dark:'#3b2c4a',mid:'#73587a',lite:'#c79a96'});
  // incandescent core
  const core=blastBlobs(cx,cy+60,R*0.42,t*1.4,23,{n:14,down:0.25});
  blobs(core,{dark:'#ff5a1f',mid:'#ff9a2a',lite:'#ffe88a',outline:'#7a1f2c',ow:5});
  glow(cx,cy,R*0.8,'rgba(255,200,90,0.5)');
  ejecta(cx,cy,t,31);
  if(Math.floor(t*12)%5===0) lightning(cx-R*0.4,cy-R*0.5,cx-R*0.1+((t*997)%120),cy+R*0.1,Math.floor(t*12));
  // foreground ridge
  ridge(ridgeLine(21,my+60,26),'#3a2a55'); const fr=ridgeLine(22,my+190,34); ridge(fr,'#241a3d');
  const r=mulberry(77); for(let i=0;i<26;i++){ const x=r()*W; pine(x,yOn(fr,x)+10,70+r()*60,'#1d1533',Math.sin(t*14+i)*0.05-0.06,'#150f27'); }
}

// ---------------------------------------------------------------- beat: hook
function eyesCutIn(t,k){ // k: seconds since the cut-in started
  const x=lerp(W+200,0,easeOutCubic(k/0.14)), cy=720, hh=128, sl=44;
  ctx.save(); ctx.translate(x,0); const band=[[-60,cy-hh+sl],[W+60,cy-hh-sl],[W+60,cy+hh-sl],[-60,cy+hh+sl]];
  poly(band,INK,INK,22); ctx.save(); pathOf(band); ctx.clip();
  fillAll(SKIN); poly([[-60,cy+70],[W+60,cy+10],[W+60,cy+300],[-60,cy+300]],SKIN_SH);
  glow(180,cy-40,520,'rgba(255,140,50,0.45)');
  const jx=Math.sin(t*61)*3, jy=Math.sin(t*53+1)*3;
  for(const side of [-1,1]){ ctx.save(); ctx.translate(540+side*215,cy+12-side*18); ctx.rotate(-0.08); ctx.scale(side,1);
    // eyebrow (raised, inner end up), sclera, iris with the blast reflected, heavy upper lid
    poly([[-150,-108],[-40,-150],[80,-150],[120,-128],[70,-126],[-40,-124]],'#a8752c',INK,5);
    ctx.beginPath(); ctx.moveTo(-128,6); ctx.quadraticCurveTo(-70,-84,16,-86); ctx.quadraticCurveTo(102,-80,132,-10); ctx.quadraticCurveTo(70,62,-26,60); ctx.quadraticCurveTo(-92,52,-128,6); ctx.closePath();
    ctx.fillStyle='#fff'; ctx.fill(); ctx.save(); ctx.clip();
    ctx.fillStyle='rgba(120,90,140,0.28)'; ctx.fillRect(-160,-100,320,44);
    const ix=4+jx*side, iy=-10+jy; circ(ix,iy,62,'#2c6fb8',INK,6); circ(ix,iy+16,44,'#63c3e6'); circ(ix,iy,15,'#0d1326');
    blobs([[ix-24,iy-22,22],[ix-2,iy-34,17],[ix-38,iy-6,13]],{dark:'#ff7a1a',mid:'#ffb347',lite:'#fff2b0',outline:null});
    circ(ix+24,iy+24,8,'#ffffff'); ctx.restore();
    ctx.beginPath(); ctx.moveTo(-140,14); ctx.quadraticCurveTo(-72,-92,16,-94); ctx.quadraticCurveTo(108,-88,140,-12); ctx.strokeStyle=INK; ctx.lineWidth=15; ctx.lineCap='round'; ctx.stroke();
    line([[140,-12],[166,-34]],INK,10); ctx.beginPath(); ctx.moveTo(-70,58); ctx.quadraticCurveTo(0,70,80,44); ctx.strokeStyle=INK; ctx.lineWidth=5; ctx.stroke();
    for(let q=0;q<3;q++) line([[-60+q*26,92],[-78+q*26,118]],SKIN_SH,5);
    ctx.restore(); }
  poly([[505,cy+40],[560,cy+26],[548,cy+140],[520,cy+140]],SKIN_SH);
  // bangs
  const bg=[[-60,cy-hh-80]]; for(let i=0;i<=12;i++){ bg.push([-60+i*100, cy-hh+((i%2)?64:8)-i*7+Math.sin(t*9+i)*5]); } bg.push([W+60,cy-hh-200]); poly(bg,BLOND,INK,7);
  // sweat
  ctx.beginPath(); ctx.moveTo(930,cy-40); ctx.quadraticCurveTo(906,cy+6,930,cy+18); ctx.quadraticCurveTo(954,cy+6,930,cy-40); ctx.fillStyle='#d9f1ff'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=4; ctx.stroke();
  streaks(t,{n:10,y0:cy-hh,y1:cy+hh,alpha:0.5,len:300,seed:9});
  ctx.restore(); line([band[0],band[1]],'#fff',6,'butt'); line([band[3],band[2]],'#fff',6,'butt'); ctx.restore(); }

function beatHook(tb,t,b){
  const g=easeOutCubic(tb/2.6)*0.75+0.25*tb/2.6, sh=shakeXY(t,10*(1-0.5*smooth(0.4,2.2,tb)));
  S(()=>{ ctx.save(); ctx.translate(sh[0],sh[1]); const tS2=wt('hook','seconds'), z=1.0+0.085*tb+0.05*Math.exp(-Math.max(0,t-tS2)*7)*(t>tS2?1:0); ctx.translate(540,760); ctx.scale(z,z); ctx.translate(-540,-760);
    eruptionWide(t,g);
    for(let i=0;i<3;i++){ const k=((tb*0.9+i/3)%1); ctx.save(); ctx.globalAlpha=(1-k)*0.75; ell(560,560,160+k*900,(160+k*900)*0.42,0,null,'#fff3d0',16*(1-k)+3); ctx.restore(); }   // shock rings
    if(t>tS2&&t<tS2+0.3) speedLines(560,600,t,{n:50,inner:380,color:'#fff',alpha:0.7*(1-(t-tS2)/0.3),seed:4});
    davidBack(430,1330,0.86,t,{radio:smooth(0.35,0.75,tb),wind:1});
    ctx.restore();
    // blast light + shadow grade
    glow(560,560,1100,'rgba(255,120,40,0.20)'); const v=ctx.createRadialGradient(540,800,500,540,960,1250); v.addColorStop(0,'rgba(20,8,40,0)'); v.addColorStop(1,'rgba(20,8,40,0.55)'); ctx.fillStyle=v; ctx.fillRect(0,0,W,H);
    if(tb<0.07){ ctx.save(); ctx.globalCompositeOperation='difference'; ctx.fillStyle='#fff'; ctx.fillRect(0,0,W,H); ctx.restore(); speedLines(560,640,t,{n:60,inner:300,color:'#000',alpha:0.9,seed:2,wid:0.03}); }
    else { flash(t,b.start+0.07,{dur:0.3,peak:0.8}); flash(t,wt('hook','seconds'),{dur:0.2,peak:0.5}); }
    const tc=wt('hook','world')+0.05; if(t>tc){ eyesCutIn(t,t-tc); flash(t,tc,{dur:0.15,peak:0.5}); }
  });
  // readable: true-story tag (frame 0); the spoken line is the caption
  const s=tb<0.25?lerp(1.08,1,easeOutBack(tb/0.25)):1; ctx.save(); ctx.translate(540,322); ctx.scale(s,s); ctx.rotate(-0.03);
  pill('TRUE STORY  •  MAY 18, 1980',0,0,{size:44,weight:900,bg:'#ffd60a',fg:INK,border:INK,padX:34}); ctx.restore();
  title('8:32 AM',540,420,{size:76,color:'#fff',alpha:smooth(0.12,0.3,tb)});
}

// ---------------------------------------------------------------- beat: who (the calm morning)
function morning(t,{zoom=1,ox=0,oy=0}={}){
  ctx.save(); ctx.translate(540+ox,900+oy); ctx.scale(zoom,zoom); ctx.translate(-540,-900);
  fillAll(vgrad(0,1150,[[0,'#1c5fe0'],[0.5,'#47a5f5'],[0.85,'#aee0ff'],[1,'#e9f8ff']]));
  glow(900,330,520,'rgba(255,250,220,0.55)'); circ(900,330,58,'#fffbe6');
  cumulus(((t*14+180)%1500)-200,470,1.5,3); cumulus(((t*9+900)%1500)-200,640,1.0,8); cumulus(((t*11+520)%1500)-200,330,0.8,12);
  ridge(ridgeLine(41,1085,22),'#7fa6dc');
  const P=cone(560,1110,920,560,{pal:PAL_DAY});
  // a wisp of steam at the summit: the mountain has been restless since March
  const st=[]; for(let i=0;i<5;i++){ const k=((t*0.22+i*0.2)%1); st.push([560+18+k*70+Math.sin(t+i)*8, 562-k*120, 16+k*30]); } ctx.save(); ctx.globalAlpha=0.85; blobs(st,{dark:'#d7e3f7',mid:'#ffffff',lite:null,outline:null}); ctx.restore();
  ridge(ridgeLine(42,1120,20),'#3f7f8f');
  // Spirit Lake with the mountain's reflection
  ctx.save(); pathOf([[-60,1190],[380,1168],[820,1178],[W+60,1200],[W+60,1300],[-60,1300]]); ctx.fillStyle='#3d8fe0'; ctx.fill(); ctx.clip();
  ctx.save(); ctx.globalAlpha=0.35; ctx.translate(0,2290); ctx.scale(1,-1); cone(560,1110,920,560,{pal:PAL_DAY,outline:false}); ctx.restore();
  for(let i=0;i<9;i++){ const x=((i*173+t*30)%1200)-60, y=1196+((i*37)%90); line([[x,y],[x+70+i*6,y]],'rgba(255,255,255,0.75)',4); } ctx.restore();
  const f1=ridgeLine(43,1290,26); ridge(f1,'#2c6e5d'); const r=mulberry(5); for(let i=0;i<34;i++){ const x=r()*W; pine(x,yOn(f1,x)+12,60+r()*50,'#1f5b4a',0); }
  // birds
  for(let i=0;i<4;i++){ const x=((t*60+i*90)%1300)-100, y=560+i*26+Math.sin(t*3+i)*10, fl=Math.sin(t*10+i)*8; line([[x-14,y-fl],[x,y],[x+14,y-fl]],INK,4); }
  ctx.restore(); return P; }
function trailer(x,y,s){ ctx.save(); ctx.translate(x,y); ctx.scale(s,s); rr(-170,-150,340,150,26); ctx.fillStyle='#f4f1e6'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=7; ctx.stroke(); ctx.fillStyle='#e0862e'; ctx.fillRect(-166,-78,332,20);
  rr(-120,-128,90,42,8); ctx.fillStyle='#7fd0f0'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=5; ctx.stroke(); rr(40,-128,60,112,6); ctx.fillStyle='#d9d4c2'; ctx.fill(); ctx.stroke(); circ(-70,6,26,'#2b2b36',INK,5); circ(-70,6,10,'#9a9aa8'); line([[170,-20],[230,-6]],INK,8); ctx.restore(); }
function beatWho(tb,t,b){
  const tCut=wt('who','mount')-0.08, tD=wt('who','david'), tSix=wt('who','six');
  if(t<tCut){ // shot A: David in his camp chair, the mountain across the valley
    S(()=>{ morning(t,{zoom:1.04+0.012*tb,oy:-60});
      const fg=ridgeLine(51,1430,18); ridge(fg,'#1b4a3f',INK); trailer(815,1420,0.8);
      davidBack(330,1400,0.7,t,{wind:0.25});
      // coffee steam from a mug on the chair arm
      rr(520,1346,56,64,8); ctx.fillStyle='#e9e4d4'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=6; ctx.stroke(); for(let i=0;i<3;i++){ const k=(t*0.5+i/3)%1; ctx.save(); ctx.globalAlpha=0.7*(1-k); circ(548+Math.sin(t*2+i*2)*10,1330-k*90,8+k*12,'#ffffff'); ctx.restore(); }
    });
    ctx.save(); ctx.globalAlpha=smooth(0.05,0.3,tb); title('MAY 18, 1980',540,330,{size:92,color:'#ffd60a'}); title('8:31 AM  •  A CLEAR SUNDAY',540,424,{size:42,color:'#fff',slant:0}); ctx.restore();
    if(t>tD){ const s=pop(t,tD); ctx.save(); ctx.translate(480,1170); ctx.scale(s,s); tag('DAVID JOHNSTON, 30',0,0,{size:46,bg:'#fff',fg:INK,border:INK}); ctx.restore();
      ctx.save(); ctx.globalAlpha=smooth(0.25,0.5,t-tD); tag('USGS VOLCANOLOGIST',480,1094,{size:32,bg:INK,fg:'#ffd60a',border:'#ffd60a'}); ctx.restore(); }
    return; }
  // shot B: the whole valley, his ridge marked, the distance drawn in
  const k=t-tCut;
  S(()=>{ morning(t,{zoom:1.0+0.01*k,oy:-40});
    const fg=ridgeLine(52,1470,16); ridge(fg,'#1b4a3f',INK); trailer(250,1466,0.34); davidBack(330,1438,0.09,t,{});
    flash(t,tCut,{dur:0.2,peak:0.5}); });
  ctx.save(); ctx.globalAlpha=smooth(0.1,0.35,k); title('MOUNT ST. HELENS',540,330,{size:84,color:'#fff'}); tag('9,677 FT  •  WASHINGTON STATE',540,424,{size:34,bg:INK,fg:'#fff',border:'#fff'}); ctx.restore();
  if(t>tSix-0.15){ const a=smooth(0,0.5,t-tSix+0.15); const p0=[330,1390], p1=[560,560]; ctx.save(); ctx.setLineDash([22,16]); ctx.lineDashOffset=-t*60;
    const pts=bezierPts(p0,[200,900],p1,40).slice(0,Math.max(2,Math.floor(40*a))); line(pts,INK,14,'butt'); line(pts,'#ffd60a',8,'butt'); ctx.restore();
    circ(p0[0],p0[1],16,'#ffd60a',INK,6); const s=pop(t,tSix); if(s){ ctx.save(); ctx.translate(390,1120); ctx.scale(s,s); ctx.rotate(-0.05); title('6 MILES',0,0,{size:96,color:'#ffd60a'}); ctx.restore(); }
    tag('DAVID',330,1330,{size:30,bg:'#fff',fg:INK,border:INK,alpha:a}); }
}

// ---------------------------------------------------------------- cross-section (north is to the right, toward David)
const XS={sumL:[470,640],sumR:[545,640],baseY:1420};
function xsR(s){ return [545+495*s, 640+780*(1-Math.pow(1-s,1.5))]; }
function xsL(s){ return [470-430*s, 640+780*(1-Math.pow(1-s,1.5))]; }
function xsSurf(s,bulge){ const p=xsR(s), u=clamp((s-0.04)/0.56,0,1), bmp=78*bulge*Math.pow(Math.sin(Math.PI*u),1.4); return [p[0]+0.75*bmp, p[1]-0.66*bmp]; }
const XS_S0=0.03, XS_S1=0.62, XS_C=[640,1020];
function xsPlane(u){ const a=xsR(XS_S0), b=xsR(XS_S1), q=(1-u)*(1-u), w=2*(1-u)*u, e=u*u; return [q*a[0]+w*XS_C[0]+e*b[0], q*a[1]+w*XS_C[1]+e*b[1]]; }
function xsBlock(u0,u1,bulge){ const pts=[]; for(let i=0;i<=14;i++){ pts.push(xsSurf(lerp(XS_S0,XS_S1,lerp(u0,u1,i/14)),bulge)); } for(let i=14;i>=0;i--){ pts.push(xsPlane(lerp(u0,u1,i/14))); } return pts; }
function xsRock(pts){ ctx.save(); pathOf(pts); ctx.fillStyle='#6a567c'; ctx.fill(); ctx.clip();
  for(let k=0;k<9;k++){ const y=760+k*84; ctx.beginPath(); ctx.moveTo(0,y+40); ctx.quadraticCurveTo(505,y-70,W,y+40); ctx.strokeStyle=k%2?'#7d6790':'#5a4770'; ctx.lineWidth=k%2?10:22; ctx.stroke(); } ctx.restore(); }
function magma(t,heat=0){ const hot=0.5+0.5*Math.sin(t*6);
  poly([[585,1600],[640,1600],[628,1300],[640,1190],[600,1085],[572,1190],[596,1300]],'#ff6a1f',INK,6); line([[612,1600],[610,1300],[606,1150]],'#ffd35a',10);
  glow(612,1000,260+40*hot+200*heat,'rgba(255,140,40,0.55)');
  ctx.save(); ctx.translate(612,1000); ctx.rotate(-0.42); ell(0,0,74,116,0,'#ff5a1f',INK,7); ell(-6,6,54,92,0,'#ff9a2a'); ell(-12,14,32,62,0,lerp(0,1,heat)>0.5?'#ffffff':'#ffe27a');
  for(let i=0;i<5;i++){ const k=(t*0.5+i*0.2)%1; circ(-30+i*14+Math.sin(t*3+i)*6, 80-k*150, 7+3*Math.sin(i), 'rgba(255,240,170,0.9)'); } ctx.restore(); }
function xsec(t,{bulge=0,slide=-1,heat=0,ghost=false}={}){
  fillAll(vgrad(0,1500,[[0,'#2466e2'],[0.6,'#69b7f7'],[1,'#d5f0ff']])); cumulus(190,720,1.0,3); cumulus(930,600,0.8,9);
  ridge(ridgeLine(61,1390,14),'#6f9fd8');
  const body=[[-80,XS.baseY]]; for(let i=20;i>=0;i--) body.push(xsL(i/20)); body.push(XS.sumL,XS.sumR,xsR(XS_S0));
  for(let i=1;i<=20;i++) body.push(xsPlane(i/20)); for(let i=0;i<=10;i++) body.push(xsSurf(lerp(XS_S1,1,i/10),bulge)); body.push([W+80,XS.baseY],[W+80,H],[-80,H]);
  pathOf(body); ctx.strokeStyle=INK; ctx.lineWidth=14; ctx.lineJoin='round'; ctx.stroke(); xsRock(body);
  ctx.save(); pathOf(body); ctx.clip(); magma(t,heat); ctx.fillStyle='#3d6b4f'; ctx.fillRect(-80,XS.baseY+6,W+160,H); ctx.fillStyle='#2f5741'; ctx.fillRect(-80,XS.baseY+70,W+160,H); ctx.restore();
  // snow cap on the intact surface
  const cap=[]; for(let i=11;i>=0;i--) cap.push(xsL(i/20*0.9)); cap.push(XS.sumL,XS.sumR,xsR(XS_S0)); line(cap,'#ffffff',22); line(cap.map(p=>[p[0],p[1]+14]),'#c3d4f5',8);
  // the north-face block (in place, or sliding away in three pieces)
  for(let pi=0;pi<3;pi++){ const u0=pi/3,u1=(pi+1)/3, k=slide<0?0:clamp((slide-(2-pi)*0.16)/1.5,0,1), d=k*k*(3-2*k)*620, pts=xsBlock(u0,u1,bulge); if(k>=1) continue;
    ctx.save(); ctx.beginPath(); ctx.rect(-100,0,W+200,XS.baseY+8); ctx.clip(); const c=pts[7]; ctx.translate(d*0.78,d*0.63); ctx.translate(c[0],c[1]); ctx.rotate(k*0.35*(pi-0.5)); ctx.translate(-c[0],-c[1]); ctx.globalAlpha=1-smooth(0.75,1,k);
    pathOf(pts); ctx.strokeStyle=INK; ctx.lineWidth=12; ctx.lineJoin='round'; ctx.stroke(); xsRock(pts);
    const top=pts.slice(0,15); line(top,'#ffffff',20); ctx.restore();
    if(k>0.05){ const r=mulberry(pi*7+3), dust=[]; for(let j=0;j<7;j++){ dust.push([c[0]+d*0.78+(r()-0.5)*190, Math.min(XS.baseY-20,c[1]+d*0.63+(r()-0.3)*120), (30+r()*56)*smooth(0.05,0.5,k)*(1+0.1*Math.sin(t*7+j))]); }
      blobs(dust,{dark:'#8d7a86',mid:'#b9a8ac',lite:'#e6dcd8',ow:5}); } }
  if(ghost){ ctx.save(); ctx.setLineDash([16,14]); const gp=[]; for(let i=0;i<=20;i++) gp.push(xsR(i/20*0.7)); line(gp,'rgba(255,255,255,0.95)',6,'butt'); ctx.restore(); }
  const r=mulberry(6); for(let i=0;i<9;i++){ const x=30+r()*210+(i>4?800:0); if(x<W-10) pine(x,XS.baseY+10,50+r()*34,'#1f5b4a'); }
}
function xsCam(z=1){ ctx.translate(560,640); ctx.scale(1.17*z,1.17*z); ctx.translate(-560,-640); }
function XP(x,y){ return [560+(x-560)*1.17, 640+(y-640)*1.17]; }
function fgForest(seed,y,t){ const g=ridgeLine(seed,y,18); ridge(g,'#173f36',INK); const r=mulberry(seed); for(let i=0;i<18;i++){ const x=r()*W; pine(x,yOn(g,x)+30,130+r()*90,'#12332c',0,'#0d2621'); } }
function compass(alpha=1){ ctx.save(); ctx.globalAlpha=ctx.globalAlpha*alpha; tag('SOUTH',190,1500,{size:28,bg:'rgba(27,23,48,0.85)',border:null}); tag('NORTH  →  DAVID',690,1500,{size:28,bg:'#fff',fg:INK,border:INK}); ctx.restore(); }

function beatBulge(tb,t,b){
  const tM=wt('bulge','magma'), tF=wt('bulge','five'), bl=smooth(0.2,3.2,tb)*(0.9+0.1*Math.sin(t*9));
  S(()=>{ ctx.save(); xsCam(1.0+0.012*tb); xsec(t,{bulge:bl,ghost:true});
    for(let i=0;i<3;i++){ const p=xsSurf(0.16+i*0.14,bl), k=(t*1.2+i*0.3)%1, a=smooth(0.3,0.8,tb); ctx.save(); ctx.globalAlpha=a*(1-k*0.7); ctx.translate(p[0]+18+k*34,p[1]-16-k*30); ctx.rotate(-0.72);
      poly([[0,-12],[46,-12],[46,-30],[92,0],[46,30],[46,12],[0,12]],'#ffd60a',INK,6); ctx.restore(); } ctx.restore(); fgForest(5,1700,t); });
  const a0=smooth(0,0.25,tb); compass(a0);
  if(t>tM-0.05){ const s=pop(t,tM-0.05); ctx.save(); ctx.translate(290,1090); ctx.scale(s,s); tag('MAGMA',0,0,{size:44,bg:'#ff5a1f',fg:'#fff',border:INK}); ctx.restore(); S(()=>line([[386,1084],[540,1064]],INK,8)); }
  if(t>tF-0.05){ const s=pop(t,tF-0.05); ctx.save(); ctx.translate(700,600); ctx.scale(s,s); ctx.rotate(-0.06); title('+5 FT',0,0,{size:120,color:'#ffd60a'}); title('EVERY DAY',0,104,{size:60,color:'#fff'}); ctx.restore(); }
}

function seismo(t,t0,x0,x1,y){ const k=t-t0; if(k<0) return; rr(x0-24,y-78,x1-x0+48,156,22); ctx.fillStyle='#fffdf2'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=6; ctx.stroke();
  const pts=[], n=120, head=clamp(k/1.1,0,1); for(let i=0;i<=n*head;i++){ const u=i/n, tt=u*1.1, amp=58*Math.exp(-Math.pow((tt-0.35)/0.22,2))+4; pts.push([lerp(x0,x1,u), y+amp*Math.sin(tt*70+Math.sin(tt*23)*2)]); }
  if(pts.length>1) line(pts,'#e5261e',5); }
function beatSlide(tb,t,b){
  const tQ=wt('slide','earthquake'), tL=wt('slide','loose')-0.05, tBig=wt('slide','biggest'), tC=wt('slide','eight');
  const q=smooth(tQ,tQ+0.15,t)*(1-smooth(tL+1.2,tL+2.0,t)), sh=shakeXY(t,22*q+4*smooth(tL,tL+0.3,t)), sl=t<tL?-1:(t-tL);
  S(()=>{ ctx.save(); ctx.translate(sh[0],sh[1]); xsCam(1.02); xsec(t,{bulge:0.95,slide:sl,heat:sl>0?smooth(0.6,2.0,sl):0}); ctx.restore(); fgForest(5,1700,t);
    if(q>0.2&&t<tL) speedLines(620,900,t,{n:30,inner:620,color:'#fff',alpha:0.35,seed:8}); if(sl>0) flash(t,tL,{dur:0.25,peak:0.6}); });
  compass(1-smooth(tQ-0.2,tQ,t));
  if(t>tC-0.05&&t<tBig){ const s=pop(t,tC-0.05); ctx.save(); ctx.translate(400,560); ctx.scale(s,s); ctx.rotate(-0.05); title('8:32 AM',0,0,{size:92,color:'#ffd60a'}); ctx.restore(); }
  if(t>tQ&&t<tBig){ ctx.save(); ctx.translate(sh[0]*0.4,sh[1]*0.4); seismo(t,tQ,170,640,1320); const s=pop(t,tQ+0.1); if(s){ ctx.translate(590,1212); ctx.scale(s,s); ctx.rotate(0.05); pill('MAGNITUDE 5.1',0,0,{size:40,weight:900,bg:'#e5261e',fg:'#fff',border:INK,align:'center'}); } ctx.restore(); }
  if(t>tBig-0.05){ const s=pop(t,tBig-0.05,0.3); ctx.save(); ctx.translate(540,1300); ctx.scale(s,s); ctx.rotate(-0.04); title('BIGGEST LANDSLIDE',-55,0,{size:54,color:'#fff'}); title('EVER RECORDED',-55,74,{size:64,color:'#ffd60a'}); ctx.restore(); }
}

// ---------------------------------------------------------------- beat: blast (soda cut-in, then the lateral blast seen from the side)
function soda(cx,cy,t,k){ // k seconds since the inset appeared; the cap blows at k=0.75
  const s=pop(t,t-k,0.25); ctx.save(); ctx.translate(cx,cy); ctx.scale(s,s); circ(0,0,176,'#fff',INK,10); ctx.save(); ctx.beginPath(); ctx.arc(0,0,170,0,TAU); ctx.clip();
  ctx.fillStyle='#ffe07a'; ctx.fillRect(-200,-200,400,400); speedLines(0,0,t,{n:22,inner:120,outer:300,color:'#fff',alpha:0.6,seed:4,wid:0.05});
  const openK=k-0.75, jit=openK<0?Math.sin(t*70)*7*smooth(0,0.5,k):0; ctx.save(); ctx.translate(-36+jit,26-jit*0.4); ctx.rotate(0.95);
  rr(-46,-70,92,190,26); ctx.fillStyle='#5a2a18'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=7; ctx.stroke(); ctx.fillStyle='#e5261e'; ctx.fillRect(-43,-10,86,64); ctx.fillStyle='#fff'; ctx.fillRect(-43,10,86,10);
  poly([[-42,-66],[-20,-120],[-20,-150],[20,-150],[20,-120],[42,-66]],'#5a2a18',INK,7);
  if(openK<0){ rr(-26,-170,52,24,6); ctx.fillStyle='#d9d9e4'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=6; ctx.stroke(); }
  else { const f=[], r=mulberry(9); for(let i=0;i<12;i++){ const u=((r()+openK*1.6)%1); f.push([(r()-0.5)*60*u*2, -160-u*250, 14+u*38]); } blobs(f,{dark:'#e9c9a0',mid:'#fff6e0',lite:'#ffffff',ow:5});
    ctx.save(); ctx.translate(60+openK*260,-190-openK*200); ctx.rotate(openK*9); rr(-26,-12,52,24,6); ctx.fillStyle='#d9d9e4'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=6; ctx.stroke(); ctx.restore(); }
  ctx.restore(); ctx.restore(); ctx.restore(); }
const SIDE_G=ridgeLine(71,1290,24);
function sideBlast(t,k){ // k seconds since the cut to the exterior; front races right toward the ridge David is on
  const xF=lerp(360,600,Math.pow(clamp(k/3.3,0,1),0.85));
  fillAll(vgrad(0,1300,[[0,'#2466e2'],[0.55,'#69b7f7'],[1,'#e2f5ff']])); cumulus(820,560,1.0,5); glow(250,760,700,'rgba(255,160,70,0.35)');
  ridge(ridgeLine(72,1215,18),'#7fa6dc');
  // the mountain from the west: summit gone on the north (right) side
  const m=[[-60,1290],[40,1120],[130,930],[200,790],[246,716],[282,706],[300,760],[322,850],[362,930],[430,1010],[520,1090],[640,1180],[760,1290]];
  poly(m,'#ffffff',INK,8); ctx.save(); pathOf(m); ctx.clip(); poly([[282,700],[300,760],[322,850],[362,930],[430,1010],[520,1090],[640,1180],[760,1290],[300,1290],[262,900]],'#5b4775'); poly([[-60,1300],[-60,1130],[60,1160],[130,1100],[230,1170],[300,1130],[330,1300]],'#5a6a9e'); ctx.restore();
  // vertical column climbing behind
  const col=[], rc=mulberry(4); for(let i=0;i<22;i++){ const u=i/21, hgt=Math.min(1,k/2.6+0.25); if(u>hgt) continue; col.push([300+Math.sin(u*9+t)*26+(rc()-0.5)*90*(0.4+u), 760-u*560, (58+rc()*60)*(0.6+u*0.9)*(1+0.05*Math.sin(t*4+i))]); }
  blobs(col,{dark:'#3b2c4a',mid:'#6f5a7c',lite:'#b79aa6'});
  ridge(SIDE_G,'#2c6e5d',INK);
  // David's ridge on the right, with the trailer
  const dr=[[590,1330],[650,1262],[730,1238],[820,1250],[900,1290],[W+60,1300],[W+60,1400],[590,1400]]; poly(dr,'#3f8a6c',INK,6); trailer(732,1240,0.2);
  // forest: standing ahead of the front, flattened and grey behind it
  const r=mulberry(12); for(let i=0;i<64;i++){ const x=380+r()*640, row=Math.floor(r()*3), y=(x>610&&row===0?yOn(dr,x):yOn(SIDE_G,x))+18+row*52, h=58+r()*40, f=smooth(0,90,xF-x+row*20); pine(x,y,h,f>0.5?'#6d6672':'#1f5b4a',f*1.45,f>0.5?'#575160':'#17463b'); }
  // the blast cloud: ground-hugging, fastest at the front
  const B=[], rb=mulberry(8); for(let i=0;i<54;i++){ const u=Math.pow(rb(),0.8), x=330+u*(xF-330), big=0.6+rb()*0.7, ph=rb()*TAU, hgt=rb(); const rad=(64+90*big)*smooth(0,1,(xF-330)/220)*(0.75+0.5*u)*(1+0.06*Math.sin(t*6+ph));
    B.push([x, yOn(SIDE_G,x)-20-hgt*hgt*330*(0.5+0.5*u), rad]); } B.sort((a,b)=>a[1]-b[1]);
  blobs(B,{dark:'#3b2c4a',mid:'#73587a',lite:'#c9a8a2'});
  const core=[]; for(let i=0;i<10;i++){ core.push([330+rb()*120, 900+rb()*200, 30+rb()*40]); } blobs(core,{dark:'#ff5a1f',mid:'#ff9a2a',lite:'#ffe88a',outline:'#7a1f2c',ow:4});
  ejecta(320,800,t,41,12,520);
  streaks(t,{n:18,y0:700,y1:1250,alpha:0.55,len:360,seed:6});
  return xF; }
function beatBlast(tb,t,b){
  const tS=wt('blast','shaken')-0.25, tX=wt('blast','explodes')-0.06, t3=wt('blast','three')-0.05, tU=wt('blast','uncorks');
  if(t<tX){ const heat=smooth(tU,tX,t), sh=shakeXY(t,5+16*heat);
    S(()=>{ ctx.save(); ctx.translate(sh[0],sh[1]); xsCam(1.02); xsec(t,{bulge:0.95,slide:9,heat});
      // gas bursting out of the opened flank
      const j=[], r=mulberry(14); for(let i=0;i<16;i++){ const u=((r()+t*0.9)%1); j.push([660+u*330*heat+(r()-0.5)*40, 990-u*230*heat+(r()-0.5)*50, (20+u*70)*heat]); } blobs(j,{dark:'#8d7a86',mid:'#d9c9c4',lite:'#ffffff',ow:5});
      ctx.restore(); fgForest(5,1700,t); if(t>tS) soda(300,1290,t,t-tS); });
    if(t>tU-0.05){ const s=pop(t,tU-0.05); ctx.save(); ctx.translate(540,560); ctx.scale(s,s); ctx.rotate(-0.04); title('THE LID IS GONE',0,0,{size:84,color:'#ffd60a'}); ctx.restore(); }
    if(t>tS+0.3) tag('SHAKEN SODA',300,1500,{size:30,bg:'#fff',fg:INK,border:INK,alpha:smooth(0.3,0.5,t-tS)});
    return; }
  const k=t-tX, sh=shakeXY(t,12);
  S(()=>{ ctx.save(); ctx.translate(sh[0],sh[1]); ctx.translate(540,700); ctx.scale(1.15,1.15); ctx.translate(-540,-700); sideBlast(t,k); ctx.restore(); fgForest(7,1720,t);
    if(k<0.07){ ctx.save(); ctx.globalCompositeOperation='difference'; ctx.fillStyle='#fff'; ctx.fillRect(0,0,W,H); ctx.restore(); } else flash(t,tX+0.07,{dur:0.3,peak:0.8}); });
  ctx.save(); ctx.globalAlpha=smooth(0.1,0.3,k); title('SIDEWAYS',540,548,{size:96,color:'#fff'}); ctx.restore();
  if(t>t3){ const s=pop(t,t3,0.3); ctx.save(); ctx.translate(540+sh[0],700+sh[1]); ctx.scale(s,s); ctx.rotate(-0.05); title('300 MPH',0,0,{size:138,color:'#ffd60a',sw:22}); ctx.restore(); }
  ctx.save(); ctx.globalAlpha=smooth(0.5,0.8,k); tag('DAVID',700,1230,{size:30,bg:'#fff',fg:INK,border:INK}); S(()=>line([[728,1256],[752,1296]],INK,7)); ctx.restore();
}

// ---------------------------------------------------------------- beat: radio
function blastWall(t,g){ fillAll(vgrad(0,H,[[0,'#2a1846'],[0.5,'#a8384f'],[1,'#ff9a4a']]));
  const B=blastBlobs(540,820,lerp(700,1050,g),t,19,{n:40,a0:-Math.PI,a1:0,down:0.3}); blobs(B,{dark:'#33263f',mid:'#6a4f6e',lite:'#b98686'}); glow(540,900,900,'rgba(255,130,50,0.45)');
  const c=blastBlobs(540,1000,lerp(300,460,g),t*1.3,29,{n:12,down:0.2}); blobs(c,{dark:'#ff5a1f',mid:'#ff9a2a',lite:'#ffe88a',outline:'#7a1f2c',ow:5}); }
function hand(x,y,s,rot,grip){ ctx.save(); ctx.translate(x,y); ctx.rotate(rot); ctx.scale(s,s);
  rr(-120,-40,260,230,70); ctx.fillStyle=SKIN; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=9; ctx.stroke();
  for(let i=0;i<4;i++){ const fx=-104+i*62, len=lerp(210,120,grip)-Math.abs(i-1.5)*18; rr(fx,-len,54,len+30,27); ctx.fillStyle=SKIN; ctx.fill(); ctx.stroke(); line([[fx+10,-len*0.45],[fx+44,-len*0.45]],SKIN_SH,6); }
  ctx.save(); ctx.translate(-120,60); ctx.rotate(-0.7+0.5*grip); rr(-40,-150,62,180,31); ctx.fillStyle=SKIN; ctx.fill(); ctx.stroke(); ctx.restore();
  poly([[-130,190],[150,190],[210,520],[-190,520]],'#d8502a',INK,9); ctx.fillStyle='#a53a22'; ctx.fillRect(-140,186,300,36); ctx.strokeRect(-140,186,300,36); ctx.restore(); }
function mic(x,y,s,rot){ ctx.save(); ctx.translate(x,y); ctx.rotate(rot); ctx.scale(s,s); rr(-90,-150,180,300,40); ctx.fillStyle='#2b2b36'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=9; ctx.stroke();
  rr(-62,-122,124,110,18); ctx.fillStyle='#454556'; ctx.fill(); for(let k=0;k<5;k++) line([[-46,-104+k*20],[46,-104+k*20]],'#1d1d27',7); rr(-98,10,22,90,8); ctx.fillStyle='#e5261e'; ctx.fill(); ctx.stroke();
  const cord=[]; for(let i=0;i<=60;i++){ cord.push([Math.sin(i*0.9)*22, 150+i*14]); } line(cord,INK,16); line(cord,'#454556',7); ctx.restore(); }
function shoutBubble(cx,cy,rx,ry,t,seed){ const r=mulberry(seed), pts=[], n=26; for(let i=0;i<n*2;i++){ const a=i/(n*2)*TAU, sp=(i%2)?1.0:0.74+r()*0.08, wob=1+0.03*Math.sin(t*30+i); pts.push([cx+Math.cos(a)*rx*sp*wob, cy+Math.sin(a)*ry*sp*wob]); }
  poly(pts.map(p=>[p[0]+10,p[1]+12]),INK); poly(pts,'#ffffff',INK,9); }
function beatRadio(tb,t,b){
  const tV1=wt('radio','vancouver',0)-0.06, tV2=wt('radio','vancouver',1)-0.04, tT=wt('radio','this')-0.04, tIt=wt('radio','it'), tEnd=tIt+0.42, tG=wt('radio','grabs');
  if(t>=tEnd){ // whiteout, then the line goes dead
    const k=t-tEnd; S(()=>{ fillAll('#07060c'); const pts=[]; for(let i=0;i<=140;i++){ const x=130+i*820/140, live=Math.max(0,1-k/0.5)*smooth(0,1,1-Math.abs(i/140-0.5)*2+0.3); pts.push([x, 960+Math.sin(i*1.7+t*60)*70*live*Math.sin(i*0.37+t*31)+(Math.sin(i*12.9+t*90)*3)]); }
      line(pts,'#3ddc84',6); glow(540,960,500,'rgba(61,220,132,0.12)'); const r=mulberry(Math.floor(t*30)); ctx.fillStyle='rgba(255,255,255,0.10)'; for(let i=0;i<260;i++){ ctx.fillRect(r()*W,r()*H,3,3); }
      flash(t,tEnd,{dur:0.5,peak:1}); });
    ctx.save(); ctx.globalAlpha=smooth(0.35,0.7,k); title('. . .',540,700,{size:120,color:'#fff',slant:0}); tag('8:32 AM  •  NO REPLY',540,1180,{size:40,bg:'#07060c',fg:'#3ddc84',border:'#3ddc84'}); ctx.restore(); return; }
  if(t<tV1){ // the grab: hand snatches the handset
    const k=smooth(tG-0.1,tG+0.22,t), sh=shakeXY(t,9);
    S(()=>{ ctx.save(); ctx.translate(sh[0],sh[1]); blastWall(t,0.2+0.2*tb); speedLines(560,1130,t,{n:40,inner:460,color:'#fff',alpha:0.5,seed:3});
      // radio set on the truck's dash
      rr(170,1250,740,420,36); ctx.fillStyle='#3a3a48'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=10; ctx.stroke(); rr(220,1300,300,200,20); ctx.fillStyle='#22222c'; ctx.fill(); for(let i=0;i<7;i++) line([[244,1326+i*26],[496,1326+i*26]],'#55556a',8);
      circ(640,1380,54,'#d9d9e4',INK,8); line([[640,1380],[640+Math.cos(t*3)*40,1380+Math.sin(t*3)*40]],INK,8); circ(790,1380,34,(Math.floor(t*8)%2)?'#ff3b3b':'#8a2424',INK,7);
      const mx=lerp(560,520,k), my=lerp(1120,900,k); mic(mx,my,0.95,-0.25+0.2*k); hand(lerp(1250,600,easeOutCubic(k)),lerp(300,910,easeOutCubic(k)),1.05,-0.55+0.25*k,k);
      ctx.restore(); if(k>0&&k<1) streaks(t,{n:14,y0:500,y1:1300,alpha:0.6,len:500,dir:-1,seed:2}); flash(t,b.start,{dur:0.2,peak:0.5}); });
    return; }
  // the call: back view again, radio at his mouth, the cloud filling the sky
  const g=clamp((t-tV1)/(tEnd-tV1),0,1), sh=shakeXY(t,10+16*g), z=1.25+0.35*g;
  S(()=>{ ctx.save(); ctx.translate(sh[0],sh[1]); blastWall(t,0.4+0.6*g); speedLines(540,900,t,{n:50,inner:520,color:'#ffe9b0',alpha:0.35+0.3*g,seed:6});
    ctx.translate(540,1500); ctx.scale(z,z); ctx.translate(-540,-1500); davidBack(470,1320,0.9,t,{radio:1,wind:1.6}); ctx.restore();
    const v=ctx.createRadialGradient(540,900,400,540,960,1200); v.addColorStop(0,'rgba(20,8,40,0)'); v.addColorStop(1,'rgba(20,8,40,0.6)'); ctx.fillStyle=v; ctx.fillRect(0,0,W,H);
    flash(t,tV1,{dur:0.2,peak:0.7}); flash(t,tT,{dur:0.25,peak:0.8}); if(t>tEnd-0.3){ ctx.fillStyle=`rgba(255,255,255,${smooth(tEnd-0.3,tEnd,t)})`; ctx.fillRect(0,0,W,H); } });
  const out=1-smooth(tEnd-0.22,tEnd-0.05,t); ctx.save(); ctx.globalAlpha=out; ctx.translate(sh[0]*0.5,sh[1]*0.5);
  if(t<tT){ const s=lerp(1.07,1,easeOutBack((t-tV1)/0.2)); ctx.save(); ctx.translate(540,480); ctx.scale(s,s); shoutBubble(0,0,385,200,t,3); title('VANCOUVER!',0,t>tV2?-48:0,{size:86,color:INK,sw:1,slant:-0.1}); if(t>tV2){ const s2=pop(t,tV2,0.2); title('VANCOUVER!',0,56,{size:86,color:'#e5261e',sw:1,slant:-0.1,scale:s2}); } ctx.restore(); }
  else { const s=lerp(1.07,1,easeOutBack((t-tT)/0.2))*(1+0.012*Math.sin(t*40)); ctx.save(); ctx.translate(540,510); ctx.scale(s,s); ctx.rotate(-0.04); shoutBubble(0,0,385,215,t,5); title('THIS IS IT!',0,4,{size:116,color:'#e5261e',sw:1,slant:-0.12}); ctx.restore(); }
  ctx.restore();
}

// ---------------------------------------------------------------- beat: harry
function cat(x,y,s,col,sh,t,{tail=true,flip=1}={}){ ctx.save(); ctx.translate(x,y); ctx.scale(s*flip,s);
  if(tail){ ctx.beginPath(); ctx.moveTo(70,10); ctx.quadraticCurveTo(150,-10+Math.sin(t*3)*20,130,-90+Math.sin(t*3)*14); ctx.strokeStyle=INK; ctx.lineWidth=30; ctx.lineCap='round'; ctx.stroke(); ctx.strokeStyle=col; ctx.lineWidth=18; ctx.stroke(); }
  ell(0,20,95,70,0,col,INK,7); ell(20,40,60,40,0,sh); poly([[-96,-92],[-84,-150],[-48,-112]],col,INK,7); poly([[-28,-112],[6,-150],[18,-92]],col,INK,7); circ(-40,-70,62,col,INK,7);
  line([[-70,-74],[-56,-66],[-44,-74]],INK,5); line([[-32,-74],[-18,-66],[-6,-74]],INK,5); poly([[-44,-56],[-32,-56],[-38,-48]],'#f08a9a'); line([[-38,-48],[-38,-40]],INK,3); ctx.restore(); }
function lodge(x,y,s,t){ ctx.save(); ctx.translate(x,y); ctx.scale(s,s);
  rr(-300,-230,600,240,6); ctx.fillStyle='#9a5f3a'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=8; ctx.stroke(); for(let k=1;k<6;k++) line([[-296,-230+k*40],[296,-230+k*40]],'#74432a',6);
  poly([[-350,-220],[0,-440],[350,-220]],'#b8322c',INK,8); poly([[0,-440],[350,-220],[120,-220]],'#8e2420'); rr(150,-470,56,120,4); ctx.fillStyle='#7a6a66'; ctx.fill(); ctx.stroke();
  for(let i=0;i<4;i++){ const k=(t*0.3+i/4)%1; ctx.save(); ctx.globalAlpha=0.8*(1-k); circ(178+Math.sin(t+i*2)*14+k*40,-480-k*170,16+k*30,'#fff7ea'); ctx.restore(); }
  for(const wx of [-220,90]){ rr(wx,-170,130,100,6); ctx.fillStyle='#ffd76a'; ctx.fill(); ctx.stroke(); line([[wx+65,-170],[wx+65,-70]],INK,5); line([[wx,-120],[wx+130,-120]],INK,5); }
  rr(-50,-150,90,160,6); ctx.fillStyle='#5a3422'; ctx.fill(); ctx.stroke(); rr(-330,8,660,34,6); ctx.fillStyle='#74432a'; ctx.fill(); ctx.stroke();
  rr(-180,-292,360,60,10); ctx.fillStyle='#fff3d0'; ctx.fill(); ctx.stroke(); text('SPIRIT LAKE LODGE',0,-260,{size:30,weight:900,color:INK,stroke:false,shadow:false}); ctx.restore(); }
function harryBust(cx,cy,s,t){ ctx.save(); ctx.translate(cx,cy); ctx.scale(s,s); const bob=Math.sin(t*2.2)*4; ctx.translate(0,bob);
  const shirt=()=>{ ctx.beginPath(); ctx.moveTo(-360,640); ctx.lineTo(-320,200); ctx.quadraticCurveTo(-300,90,-160,56); ctx.lineTo(160,56); ctx.quadraticCurveTo(300,90,320,200); ctx.lineTo(360,640); ctx.closePath(); };
  shirt(); ctx.fillStyle='#c0392f'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=8; ctx.stroke(); ctx.save(); shirt(); ctx.clip(); for(let k=-5;k<6;k++){ ctx.fillStyle='rgba(60,10,20,0.35)'; ctx.fillRect(k*74-10,0,22,700); ctx.fillRect(-400,120+ (k+5)*74,800,22); } ctx.restore();
  poly([[-70,40],[0,150],[70,40],[110,70],[0,220],[-110,70]],'#a12c26',INK,7); ctx.fillStyle=SKIN_SH; ctx.fillRect(-50,-40,100,110); poly([[-50,62],[0,150],[50,62]],SKIN);
  ell(-150,-150,26,44,0,SKIN,INK,6); ell(150,-150,26,44,0,SKIN,INK,6);
  ctx.beginPath(); ctx.moveTo(-138,-250); ctx.quadraticCurveTo(-150,-360,0,-366); ctx.quadraticCurveTo(150,-360,138,-250); ctx.quadraticCurveTo(150,-90,96,-20); ctx.quadraticCurveTo(0,60,-96,-20); ctx.quadraticCurveTo(-150,-90,-138,-250); ctx.closePath(); ctx.fillStyle=SKIN; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=8; ctx.stroke();
  ctx.save(); ctx.clip(); poly([[40,-380],[200,-380],[200,80],[60,80],[96,-120]],'rgba(217,154,122,0.6)'); ctx.restore();
  // white hair: side tufts and a thin sweep on top
  blobs([[-140,-262,44],[-158,-212,36],[140,-262,44],[158,-212,36]],{dark:'#c9cfe0',mid:'#f4f5fa',lite:null,ow:6}); poly([[-120,-320],[-60,-372],[40,-384],[124,-330],[70,-346],[-10,-340],[-70,-322]],'#f4f5fa',INK,6);
  // bushy brows, happy closed eyes, nose, big grin
  blobs([[-88,-212,20],[-60,-220,22],[-32,-212,18],[88,-212,20],[60,-220,22],[32,-212,18]],{dark:'#c9cfe0',mid:'#ffffff',lite:null,ow:5});
  for(const sx of [-1,1]){ ctx.beginPath(); ctx.moveTo(sx*98,-160); ctx.quadraticCurveTo(sx*62,-196,sx*28,-160); ctx.strokeStyle=INK; ctx.lineWidth=9; ctx.lineCap='round'; ctx.stroke(); line([[sx*110,-172],[sx*128,-182]],INK,4); line([[sx*112,-158],[sx*132,-158]],INK,4); ell(sx*84,-96,30,18,0,'rgba(240,120,110,0.45)'); }
  ctx.beginPath(); ctx.moveTo(-14,-150); ctx.quadraticCurveTo(-34,-90,-6,-84); ctx.quadraticCurveTo(14,-82,22,-96); ctx.strokeStyle=INK; ctx.lineWidth=6; ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-70,-52); ctx.quadraticCurveTo(0,-34,70,-52); ctx.quadraticCurveTo(40,22,0,22); ctx.quadraticCurveTo(-40,22,-70,-52); ctx.closePath(); ctx.fillStyle='#6a1f28'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=7; ctx.stroke(); poly([[-56,-46],[56,-46],[46,-24],[-46,-24]],'#ffffff');
  line([[-104,-70],[-88,-30]],SKIN_SH,6); line([[104,-70],[88,-30]],SKIN_SH,6);
  ctx.restore(); }
function beatHarry(tb,t,b){
  const tN=wt('harry','harry'), tR=wt('harry','refused')-0.05;
  S(()=>{ ctx.save(); const z=1.03+0.012*tb; ctx.translate(540,900); ctx.scale(z,z); ctx.translate(-540,-900);
    fillAll(vgrad(0,1100,[[0,'#ff9a5a'],[0.5,'#ffc27a'],[1,'#fff0c4']])); glow(210,520,560,'rgba(255,250,210,0.7)'); circ(210,520,64,'#fff8dc');
    cumulus(820,470,1.2,4,['#f2a38a','#ffd9c0','#fff3e6']); cone(700,960,900,520,{pal:PAL_DUSK}); ridge(ridgeLine(81,960,18),'#7a6a9a');
    ctx.fillStyle='#f0a868'; ctx.fillRect(-100,985,W+200,120); for(let i=0;i<8;i++){ const x=((i*191+t*24)%1300)-80; line([[x,1000+(i*29)%80],[x+90,1000+(i*29)%80]],'rgba(255,255,255,0.7)',4); }
    const g1=ridgeLine(82,1090,14); ridge(g1,'#4f7a52'); const r=mulberry(3); for(let i=0;i<12;i++){ const x=r()*W; pine(x,yOn(g1,x)+10,90+r()*70,'#2f5c44',0,'#234636'); }
    lodge(690,1010,0.72,t);
    ridge(ridgeLine(83,1420,10),'#3d6a45',INK);
    cat(760,1500,0.9,'#8d8f9c','#6f717e',t,{flip:-1}); cat(905,1560,0.75,'#2b2b36','#1d1d27',t+1);
    harryBust(360,1420,0.92,t); cat(250,1640,1.0,'#f09a3e','#d27a26',t+2,{tail:false});
    ctx.restore();
    // flashback grade: warm wash + soft white frame
    ctx.fillStyle='rgba(255,190,110,0.14)'; ctx.fillRect(0,0,W,H); const v=ctx.createRadialGradient(540,960,620,540,960,1180); v.addColorStop(0,'rgba(255,255,255,0)'); v.addColorStop(1,'rgba(255,248,230,0.9)'); ctx.fillStyle=v; ctx.fillRect(0,0,W,H);
    flash(t,b.start,{dur:0.3,peak:0.9}); });
  if(t>tN-0.05){ const s=pop(t,tN-0.05); ctx.save(); ctx.translate(540,320); ctx.scale(s,s); ctx.rotate(-0.03); tag('HARRY R. TRUMAN, 83',0,0,{size:50,bg:'#fff',fg:INK,border:INK}); ctx.restore(); }
  if(t>tR){ const a=smooth(0,0.25,t-tR); ctx.save(); ctx.globalAlpha=a; title('“IF THE MOUNTAIN GOES,',540,430,{size:56,color:'#fff',slant:-0.08}); title('I’M GOING WITH IT.”',540,506,{size:64,color:'#ffd60a',slant:-0.08}); ctx.restore(); }
}

// ---------------------------------------------------------------- beat: toll
function person(x,y,s,hair,coat){ ctx.save(); ctx.translate(x,y); ctx.scale(s,s); poly([[-110,260],[-96,40],[-40,0],[40,0],[96,40],[110,260]],coat,INK,7); circ(0,-62,66,hair,INK,7); ctx.save(); ctx.beginPath(); ctx.arc(0,-62,62,0,TAU); ctx.clip(); ctx.fillStyle='rgba(0,0,0,0.18)'; ctx.fillRect(10,-140,90,160); ctx.restore(); ctx.restore(); }
function car(x,y,s,col){ ctx.save(); ctx.translate(x,y); ctx.scale(s,s); rr(-150,-90,300,120,24); ctx.fillStyle=col; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=8; ctx.stroke(); rr(-110,-170,220,100,26); ctx.fill(); ctx.stroke(); rr(-88,-152,176,62,12); ctx.fillStyle='#9fd6f2'; ctx.fill(); ctx.stroke();
  rr(-138,-52,60,30,8); ctx.fillStyle='#e5261e'; ctx.fill(); ctx.stroke(); rr(78,-52,60,30,8); ctx.fill(); ctx.stroke(); rr(-130,20,60,36,8); ctx.fillStyle='#22222c'; ctx.fill(); rr(70,20,60,36,8); ctx.fill(); ctx.restore(); }
function beatToll(tb,t,b){
  const tBut=wt('toll','but')-0.08, tClose=wt('toll','close'), tTh=wt('toll','thousands')-0.05, t57=wt('toll','fifty-seven');
  if(t<tBut){ // the grey after
    S(()=>{ fillAll(vgrad(0,H,[[0,'#2b2a3a'],[0.55,'#6a6878'],[1,'#a9a6b0']])); cone(540,1040,940,560,{pal:{snow:'#b9b6c4',snowSh:'#8a8798',rock:'#6c6a7c',rockSh:'#55536a',line:'#9c99aa'},crater:1});
      const st=[]; for(let i=0;i<7;i++){ const k=((t*0.12+i/7)%1); st.push([545+Math.sin(i*3+t*0.6)*30+k*60, 720-k*330, 30+k*80]); } blobs(st,{dark:'#55536a',mid:'#8a8798',lite:'#b9b6c4',ow:5});
      const g=ridgeLine(91,1130,26); ridge(g,'#8d8a98',INK); const r=mulberry(4); for(let i=0;i<70;i++){ const x=r()*W, y=1170+r()*520, l=60+r()*90; line([[x,y],[x+l,y-10+r()*8]],'#55536a',7); } ridge(ridgeLine(92,1640,16),'#6c6a7c');
      const ra=mulberry(2); ctx.fillStyle='rgba(235,235,240,0.75)'; for(let i=0;i<120;i++){ const x=(ra()*W+Math.sin(t+i)*20)%W, y=(ra()*H+t*(60+ra()*70))%H; ctx.fillRect(x,y,4+ra()*4,4+ra()*4); }
      // 57 lanterns
      const rl=mulberry(57); for(let i=0;i<57;i++){ const x=140+rl()*800, y0=1500-rl()*700, d=rl()*0.9, k=t-b.start-d*0.8; if(k<0) continue; const y=y0-k*26, a=smooth(0,0.4,k); ctx.save(); ctx.globalAlpha=a; glow(x,y,46,'rgba(255,190,90,0.8)'); rr(x-9,y-12,18,24,5); ctx.fillStyle='#ffe2a0'; ctx.fill(); ctx.strokeStyle='#b8621f'; ctx.lineWidth=3; ctx.stroke(); ctx.restore(); }
      flash(t,b.start,{dur:0.3,peak:0.8}); });
    const s=pop(t,t57-0.05,0.3); if(s){ ctx.save(); ctx.translate(540,380); ctx.scale(s,s); title('57',0,0,{size:230,color:'#fff',sw:30,slant:0}); ctx.restore(); title('PEOPLE DIED',540,540,{size:66,color:'#fff',alpha:smooth(0.25,0.5,t-t57)}); }
    return; }
  // weeks earlier: the roadblock that kept the crowds out
  const k=t-tBut;
  S(()=>{ ctx.save(); const z=1.03+0.01*k; ctx.translate(540,900); ctx.scale(z,z); ctx.translate(-540,-900);
    fillAll(vgrad(0,1150,[[0,'#1c5fe0'],[0.5,'#47a5f5'],[1,'#dff4ff']])); cumulus(250,560,1.1,6); cumulus(900,680,0.8,2); cone(540,1130,900,540,{pal:PAL_DAY}); ridge(ridgeLine(95,1140,20),'#3f7f8f');
    const g=ridgeLine(96,1230,12); ridge(g,'#2c6e5d'); const r=mulberry(9); for(let i=0;i<22;i++){ const x=r()*W; if(Math.abs(x-540)<170) continue; pine(x,yOn(g,x)+30,120+r()*90,'#1f5b4a'); }
    poly([[470,1200],[610,1200],[900,H],[180,H]],'#4a4a58',INK,6); for(let i=0;i<6;i++){ const u=((i/6+t*0.0)%1), y=lerp(1220,1900,u*u), w=6+u*18; ctx.fillStyle='#ffd60a'; ctx.fillRect(540-w/2,y,w,30+u*60); }
    // barrier
    line([[250,1250],[250,1400]],INK,26); line([[250,1250],[250,1400]],'#d9d9e4',12); line([[830,1250],[830,1400]],INK,26); line([[830,1250],[830,1400]],'#d9d9e4',12);
    ctx.save(); rr(230,1280,620,56,10); ctx.fillStyle='#fff'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=8; ctx.stroke(); ctx.clip(); ctx.fillStyle='#e5261e'; for(let i=0;i<10;i++){ poly([[230+i*80,1340],[270+i*80,1340],[310+i*80,1276],[270+i*80,1276]],'#e5261e'); } ctx.restore();
    car(330,1640,1.0,'#f0b63e'); car(770,1700,1.1,'#5fb0e8');
    const cols=[['#3a2a22','#3d8f6a'],['#f0c659','#7a5ad0'],['#22222c','#e07a3e'],['#a8572c','#3d6fd0'],['#d9d9e4','#c0392f'],['#5a3422','#e8c23e'],['#22222c','#4aa0a8']];
    const n=clamp(Math.floor((t-tTh+0.3)*30),3,40); const rp=mulberry(15); for(let i=0;i<40;i++){ const x=80+rp()*920, y=1500+rp()*360, c=cols[i%7]; if(i<n) person(x,y+Math.sin(t*3+i)*4,0.5+((y-1500)/360)*0.35,c[0],c[1]); }
    ctx.restore(); flash(t,tBut,{dur:0.3,peak:0.8}); });
  ctx.save(); ctx.globalAlpha=smooth(0.1,0.35,k); tag('WEEKS BEFORE',540,310,{size:36,bg:INK,fg:'#fff',border:'#fff'}); ctx.restore();
  if(t>tClose-0.1){ const s=pop(t,tClose-0.1); ctx.save(); ctx.translate(540,1140); ctx.scale(s,s); ctx.rotate(-0.04); rr(-236,-62,472,124,16); ctx.fillStyle='#ffd60a'; ctx.fill(); ctx.strokeStyle=INK; ctx.lineWidth=9; ctx.stroke(); text('ROAD CLOSED',0,-18,{size:54,weight:900,color:INK,stroke:false,shadow:false}); text('VOLCANO HAZARD',0,32,{size:30,weight:900,color:'#e5261e',stroke:false,shadow:false}); ctx.restore(); }
  if(t>tTh){ const s=pop(t,tTh,0.3); ctx.save(); ctx.translate(540,470); ctx.scale(s,s); ctx.rotate(-0.04); title('THOUSANDS',0,0,{size:100,color:'#ffd60a',sw:18}); title('KEPT OUT',0,90,{size:72,color:'#fff'}); ctx.restore(); }
}

// ---------------------------------------------------------------- beat: ask (the crater today, from the ridge that carries his name)
function beatAsk(tb,t,b){
  const tW=wt('ask','would')-0.05;
  S(()=>{ ctx.save(); const z=1.02+0.015*tb; ctx.translate(540,900); ctx.scale(z,z); ctx.translate(-540,-900);
    fillAll(vgrad(0,1200,[[0,'#3a2a7a'],[0.45,'#c0508a'],[0.8,'#ff9a5a'],[1,'#ffe0a0']])); glow(540,1080,700,'rgba(255,230,160,0.6)');
    cumulus(240,520,1.2,7,['#b0609a','#f09a9a','#ffd9c0']); cumulus(880,640,0.9,3,['#b0609a','#f09a9a','#ffd9c0']);
    cone(540,1130,960,580,{pal:PAL_DUSK,crater:1});
    const st=[]; for(let i=0;i<5;i++){ const k=((t*0.15+i/5)%1); st.push([548+Math.sin(i*3+t*0.5)*14+k*40, 800-k*170, 14+k*34]); } ctx.save(); ctx.globalAlpha=0.9; blobs(st,{dark:'#f0c0b0',mid:'#fff3e6',lite:null,outline:null}); ctx.restore();
    ridge(ridgeLine(97,1150,22),'#5a4a8a'); const g=ridgeLine(98,1290,20); ridge(g,'#2f5c44',INK);
    const r=mulberry(8); for(let i=0;i<16;i++){ const x=r()*W; pine(x,yOn(g,x)+14,50+r()*40,'#1f4a3a'); }
    for(let i=0;i<60;i++){ const x=r()*W, y=1330+r()*560, sway=Math.sin(t*3+i)*5; line([[x,y+26],[x+sway,y]],'#2f7a4a',5); circ(x+sway,y,9+r()*5,['#ff6fae','#ffd60a','#ffffff','#b48cff'][i%4],INK,3); }
    ctx.restore(); flash(t,b.start,{dur:0.3,peak:0.8});
    const e=smooth(b.duration-0.2,b.duration,tb); if(e>0){ ctx.fillStyle=`rgba(255,255,255,${e})`; ctx.fillRect(0,0,W,H); } });
  const out=1-smooth(b.duration-0.2,b.duration-0.03,tb); ctx.save(); ctx.globalAlpha=out;
  const s=pop(t,tW,0.3); if(s){ ctx.save(); ctx.translate(540,400); ctx.scale(s,s); ctx.rotate(-0.04); title('WOULD YOU',0,-50,{size:88,color:'#fff'}); title('HAVE LEFT?',0,56,{size:100,color:'#ffd60a',sw:18}); ctx.restore(); }
  ctx.save(); ctx.globalAlpha=out*smooth(0.5,0.8,tb); tag('JOHNSTON RIDGE  •  NAMED FOR DAVID',486,1500,{size:30,bg:'#fff',fg:INK,border:INK}); ctx.restore();
  ctx.restore();
}

const SHOUT=()=>({a:wordTime('radio','vancouver',0)-0.1, b:wordTime('radio','it')+1.4});
window.BEATS = {
  draw: {hook:beatHook, who:beatWho, bulge:beatBulge, slide:beatSlide, blast:beatBlast, radio:beatRadio, harry:beatHarry, toll:beatToll, ask:beatAsk},
  cutFlash: ['who','bulge'],
  vignette: 0,
  caption: { y: 980, yByBeat: {bulge:380, slide:380, blast:380, radio:420, harry:720, ask:980}, skip:(t)=>{ const s=SHOUT(); return t>=s.a && t<s.b; } },
  keywords: ['seconds','warn','world','david','johnston','volcanologist','six','miles','magma','north','five','feet','earthquake','loose','biggest','landslide','uncorks','soda','sideways','three','hundred','radio','harry','truman','refused','lodge','died','close','mountain','saved','thousands','left'],
};
})();
