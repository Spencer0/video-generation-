# Brief: video 005, the Kaye effect (leaping shampoo)

Read AGENTS.md and README.md first. Then produce video 005 in this repo end to
end: `videos/005-kaye-effect/{script.json, beats.js, sfx_cues.py}`, a scene
script `pipeline/blender/scene_kaye.py`, and the deliverables listed at the
bottom. Work autonomously; do not stop to ask unless a hard requirement below
is impossible, and say so explicitly in that case.

## Why this brief exists (what the analytics taught us)

Three videos have been posted (001 water bag, 002 chain fountain, 004
Leidenfrost). Every one stalled at the TikTok test-batch ceiling: 154, 692 and
705 views. On 004: average watch 11.9 s of 39 s (31 %), 6.4 % finished, likes
6 % of views (good), 0 comments, 0 shares, 0 saves. Retention falls to ~50 %
by 3 s, and TikTok flags 0:01 as the drop point. Likes peak at 0:01 and
collapse by 0:04: viewers liked the *claim* on screen, then the picture failed
to deliver it. TikTok's auto-suggested search for the video was "water under
microscope": its classifier read the dark circle with specks as microscopy.

Measured on the three posted finals:

| video | mean luma Y, first 3 s | mean luma Y, whole | first spoken word |
|---|---|---|---|
| 001 | 50 / 255 | 55 | — |
| 002 | 71 / 255 | 55 | — |
| 004 | 55 / 255 | 52 | ~1.0 s |

Conclusions, which are now hard requirements:

1. The hook must be a falsifiable claim, spoken and on screen, on frame 0.
2. The phenomenon must be visible, large and moving on frame 0. No mood shot,
   no single object wobbling, no build-up.
3. The frame must be bright and must contain a recognisable everyday object so
   it reads as "kitchen physics", not CGI or microscopy.
4. The video must give the viewer something to do (try it) and something to
   say (a question to answer in comments). Zero comments and zero shares is
   the real gate, not the hook.
5. Shorter: 26–30 s total. Completion rate gates the next distribution batch.

## Topic and physics (keep claims this honest)

The Kaye effect: a thin stream of shampoo (or liquid hand soap) poured from
~20–30 cm onto a heap of itself will, every so often, shoot a jet back out
sideways and upward, as if the liquid is bouncing off itself. Discovered by
Alan Kaye (Nature, 1963). Explained by Versluis, Blom, van der Meer, van der
Weele and Lohse, "Leaping shampoo and the stable Kaye effect", J. Stat. Mech.
(2006).

Mechanism to explain on screen:
- Shampoo is shear-thinning (non-Newtonian): thick when it moves slowly, much
  runnier when sheared fast. Say "roughly ten times thinner" only if you keep
  the "roughly"; the drop depends on the product.
- The incoming stream hits the heap and digs a small dimple. Inside the dimple
  the fluid is sheared very fast, so a thin, low-viscosity layer forms between
  the stream and the heap.
- That layer acts as a lubricated slide: the stream skids along the dimple
  wall instead of merging, and exits as a jet. The jet typically lasts a few
  tenths of a second before the heap shifts and it collapses; on a tilted
  surface it can be made stable (Versluis et al.).
- Newtonian fluids do not do this: honey poured the same way just coils (rope
  coiling). Water splashes. This is the side-by-side comparison.
- Works at home with most shampoos and liquid hand soaps, a thin stream
  (~1–2 mm), from about a hand-span above a plate. Takes a few tries. No
  safety caveat needed beyond "it is messy".

Do not claim a specific viscosity, jet speed or leap height as fact. Round
numbers may appear on screen as bars or labels; the voice says "about".

## Script structure (fill, do not reorder)

~3 words/s at Kokoro `af_heart`, speed 1.06–1.12. Total 26–30 s. No beat
longer than 7 s. Keep these beat ids: `hook`, `compare`, `why1`, `why2`,
`tryit`, `ask`, `loop`.

1. `hook` (0–2.5 s). Claim, on frame 0, voice on frame 0. Candidates, pick
   the one that reads best on screen in 3 words per chunk:
   - "Shampoo can bounce off itself."
   - "Pour shampoo slowly enough and it jumps back out."
   - "This liquid is bouncing off itself."
   Footage: the jet already in the air on frame 0, mid-leap, wide enough to
   see bottle, stream, heap, plate and jet. Headline text on screen from
   frame 0 for the whole beat.
2. `compare` (~5 s). "Honey coils. Water splashes. Shampoo leaps." Split-screen
   (use the `bg_plan` `split` mechanism from 004) or three quick cuts; the
   shampoo panel must be the one that moves most.
3. `why1` (~6 s). Shear-thinning in one sentence plus one graphic: a simple
   "thick when slow / thin when fast" bar or curve, each symbol or label
   lit as it is spoken (use `wordTime`).
4. `why2` (~6 s). The dimple, the thin fast layer, the slide, the jet. A
   cutaway diagram over the footage, labels appearing on the spoken word.
5. `tryit` (~4 s). "Try it: a plate, a bottle of shampoo, pour a thin stream
   from a hand-span up. It takes a few tries." Footage: the leap again from a
   different angle.
