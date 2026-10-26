"""Sound cues for video 002 (chain fountain). Called by pipeline/sfx.py.
Slow-motion picture (4x), so the chain sound is a pitched-down, dense metallic
rattle whose density follows the chain speed, plus a continuous hiss of beads
sliding over the glass rim."""
import numpy as np
from audiolib import *

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(11)
    t_release = B["hook"]["start"] + 3.8            # scene_chain.py T_RELEASE (the tug)
    fl = B["flash"]
    def speed(t):                                   # mirrors scene_chain.speed(), normalized 0..1; flash-forward is at full speed
        if fl["start"] <= t < fl["end"]: return 1.0
        u = max(0.0, min(1.0, (t - t_release) / 4.5)); return u * u * (3 - 2 * u)
    # bead rattle: random metallic clicks, density ~ speed, slightly pitched down for slow-mo
    t = 0.0
    while t < D:
        r = 4 + 110 * speed(t)
        t += min(rng.exponential(1 / r), 0.05)
        if rng.random() > speed(t) * 0.9 + 0.1: continue
        f = rng.uniform(1800, 5200); d = rng.uniform(0.012, 0.03)
        tt = t_axis(d); click = np.sin(2 * np.pi * f * tt) * np.exp(-tt / (d * 0.25)) + 0.4 * np.sin(2 * np.pi * f * 2.3 * tt) * np.exp(-tt / (d * 0.15))
        place(sfx, click, t, rng.uniform(0.05, 0.16))
    # glass rim hiss + low rumble rising with speed
    hiss = bandpass_fast(noise(D), 2500, 9000); rum = lowpass_fast(noise(D), 180)
    ta = t_axis(D); env = np.interp(ta, np.arange(0, D, 0.1), [speed(x) for x in np.arange(0, D, 0.1)])
    place(sfx, hiss / (np.abs(hiss).max() + 1e-9) * env, 0, 0.10); place(sfx, rum / (np.abs(rum).max() + 1e-9) * env, 0, 0.25)
    # beads landing on the floor: softer patter, delayed by the fall
    t = t_release + 1.2
    while t < D:
        t += rng.exponential(1 / (3 + 40 * speed(t)))
        place(sfx, tick(rng.uniform(900, 2200), 0.02), t, rng.uniform(0.03, 0.08))
    # release: a glass "tink" and a short slide
    place(sfx, ding(2093, 0.5), t_release - 0.05, 0.35); place(sfx, whoosh(0.4, 800, 6000), t_release, 0.3)
    # cuts and stamps
    for bid in ("hook", "kick", "equation", "scale", "cta"): place(sfx, whoosh(0.32), B[bid]["start"] - 0.18, 0.45)
    place(sfx, thud(70, 0.5), B["hook"]["start"], 0.8); place(sfx, ding(1760, 0.6), W("flash", "on"), 0.4)
    place(sfx, shimmer(0.6), W("reversal", "lifts") - 0.5, 0.35); place(sfx, ding(1568, 1.0), W("reversal", "lifts") + 0.05, 0.6)
    place(sfx, thud(80, 0.4), W("reversal", "how"), 0.7); place(sfx, shimmer(0.5), W("reversal", "how") - 0.45, 0.3)
    for wd in ("yanks", "kicks"): place(sfx, whoosh(0.3, 300, 2500), W("kick", wd), 0.35)
    place(sfx, thud(90, 0.4), W("kick", "back"), 0.7); place(sfx, ding(1318, 0.8), W("kick", "back") + 0.02, 0.4)
    place(sfx, tick(1500, 0.1), W("equation", "alpha"), 0.5); place(sfx, ding(1760, 0.8), W("equation", "eighth"), 0.45)
    place(sfx, whoosh(0.5, 400, 3000), W("scale", "meters"), 0.3); place(sfx, whoosh(0.7, 300, 3000), W("scale", "balcony"), 0.4)
    place(sfx, ding(2093, 0.9), W("scale", "tall"), 0.45)
    place(sfx, ding(1046, 1.2), W("cta", "follow"), 0.55)
    # music bed: same pad language as 001, a touch brighter, 100 bpm
    bpm = 100; beat = 60 / bpm; chords = [(57, 60, 64, 67), (53, 57, 60, 64), (55, 59, 62, 65), (52, 55, 59, 62)]
    def note(f, d, a=0.4, det=0.004):
        tt = t_axis(d); o = np.zeros_like(tt)
        for k, dd in ((1, 1 - det), (1, 1 + det), (0.5, 1), (0.25, 2)): o += k * np.sin(2 * np.pi * f * dd * tt)
        return o * np.minimum(1, tt / a) * np.minimum(1, (d - tt) / 0.6)
    tt = 0.0; ci = 0
    while tt < D:
        d = beat * 4
        for m in chords[ci % 4]:
            place(music, note(440 * 2 ** ((m - 69) / 12), d), tt, 0.09)
        ci += 1; tt += d
    music[:] = lowpass_fast(music, 1600)
    tt = 0.0; k = 0
    while tt < D:
        lvl = 0.5 + 0.5 * min(1, max(0, (tt - B["reversal"]["start"]) / 10))
        if k % 2 == 0: place(music, thud(52, 0.25), tt, 0.45 * lvl)
        place(music, tick(6000, 0.03) * 0.6 + bandpass_fast(noise(0.03), 5000, 12000) * 0.3 * env_exp(0.03, 0.008), tt, 0.10 * lvl)
        tt += beat; k += 1
