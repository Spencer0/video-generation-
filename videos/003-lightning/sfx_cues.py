"""Sound cues for video 003 (lightning). Called by pipeline/sfx.py."""
import numpy as np
from audiolib import *

def crack(d=0.9, body=2.6):
    """Close thunder: sharp white crack, then a long low rumble."""
    c = bandpass_fast(noise(d), 600, 9000); t = t_axis(d); c *= np.exp(-t / 0.09) * np.minimum(1, t / 0.004)
    r = lowpass_fast(noise(body), 160); tr = t_axis(body); r *= np.exp(-tr / 0.9) * np.minimum(1, tr / 0.05) * (1 + 0.5 * lowpass_fast(noise(body), 4))
    out = np.zeros(int(body * SR)); out[:len(c)] += c / (np.abs(c).max() + 1e-9) * 1.0; out += r / (np.abs(r).max() + 1e-9) * 0.9
    return out
def rumble(d=2.2, fc=120):
    r = lowpass_fast(noise(d), fc); t = t_axis(d); return r / (np.abs(r).max() + 1e-9) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.6
def crackle(d, rate, rng, lo=2500, hi=9000):
    out = np.zeros(int(d * SR)); t = 0.0
    while t < d:
        t += rng.exponential(1 / rate); n = bandpass_fast(noise(0.02), lo, hi) * env_exp(0.02, 0.004); place(out, n, t, rng.uniform(0.3, 1.0))
    return out
