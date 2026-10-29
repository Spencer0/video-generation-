// c002: the answer to c001. HH takes 6 flips on average, HT takes 4.
// Red = HH series, blue = HT series (second accent, answer posts only).
// The proof panel draws window.SIM (out/sim.json from sim.py), never typed numbers.
(function(){
const CX = 540, RED = PAPER.red, BLUE = PAPER.blue;

function p1(){
  const size = fitSize(['YOU WERE'], 846, {weight:900, max:190});
  ink('YOU WERE', CX, 290 + size*0.73, {size, weight:900, baseline:'alphabetic'});
  const w = ink('WRONG.', CX, 290 + size*1.75, {size, weight:900, baseline:'alphabetic'});
  markerUnderline(CX - w/2, CX + w/2 - 40, 290 + size*1.75 + 34, {width:14, slope:-8});
  markerText('average flips', 790, 780, {size:52, color:PAPER.ink, rot:-0.04});
  const rows = [[['H','H'], '6', RED, 930], [['H','T'], '4', BLUE, 1220]];
  for(const [faces, num, col, y] of rows){
    coinRow(faces, 330, y, {r:105, gap:18});
    markerText(num, 755, y + 6, {size:250, color:col, rot:-0.05});   // stays left of x=860 (TikTok icon column)
  }
  markerLine(130, 1075, 850, 1068, {color:PAPER.ink, width:5, alpha:0.35, wobble:1.5, streaks:false});
}

function p2(){
  inkLine([['HH', {weight:900, color:RED}], [' takes ', {}], ['6', {weight:900, color:RED}], [' flips on average.', {}]], CX, 345, {size:56});
  inkLine([['HT', {weight:900, color:BLUE}], [' takes ', {}], ['4', {weight:900, color:BLUE}], ['.', {}]], CX, 445, {size:56});
  markerText('for example:', 300, 590, {size:56, color:PAPER.ink, rot:-0.04});
  // an HH game: twice an H gets wiped out by a T before H H lands
  const xs = coinRow(['H','T','H','T','H','H'], CX, 760, {r:62, gap:26});
  markerCircle((xs[4]+xs[5])/2, 760, 150, 84, {width:11, color:RED});
  markerText('6 flips', 860, 905, {size:60, color:RED, rot:-0.04});
  // an HT game: the extra H's don't hurt, you're still holding an H
  const ys = 1140, xt = coinRow(['H','H','H','T'], 420, ys, {r:62, gap:26});
  markerCircle((xt[2]+xt[3])/2, ys, 150, 84, {width:11, color:BLUE});
  markerText('4 flips', 700, ys + 130, {size:60, color:BLUE, rot:-0.04});   // under the row: x>860 at this height is TikTok's icon column
}

// ---- state diagram pieces
const NR = 74;                                         // node radius
function node(x, y, {seed}={}){ markerCircle(x, y, NR, NR*0.94, {color:PAPER.ink, width:9, turns:1.06, wobble:1.6, streaks:false, seed}); }
function selfLoop(x, y, face, col){                    // loop over the top of a node, labelled with a mini coin
  const cy = y - NR - 50, R = 54, pts = [];
  for(let k = 0; k <= 40; k++){ const a = Math.PI*(0.72 + 1.56*k/40); pts.push([x + Math.cos(a)*R*0.9, cy + Math.sin(a)*R*(k < 20 ? 1 : 1)]); }
  // start and end on the node rim
  pts.unshift([x - 30, y - NR + 4]); pts.push([x + 30, y - NR + 2]);
  markerPath(pts, {color:col, width:8, wobble:1.4, streaks:false});
  markerArrowHead(pts[pts.length-1], pts[pts.length-4], {color:col, width:8, head:22});
  coin(x, cy - R - 30, 32, face, {shadow:false});
}
function edge(x0, x1, y, face, col){                   // straight-ish arrow between nodes, coin above it
  markerArrow(x0 + NR + 10, y, x1 - NR - 12, y, {bend:0.04, width:8, head:24, color:col, streaks:false});
  coin((x0 + x1)/2, y - 46, 32, face, {shadow:false});
}
function doneMark(x, y){ markerPath([[x-30,y+2],[x-8,y+26],[x+34,y-30]], {color:PAPER.ink, width:12, wobble:1, streaks:false}); }

function p3(){
  ink('WHY?', CX, 330, {size:120, weight:900});
  const X = [210, 520, 810];   // the lower row sits at y=1050: everything right of x=860 is under TikTok's icon column
  // HT: once you hold an H you can't lose it
  let y = 650;
  ink('HT', 120, y - 105, {size:64, weight:900, color:BLUE, align:'left'});
  X.forEach(x => node(x, y));
  selfLoop(X[0], y, 'T', PAPER.ink); selfLoop(X[1], y, 'H', BLUE);
  coin(X[1], y, 46, 'H', {shadow:false}); doneMark(X[2], y);
  edge(X[0], X[1], y, 'H', PAPER.ink); edge(X[1], X[2], y, 'T', PAPER.ink);
  ink('start', X[0], y + NR + 40, {size:34, weight:700, color:PAPER.soft});
  ink('holding an H', X[1], y + NR + 40, {size:34, weight:700, color:PAPER.soft});
  ink('done', X[2], y + NR + 40, {size:34, weight:700, color:PAPER.soft});
  // HH: the same, except a T from "holding an H" throws you back to the start
  y = 1050;
  ink('HH', 120, y - 105, {size:64, weight:900, color:RED, align:'left'});
  X.forEach(x => node(x, y));
  selfLoop(X[0], y, 'T', PAPER.ink);
  coin(X[1], y, 46, 'H', {shadow:false}); doneMark(X[2], y);
  edge(X[0], X[1], y, 'H', PAPER.ink); edge(X[1], X[2], y, 'H', PAPER.ink);
  const back = bezierPts([X[1] - 20, y + NR + 6], [(X[0]+X[1])/2, y + 250], [X[0] + 20, y + NR + 8]);
  markerPath(back, {color:RED, width:11});
  markerArrowHead(back[back.length-1], back[back.length-5], {color:RED, width:11, head:30});
  coin((X[0]+X[1])/2, y + 170, 34, 'T', {shadow:false});
  markerCircle((X[0]+X[1])/2, y + 158, 245, 92, {width:10, tilt:-0.03});
  markerText('this is the whole', 600, y + 270, {size:50, rot:-0.06});
  markerText('difference.', 620, y + 346, {size:50, rot:-0.06});
}

function p4({sim}){
  const S = sim || {display:{hh:'?', ht:'?', trials:'?'}, HH:{mean:6}, HT:{mean:4}};
  const w = ink('PROOF.', CX, 340, {size:130, weight:900});
  markerUnderline(CX - w/2, CX + w/2 - 20, 410, {width:14, slope:-6});
  ink('Average flips,', CX, 520, {size:56, weight:700});
  ink(`${S.display.trials} simulated games each.`, CX, 592, {size:50, weight:700});
  // hand-drawn bars, hatched in the series colour; length from the simulation
  const x0 = 300, scale = 590/6.5;
  const bars = [[['H','H'], S.HH.mean, S.display.hh, RED, 800], [['H','T'], S.HT.mean, S.display.ht, BLUE, 1080]];
  markerLine(x0 - 4, 680, x0 - 2, 1210, {color:PAPER.ink, width:7, wobble:1, streaks:false});
  for(const [faces, v, label, col, y] of bars){
    coinRow(faces, 212, y, {r:52, gap:8});   // coin letters clear of the x<110 side crop
    const L = v*scale, h = 150, top = y - h/2;
    markerPath([[x0, top], [x0 + L, top + 2], [x0 + L - 2, top + h], [x0, top + h - 2]], {color:col, width:8, wobble:1.4, streaks:false});
    for(let k = -h; k < L; k += 26){                    // hatching, clipped to the bar
      const a = Math.max(0, k), b = Math.min(L, k + h); if(b - a < 8) continue;
      markerLine(x0 + a, top + h - (a - k), x0 + b, top + h - (b - k), {color:col, width:6, alpha:0.55, wobble:0.8, streaks:false});
    }
    markerText(label, Math.min(x0 + L + 20, 1010) , y + 140, {size:84, color:col, align:'right', rot:-0.03});
  }
  ink('Want the code? Comment CODE.', CX, 1400, {size:38, weight:700});   // below y=1040 a centred line may be 640 wide
}

function p5(){
  const size = fitSize(['NEXT ONE', 'IS WORSE.'], 846, {weight:900, max:170});
  ink('NEXT ONE', CX, 300 + size*0.73, {size, weight:900, baseline:'alphabetic'});
  ink('IS WORSE.', CX, 300 + size*1.73, {size, weight:900, baseline:'alphabetic'});
  testStrip(CX, 830, {rot:-0.08});
  markerCircle(CX + 15, 832, 150, 105, {width:11});
  ink('A 99% accurate test', CX, 1080, {size:64, weight:700});
  ink("says you're sick.", CX, 1160, {size:64, weight:700});
  ink('Are you?', CX, 1250, {size:64, weight:900});
  const w = ink('Follow.', CX, 1390, {size:96, weight:900});
  markerUnderline(CX - w/2, CX + w/2, 1440, {width:12, slope:-5});
}

window.PANELS = {
  draw: [p1, p2, p3, p4, p5],
  meta: {
    handle: '@stemhead',
    caption: "Most of you said SAME. Here's the proof.",
    hashtags: ['#math', '#probability', '#puzzle', '#brainteaser', '#sciencetok', '#youshouldbeabletosolvethis'],
    pinned: 'Still don’t believe it? Grab a coin and play each game 5 times (start over after every finish). Post your average flips for HH and HT.',
    sound_note: 'Trending sound at low volume, no lyrics over the first 3 s.',
    typos: [],
    spell_ok: [],
    required_phrases: ['on average', 'simulated games each'],
    sim_on_panels: ['hh', 'ht', 'trials'],
    allow_blue: true,
    extra: [["caption check", "The caption assumes most c001 comments said SAME. If most said HT, use: \"Most of you said HT. Here's the proof.\" Keep the rest."], ["why the pinned comment is not \"flip 20 times and count\"", "In one long run of flips HH and HT each show up equally often (every adjacent pair is HH or HT with chance 1/4). Counting them would 'disprove' us. What differs is the wait for the FIRST one, so viewers have to replay each game from scratch. 5 games each is noisy but usually shows it; HH's spread is wide (median 4, mean 6)."], ["reply to WHY comments", "From \"holding an H\": in HT, another H keeps you holding an H, so you only ever wait for a T. In HH, a T throws you back to the start. Expected flips E from start: HT: E = 2 (to get an H) + 2 (to get a T) = 4. HH: E = 1 + E1/2 + E/2 and E1 = 1 + E/2 give E = 6."], ["reply to CODE comments", "Paste carousels/c002-coin-flips-answer/sim.py (40 lines, numpy) or the 20-line pure-Python one in carousels/c001-coin-flips/sim.py."]],
    review: {
      thumbnail: 'viewed out/thumb.png at 135x240: YOU WERE WRONG plus the big red 6 and blue 4 read; works cold.',
      accent: 'red = HH series + emphasis marks (underlines, the back-to-start arrow and its circle); blue = HT series only.',
      statement: 'answer post: restates HH 6 / HT 4 on average; the proof panel says simulated, 1,000,000 games each (not flips: 1M games is ~10M flips).',
      flow: 'p1 claim -> p2 what that looks like -> p3 why (diagram) -> p4 proof with real sim numbers + comment CODE -> p5 tease c003 + follow.',
      overlays: 'helpers.js refactor: overlays for 001-005 rendered at every 15th frame before and after (418 frames, same fake timeline.json since Kokoro is not installed here): 0 pixels differ.',
    },
  },
};
})();
