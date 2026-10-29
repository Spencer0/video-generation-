// c004: the infinite captcha prank (https://spencer0.github.io/infinitemoneyglitch/).
// Screenshot post: real chats (names redacted by make_assets.py) + captures of the site.
// Look: blurred copy of the screenshot as the background, the shot as a card, TikTok-style
// white outlined text, red marker on the screenshots only.
(function(){
const CX = 540, WHITE = '#FFFFFF';
const MAXW = 820;                                   // readable width for centred text above y=1040 is 846
const fit = (s, size, w=MAXW) => Math.min(size, fitSize([s], w, {weight:900, max:size}));
const say = (s, y, size=76) => { size = fit(s, size); text(s, CX, y, {size, weight:900, color:WHITE, strokeW:Math.max(10, size*0.15)}); };
const sub = (s, y, size=50) => text(s, CX, y, {size:Math.min(size, fitSize([s], MAXW, {weight:800, max:size})), weight:800, color:WHITE, strokeW:9, shadow:true});

function p1(){
  const img = IMG.chat_preview, crop = [0, 140, 1260, 1135];
  coverBlur(img, {crop, dim:0.55});
  const size = fitSize(['infinite captcha'], MAXW, {weight:900, max:128});
  say('infinite captcha', 330, size); say('prank', 330 + size*1.05, size);
  sub("i sent my friends my “ai trading bot”", 330 + size*1.05 + 105);
  shotCard(img, 490, 680, 760, {crop, maxH:740, rot:-0.015});
}

function p2(){
  const img = IMG.site_gate, crop = [0, 150, 1170, 1500];
  coverBlur(img, {crop, dim:0.35});
  say('the catch: to see the gains', 320, 57);
  say("you have to prove you're human", 394, 57);
  const box = shotCard(img, CX, 480, 840, {crop, maxH:980});
  const [x0, y0] = shotPt(box, 125, 1200), [x1, y1] = shotPt(box, 1045, 1430);
  markerCircle((x0+x1)/2, (y0+y1)/2, (x1-x0)/2 + 16, (y1-y0)/2 + 12, {width:13});
}

function p3(){
  const r1 = [24, 450, 1098, 1185], r2 = [24, 414, 1098, 1704];
  coverBlur(IMG.site_round2, {crop:r2, dim:0.45});
  say("you can't.", 320, 96);
  say('it never lets you in.', 420, 76);
  shotCard(IMG.site_round4, 430, 560, 560, {crop:r2, rot:-0.10});
  shotCard(IMG.site_round1, 650, 530, 560, {crop:r1, rot:0.07});
  shotCard(IMG.site_round2, 540, 600, 580, {crop:r2, rot:-0.015});
}

function p4(){
  const img = IMG.chat_imessage, crop = [0, 640, 1290, 1140];
  coverBlur(img, {crop, dim:0.45});
  say('friend 1 lasted 20 minutes', 330, 72);
  const box = shotCard(img, CX, 450, 860, {crop});
  const [x0, y0] = shotPt(box, 55, 1340), [x1, y1] = shotPt(box, 840, 1760);
  markerCircle((x0+x1)/2, (y0+y1)/2, (x1-x0)/2 + 30, (y1-y0)/2 + 26, {width:12});
}

function p5(){
  const img = IMG.chat_discord, crop = [0, 330, 1290, 1075];
  coverBlur(img, {crop, dim:0.45});
  say('friend 2 thought the captcha', 320, 66);
  say('was the money glitch', 400, 66);
  const box = shotCard(img, CX, 490, 860, {crop});
  let [x0, y0] = shotPt(box, 200, 940), [x1] = shotPt(box, 700, 940);
  markerUnderline(x0, x1, y0, {width:10, slope:-4});
  [x0, y0] = shotPt(box, 195, 1266); [x1, ] = shotPt(box, 675, 1266); const [, y1] = shotPt(box, 0, 1330);
  markerCircle((x0+x1)/2 + 4, (y0+y1)/2 + 4, (x1-x0)/2 + 34, (y1-y0)/2 + 20, {width:11});
}

function p6(){
  const r2 = [24, 414, 1098, 1704];
  coverBlur(IMG.site_round4, {crop:r2, dim:0.45});
  say('try it on', 320, 112);
  say('your friends', 435, 112);
  sub('link in bio', 540, 52);
  shotCard(IMG.site_round4, CX, 600, 640, {crop:r2, maxH:840, rot:0.02});
}

window.PANELS = {
  draw: [p1, p2, p3, p4, p5, p6],
  meta: {
    handle: '',
    chrome: '#FFFFFF',
    caption: "sent my friends a fake ai trading bot. the gains are behind a captcha you can't pass \u{1F480} try it on yours",
    hashtags: ['#prank', '#captcha', '#recaptcha', '#tradingbot', '#ai', '#pranks', '#fyp'],
    pinned: 'tag the friend who would sit there for 20 minutes',
    sound_note: 'Trending sound, normal volume is fine here (nothing to read on slide 1 but the hook). Something smug or a laugh track fits.',
    extra: [
      ['title (TikTok title field)', 'infinite recaptcha prank'],
      ['if you cannot add a bio link yet', 'A clickable bio link may need more followers or a Business account (check Edit profile > Website). If you don't have one, change slide 6 to "comment LINK and i’ll send it" and reply to those comments.'],
      ['privacy', 'Friends’ names and the location are pixelated in assets/ (make_assets.py). The unredacted originals are not in the repo. Still worth a "mind if i post this?" text to both friends.'],
    ],
    typos: [],
    spell_ok: ['captcha', 'ai', 'bot', 'bio'],
    required_phrases: [],
    sim_on_panels: [],
    allow_blue: true,
    review: {
      thumbnail: "viewed out/thumb.png at 135x240: 'infinite captcha prank' reads; the green P&L card reads as money.",
      accent: "red marker only on the screenshots (the robot checkbox, Kayton's bubble, Garrett's two lines). Blue is the screenshots' own UI (reCAPTCHA, iMessage), so allow_blue.",
      statement: "no puzzle. Slide 1 says prank and puts 'ai trading bot' in quotes, so the $4,812 is never presented as real. Friends' names and the location are pixelated.",
      flow: 'hook (prank + the bait text) -> the gate -> the captcha never ends -> friend 1 -> friend 2 -> try it on your friends. Each slide answers the previous one and opens the next.',
      overlays: 'helpers.js additions (blend option, coverBlur, shotCard) leave c001-c003 byte-identical (same sha1s).',
    },
  },
};
})();
