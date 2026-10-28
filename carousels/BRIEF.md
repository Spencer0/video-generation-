# Brief: photo carousels, "You should be able to solve this"

Read AGENTS.md first for repo conventions, then this file. Build the carousel
renderer described below, then produce the first two posts (`c001-coin-flips`
question, `c002-coin-flips-answer` solution) end to end, plus the panels for
`c003` if time allows. Work autonomously. Go for maximum engagement. The
constraint is in the next section; everything else is yours to push.

## The one constraint: the math is true

This is engagement bait, and that is fine. The bait lives in the framing, the
open ending, the dare, the deliberate typo and the "most people are wrong"
claim. It never lives in the answer. Every puzzle has a correct answer, the
answer post states it, and the answer is verified by a simulation script
committed next to the panels. A fake answer burns the account; a true answer
people refuse to believe is the whole business model.

## Why carousels, and what the analytics say

Three videos posted (see `videos/`). All stalled at TikTok's test-batch
ceiling (154, 692, 705 views) with ~31 % average retention, 6 % likes
(healthy), and 0 comments, 0 shares, 0 saves. Comments and saves are the
gate we keep failing. Photo carousels are TikTok's comment-and-save format,
they cost no render time (four PNGs instead of five hours of Cycles), and
they can go out daily. Audience measured on the last video: 82 % male, 64 %
aged 18–24, which is exactly who knows the /sci/ "you should be able to
solve this" meme.

## Format facts

- TikTok photo post: 1080x1920 PNGs, in order. Up to 35 images; we use 4–6.
  TikTok auto-advances with a sound; the viewer can also swipe.
- The first image is the feed thumbnail and the cover. It is the hook. It
  must read at 1/8 scale (135x240 px): one huge line plus one supporting
  line, nothing else.
- All text lives in the images. Keep text inside x 60..1020, y 250..1500
  (platform UI covers the rest), same safe area as the videos.
- No video, no voice. Sound is picked at upload time by the human.

## Engagement playbook (use all of it)

1. **Hook as a dare.** Panel 1 is the meme line, verbatim, in huge type:
   "YOU SHOULD BE ABLE TO SOLVE THIS." Then the setup.
2. **Make the comment one word.** Tell them the only legal answers:
   "HH", "HT" or "SAME". A one-word comment has no friction. Ask them to
   add how confident they are, 1–10. People love rating themselves.
3. **"Most people are wrong."** State what most people answer, then that it
   is wrong. Do not say what is right.
4. **Open ending, with a promise.** "Solution tomorrow. Follow so you don't
   miss it." The answer post goes up ~24 h later. Never leave a puzzle
   unanswered for more than a day; after that it reads as not knowing.
5. **One deliberate harmless typo** in panel 3 (never in the problem
   statement, never in the math): "Most people say their the same."
   The correction crowd comments; the puzzle stays exact.
6. **Dare in the caption**, not just the image. Caption: "Don't google it."
7. **Pinned comment immediately after posting** (the human does this; write
   the text into post.txt): "Solution tomorrow. No googling. Drop HH, HT or
   SAME and your confidence 1–10."
8. **The answer post re-hooks.** Its panel 1 is also a thumbnail-grade
   claim ("YOU WERE WRONG." or "6 vs 4.") so it works for people who never
   saw the question, and it ends by teasing the next puzzle.

## Art direction: very interesting graphics

Not white text on black. Not a slide deck. The look is a textbook page that
someone attacked with a marker:

