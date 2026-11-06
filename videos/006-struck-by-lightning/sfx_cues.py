"""Sound cues for video 006 (struck by lightning, and lived). Called by pipeline/sfx.py.
Strike times follow pipeline/blender/scene_struck.py (H_STRIKES etc.) mapped through script.json bg_plan."""
import numpy as np
from audiolib import *

H_STRIKES = [0.0, 3.62, 4.55, 5.78, 6.72, 7.36, 8.30]; H_ROY0 = 78 / 24
G_STRIKE, G_RAISE0 = 1.40, 3.95
F_STRIKE, F_SHOES = 1.95, 6.70
R_STRIKE, R_LEG0, R_LEG1 = 1.38, 3.85, 5.05

def crack(d=0.9, body=2.6):
    c = bandpass_fast(noise(d), 600, 9000); t = t_axis(d); c *= np.exp(-t / 0.09) * np.minimum(1, t / 0.004)
    r = lowpass_fast(noise(body), 160); tr = t_axis(body); r *= np.exp(-tr / 0.9) * np.minimum(1, tr / 0.05) * (1 + 0.5 * lowpass_fast(noise(body), 4))
    out = np.zeros(int(body * SR)); out[:len(c)] += c / (np.abs(c).max() + 1e-9); out += r / (np.abs(r).max() + 1e-9) * 0.9
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
def buzz(d, f=120):   # electric zap texture: square-ish hum + crackle
    t = t_axis(d); o = np.tanh(4 * np.sin(2 * np.pi * f * t)) * 0.5 + 0.5 * bandpass_fast(noise(d), 1500, 6000)
    return o / (np.abs(o).max() + 1e-9) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.3
def sizzle(d=0.8):
    n = bandpass_fast(noise(d), 3000, 11000); t = t_axis(d); e = np.minimum(1, t / 0.03) * np.exp(-t / (d * 0.5)) * (1 + 0.6 * np.sin(2 * np.pi * 23 * t))
    return n * e / (np.abs(n).max() + 1e-9)
def boing(f0=220, d=0.45):   # comic spring for the hat
    t = t_axis(d); f = f0 * (1 + 0.5 * np.sin(2 * np.pi * 9 * t) * np.exp(-t / 0.15)) * (1 + 0.6 * t / d); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.18) * 0.8
def poof(d=0.35):
    n = lowpass_fast(noise(d), 1200); t = t_axis(d); return n * np.minimum(1, t / 0.01) * np.exp(-t / 0.08) / (np.abs(n).max() + 1e-9)
def beep(f=1000, d=0.12):
    t = t_axis(d); return np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.005) * np.minimum(1, (d - t) / 0.01)