def hum(d, f0=55, f1=140, harm=(1, 2, 3, 5)):
    t = t_axis(d); f = f0 * (f1 / f0) ** (t / d); ph = 2 * np.pi * np.cumsum(f) / SR
    o = sum(np.sin(h * ph) / h for h in harm); return o / (np.abs(o).max() + 1e-9) * (t / d) ** 1.5

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(21)
    # --- rain + wind under every 3D beat
    rain = bandpass_fast(noise(D), 1500, 9000); wind = lowpass_fast(noise(D), 220) * (1 + 0.6 * lowpass_fast(noise(D), 0.5))
    ta = t_axis(D); env = np.zeros_like(ta)
    for bid in ("flash", "hook", "streamer", "return", "flicker", "cta"):
        b = B[bid]; env += np.clip((ta - b["start"] + 0.3) / 0.5, 0, 1) * np.clip((b["end"] - ta + 0.3) / 0.5, 0, 1)
    env = np.clip(env, 0, 1)
    place(sfx, rain / (np.abs(rain).max() + 1e-9) * env, 0, 0.16); place(sfx, wind / (np.abs(wind).max() + 1e-9) * env, 0, 0.22)
    # --- strikes: (beat, offset of the return stroke in the beat's footage), re-strikes follow the scene timing
    def strike_at(t, gain=1.0, restrikes=True):
        place(sfx, crack(), t - 0.01, 1.0 * gain)
        if restrikes:
            for dt, a in ((0.6, 0.55), (1.0, 0.4), (1.3, 0.3)): place(sfx, crack(0.5, 1.4), t + dt, a * gain)
    strike_at(B["flash"]["start"] + 10 / 24); strike_at(B["streamer"]["start"] + 4.0, 1.0); strike_at(B["return"]["start"] + 7 / 24)
    strike_at(B["flicker"]["start"] + 3 / 24, 0.9)
    # leader crackle before each strike (hook: leader descends in the last 1.7 s of the footage; streamer: last 2 s)
    h = B["hook"]; place(sfx, crackle(1.7, 25, rng), h["start"] + 2.4, 0.35); place(sfx, hum(1.7, 50, 120), h["start"] + 2.4, 0.12)
    st = B["streamer"]; place(sfx, crackle(2.0, 30, rng), st["start"] + 2.0, 0.4); place(sfx, hum(2.0, 50, 160), st["start"] + 2.0, 0.14)
    # distant cloud flickers in the hook footage (scene flickers at 0.7, 1.6, 3.3 s, thunder delayed)
    for dt, a in ((0.7, 0.5), (1.6, 0.35), (3.3, 0.25)): place(sfx, rumble(2.0), h["start"] + dt + 0.35, 0.5 * a)
    # --- 2D explainer beats
    c = B["cloud"]
    for k in range(40): place(sfx, tick(rng.uniform(2500, 5000), 0.015), rng.uniform(c["start"] + 1.0, c["end"]), rng.uniform(0.05, 0.14))
    place(sfx, whoosh(0.8, 200, 2500, rev=True), W("cloud", "updrafts") - 0.1, 0.3)
    ch = B["charge"]
    for wd, f in (("positive", 1760), ("negative", 880), ("ground", 1318)): place(sfx, ding(f, 0.5), W("charge", wd), 0.35)
    place(sfx, ding(2093, 0.7), W("charge", "positive", 1), 0.4)
    f = B["field"]; place(sfx, hum(W("field", "insulator") - f["start"] - 0.2, 45, 180, (1, 2, 3, 4, 6)), f["start"] + 0.2, 0.22)
    place(sfx, crackle(1.2, 12, rng), W("field", "insulator"), 0.25); place(sfx, crack(0.4, 0.9), W("field", "isn't") + 0.15, 0.6)
    L = B["leader"]; t = L["start"] + 0.4
    while t < L["end"] - 0.3:
        place(sfx, tick(rng.uniform(3000, 7000), 0.02), t, 0.35); place(sfx, bandpass_fast(noise(0.05), 2000, 8000) * env_exp(0.05, 0.012), t, 0.2); t += 0.11
    place(sfx, hum(L["end"] - L["start"] - 0.8, 40, 90), L["start"] + 0.4, 0.10)
    r = B["return"]; place(sfx, whoosh(0.5, 300, 5000, rev=True), W("return", "races") - 0.2, 0.5); place(sfx, ding(1760, 0.6), W("return", "third"), 0.3)
    place(sfx, whoosh(0.35, 400, 6000), W("return", "going"), 0.4)
    hb = B["heat"]; place(sfx, hum(1.2, 60, 400, (1, 2, 3)), hb["start"] + 0.2, 0.2); place(sfx, crack(0.5, 2.4), W("heat", "explodes"), 0.8)
    place(sfx, thud(45, 0.6), W("heat", "thunder"), 0.9)
    th = B["thunder"]; t0 = W("thunder", "count")
    for k in range(3): place(sfx, tick(1200, 0.08), t0 + 0.5 + k * 0.75, 0.5)
    place(sfx, rumble(1.8, 100), W("thunder", "bang"), 0.6); place(sfx, ding(1568, 0.8), W("thunder", "kilometers"), 0.4)
    fl = B["flicker"]
    for k in range(4): place(sfx, crack(0.25, 0.8), W("flicker", "strokes") + 0.6 + k * 0.22, 0.35)
    p = B["payoff"]
    for k in range(18): place(sfx, crack(0.2, 0.7), rng.uniform(p["start"] + 0.2, p["end"]), rng.uniform(0.08, 0.25))
    for bid in ("hook", "cloud", "charge", "field", "leader", "streamer", "return", "heat", "thunder", "flicker", "payoff", "cta"):
        place(sfx, whoosh(0.32), B[bid]["start"] - 0.18, 0.4)
    place(sfx, ding(1046, 1.2), W("cta", "follow"), 0.55)
    # --- music: darker pad, 92 bpm, riser into the big strike
    bpm = 92; beat = 60 / bpm; chords = [(52, 55, 59, 62), (48, 52, 55, 59), (50, 53, 57, 60), (47, 50, 54, 57)]
    def note(f, d, a=0.5, det=0.004):
        tt = t_axis(d); o = np.zeros_like(tt)
        for k, dd in ((1, 1 - det), (1, 1 + det), (0.5, 1), (0.25, 2)): o += k * np.sin(2 * np.pi * f * dd * tt)
        return o * np.minimum(1, tt / a) * np.minimum(1, (d - tt) / 0.6)
    tt = 0.0; ci = 0
    while tt < D:
        d = beat * 4
        for m in chords[ci % 4]: place(music, note(440 * 2 ** ((m - 69) / 12), d), tt, 0.09)
        ci += 1; tt += d
    music[:] = lowpass_fast(music, 1400)
    tt = 0.0; k = 0
    while tt < D:
        lvl = 0.5 + 0.5 * min(1, max(0, (tt - B["cloud"]["start"]) / 12))
        if k % 2 == 0: place(music, thud(49, 0.25), tt, 0.4 * lvl)
        place(music, tick(6000, 0.03) * 0.5 + bandpass_fast(noise(0.03), 5000, 12000) * 0.3 * env_exp(0.03, 0.008), tt, 0.09 * lvl)
        tt += beat; k += 1
    place(music, whoosh(2.2, 150, 4000, rev=True), B["streamer"]["start"] + 1.8, 0.9)
