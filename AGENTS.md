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
  blender/render_all.sh    renders every shot listed in script.json "shots" with the "scene" script
  overlays/overlay.html    canvas overlay engine: captions, helpers, renderFrame (video-agnostic)
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

## Overlay / caption conventions (what tested well visually)

- Safe area: keep text inside x 60..1020, y 250..1500 (platform UI covers
  the rest). Captions at y=1460, 78 px Inter 900, uppercase, 14 px black
  stroke, max 3 words per chunk, active word yellow + 1.12x pop, keyword
  words orange after they are spoken.
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
