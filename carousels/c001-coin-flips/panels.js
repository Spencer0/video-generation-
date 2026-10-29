// c001: "You should be able to solve this": HH vs HT waiting times (question post).
// Panels are pure functions of the panel index; helpers in pipeline/overlays/helpers.js.
(function(){
const CX = 540;

// Big stacked Inter 900 headline, fitted to width; returns [{line, y, w}] (y = baseline).
function headline(lines, top, {maxW=846, max=200, lh=1.0, color=PAPER.ink}={}){
  const size = fitSize(lines, maxW, {weight:900, max}); const out = [];
  lines.forEach((l, k)=>{ const y = top + size*0.73 + k*size*lh; const w = ink(l, CX, y, {size, weight:900, baseline:'alphabetic', color}); out.push({line:l, y, w, size}); });
  return out;
}

function p1(){
  const hl = headline(['YOU SHOULD', 'BE ABLE TO', 'SOLVE THIS.'], 290, {max:150, lh:1.02});
  const last = hl[2]; markerUnderline(CX - last.w/2, CX + last.w/2 - 30, last.y + 30, {width:14, slope:-8});
  coin(CX-160, 1010, 140, 'H', {rot:-0.06}); coin(CX+160, 1010, 140, 'H', {rot:0.05});
  problem(()=>{ markerText('flip a fair coin', CX, 1272, {size:74, color:PAPER.ink, rot:-0.035});
                markerText('until you see this.', CX, 1372, {size:74, color:PAPER.ink, rot:-0.035}); });
  markerCircle(CX, 1012, 368, 196, {width:12});
}

function p2(){
  ink('NOW START OVER.', CX, 330, {size:86, weight:900});   // 92 was 869 px wide: cropped on tall phones
  problem(()=> markerText('and flip until you see this.', CX, 440, {size:62, color:PAPER.ink, rot:-0.03}));
  coin(CX-140, 640, 122, 'H', {rot:0.04}); coin(CX+140, 640, 122, 'T', {rot:-0.05});
  // the rules, textbook style: a ruled card with a margin line
  const x0 = 110, x1 = 860, y0 = 780, y1 = 1188;   // readable area: the card's lower half is beside TikTok's icon column
  ctx.save(); ctx.shadowColor = 'rgba(60,40,10,0.18)'; ctx.shadowBlur = 18; ctx.shadowOffsetY = 6;
  rr(x0, y0, x1-x0, y1-y0, 10); ctx.fillStyle = '#FBF8F1'; ctx.fill(); ctx.restore();
  ctx.strokeStyle = 'rgba(22,22,22,0.10)'; ctx.lineWidth = 2;
  for(let y = y0+92; y < y1-10; y += 56){ ctx.beginPath(); ctx.moveTo(x0+16, y+0.5); ctx.lineTo(x1-16, y+0.5); ctx.stroke(); }
  ctx.strokeStyle = 'rgba(229,38,30,0.35)'; ctx.beginPath(); ctx.moveTo(x0+76.5, y0+10); ctx.lineTo(x0+76.5, y1-10); ctx.stroke();
  problem(()=>{
    const L = 36, X = x0 + 96;
    ink('THE RULES', X, y0+58, {size:34, weight:900, align:'left', color:PAPER.soft});
    inkLine([['A ', {}], ['fair coin', {weight:900}], [' is flipped. Count every flip.', {}]], X, y0+136, {size:L, align:'left'});
    inkLine([['HH', {weight:900}], [': stop the first time heads is', {}]], X, y0+192, {size:L, align:'left'});
    inkLine([['immediately followed by', {weight:900}], [' heads.', {}]], X, y0+248, {size:L, align:'left'});
    inkLine([['HT', {weight:900}], [': stop the first time heads is', {}]], X, y0+304, {size:L, align:'left'});
    inkLine([['immediately followed by', {weight:900}], [' tails.', {}]], X, y0+360, {size:L, align:'left'});
  });
  problem(()=>{
    const qs = fitSize(['WHICH TAKES MORE', 'FLIPS, ON AVERAGE?'], 640, {weight:900, max:88});   // below y=1040 a centred line may be 640 wide
    ink('WHICH TAKES MORE', CX, 1278, {size:qs, weight:900});
    const w = ink('FLIPS, ON AVERAGE?', CX, 1378, {size:qs, weight:900});
    const wA = measure('ON AVERAGE?', qs, 900); markerUnderline(CX + w/2 - wA, CX + w/2 - 40, 1424, {width:13, slope:-5});
  });
}

function p3(){
  // never name an answer here: anything that rules one out leaks the solution
  ink('Most people are', CX, 345, {size:80, weight:700});
  markerText('CONFIDENTLY', CX, 500, {size:120, rot:-0.05});   // 132 was 907 px wide: cropped on tall phones
  markerText('WRONG.', CX, 650, {size:150, rot:-0.05});
  markerUnderline(330, 760, 735, {width:13, slope:-14});
  const xs = confidenceScale(170, 820, 960);   // the '10' label sits at y=1060, so it must stay left of TikTok's icon column (x<860)
  markerArrow(xs[9] - 260, 820, xs[9] - 50, 920, {bend:-0.25, width:9, head:24});
  const w = ink('Are you?', CX, 1300, {size:140, weight:900});
}

function p4(){
  ink('COMMENT:', CX, 330, {size:96, weight:900});
  const rows = [['HH', ['H','H']], ['HT', ['H','T']], ['SAME', null]];
  rows.forEach(([lab, faces], k)=>{
    const y = 500 + k*150, bx = 200;
    markerPath([[bx-42,y-44],[bx+44,y-46],[bx+46,y+42],[bx-44,y+44],[bx-44,y-40]], {color:PAPER.ink, width:9, wobble:1.6, streaks:false});
    ink(lab, bx+100, y+34, {size:100, weight:900, align:'left', baseline:'alphabetic'});
    if(faces) coinRow(faces, 790, y, {r:52, gap:10});
  });
  inkLine([['+ your confidence ', {}], ['1–10', {weight:900}]], CX, 1000, {size:64});
  ink('Solution tomorrow.', CX, 1170, {size:67, weight:900});   // below y=1040 a centred line may be 640 wide
  ink('Follow.', CX, 1268, {size:84, weight:900});
  markerText('no googling.', 620, 1400, {size:62, rot:-0.08});
}

window.PANELS = {
  draw: [p1, p2, p3, p4],
  meta: {
    handle: '@stemhead',
    caption: "Don't google it.",
    hashtags: ['#math', '#probability', '#puzzle', '#brainteaser', '#sciencetok', '#youshouldbeabletosolvethis'],
    pinned: 'Solution tomorrow. No googling. Drop HH, HT or SAME and your confidence 1–10.',
    sound_note: 'Trending sound at low volume, no lyrics over the first 3 s (the hook is read, not heard).',
    typos: [],
    spell_ok: ['googling'],
    required_phrases: ['fair coin', 'immediately followed by', 'on average', 'start over', 'count every flip'],
    sim_on_panels: [],
    allow_blue: false,
    extra: [["truth check", "The answer (HH 6 flips, HT 4) is verified by sim.py next to panels.js and by carousels/c002-coin-flips-answer/sim.py."]],
    review: {
      thumbnail: 'viewed out/thumb.png at 135x240: the 3-line headline reads clearly, the two gold H coins read as coins, the marker line is secondary; nothing competes.',
      accent: 'red only on the headline underline, the target circle, CONFIDENTLY WRONG + its underline, the circle and arrow on 10 of the confidence scale, no googling. No blue.',
      statement: 'p1 + p2 card: fair coin, count every flip, stop the first time heads is immediately followed by heads (HH) / tails (HT), start over between games, on average. One reading only.',
      flow: 'p1 half a puzzle (HH) -> p2 the other half + the question -> p3 "most people are confidently wrong.. are you?" with a 1-10 scale circled at 10 (names no answer, rules none out) -> p4 one-word comment + promise. Every panel but the last ends unresolved; counter carries a swipe arrow.',
      overlays: 'helpers.js refactor: overlays for 001-005 rendered at every 15th frame before and after (418 frames, same fake timeline.json since Kokoro is not installed here): 0 pixels differ.',
    },
  },
};
})();