def pluck(f, d=0.5):
    t = t_axis(d); o = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (6 + 4 * k)) / k for k in (1, 2, 3, 4)); return o * np.minimum(1, t / 0.003)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(6)
    # --- rain + wind under the storm beats (not under the hospital close-up or the panel beats)
    rain = bandpass_fast(noise(D), 1500, 9000); wind = lowpass_fast(noise(D), 220) * (1 + 0.6 * lowpass_fast(noise(D), 0.5))
    ta = t_axis(D); env = np.zeros_like(ta)
    for bid, lvl in (("hook", 1), ("roy", 1), ("golf", 1), ("how", 1), ("flash", 0.5), ("ground", 1), ("heart", 0.35), ("odds", 0.35), ("roymath", 0.8), ("cta", 0.8)):
        b = B[bid]; env += lvl * np.clip((ta - b["start"] + 0.2) / 0.3, 0, 1) * np.clip((b["end"] - ta + 0.2) / 0.3, 0, 1)
    env = np.clip(env, 0, 1)
    place(sfx, rain / (np.abs(rain).max() + 1e-9) * env, 0, 0.14); place(sfx, wind / (np.abs(wind).max() + 1e-9) * env, 0, 0.18)
    # --- shot H strikes (hook + roy), comic extras on the injuries, the montage again under roymath
    def h_abs(beat, ts): return B[beat]["start"] + (ts - (0 if beat == "hook" else H_ROY0))
    place(sfx, crack(), 0.0, 1.0); place(sfx, sizzle(0.5), 0.05, 0.3); place(sfx, boing(240), 0.1, 0.35)
    for i, ts in enumerate(H_STRIKES[1:], 1):
        t0 = h_abs("roy", ts); place(sfx, crack(0.6, 1.6), t0 - 0.01, 0.75); place(sfx, buzz(0.3, 110 + 15 * i), t0, 0.18)
        if i < 4: place(sfx, boing(220 + 30 * i), t0 + 0.08, 0.3)
    place(sfx, poof(), h_abs("roy", H_STRIKES[3]) + 0.06, 0.6)                    # eyebrows
    for k in (4, 5): place(sfx, sizzle(0.7), h_abs("roy", H_STRIKES[k]) + 0.08, 0.55); place(sfx, ignite(0.5), h_abs("roy", H_STRIKES[k]) + 0.06, 0.4)
    place(sfx, poof(0.4), h_abs("roy", H_STRIKES[6]) + 0.05, 0.7)                  # the shoe
    rm = B["roymath"]
    for ts in H_STRIKES[1:]:
        t0 = rm["start"] + (ts - H_ROY0)
        if t0 < rm["end"]: place(sfx, crack(0.4, 1.0), t0, 0.35)
    tO = W("roymath", "one")
    for k in range(29): place(sfx, tick(2000 + 60 * k, 0.02), tO + k / 30, 0.25)
    place(sfx, ding(1568, 0.8), tO + 0.97, 0.4); place(sfx, ding(1046, 0.9), W("roymath", "roy"), 0.35)
    # --- golf: strike into the pond, umbrella whoosh, steam hiss; the raised 1-iron gets a hopeful rumble and nothing
    g = B["golf"]; place(sfx, crack(), g["start"] + G_STRIKE - 0.01, 0.95); place(sfx, sizzle(1.4), g["start"] + G_STRIKE + 0.05, 0.4)
    place(sfx, whoosh(0.6, 300, 3000), g["start"] + G_STRIKE + 0.1, 0.4); place(sfx, rumble(2.0, 90), W("golf", "not"), 0.5)
    place(sfx, ding(1318, 0.6), W("golf", "advice"), 0.3)
    c = B["cta"]; place(sfx, rumble(1.6, 90), c["start"] + 0.3, 0.35)
    # --- flashover in slow motion: stepped leader crackle + rising hum, a slowed-down boom, sizzle over skin, shoes pop
    h = B["how"]; place(sfx, crackle(1.8, 22, rng), h["start"] + 0.1, 0.35); place(sfx, hum(1.8, 45, 130), h["start"] + 0.1, 0.18)
    tS = h["start"] + F_STRIKE
    boom = lowpass_fast(crack(1.2, 3.5), 900); place(sfx, boom / (np.abs(boom).max() + 1e-9), tS - 0.02, 1.0); place(sfx, thud(40, 0.9), tS, 0.8)
    place(sfx, buzz(3.0, 80) * 0.6 + sizzle(3.0) * 0.4, tS + 0.2, 0.25)
    place(sfx, poof(0.4), h["start"] + F_SHOES, 0.8); place(sfx, boing(300, 0.5), h["start"] + F_SHOES + 0.05, 0.4); place(sfx, whoosh(0.5), h["start"] + F_SHOES, 0.35)
    place(sfx, ding(1760, 0.5), W("flash", "millionths"), 0.3)
    # --- ground current: tree strike, crackle spreading, zap up one leg and down the other
    gr = B["ground"]; place(sfx, crack(), gr["start"] + R_STRIKE - 0.01, 0.95)
    place(sfx, crackle(2.4, 40, rng, 1500, 7000), gr["start"] + R_STRIKE + 0.1, 0.45)
    place(sfx, buzz(R_LEG1 - R_LEG0, 140), gr["start"] + R_LEG0, 0.35); place(sfx, boing(180, 0.4), gr["start"] + R_LEG1, 0.3)
    # --- fern: quiet room, a soft shimmer as it grows, a reverse swell as it fades
    fe = B["fern"]; place(sfx, shimmer(1.2), fe["start"] + 0.5, 0.25); place(sfx, ding(1046, 1.0), W("fern", "lichtenberg"), 0.3)
    place(sfx, whoosh(1.0, 200, 3000, rev=True), W("fern", "fade") - 0.2, 0.25)
    # --- heart: monitor beeps on the drawn spikes, flatline tone while stopped, beeps back after CPR
    he = B["heart"]; tSt, tC = W("heart", "stopped"), W("heart", "cpr")
    t = he["start"] - 0.3
    while t < he["end"]:   # the ECG spike reaches the right edge when (t*1.6)%1 == 0.30
        k = np.floor(t * 1.6); ts = (k + 0.30) / 1.6
        if he["start"] < ts < he["end"] - 0.3 and (ts < tSt or ts > tC + 0.2) and ts < W("heart", "when"): place(sfx, beep(1000, 0.1), ts, 0.25)
        t += 1 / 1.6
    place(sfx, beep(1000, tC + 0.2 - tSt), tSt + 0.1, 0.18); place(sfx, ding(1568, 0.7), tC, 0.35)
    place(sfx, rumble(2.0, 110), W("heart", "thunder"), 0.6)
    # --- odds: number lands, figures pop up one by one
    o = B["odds"]; place(sfx, ding(1318, 0.6), W("odds", "about"), 0.35)
    tSv = W("odds", "survive")
    for i in range(9): place(sfx, pluck(523.25 * 2 ** (i / 12 * 2), 0.25), tSv + i * 0.04, 0.25)
    # --- cut whooshes
    for bid in ("golf", "how", "ground", "fern", "heart", "roymath", "cta"): place(sfx, whoosh(0.32), B[bid]["start"] - 0.18, 0.35)
    place(sfx, ding(1046, 1.2), W("cta", "follow"), 0.5)
    # --- music: light-hearted plucky major progression at 112 bpm (I-V-vi-IV), soft kick + shaker
    bpm = 112; beat = 60 / bpm; chords = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]
    tt, k = 0.0, 0
    while tt < D:
        ch = chords[(k // 8) % 4]; f = 440 * 2 ** ((ch[k % 3] - 69) / 12) * (2 if k % 4 == 3 else 1)
        place(music, pluck(f, 0.4), tt, 0.5 if k % 2 == 0 else 0.35)
        if k % 8 == 0:
            for m in ch: place(music, pluck(440 * 2 ** ((m - 12 - 69) / 12), 1.2), tt, 0.35)
        if k % 4 == 0: place(music, thud(55, 0.25), tt, 0.5)
        place(music, bandpass_fast(noise(0.04), 6000, 12000) * env_exp(0.04, 0.01), tt + beat / 4, 0.12)
        tt += beat / 2; k += 1
    music[:] = lowpass_fast(music, 3500)
