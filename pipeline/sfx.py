#!/usr/bin/env python3
"""Mix voiceover + per-video sound cues + music into build/mix.wav (48 kHz stereo).

usage: python3 pipeline/sfx.py <video_id>
Cues live in videos/<id>/sfx_cues.py as `cues(tl, B, W, sfx, music, D, N)`:
write into the `sfx` and `music` buffers with audiolib.place(); W(beat, word)
returns the spoken time of a word, B[beat] the beat dict. Everything is
synthesized with numpy from the timeline so it stays in sync with the picture.
"""
import sys, os, importlib.util, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import load_json, video_dir
from audiolib import *

def main(video_id):
    vd = video_dir(video_id); tl = load_json(os.path.join(vd, "build", "timeline.json"))
    B = {b["id"]: b for b in tl["beats"]}
    D = tl["duration"] + 0.5; N = int(D * SR)
    sfx = np.zeros(N); music = np.zeros(N)
    def W(beat, word, nth=0):
        n = 0
        for l in B[beat]["lines"]:
            for w in l["words"]:
                if "".join(ch for ch in w["word"].lower() if ch.isalnum() or ch == "'") == word:
                    if n == nth: return w["start"]
                    n += 1
        return B[beat]["start"]
    spec = importlib.util.spec_from_file_location("sfx_cues", os.path.join(vd, "sfx_cues.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.cues(tl, B, W, sfx, music, D, N)
    # caption chunk ticks (very subtle), same chunking rule as the overlay
    words = [w for b in tl["beats"] for l in b["lines"] for w in l["words"]]
    cur = 0
    for w in words:
        if cur == 0: place(sfx, tick(2400, 0.02), w["start"], 0.07)
        cur += 1
        if w["word"][-1] in ".!?,;:" or cur >= 3: cur = 0
    # --- VO
    vo, vsr = sf.read(tl["vo"])
    if vo.ndim > 1: vo = vo.mean(1)
    vo = np.interp(np.arange(0, len(vo) / vsr, 1 / SR), np.arange(len(vo)) / vsr, vo)
    vo = highpass_fast(vo, 80); vo = vo / (np.abs(vo).max() + 1e-9)
    vo = np.tanh(vo * 1.6) / np.tanh(1.6)
    vo_buf = np.zeros(N); place(vo_buf, vo, 0, 1.0)
    rms = np.sqrt(lowpass_fast(vo_buf ** 2, 8).clip(0)); duck = 1 - 0.55 * np.clip(rms / (rms.max() + 1e-9) * 3, 0, 1)
    sfx = np.tanh(sfx * 1.2); music = music / (np.abs(music).max() + 1e-9)
    mix = vo_buf * 0.95 + sfx * 0.42 * (0.7 + 0.3 * duck) + music * 0.12 * duck
    fo = np.ones(N); nf = int(0.6 * SR); fo[-nf:] = np.linspace(1, 0, nf); mix *= fo
    mix = mix / max(1.0, np.abs(mix).max() / 0.98)
    bd = os.path.join(vd, "build")
    sf.write(os.path.join(bd, "sfx.wav"), sfx, SR); sf.write(os.path.join(bd, "music.wav"), music, SR)
    sf.write(os.path.join(bd, "mix.wav"), np.stack([mix, mix], 1), SR)
    print(f"mix {D:.1f}s written: peak {np.abs(mix).max():.2f}")

if __name__ == "__main__":
    main(sys.argv[1])