6. `ask` (~3 s). Spoken question that invites a one-word answer: "Which
   shampoo worked for you?" or "Does yours bounce?" On screen: the question
   plus a small "follow for the next one". No separate 3 s CTA beat.
7. `loop` (1–1.5 s, no lines). Footage that lands visually on the exact
   frame-0 composition so the video loops without a visible seam. Rewatches
   count.

## Visual direction (hard requirements)

- Bright set. Target mean luma Y ≥ 110/255 over the first 3 s and ≥ 90/255
  over the whole video (measure with ffmpeg `signalstats` YAVG, as in the
  table above). White or pale ceramic plate, light grey or warm cream
  backdrop, warm key light plus soft fill. No black backgrounds anywhere,
  including 2D explainer beats: paint a light panel.
- Recognisable objects: a real-looking shampoo bottle (generic, no brand) or
  a clear pump bottle, the plate, a hint of counter or table edge. The viewer
  must be able to name the scene in 0.5 s.
- Fluid is opaque and glossy, pearlescent white or pale pastel (Principled,
  high specular, low roughness, no transmission, no subsurface). This is also
  why the scene should render cheaply: no glass, no refraction.
- Kinematic, not simulated, as in video 002: stream = bevelled curve with a
  slow sine wobble and slight necking; heap = dome whose height grows and
  settles; dimple = small depression at the impact point; jet = bevelled
  curve whose profile is a parabola from the dimple, animated in with
  `bevel_factor_end`, thinning along its length, lifetime ~0.3 s real time.
  Honey panel: rope coiling (helix of a thick curve). Water panel: a thin
  stream plus spreading puddle and a few splash droplets.
- Run at 4x slow motion so the jet is readable and label it "SLOW MOTION 4x"
  on screen while slow footage plays, as video 002 did. Use real-time for the
  `tryit` beat if it still reads.
- Scale: 1 unit = 1 cm (see video 004 notes). Camera f/4 or slower, focus on
  the impact point. Motion blur on, shutter 0.5.
- Captions: existing style (Inter 900, uppercase, 3 words per chunk, active
  word yellow). Keep the headline band at the top as in 004. Stay inside the
  safe area.

## Production constraints

- The container is fresh: `/home/user/tools` is empty and `kokoro-onnx` is
  not installed. Reinstall per README (pip packages, Kokoro model files,
  Blender 4.5 LTS download) before anything else.
- 30 fps. Render at 720x1280 and lanczos-upscale to 1080x1920 (AGENTS.md).
  Time three consecutive frames per shot before committing; stay under
  ~5 h of total render. If a shot exceeds 12 s/frame at 720, drop to 576 wide
  or cut samples, not the brightness or the composition.
- Reuse shots behind explainer panels rather than rendering unique footage
  for every beat. Do not reuse any frames from videos 001–004.
- Follow the AGENTS.md workflow: `tts.py` first and read the beat durations;
  `--preview` single frames per shot until the look passes the checks below;
  `--every 30` contact sheet of overlays before full render; `assemble.py
  --preview` early for pacing; full render through the harness background
  runner so a restart does not lose it; frame-skip resume.
- Sound: existing procedural stack. Add a wet "splat" on the impact, a short
  rising "boing"-free whoosh on each leap (no cartoon sounds), ding on labels,
  whoosh on cuts. Music bed at about −20 dB, VO ~8 dB above everything,
  loudnorm −14 LUFS as before.

## Acceptance checks (run all, report the numbers)

1. Export frame 0 as PNG and look at it. It must show: the jet in the air,
   the bottle, the plate, the headline text. If any is missing, fix it before
   rendering anything else.
2. First spoken word onset ≤ 0.3 s (ffmpeg `astats`, 50 ms windows, RMS
   > −20 dB on the VO stem, not the mix).
3. Mean luma: first 3 s ≥ 110, whole ≥ 90 (ffmpeg `signalstats` YAVG).
4. Duration 26–30 s; no beat over 7 s; the `loop` beat's last frame matches
   frame 0's composition.
5. Contact sheet at 1 frame/s reviewed by you: every frame must have either
   motion in the fluid or a label appearing. No frame may be mostly black.
6. Spoken numbers carry "about"; no claim outside the physics section above.
7. Captions never cross the TikTok UI zones (x 60..1020, y 250..1500).

## Deliverables

- `videos/005-kaye-effect/out/final.mp4` (1080x1920, 30 fps, −14 LUFS)
- `videos/005-kaye-effect/out/final_nocaptions.mp4`
- `videos/005-kaye-effect/out/cover.png`: the frame to upload as the cover,
  with the headline on it
- `videos/005-kaye-effect/out/post.txt`: one caption line that is a question
  (e.g. "Does your shampoo bounce? Try it and tell me which one."), then
  hashtags: `#physics #science #sciencetok #learnontiktok #shampoo`. Do not
  use #infographic or #woah.
- `videos/005-kaye-effect/out/checks.txt`: the measured numbers from the
  acceptance checks
- A "Video 005 notes" section in AGENTS.md in the style of the existing ones
- Commit the four source files, the scene script, the notes, the cover,
  post.txt and final.mp4 (keep build/ and stems out, as .gitignore does).
