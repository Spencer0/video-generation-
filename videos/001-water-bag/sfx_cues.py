"""Sound cues for video 001 (water bag over flame). Called by pipeline/sfx.py."""
import numpy as np
from audiolib import *

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(3)
    # --- burner: lit from hook ignition until the end (cuts keep it continuous)
    t_ign = B["hook"]["start"] + 2.45 - B["hook"].get("bg_offset", 0) / tl["fps"]   # shot A ignites at 2.45 s of footage
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
        if t < B["water"]["end"]:
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
    for bid in ("empty", "water", "temps", "equation", "punch", "noodles", "cta"): place(sfx, whoosh(0.32), B[bid]["start"] - 0.18, 0.45)
    place(sfx, whoosh(0.5, 200, 2500, rev=True), t_ign - 0.5, 0.3)
    place(sfx, ding(), W("water", "impossible") + 0.05, 0.6); place(sfx, thud(80, 0.4), W("water", "how"), 0.7); place(sfx, shimmer(0.5), W("water", "how") - 0.45, 0.3)
    for i, wd in enumerate(("flame", "plastic", "never")):
        at = W("temps", wd); place(sfx, whoosh(0.5, 400, 3000), at, 0.25); place(sfx, tick(900 + 300 * i, 0.08), at + 0.75, 0.3)
    place(sfx, thud(90, 0.4), W("ceiling", "boils"), 0.6); place(sfx, tick(1200, 0.08), W("ceiling", "boils") + 0.02, 0.4)
    place(sfx, ding(1760), W("punch", "twenty"), 0.5); place(sfx, thud(60, 0.5), W("punch", "cannot"), 0.9)
    place(sfx, tick(1500, 0.1), W("equation", "thin"), 0.5); place(sfx, ding(1568, 0.8), W("ceiling", "joule"), 0.4)
    place(sfx, ding(1318, 0.9), B["noodles"]["start"] + 0.15, 0.5); place(sfx, thud(70, 0.4), W("noodles", "bag") + 0.02, 0.6)
    place(sfx, ding(1046, 1.2), W("cta", "follow"), 0.55)
    # steam hiss burst
    st = W("ceiling", "steam"); sh = bandpass_fast(noise(1.2), 2000, 8000); sh *= np.exp(-t_axis(1.2) / 0.5); place(sfx, sh / (np.abs(sh).max() + 1e-9), st, 0.25)
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
