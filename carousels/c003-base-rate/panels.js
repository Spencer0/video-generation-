// c003: the 99 % test (base-rate question post). Answer post comes later;
// sim.py already verifies the answer (~0.98 %).
(function(){
const CX = 540;

function p1(){
  const size = fitSize(['YOU SHOULD', 'BE ABLE TO', 'SOLVE THIS.'], 846, {weight:900, max:150});
  ['YOU SHOULD', 'BE ABLE TO', 'SOLVE THIS.'].forEach((l, k) => ink(l, CX, 290 + size*0.73 + k*size*1.02, {size, weight:900, baseline:'alphabetic'}));
  const w = measure('SOLVE THIS.', size, 900), yl = 290 + size*0.73 + 2*size*1.02 + 30;
  markerUnderline(CX - w/2, CX + w/2 - 30, yl, {width:14, slope:-8});
  testStrip(CX, 1010, {rot:-0.07, scale:1.2});
  markerCircle(CX + 50, 1010, 190, 120, {width:12});
  problem(() => markerText('you test positive.', CX, 1320, {size:72, color:PAPER.ink, rot:-0.035}));
}

function p2(){
  // 10,000 people as dots, one of them sick
  const cols = 100, step = 4.8, gx = 110, gy = 290, sick = 55*cols + 85;
  const pos = dotGrid(gx, gy, cols, 100, step, {r:1.45, mark:[sick], markR:4.5});
  const [sx, sy] = pos(sick);
  markerCircle(sx, sy, 30, 27, {width:8});
  problem(() => {
    markerText('10,000', 800, 360, {size:74, color:PAPER.ink, rot:-0.04});
    markerText('people', 800, 440, {size:60, color:PAPER.ink, rot:-0.04});
    markerText('1 has it.', 820, 650, {size:66, rot:-0.05});
  });
  markerArrow(705, 612, sx + 36, sy + 6, {bend:0.18, width:9, head:24});
  const x0 = 110, x1 = 860, y0 = 810, y1 = 1230;   // readable area: the card's lower half is beside TikTok's icon column
  ctx.save(); ctx.shadowColor = 'rgba(60,40,10,0.18)'; ctx.shadowBlur = 18; ctx.shadowOffsetY = 6;
  rr(x0, y0, x1-x0, y1-y0, 10); ctx.fillStyle = '#FBF8F1'; ctx.fill(); ctx.restore();
  ctx.strokeStyle = 'rgba(22,22,22,0.10)'; ctx.lineWidth = 2;
  for(let y = y0+84; y < y1-10; y += 52){ ctx.beginPath(); ctx.moveTo(x0+16, y+0.5); ctx.lineTo(x1-16, y+0.5); ctx.stroke(); }
  ctx.strokeStyle = 'rgba(229,38,30,0.35)'; ctx.beginPath(); ctx.moveTo(x0+70.5, y0+10); ctx.lineTo(x0+70.5, y1-10); ctx.stroke();
  problem(() => {
    const L = 32, X = x0 + 88;
    ink('THE SETUP', X, y0+54, {size:32, weight:900, align:'left', color:PAPER.soft});
    inkLine([['1 in 10,000', {weight:900}], [' people have a disease.', {}]], X, y0+124, {size:L, align:'left'});
    inkLine([['The test is ', {}], ['99% accurate', {weight:900}], [':', {}]], X, y0+176, {size:L, align:'left'});
    inkLine([['it catches ', {}], ['99% of people who have it', {weight:900}]], X, y0+228, {size:L, align:'left'});
    inkLine([['and clears ', {}], ["99% of people who don't", {weight:900}], ['.', {}]], X, y0+280, {size:L, align:'left'});
    inkLine([["You're ", {}], ['tested at random', {weight:900}]], X, y0+332, {size:L, align:'left'});
    inkLine([['and ', {}], ['test positive', {weight:900}], ['.', {}]], X, y0+384, {size:L, align:'left'});
    const qs = fitSize(['WHAT ARE THE ODDS', 'YOU HAVE IT?'], 640, {weight:900, max:80});   // below y=1040 a centred line may be 640 wide
    ink('WHAT ARE THE ODDS', CX, 1318, {size:qs, weight:900});
    ink('YOU HAVE IT?', CX, 1318 + qs*1.15, {size:qs, weight:900});
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
  ['99%', '50%', '1%'].forEach((lab, k) => {
    const y = 500 + k*150, bx = 330;
    markerPath([[bx-42,y-44],[bx+44,y-46],[bx+46,y+42],[bx-44,y+44],[bx-44,y-40]], {color:PAPER.ink, width:9, wobble:1.6, streaks:false});
    ink(lab, bx+100, y+34, {size:100, weight:900, align:'left', baseline:'alphabetic'});
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
    caption: "Don't google it. Doctors get this wrong too.",
    hashtags: ['#math', '#probability', '#puzzle', '#brainteaser', '#sciencetok', '#youshouldbeabletosolvethis'],
    pinned: 'Solution tomorrow. No googling. Drop 99%, 50% or 1% and your confidence 1–10.',
    sound_note: 'Trending sound at low volume, no lyrics over the first 3 s.',
    typos: [],
    spell_ok: ['googling'],
    required_phrases: ['1 in 10,000', '99% accurate', '99% of people who have it', "99% of people who don't", 'tested at random', 'test positive'],
    sim_on_panels: [],
    allow_blue: false,
    extra: [["truth check", "Answer: about 1% (0.98%). Per 1,000,000 people tested: 100 have it, 99 test positive; 999,900 don't, 9,999 of them test positive anyway. 99 / (99 + 9,999) = 0.98%. sim.py simulates 100,000,000 people."]],
    review: {
      thumbnail: 'viewed out/thumb.png at 135x240: headline reads, the positive test cassette reads as a test.',
      accent: 'red on underline, circles, the arrow, 1 has it, CONFIDENTLY WRONG + its underline, the circle and arrow on 10 of the confidence scale, no googling. No blue.',
      statement: '99% accurate is defined on the panel as 99% sensitivity and 99% specificity; tested at random (no symptoms) fixes the prior. Answer ~0.98% (sim.py).',
      flow: 'same arc as c001: hook -> setup + question -> "confidently wrong.. are you?" (names no answer) -> comment + promise.',
      overlays: 'helpers.js refactor: overlays for 001-005 rendered at every 15th frame before and after (418 frames, same fake timeline.json since Kokoro is not installed here): 0 pixels differ.',
    },
  },
};
})();
