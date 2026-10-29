# AGENTS.md — how to work in this repo

This repo makes short-form STEM videos (TikTok / YouTube Shorts, 1080x1920)
entirely from code: Blender renders the "footage", a canvas engine renders the
captions and diagrams, Kokoro synthesizes the voiceover, numpy synthesizes
the sound design, and ffmpeg assembles. No cameras, no editors, no accounts.

Read this first, then `README.md` for the per-video walkthrough.

## Layout

```
pipeline/            reusable tooling (video-agnostic)
  tts.py             script.json -> build/vo.wav + build/timeline.json  (the timing source of truth)
  timeline.py        shared helpers (word-timing estimate, paths)
  blender/scene_bag.py     procedural Cycles scene for video 001 (water bag over flame)
  blender/scene_chain.py   procedural Cycles scene for video 002 (chain fountain)
  blender/scene_leidenfrost.py, scene_kaye.py   videos 004 and 005
  checks.py          measured acceptance checks (duration, VO onset, luma, UI-zone safe area, loop seam, loudness)
  safe_area.json     the TikTok UI zones every renderer and check reads (see 'Where things may go on screen')
  fake_timeline.py   ESTIMATED timeline from script.json for overlay previews/audits without Kokoro (never assemble with it)
  blender/render_all.sh    renders every shot listed in script.json "shots" with the "scene" script
  overlays/helpers.js      shared canvas helpers (text, pill, easing, paper, marker, coins) for overlays + carousels
  overlays/overlay.html    canvas overlay engine: captions, renderFrame (video-agnostic)
  carousel/panels.html, render_panels.py   photo-carousel renderer (see Carousels below)
  overlays/render_overlays.py  loads videos/<id>/beats.js into overlay.html, screenshots PNG+alpha
  audiolib.py        synth primitives (noise, pops, whoosh, ding, thud, filters, place)
  sfx.py             generic mixer: VO + videos/<id>/sfx_cues.py cues + music -> build/mix.wav
  assemble.py        maps shots onto beats via script.json "bg_plan", upscales, composites, encodes
videos/<id>/
  script.json        narration beats + pacing, voice, fps/size, "scene", "shots", "bg_plan", "blur_beats"
  beats.js           per-beat canvas graphics (window.BEATS = {draw, cutFlash, keywords})
  sfx_cues.py        per-video sound cues: cues(tl, B, W, sfx, music, D, N)
  build/             generated, git-ignored: vo/, timeline.json, frames/<shot>/, overlay/, *.wav
  out/final.mp4      deliverable
```

A new video touches exactly four files: `script.json`, a scene script,
`beats.js`, `sfx_cues.py`. Everything else is shared.

## The one rule: the voiceover drives everything

`tts.py` lays beats out from the real synthesized durations and writes
`timeline.json` with absolute start/end per beat, line and word. Blender,
overlays, SFX and assembly all read that file. Never hand-type a timing;
if pacing feels off, change `pad_before/pad_after/min_duration` in
`script.json` and re-run `tts.py` (seconds), then re-render only what moved.

## Environment facts (cloud container, as of 2026-10)

- 4 CPU cores, no GPU. Blender 4.5 LTS is downloaded to `/home/user/tools/`
  (`tools/` is git-ignored; see README for the one-line install).
- Cycles CPU is the renderer. EEVEE under Xvfb+llvmpipe works but is *slower*
  than Cycles here, don't bother.
- Kokoro ONNX (`kokoro-onnx` pip + model files in `/home/user/tools/kokoro`)
  gives broadcast-quality TTS offline, ~0.3x realtime on CPU. `edge-tts` is a
  fallback but needs Microsoft's endpoint. Voice used: `af_heart`, speed 1.12.
- Playwright + Chromium are preinstalled (`/opt/pw-browsers`). Overlay frames
  render at ~0.15 s/frame at 1080x1920. Fonts available: full Inter family,
  Noto Color Emoji (emoji in canvas text works).
- ffmpeg 6 with libx264 is present.

## Render cost rules of thumb (Cycles CPU, this scene)

Measured on the bag scene, 32 samples, adaptive, OIDN denoise:

| resolution | s/frame (steady state) |
|-----------:|-----------------------:|
| 540x960    | ~23                    |
| 720x1280   | ~41                    |
| 1080x1920  | ~100+                  |

