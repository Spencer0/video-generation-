#!/usr/bin/env python3
"""Procedural sound design + music bed, mixed with the voiceover.

usage: python3 pipeline/sfx.py <video_id>
Writes build/sfx.wav, build/music.wav and build/mix.wav (48 kHz stereo).

Everything is synthesized with numpy from the timeline so it stays in sync
with the picture: burner roar from ignition on, bubble pops that follow the
boil ramp, a sizzle under the melt, whooshes on the cuts, soft ticks on
caption chunks and UI stamps, and a low pulsing synth bed ducked under the VO.
"""
import sys, os, json, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import load_json, video_dir
SR = 48000
rng = np.random.default_rng(3)

def t_axis(d): return np.arange(int(d * SR)) / SR
def env_exp(d, tau): t = t_axis(d); return np.exp(-t / tau)
def place(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i < 0: sig = sig[-i:]; i = 0
    n = min(len(sig), len(buf) - i)
    if n > 0: buf[i:i + n] += sig[:n] * gain
def lowpass(x, fc):  # one-pole, applied twice
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    for _ in range(2):
        for i in range(len(x)): acc = a * acc + (1 - a) * x[i]; y[i] = acc
        x = y.copy()
    return y
def lowpass_fast(x, fc):
    from numpy.fft import rfft, irfft
    X = rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / (1 + (f / fc) ** 4); return irfft(X, len(x))
def highpass_fast(x, fc):
    from numpy.fft import rfft, irfft
    X = rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= (f / fc) ** 2 / (1 + (f / fc) ** 2); return irfft(X, len(x))
def bandpass_fast(x, lo, hi): return highpass_fast(lowpass_fast(x, hi), lo)
def noise(d): return rng.standard_normal(int(d * SR))

def bubble_pop(f0=900, d=0.045, sweep=0.55):
    t = t_axis(d); f = f0 * (1 - sweep * t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / (d * 0.3)) * 0.8
def glug(f0=140, d=0.12):
    t = t_axis(d); f = f0 * (1 + 0.8 * t / d); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.04) * 0.9
def whoosh(d=0.35, lo=300, hi=4000, rev=False):
    n = bandpass_fast(noise(d), lo, hi); t = t_axis(d); e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    if rev: e = e ** 0.5 * (t / d)
    else: e = e ** 0.5 * (1 - t / d) ** 0.6
    return n * e / (np.abs(n).max() + 1e-9)
def tick(f=1800, d=0.03): t = t_axis(d); return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006)
def thud(f=70, d=0.35): t = t_axis(d); return np.sin(2 * np.pi * (f * (1 + 0.6 * np.exp(-t / 0.04))) * t) * np.exp(-t / 0.09)
def ding(f=1320, d=0.9):
    t = t_axis(d); return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t / 0.25) * 0.5
def shimmer(d=0.6):  # riser for stamps
    n = bandpass_fast(noise(d), 1500, 9000); t = t_axis(d); return n * (t / d) ** 2 / (np.abs(n).max() + 1e-9)
def clicklighter(): return (bandpass_fast(noise(0.02), 2000, 9000) * env_exp(0.02, 0.004)) * 2.0
def ignite(d=0.6):
    n = lowpass_fast(noise(d), 900); t = t_axis(d); e = np.exp(-t / 0.18) * np.minimum(1, t / 0.02); return n * e / (np.abs(n).max() + 1e-9)

