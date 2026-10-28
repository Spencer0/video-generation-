# video-generation

Code-generated short-form STEM videos. First video: **water in a plastic bag
over an open flame** (`videos/001-water-bag`).

## One-time setup (cloud container)

```bash
# Blender 4.5 LTS (CPU Cycles), ~350 MB
mkdir -p /home/user/tools && cd /home/user/tools && \
  curl -L -o b.tar.xz https://download.blender.org/release/Blender4.5/blender-4.5.15-linux-x64.tar.xz && \
  tar xJf b.tar.xz && rm b.tar.xz
# TTS + audio + overlay deps
pip install kokoro-onnx soundfile playwright
mkdir -p /home/user/tools/kokoro && cd /home/user/tools/kokoro && \
  curl -L -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx && \
  curl -L -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

## Build video 001

```bash
export BLENDER=/home/user/tools/blender-4.5.15-linux-x64/blender
python3 pipeline/tts.py 001-water-bag                      # voiceover + timeline.json
python3 pipeline/sfx.py 001-water-bag                      # sound design + mix
python3 pipeline/overlays/render_overlays.py 001-water-bag # captions/graphics PNGs
bash pipeline/blender/render_all.sh 001-water-bag          # 3D shots (hours on CPU; resumable)
python3 pipeline/assemble.py 001-water-bag                 # -> videos/001-water-bag/out/final.mp4
```

`assemble.py --preview` works at any point during the 3D render (missing
frames are substituted) so you can check pacing early.

## Build video 005 (Kaye effect) — same five commands, plus the checks

```bash
python3 pipeline/tts.py 005-kaye-effect && python3 pipeline/sfx.py 005-kaye-effect
python3 pipeline/overlays/render_overlays.py 005-kaye-effect
python3 pipeline/overlays/render_overlays.py 005-kaye-effect --no-captions --out videos/005-kaye-effect/build/overlay_nocap
bash pipeline/blender/render_all.sh 005-kaye-effect 576 12       # ~2 h on 4 cores; resumable
python3 pipeline/assemble.py 005-kaye-effect
python3 pipeline/assemble.py 005-kaye-effect --overlay-dir overlay_nocap --out videos/005-kaye-effect/out/final_nocaptions.mp4
python3 pipeline/checks.py 005-kaye-effect                        # -> out/checks.txt
```

See `AGENTS.md` for the design decisions, measured render costs and the
conventions that make the pieces line up.