- Transparent plastic + glass water means most pixels carry 4-8 interfaces;
  adaptive sampling barely helps. Resolution and sample count are the levers.
  DoF, bubbles (110 glass icospheres), bloom, bounce caps all cost < 10% each.
- The bag shader (fresnel film + bump + soot + melt-hole masks) is ~20% of
  frame time; the flame (two emissive shells with animated noise alpha) is free.
- Sample count barely matters above 16: adaptive sampling runs its first
  convergence check at the first power of two >= `adaptive_min_samples`, and
  most pixels stop there. Each sample costs ~1 s at 540p in this scene, so
  set `adaptive_min_samples = 4`, `adaptive_threshold = 0.1`, 24 samples, and
  spend the budget on resolution instead. Scene sync + BVH is only 0.3 s/frame.
- Profile with `SCENE_FLAGS=nodof,nobubbles,...` toggles (see scene_bag.py)
  and read the second frame's time, never the first (first frame carries
  kernel load + shader compile).
- `use_persistent_data = True` and rendering frames in a loop inside one
  Blender process avoids a ~30 s scene rebuild per frame. Do not launch one
  Blender process per frame.
- Render at 720 wide and lanczos-upscale to 1080: phones + platform
  compression hide it, and it halves the render time versus 1080.
- Budget: ~630 frames of 3D at 24 fps for a 46 s video = 7 h at 720 /
  4 h at 540. Reuse shots behind explainer panels (blur+dim) rather than
  rendering unique footage for every beat. Check `BG_PLAN` in `assemble.py`.

## Scene-building patterns that worked

- Everything procedural, no .blend: parametric bag mesh (superellipse rings,
  bulge profile below the waterline, noise crinkle above it), water = inset
  copy of the same rings capped at the waterline.
- Cheap plastic: `Fresnel -> Mix(Transparent, Glossy)` instead of a refractive
  Principled transmission. Looks like film, renders 4x faster.
- Water: plain Glass IOR 1.333, caustics off, `blur_glossy` 1.5.
- Bubbles inside water: Glass with IOR 1/1.333 (= 0.75) on icospheres.
- Flame: revolve a teardrop profile, Emission color-ramped by generated Z,
  alpha = facing^2 * animated 4D noise * tip fade; a brighter inner core
  shell; two flickering point lights; compositor Glare(BLOOM).
- Per-frame animation is done in Python in a `shot_update(frame)` function
  (camera, flicker, melt progress, bubble positions), not with keyframes, so
  any frame range renders standalone and shots can be split across machines.
- Bubble "simulation": Poisson spawn times from a rate curve (cap the
  exponential step at 50 ms or zero-rate periods jump past the shot - that
  bug cost a render), grow attached, rise with wobble, pop at the surface.
- Melting: shader radial hole mask with noisy edge (transparent inside,
  emissive bead at rim, charred ring outside) + a shape key that shrinks the
  film toward the heat. Reads as "burn-through" without any physics sim.

## Where things may go on screen (TikTok UI zones)

Measured 2026-10-29 from a feed screenshot (iPhone, 19.5:9): TikTok scales a
1080x1920 video to fill the screen *height*, so ~54 px are cropped off each
side (~108 on 20:9 Androids), and its UI sits on top of what is left. The old
rule "x 60..1020, y 250..1500" let the 005 slow-motion pill sit under the
comment icon and cropped the 004 headline to "VATER SHOULDN'T DO THI". The
zones live in `pipeline/safe_area.json` (single source of truth; every
renderer and check reads it):

| zone | video px | covered by |
|---|---|---|
| side crops | x < 110 and x > 970 | off-screen on tall phones |
| top bar | y < 250 | status bar, Following / For You tabs, search |
| right column | x > 860 and y > 1040 | avatar, like, comment, save, share, sound disc |
| bottom caption | y > 1560 and x < 900 | username, caption, sound marquee |

Readable area: x 110..970, y 250..1560, and below y=1040 the right edge is
860. A centred line may be 846 px wide above y=1040 and 640 px below it.
This applies to everything readable (panels, pills, labels, diagrams,
counters, coins), not just captions; decoration (vignette, flashes, blur,
footage) may cover the zones. Captions default to y=980 now; 1460 (videos
001-003) was under the icons. Prefer the band y 250..1040 for anything
wide; put small labels bottom-left, never bottom-right.

Enforcement:
- `pipeline/checks.py` fails its safe-area line when overlay pixels with
  alpha > 128 land in a zone (full-frame flashes skipped), per zone with the
  worst frame and bounding box. `--only-safe-area --overlay-dir <dir>` runs
  just that on any overlay render.
