# Brief and notes: video 006, how a forest is born (120-year succession timelapse)

Request: "Viral TikTok video 'how a forest is born', detailed 3D timelapse start to
finish." Produced end to end in this repo: `script.json`, `beats.js`,
`sfx_cues.py`, the scene `pipeline/blender/scene_forest.py`, `out/final.mp4`.

## Format decision (from the guide the request pointed at)

Theo (@theoxmotion) collected the free Claude Code video formats on 2026-11-01;
the proven one for "dirt becomes X" is the You Built It format (58.6M TikTok
views in 19 days; "a strip of dirt that becomes a road" alone has 5.3M): a block
of land cut open like a cake so the underground shows in section, a calm fast
narrator, captions on the spoken word, a camera that moves in every shot and
cuts every 2 to 3 s, action on frame 1, photo textures on anything big, natural
shapes for natural things, nothing floating. His rebuilt kit:
https://github.com/Theoxmotion/whatif-3d-studio (`whatif_guide.md`). What this
video takes from it:

- The soil block: 24 x 16 x 8 m, cut face toward the camera, so the topsoil band
  thickening and roots growing are part of the picture, not a diagram.
- One framing per beat (ten shots), each gliding; two beats get a mid-beat cut.
- Frame 0 has the claim on screen, the clock ticking, seeds blowing in.
- Poly Haven CC0 textures (1k) for the soil wall, bare dirt, grass, forest floor
  and three barks; procedural foliage, bark detail and sky.
- His seven rater rows (hook, premise, look, motion, captions, voice, pacing)
  are the by-eye checklist at the bottom.

Kept from this repo's own analytics (005 brief): bright frame (Y >= 110 first
3 s), claim spoken and on screen on frame 0, something to do and something to
answer, loop seam, UI safe zones, 7 s max per beat.

## Science (old-field secondary succession; keep claims this honest)

Ecological succession on abandoned ground in a temperate humid climate (the
classic eastern North American "old field" sequence, Oosting 1942, Odum 1969,
Keever 1950 on the Piedmont):

- **Year 1, annual weeds.** Crabgrass, horseweed, ragweed; wind-dispersed seeds
  already in the seed bank or blown in; shade-intolerant; live one season.
- **Years 2 to 10, perennial grasses and forbs** (broomsedge, asters,
  goldenrod). Dead leaves and roots add organic matter; the dark A horizon
  (topsoil) thickens. On the section the band is exaggerated to ~1 m by year 120
  so it reads at phone size; real rates are a few millimetres a decade and the
  VO says only "richer soil", no number.
- **Years 10 to 25, shrubs** (sumac, blackberry, dogwood), largely
  bird-dispersed (fleshy fruit), the first real shade.
- **Years 15 to 60, pioneer trees**: birch, aspen, pine (loblolly, white pine).
  Fast, shade-intolerant: their own seedlings cannot establish under the
  closed canopy ("they can't grow in shade, not even their own" is the textbook
  statement). Self-thinning and 40 to 70 year lifespans for birch; pines live
  longer in reality (the model kills them on the same schedule, a
  simplification that is not spoken).
- **Years 60 to 150+, shade-tolerant hardwoods**: oak, hickory, maple, beech
  germinate under the pioneers, grow slowly, overtop them and take over; the
  pioneers die out. "The forest is born" at year 100 is the start of that
  takeover, not a finished climax (oak-hickory forests keep changing for
  centuries); the counter runs to 128 and the VO says "year one hundred".
- "Each stage changes the ground, kills the stage before it, and makes room for
  the next": facilitation and inhibition (Connell & Slatyer 1977) condensed;
  honest as a one-line summary.
- "Every empty lot is on this clock": true for humid temperate climates with a
  seed source nearby; deserts and polluted brownfields follow other paths.
  Primary succession on bare rock or lava (lichens, moss) is a different, much
  slower story and is not what the video shows (the block starts as soil).

Numbers spoken: year one / five / fifteen / thirty / one hundred (written as
words for Kokoro). None are presented as precise.

## Model (what the scene does, all pure functions of the year)

- Plants: 900 annual weeds (live 1 yr), 1700 grass tufts, 560 wildflowers
  (bloom once a year, Object colour alpha), 110 shrubs, 150 pioneers (60 %
  birch, 40 % pine), 34 climax trees (oak / maple). Deaths from shade are
  computed once with numpy: crown cover = sum of exp(-(d / r)^2) over trees
  taller than the victim; grass dies above 0.55, weeds/flowers 0.45, shrubs 0.7,
  pioneers 0.5 from climax trees at least 1 m taller, plus self-thinning and age.
- A dying pioneer: crown browns (1.8 yr), crown gone (1.6 yr), stands dead and
  grey (to +4 yr), falls over 1.2 yr about a random horizontal axis, the log
  sinks and shrinks into the litter (to +12 yr). 98 falls; sfx thins them to one
  per 0.35 s.
- Ground: one material; Normal.z picks top (dirt -> grass -> litter by GRASS /
  LITTER values with patchy noise) or the cut face (soil wall texture, topsoil
  band = TOPSOIL metres with a noisy edge and pale root streaks, stones at
  depth). Roots are POLY curves at y = -0.05 (just in front of the face) grown
  with bevel_factor_end for the 13 trees within 1.3 m of the face.
- Clock: script.json "years" per beat; the ask + loop beats rewind with a
  quintic ease so the last frame is year 0 with the hook's camera pose (loop).

## Render

576x1024, 8 samples adaptive, OIDN, 3 bounces (1 diffuse), Standard view
transform at -0.6 EV (AgX muted the sky to grey and greens to pastel; measured
on a frame, see AGENTS.md). ~13 s/frame average on 4 cores (20 s for the
low-angle DoF shot, 12 s for wides). 1192 frames.

## By-eye checklist (the rater rows)

- Hook: claim on frame 0, clock ticking, seeds in the air, sprouts by 0.5 s.
- Premise: five real stages with named parts, the "huh" (pioneers die in their
  own shade), one question to answer.
- Look: textures on the block and barks, lumpy foliage, nothing floats (roots
  attach at the trunk base, logs lie on the top, stones half buried).
- Motion: camera glides in every shot, 11 cuts in 40 s, the timelapse itself.
- Captions: 58 px at y 1430, word-synced, inside the UI safe area (checked).
- Voice: Kokoro af_heart 1.1, onset ~0.1 s, ends 0.8 s before the end.
- Pacing: no beat over 6.5 s, no still over 1 s (the loop hold is 0.8 s with
  cloud shadows moving).