- Background: warm off-white paper (#F4F0E6) with a faint grid or faint
  ruled lines and a subtle paper-grain noise. Slight vignette at the corners.
- Ink: near-black (#161616) Inter 900 for headlines, Inter 700 for body.
  One accent only: marker red (#E5261E), used for underlines, circles,
  arrows, and the word that matters. A second accent (#1F5FE0 blue) is
  allowed in the answer post only, for the second series.
- Coins are the visual. Draw real-looking coins procedurally on the canvas:
  radial gradient gold or silver, milled edge, a soft drop shadow, a big
  embossed "H" or "T". Flip sequences are rows of coins, 120–160 px each,
  with the target pattern circled in red marker. Hand-drawn-looking marker
  strokes: slightly wobbly lines (seeded noise along the path), rounded
  caps, 10–14 px wide, 90 % alpha.
- Panel 1 composition: headline in the upper third, two big coins "H H"
  centred, "flip until you see this" under them in marker. Nothing else.
- Every panel has at most ~15 words outside the problem statement. If a
  panel needs more, split it.
- Thumbnail test is mandatory (see checks): downscale panel 1 to 135x240
  and confirm the headline is readable by eye.
- Consistent corner tag on every panel, small: "@stemhead" bottom-left,
  "1/4" style counter bottom-right, both inside the safe area.

## Renderer to build (reusable, video-agnostic)

Mirror the overlay engine's shape so future posts are one JS file each.

```
pipeline/carousel/panels.html        opaque 1080x1920 canvas; loads a per-post
                                     panels.js; exposes window.renderPanel(i)
pipeline/carousel/render_panels.py   <id> [--only 2] [--contact] [--preview-mp4]
carousels/<id>/panels.js             window.PANELS = {draw: [fn, fn, ...],
                                     meta: {caption, hashtags, pinned, sound_note}}
carousels/<id>/sim.py                verifies the answer numerically (answer
                                     posts, and any question post with a number)
carousels/<id>/out/01.png ...        the deliverable images
carousels/<id>/out/contact.png       all panels side by side for review
carousels/<id>/out/preview.mp4       optional: panels 2.5 s each with a swipe
                                     transition, for judging the flow
carousels/<id>/out/post.txt          caption, hashtags, pinned comment, order
```

- Reuse the helpers in `pipeline/overlays/overlay.html` (`text`, `pill`,
  `rr`, `font`, `measure`, `mulberry`, easing) by moving them into a shared
  `pipeline/overlays/helpers.js` that both pages load, rather than copying.
  Keep overlay.html's behaviour identical (videos 001–004 must still render
  the same; diff one frame of 004's overlays before and after).
- Add paper, grain, marker-stroke, coin, coin-row and circle/underline/arrow
  helpers to the shared file; later posts will reuse them.
- Screenshots via Playwright exactly as `render_overlays.py` does: load
  fonts first (`document.fonts.load`), then screenshot the 1080x1920 clip,
  opaque (no `omit_background`). Deterministic: seed all randomness from the
  panel index so re-renders are byte-stable.
- `--preview-mp4`: ffmpeg concat of the PNGs, 2.5 s each, with a simple
  slide-left transition (xfade) and no audio. Review tool only.

## Post c001: the question

Puzzle: flip a fair coin until the first time you see HEADS followed
immediately by HEADS. Separately, flip until the first time you see HEADS
followed immediately by TAILS. Which takes more flips on average?

Panels (wording may be tightened, structure may not):

1. YOU SHOULD BE ABLE TO SOLVE THIS. / two coins H H / "flip a coin until
   you see this."
2. "now flip until you see this." / two coins H T / "Which one takes
   longer, on average?"
3. "Most people say their the same." (the typo is intentional) / big red
   marker: "MOST PEOPLE ARE WRONG."
4. "Comment HH, HT or SAME. Add your confidence 1–10." / "Solution tomorrow.
   Follow so you don't miss it." / small: "no googling."

Caption: `Don't google it.` Hashtags: `#math #probability #puzzle
#brainteaser #sciencetok #youshouldbeabletosolvethis`.

## Post c002: the answer

Truth: HH takes 6 flips on average, HT takes 4. Reason: once you hold an H,
HT cannot lose progress (a T finishes, an H keeps you holding an H), while
HH is thrown back to zero by a T. Formally, with E the expected flips: for
HT, E = 4; for HH, E = 6 (solve the two-state Markov chain). Verify with
`sim.py`: 1,000,000 trials each, report the means to two decimals, and put
the real simulated numbers on the panel, not rounded ideals.

Panels:

1. "YOU WERE WRONG." (or "6 vs 4.") / coins H H and H T with 6 and 4 in red
   marker next to them.
2. "HH takes 6 flips on average. HT takes 4." / coin rows showing an example
   run of each.
3. WHY: a two-state diagram drawn in marker. Start -> "holding an H" -> done.
   For HT the T arrow finishes and the H arrow loops in place. For HH the T
   arrow goes all the way back to start. Red circle on that arrow: "this is
   the whole difference."
4. PROOF: "We flipped a coin 1,000,000 times (simulated)." Two bars, HH ~6.00,
   HT ~4.00, numbers from sim.py. Small: "code in bio" is not available, so
   write "ask for the code in the comments."
5. "Next one is worse. Follow." / tease c003 in one line.

Caption: `Most of you said SAME. Here's the proof.` Hashtags as above.
Pinned: "Still don't believe it? Flip a coin 20 times and count. Post your
numbers."

## Post c003 (if time allows): the 99 % test

A disease 1 in 10,000 people have. A test that is 99 % accurate. You test
positive. What are the odds you have it? Most people say 99 %. It is about
1 %. Build the question panels only; its answer post can wait. Define
"99 % accurate" on the panel as 99 % sensitivity and 99 % specificity so
the answer is well-posed (~0.98 %). Verify with a sim.py.

Backlog for later posts, in order: Penney's game (second player always
wins), 100 prisoners (31 %), the lottery ticket 1-2-3-4-5-6 vs a random
one, Newton–Pepys dice. Avoid Monty Hall and the two-child problem: the
first is too famous, the second is ambiguous as usually worded.

## Acceptance checks (run all, write the results to out/checks.txt)

1. Thumbnail test: downscale panel 1 to 135x240 with ffmpeg and look at it.
   Headline readable, nothing else competing. Fix before anything else.
2. Safe area: no text outside x 60..1020, y 250..1500 (assert in the
   renderer by measuring text bounds, not by eye).
3. Contrast: ink on paper ≥ 10:1; red accent only where listed.
4. Word count: ≤ 15 words per panel outside the problem statement.
5. Exactly one typo in the whole post, the intended one, in panel 3 of c001.
   None in c002.
6. The problem statement is unambiguous: "fair coin", "immediately
   followed by", "on average". A reader who disagrees with the answer must
   be wrong, not reading a different problem.
7. sim.py runs in under a minute, prints both means, and the numbers on the
   c002 panel match its output.
8. Videos 001–004 overlays still render identically after the helper
   refactor (one-frame diff).
9. Contact sheet reviewed by you for flow: each panel asks for the swipe.

## Deliverables

- `pipeline/carousel/panels.html`, `pipeline/carousel/render_panels.py`,
  `pipeline/overlays/helpers.js` (shared), overlay.html updated to load it
- `carousels/c001-coin-flips/{panels.js, sim.py, out/*.png, out/contact.png,
  out/post.txt, out/checks.txt}`
- `carousels/c002-coin-flips-answer/` same set
- `carousels/c003-base-rate/{panels.js, sim.py, out/*.png}` if time allows
- A "Carousels" section in AGENTS.md: layout, how to add a post, what the
  helpers do, and anything that cost time
- Commit everything including the PNGs (they are the deliverable; a few MB
  is fine) and push to master.

## Posting instructions for the human (write these into post.txt too)

1. Upload the PNGs in order as a photo post; TikTok will offer carousel
   mode. Panel 1 is the cover.
2. Add a trending sound at low volume; pick one with no lyrics over the
   first 3 seconds so the hook is read, not heard.
3. Paste the caption and hashtags from post.txt. Post.
4. Pin the comment from post.txt within a minute of posting.
5. Reply to the first 10–20 comments, short, never giving the answer.
   "Confident?" "Interesting, why?" Replies count as engagement twice.
6. Post c002 about 24 h later, reply to c001's top comments with a link
   phrase ("answer's up"), and screenshot both analytics pages for review.