- `render_overlays.py --show-safe-area` paints the zones red on every frame:
  render `--every 30`, tile, look, before any full render.
- `render_panels.py` fails check 2 when any text run's bounds touch a zone;
  the carousel corner tags sit at y=1530, right-aligned to x=850.
- No Kokoro in the container? `pipeline/fake_timeline.py <id>` writes an
  ESTIMATED timeline (3 words/s) so overlays can be rendered and audited. It
  is marked `estimated: true`, checks.py warns on it; never assemble with it.
- Audit 2026-10-29: 001-003 had 940 px explainer panels and y=1460 captions
  under the icons (shipped as is; fix if ever re-rendered). 004 headline and
  005 pill / why1 panel / left labels fixed in beats.js, c001-c003 re-laid
  out; the posted 004/005 mp4s predate the fix.

## Overlay / caption conventions (what tested well visually)

- Placement: see the UI zones above. Captions at y=980 by default (per
  video via `BEATS.caption.y`), 78 px Inter 900, uppercase, 14 px black
  stroke, max 3 words per chunk, active word yellow + 1.12x pop, keyword
  words orange after they are spoken; the engine shrinks a chunk to the
  readable width for its y.
- Layout widths must include the active word's scale or neighbours overlap.
- Every helper multiplies into `ctx.globalAlpha` instead of setting it, so
  fades compose through nested calls.
- Beat graphics are pure functions of (t, beat); use `wordTime(beat, word)`
  to trigger animations on the spoken word rather than on hand-tuned times.
- Cuts get a 0.2 s white flash + whoosh. Explainer beats sit on blurred,
  dimmed footage (ffmpeg `gblur`/`eq` with timeline `enable=`), not black.

## Audio

- Procedural everything, 48 kHz: filtered-noise burner roar, Poisson bubble
  pops following the same boil-rate curve as the render, sizzle + thud for
  the melt, whoosh on cuts, dings on stamps, 2.4 kHz ticks on caption chunks.
- Music bed: detuned-sine minor pad + sub pulse + hat ticks at 96 bpm,
  lowpassed, ducked under VO by RMS envelope. Keep it at ~-20 dB; platforms
  often get a trending sound layered on top anyway.
- VO: highpass 80 Hz, soft tanh compression, peak-normalized, sits ~8 dB above
  everything else.

## Gotchas that cost time

- `pgrep -f name` matches the shell that runs the pgrep itself; a "wait until
  the other job exits" loop built on it never exits. Match on the binary
  (`pgrep -x blender`) or a pid file.
- `rm -rf "$VAR"/*` is refused by the harness; write `"${VAR:?}"/*`.
- Kokoro `af_heart` reads "120" as "one hundred twenty" (fine) but write
  numbers the way you want them spoken; "one twenty" in the script avoids a
  long number read.

## Script formula (feedback from video 001)

The first draft explained well but opened soft. The structure that landed:

1. **Curiosity hook, 1 line**: open directly on the question ("What happens
   when a flame touches a plastic bag?"). No channel tagline or eyebrow in
   front of it; that was tried and cut because it delayed the hook.
2. **The obvious outcome**: "Obviously, it melts. Instantly." (lets the viewer
   feel smart, sets up the reversal).
3. **The reversal + "How?"**: the impossible thing, ending on a one-word
   question that the next beat answers.
4. **Why, with an equation**: one formula on screen (q = k·ΔT/d, Q = m·L),
   each symbol highlighted as it is spoken; numbers as bars, not prose.
5. **Payoff everyone can repeat**: "You can even boil noodles in a bag."
6. **CTA, 3 s**: "Follow for more!"

Pacing: ~3 words/s at Kokoro speed 1.12; 45 s total; no beat longer than 8 s.
Keep beat ids stable when rewriting (hook, empty, water, ...) because the
overlay, SFX and background plan key on them; add new ones (noodles) rather
than renaming.

Shots are time-based with fixed nominal durations (`SHOT_DUR` in
scene_bag.py), so a script rewrite that changes beat lengths does not
invalidate rendered frames: beats trim or wrap the footage via `BG_PLAN`.

## Fact-check notes for video 001 (keep claims this honest next time)

- Mechanism is right (Fourier conduction through a thin film into water held
  at its boiling point; latent heat absorbs the surplus).
- Softest numbers: LDPE bags melt ~105-115°C (we said 120); the film's flame
  side sits ~5-15°C above the water (we said "at 100"); "cannot melt" should
  be "won't melt where water touches it". Blue flames, soot, seams and the
  dry part of the bag can all fail it. Flame "over 1,000°C" is fine for the
  hot zone. Round numbers are OK on screen, but say "about" in the VO.

## Video 002 notes (chain fountain)

- Kinematic, not simulated: one bead unit (icosphere + link) with an Array
  modifier, deformed along a POLY spline by a Curve modifier. The spline
  points are recomputed from smooth functions of time in a
  `frame_change_pre` handler, so Cycles deformation motion blur works
  (shutter 0.5). Flow = `object.location.x = -(travelled % pitch)`.
- Scene runs at 1/4 real speed (SLOWMO) so beads stay visible; say so on
  screen ("SLOW MOTION 4x").
- Physics: Biggins & Warner 2014. Pile reaction R = α·λv², fountain height
  h = α·h₁/(1−α), chain speed v² = g·h₁/(1−α), α ≈ 0.12 measured.
- Metal beads + thin-film glass beaker render at ~13-15 s/frame at 576p
  with motion blur: cheaper than the glass-in-plastic bag scene.
- Film-glass trick needs a dim glossy weight (fresnel × 0.45) in a dark
  studio, or a tall glass reads as a black cylinder.

## Video 003 notes (lightning)

- Bolt = seeded midpoint-displacement polyline (main channel rough 0.10, 7
  levels; 9 branches rough 0.18) as bevelled POLY curves. Growth via
  `bevel_factor_end`; the return-stroke wave is a shader mask on the curve's
  UV X (runs along the spline) so brightness sweeps bottom->top.
- Exposure is the whole game: a strike point light of ~1e8 W at 300 m plus
  cloud-base emission 0.2 reads as a flash; 4e9 W whites out the frame.
- Night frames never converge: 14 samples + OIDN look the same as 24 at
  ~2/3 the time. Dark scenes = fewer samples.
- Mostly-2D video: 13 beats, only 5 backed by 3D (324 frames). The canvas
  explainer (cloud cross-section, charges, voltmeter, stepped leader,
  upward wave, heat gauge, thunder math, globe) carries the middle. Opaque
  2D beats just paint their own sky; the assembler's footage is irrelevant.
- A 2D "takeover" mid-beat (switch to an opaque scene on a word) is the fix
  when a beat is longer than the usable 3D footage.
- Physics (keep): charge separation by graupel/ice collisions in updrafts;
  cloud + top / − base, ground induced +; 10^8–10^9 V; stepped leader ~50 m
  steps; upward streamers; return stroke ~1/3 c, ~30 kA, ~30,000 °C (5x the
  Sun's surface); thunder d = 343 m/s·t (÷3 km, ÷5 miles); 3–5 strokes per
  flash ~40 ms apart; ~44–50 flashes/s worldwide.

## Video 004 notes (Leidenfrost, produced from a client-style brief)

- 30 fps works end to end: `script.json` "fps" flows to tts/overlays/assembler,
  and render_all passes `--fps` to the scene. Beats may have no lines (silent
  loop beat).
- Scale the scene 100x (1 unit = 1 cm) for millimetre droplets; Cycles ray
  epsilons misbehave at true scale.
- Water that looks like water needs something to reflect: a graphite
  backdrop plane + a dim overhead panel. Pure black world = glass marbles.
- Macro droplets: Glass IOR 1.333 on a UV sphere, volume-preserving wobble,
  elongation along velocity, 0.78 flattening, hover gap, radius shrinking
  for evaporation; motion blur on. ~16 s/frame at 540p (DoF + glass +
  motion blur). Focus the camera on the droplet object, f/4 or slower.
- Camera tracking with a lag + clamp lets the drop enter and exit the frame
  (needed for the seamless-loop ending) while staying readable mid-shot.
- Cutaway: half-sphere via `bmesh.ops.bisect_plane` + `holes_fill`, cut
  face gets its own milky material (index 1). Vapor layer as a flat
  ellipsoid with a scrolling-noise emissive/transparent shader. Billboard
  wisps read as bubbles when out of focus; next time use thin vertical
  streak quads (tall aspect) and keep them in the focal plane.
- `bmesh.ops.create_grid(size=s)` spans [-s, s] (half-extent). It hid the
  cross-section face for an hour.
- Split-screen comparison: `bg_plan` entry `["M", off, {"split": [shot2,
  off2, nframes]}]`; the assembler crops the centre band of each and
  vstacks them for that window.
- `--no-captions` export: render_overlays `--no-captions --out
  build/overlay_nocap`, then assemble `--overlay-dir overlay_nocap`.
- Stems for revision live in build/ (vo.wav, music.wav, sfx.wav); copy to
  out/stems/ for delivery (git-ignored).
- render_all.sh under `set -e`: a shot with all frames present makes the
  filtering grep exit 1 and aborted the loop. Fixed with `|| true`.
  Container restarts kill detached renders; launch long renders through the
  harness background runner and rely on the frame-skip resume.

## Video 005 notes (Kaye effect, produced from an analytics-driven brief)

- Brief-level requirements that came from TikTok analytics on 001/002/004 (all
  stalled at the test-batch ceiling, ~50 % retention by 3 s): claim spoken and
  on screen on frame 0, the phenomenon large and moving on frame 0, bright
  frame (mean luma Y >= 110 first 3 s, >= 90 overall) with a recognisable
  everyday object, something to try + a question to answer, 26-30 s. These
  are now measured by `pipeline/checks.py` (writes out/checks.txt).
- Bright is not flat: the first pass (pastel fluid, cream set, big soft
  lights) hit Y=132 and looked monochrome. What fixed it: the fluid is the
  darkest, most saturated thing in frame (deep teal Principled, roughness
  0.06, coat 1.0), neutral light-grey backdrop, mid-tone wood table, one
  window-shaped 60x90 area light above-left-behind (long highlight streaks on
  stream, jet and heap), dim fill camera-right, small rim behind opposite the
  key. Camera near plate height (~11 deg above), 45 mm, f/3.2, focus on the
  impact point. Y stayed at 135 with far more contrast.
- Portrait frames are narrow: a jet leaving at 45 deg sideways exits the frame
  before its apex. Aim the jet away from the camera (+y) so the projected
  range shrinks and the arc stays inside; it also arcs against the backdrop
  instead of the table edge.
- Kinematic fluid, no sim (as in 002): stream = POLY curve with per-point
  radius (necking from free-fall speed) and a travelling sine wobble; heap =
  polar grid whose vertex heights are recomputed per frame (dome + skirt +
  periodic noise lumps + Gaussian dimple at the impact point); jet = POLY
  curve of fluid parcels on a parabola from the dimple, ages from
  max(0, tau-T_FEED) to min(tau, T_LAND): the tip grows, the thread stands
  while fed, then the root detaches and the tail flies out. Keep the point
  count constant and collapse unused points onto the tip so deformation
  motion blur keeps working. Three small spheres just past the tip read as
  spray.
- Shots are periodic (period = SHOT_DUR, events wrap) so the assembler can
  wrap them and the loop beat lands exactly on frame 0: `loop` shows A
  frames 204-239 and the first frame is A 0. The camera sways with
  sin(2*pi*t/T) for the same reason.
- Three-panel comparison: new assembler option `"stack": [[shot, off], ...],
  "stack_frames": n` vstacks N panels, each scaled to cover W x H/N and
  centre-cropped. Panel shots render at 1080x640 aspect (res_y from the shot
  id), which costs ~1/3 of a full frame.
- A flattened Glass sphere as a water puddle renders black (transmission
  bounces run out in a thin slab). Opaque, saturated blue Principled water
  with motion-blurred droplets reads better at panel size than translucent
  pale water, which vanishes against a white plate.
- Cost at 576x1024, 12 samples, motion blur + DoF, two area lights: ~10 s/frame
  solo (full shots), ~3.7 s/frame for the 576x342 panels; 720 was 21 s/frame
  so it went to 576 per the brief's 12 s/frame rule. 1050 frames, ~2.3 h.
  Two Blender processes at once run at 30 s/frame each (worse than
  sequential); chain shots, never overlap them. The harness background
  runner caps at 2 h, so a chained render needs one relaunch (frame-skip
  resume makes that free).
- Measured on the final: 29.33 s, VO onset 0.10 s, mean luma Y 130.8 (first
  3 s) / 129.3 (whole), darkest frame 99.9 (blurred footage under the
  explainer panel), -14.2 LUFS, TP -1.5 dBTP, loop seam 3.2/255 (captions
  differ; the footage itself differs by 0.17/255).
- Water splash droplets have to be exaggerated (r 0.4-0.6 cm) to survive
  motion blur and lanczos downscaling at panel size; realistic sizes vanish.
- Caption chunks were scaled to fit 960 px, but the 14 px stroke pushed wide
  chunks to x=55; the engine now fits 940 px. `assemble.py` adds half a frame
  to `-t` so the last frame is no longer dropped (880 frames, not 879).
- Overlay engine: vignette strength is now per video (`BEATS.vignette`, 0.15
  here); the default 0.5 darkened a bright set visibly. Light explainer
  panels (cream, dark ink) instead of the dark panel helper.
- Physics (keep): Kaye 1963; Versluis et al. 2006. Shear-thinning shampoo;
  the stream digs a dimple, a thin fast-sheared low-viscosity layer forms,
  the stream slides along it and exits as a jet lasting a few tenths of a
  second; stable on a tilted surface. Honey (Newtonian) coils, water
  splashes. "Roughly ten times thinner" keeps the "roughly".

## Workflow for a new video

1. Copy `videos/001-water-bag/script.json`, write beats (3 words/sec pacing,
   hook in the first 1.5 s, payoff by 60-70%, CTA last 4 s).
2. `python3 pipeline/tts.py <id>` -> check beat durations printed.
3. Write/adapt a scene script; render single `--preview` frames per shot at
   540 until the look is right; time 3 consecutive frames before committing
   to a full render.
4. Adapt overlay beat functions; render with `--every 90` and look at a
   contact sheet before rendering all frames.
5. `sfx.py`, then `assemble.py --preview` early (it tolerates missing 3D
   frames) to check pacing; full render in the background; `assemble.py` at
   the end.

## Carousels (TikTok photo posts, "you should be able to solve this")

Brief: `carousels/BRIEF.md`. Photo carousels are the comment-and-save format
and cost no render time: 4-6 opaque 1080x1920 PNGs per post, one per day.

```
pipeline/overlays/helpers.js         shared with overlay.html (loaded before the page script)
pipeline/carousel/panels.html        opaque canvas; window.renderPanel(i) -> {text log}
pipeline/carousel/render_panels.py   <id> [--only N] [--contact] [--preview-mp4] [--no-sim] [--no-checks]
pipeline/carousel/fonts/             Permanent Marker (Apache-2.0), the hand-lettering
carousels/<id>/panels.js             window.PANELS = {draw:[fn,...], meta:{caption, hashtags, pinned, ...}}
carousels/<id>/sim.py                verifies the answer; writes out/sim.json (injected as window.SIM)
carousels/<id>/out/                  01.png..., contact.png, thumb.png, post.txt, checks.txt (preview.mp4 git-ignored)
```

**Adding a post**: copy a `panels.js` (c001 for a question, c002 for an
answer), write `sim.py` if any number appears or is implied, run
`python3 pipeline/carousel/render_panels.py <id> --contact`, look at
`out/contact.png` and `out/thumb.png`, write what you saw into
`meta.review`, re-run. The script exits 1 on any failed automated check.
Put numbers from the simulation on the panels via `p.sim` (the `sim`
argument of each draw fn), never typed by hand; list their `display` keys in
`meta.sim_on_panels` and check 7 asserts they appear.

**meta fields**: `caption`, `hashtags`, `pinned`, `sound_note`, `extra`
(`[[title, text], ...]` copied into post.txt: reply templates, notes for the
human), `typos` (the deliberate ones, `[{panel, text}]`: check 5 fails on
any other), `spell_ok`, `required_phrases` (what makes the problem
unambiguous), `sim_on_panels`, `allow_blue` (answer posts only), `review`
(by-eye verdicts: thumbnail, accent, statement, flow, overlays).

**Helpers** (all globals in helpers.js; panels.js wraps itself in an IIFE):
- `paperBg(seed)` warm paper, faint grid, mottling, sparse flecks/fibres,
  corner vignette. `PAPER` = palette (bg, ink, red, blue, grid, soft).
- `markerPath(pts, {color, width, alpha, wobble, seed})` the base stroke:
  resampled, pushed sideways by smooth seeded noise, width swell, dry
  streaks; drawn opaque on an offscreen layer then *multiplied* at 90 %.
  Built on it: `markerLine`, `markerUnderline(x0,x1,y,{double})`,
  `markerCircle(cx,cy,rx,ry)` (~1.13 turns, ends overshoot),
  `markerArrow(x0,y0,x1,y1,{bend})`, `markerArrowHead`, `markerCross`,
  `markerText` (Permanent Marker, multiplied like ink), `bezierPts`.
- `ink(str,x,y,{size,weight,color,align})` plain text; `inkLine(segs,...)`
  mixed-weight/colour line, returns word boxes to underline; `fitSize`.
- `coin(cx,cy,r,'H'|'T')` gold heads / silver tails, milled rim, raised
  ring, embossed letter, drop shadow; `coinRow(faces,cx,cy,{r,gap})`
  returns centres for circling a run. `testStrip`, `dotGrid` (population
  of N dots with marked ones), `confidenceScale(x0,x1,y)` (1-10 ruler,
  10 circled).
- panels.html adds `problem(fn)` / `withKind(kind, fn)` to tag text, and
  the corner tags (handle + `i/n` + swipe arrow, inside the safe area).

**Checks** (render_panels.py writes out/checks.txt): every `fillText` and
`strokeText` (including the offscreen marker layer) is logged with its
device-space bounds and a kind (`body`, `problem`, `glyph` for coin letters,
`chrome` for corner tags). From that: safe area asserted on bounds, words
per panel counted on `body` text only (<= 15), typo audit (pyspellchecker
if installed + known grammar slips like "their the"), required phrases,
sim numbers present. Contrast is computed from the palette and measured on
the rendered ink pixels; blue pixels must be 0 unless `allow_blue`.
Thumbnail: `out/thumb.png` is the cover at 135x240; look at it. Renders are
byte-stable (all randomness seeded from the panel index): the sha1s are in
checks.txt; render twice and compare after touching helpers.

**What worked / what cost time**
- Moving helpers out of overlay.html: top-level `function` names in a later
  script silently replace earlier ones, a repeated `const` is a
  SyntaxError, and beats.js files already define `arrow`, `bar`, `label`,
  `INK`... so new helpers get prefixed names (`marker*`, `paper*`, `ink*`).
  Regression: render overlays of 001-005 with `--every 15 --out <dir>`
  before/after and compare pixels (418 frames, 0 differ). Kokoro is not in
  the container, so a fake timeline.json from script.json (3 words/s) was
  used for both sides; delete it afterwards, it is not a real timeline.
- The Python `playwright` package was missing (`pip install playwright`;
  the browser at /opt/pw-browsers is already there).
- Paper grain is sparse flecks + low-frequency mottling, not per-pixel
  noise (which PNG cannot compress and TikTok's recompression smears
  anyway); panels come out ~1.1-1.6 MB.
- `markerCircle` drew a random phase per point -> jagged circles at full
  size that looked fine on the contact sheet. Always look at one panel at
  100 %, not only the 0.4x contact sheet.
- Word cap: label diagram edges with mini coins instead of "H"/"T" text,
  and bars with coin pairs instead of "HH"/"HT"; it reads faster too.
- Honesty traps caught in review: "we flipped a coin 1,000,000 times" was
  really 1M *games* (~10M flips) -> "1,000,000 simulated games each". The
  brief's pinned comment "flip a coin 20 times and count" would hand people
  a refutation: in one long run HH and HT occur equally often; only the
  wait for the first one differs. Pinned comment now says replay each game.
- Slide 3 must never name an answer. The brief's "Most people say their
  the same. MOST PEOPLE ARE WRONG." (and "its 99%" + a crossed-out 99%)
  ruled one option out and halved the puzzle. It is now "Most people are
  CONFIDENTLY WRONG. Are you?" over a 1-10 scale circled at 10
  (`confidenceScale`), which also sets up the confidence ask on slide 4.
  The deliberate typo lived in the leaking sentence, so c001/c003 have no
  typo now (`meta.typos: []`); if one comes back it must not touch an answer.
- Base-rate question: define "99 % accurate" as 99 % sensitivity and 99 %
  specificity, and say "tested at random" so the prior is the 1 in 10,000.
- Permanent Marker has no lowercase (it renders small caps); fine for
  annotations, use Inter for anything longer than a line.

**Backlog** (from the brief, in order): c003 answer post (0.98 %; 99 true
vs 9,999 false positives per million), Penney's game, 100 prisoners (31 %),
lottery 1-2-3-4-5-6 vs random, Newton-Pepys. Avoid Monty Hall and the
two-child problem.
