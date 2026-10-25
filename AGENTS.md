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
  blender/scene_bag.py   procedural Cycles scene for video 001 (pattern to copy for new scenes)
  overlays/overlay.html  canvas overlay engine: captions + per-beat graphics, pure function of frame
  overlays/render_overlays.py  Playwright screenshots overlay.html -> PNG+alpha sequence
  sfx.py             procedural SFX + music bed + VO mix -> build/mix.wav
  assemble.py        maps shots onto the timeline, upscales, composites, encodes
videos/<id>/
  script.json        narration beats, pacing pads, voice, fps/size   (edit this to change the video)
  build/             generated, git-ignored: vo/, timeline.json, frames/<shot>/, overlay/, *.wav
  out/final.mp4      deliverable
```

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