def burner_roar(d, start, ramp=0.4):
    n = lowpass_fast(noise(d), 420) * 0.6 + lowpass_fast(noise(d), 2500) * 0.08
    t = t_axis(d); e = np.clip((t - start) / ramp, 0, 1)
    mod = 1 + 0.18 * lowpass_fast(noise(d), 6)
    return n * e * mod / (np.abs(n).max() + 1e-9)

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
    # --- burner: lit from hook ignition until the end (cuts keep it continuous)
    t_ign = B["hook"]["start"] + 2.45
    place(sfx, clicklighter(), t_ign - 0.22, 0.5)
    place(sfx, ignite(0.7), t_ign - 0.02, 0.9)
    place(sfx, burner_roar(D - t_ign, 0.0, 0.5), t_ign, 0.22)
    # --- melt (empty beat): sizzle + crackle, then a thud on "MELTED"
    e = B["empty"]; m0 = e["start"] + 0.8; m1 = e["start"] + 1.8
    siz = bandpass_fast(noise(1.6), 2500, 9000); tt = t_axis(1.6); siz *= np.sin(np.pi * np.clip(tt / 1.6, 0, 1)) ** 0.7
    place(sfx, siz / (np.abs(siz).max() + 1e-9), m0 - 0.1, 0.25)
    for k in range(60):
        at = rng.uniform(m0, m1 + 0.4); place(sfx, tick(rng.uniform(2500, 6000), 0.012), at, rng.uniform(0.08, 0.25))
    place(sfx, thud(60, 0.5), m1 + 0.08, 0.9); place(sfx, shimmer(0.4), m1 - 0.32, 0.25)
    # --- boil: pops whose rate follows the picture (shot C ramp, then rolling for every later beat)
    def rate_at(t):
        c0 = B["water"]["start"]; tc = t - c0
        if t < c0: return 0.0
        if t < B["temps"]["end"]:
            import math
            def ss(a, b, x): u = max(0, min(1, (x - a) / (b - a))); return u * u * (3 - 2 * u)
            return 0.0 if tc < 1.1 else 3 * ss(1.1, 3.0, tc) + 24 * ss(3.0, 6.0, tc) + 22 * ss(6.0, 8.5, tc)
        return 48.0
    t = B["water"]["start"]
    while t < D:
        r = rate_at(t); t += min(rng.exponential(1 / max(r, 1e-6)), 0.05)
        if r <= 0 or rng.random() > min(1, rate_at(t) / max(r, 1e-6)): continue
        small = rng.random() < 0.75
        place(sfx, bubble_pop(rng.uniform(1200, 2600) if small else rng.uniform(500, 1000), rng.uniform(0.02, 0.05)), t, rng.uniform(0.05, 0.14) * (0.6 if small else 1.0))
        if not small and rng.random() < 0.3: place(sfx, glug(rng.uniform(110, 200)), t, 0.18)
    # simmer bed (soft hiss) rising with the boil
    hiss = bandpass_fast(noise(D), 3000, 9000); ta = t_axis(D)
    env = np.interp(ta, np.arange(0, D, 0.1), [min(1.0, rate_at(x) / 48) for x in np.arange(0, D, 0.1)])
    place(sfx, hiss / (np.abs(hiss).max() + 1e-9) * env, 0, 0.06)
    # --- cuts / stamps / UI
    for bid in ("empty", "water", "sponge", "punch", "cta"): place(sfx, whoosh(0.32), B[bid]["start"] - 0.18, 0.45)
    place(sfx, whoosh(0.5, 200, 2500, rev=True), t_ign - 0.5, 0.3)
    place(sfx, ding(), W("water", "nothing") + 0.05, 0.6)
    for i, wd in enumerate(("flame", "plastic", "fine")):
        at = W("temps", wd); place(sfx, whoosh(0.5, 400, 3000), at, 0.25); place(sfx, tick(900 + 300 * i, 0.08), at + 0.75, 0.3)
    place(sfx, thud(90, 0.4), W("ceiling", "boils"), 0.6); place(sfx, tick(1200, 0.08), W("ceiling", "boils") + 0.02, 0.4)
    place(sfx, ding(1760), W("punch", "twenty"), 0.5)
    place(sfx, ding(1046, 1.2), W("cta", "follow"), 0.55)
    # steam hiss burst
    st = W("ceiling", "steam"); sh = bandpass_fast(noise(1.2), 2000, 8000); sh *= np.exp(-t_axis(1.2) / 0.5); place(sfx, sh / (np.abs(sh).max() + 1e-9), st, 0.25)
    # caption chunk ticks (very subtle)
    words = [w for b in tl["beats"] for l in b["lines"] for w in l["words"]]
    cur = 0
    for i, w in enumerate(words):
        if cur == 0: place(sfx, tick(2400, 0.02), w["start"], 0.07)
        cur += 1
        if w["word"][-1] in ".!?,;:" or cur >= 3: cur = 0
    # --- music bed: minor pad progression + soft pulse, 96 bpm
    bpm = 96; beat = 60 / bpm; chords = [(57, 60, 64, 67), (53, 57, 60, 64), (55, 59, 62, 65), (52, 55, 59, 62)]  # Am7 F C G/E-ish
    def note(f, d, a=0.4, det=0.004):
        tt = t_axis(d); o = np.zeros_like(tt)
        for k, dd in ((1, 1 - det), (1, 1 + det), (0.5, 1), (0.25, 2)): o += k * np.sin(2 * np.pi * f * dd * tt)
        env = np.minimum(1, tt / a) * np.minimum(1, (d - tt) / 0.6); return o * env
    tt = 0.0; ci = 0
    while tt < D:
        d = beat * 4
        for m in chords[ci % 4]:
            f = 440 * 2 ** ((m - 69) / 12); place(music, note(f, d), tt, 0.09)
        ci += 1; tt += d
    music = lowpass_fast(music, 1400)
    # pulse: sub kick on 1 & 3, hat ticks on 8ths, growing in level through the explainer beats
    tt = 0.0; k = 0
    while tt < D:
        lvl = 0.5 + 0.5 * min(1, max(0, (tt - B["water"]["start"]) / 10))
        if k % 2 == 0: place(music, thud(52, 0.25), tt, 0.45 * lvl)
        place(music, tick(6000, 0.03) * 0.6 + bandpass_fast(noise(0.03), 5000, 12000) * 0.3 * env_exp(0.03, 0.008), tt, 0.10 * lvl)
        place(music, tick(6000, 0.02) * 0.4, tt + beat / 2, 0.05 * lvl)
        tt += beat; k += 1
    # --- VO
    vo, vsr = sf.read(tl["vo"]); 
    if vo.ndim > 1: vo = vo.mean(1)
    vo = np.interp(np.arange(0, len(vo) / vsr, 1 / SR), np.arange(len(vo)) / vsr, vo)
    vo = highpass_fast(vo, 80); vo = vo / (np.abs(vo).max() + 1e-9)
    # gentle compression
    vo = np.tanh(vo * 1.6) / np.tanh(1.6)
    vo_buf = np.zeros(N); place(vo_buf, vo, 0, 1.0)
    # duck music + sfx under the voice
    rms = np.sqrt(lowpass_fast(vo_buf ** 2, 8).clip(0)); duck = 1 - 0.55 * np.clip(rms / (rms.max() + 1e-9) * 3, 0, 1)
    sfx = np.tanh(sfx * 1.2); music = music / (np.abs(music).max() + 1e-9)
    mix = vo_buf * 0.95 + sfx * 0.42 * (0.7 + 0.3 * duck) + music * 0.12 * duck
    # fade out tail
    fo = np.ones(N); nf = int(0.6 * SR); fo[-nf:] = np.linspace(1, 0, nf); mix *= fo
    mix = mix / max(1.0, np.abs(mix).max() / 0.98)
    st = np.stack([mix, mix], 1)
    bd = os.path.join(vd, "build")
    sf.write(os.path.join(bd, "sfx.wav"), sfx, SR); sf.write(os.path.join(bd, "music.wav"), music, SR); sf.write(os.path.join(bd, "mix.wav"), st, SR)
    print(f"mix {D:.1f}s written: peak {np.abs(mix).max():.2f}")

if __name__ == "__main__":
    main(sys.argv[1])
