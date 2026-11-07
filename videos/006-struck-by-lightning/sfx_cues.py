"""Sound cues for video 006 (struck by lightning, and lived). Called by pipeline/sfx.py.
Strike times follow pipeline/blender/scene_struck.py (H_STRIKES etc.) mapped through script.json bg_plan."""
import numpy as np
from audiolib import *

# event times from pipeline/blender/scene_struck.py (v2: the video follows Roy Sullivan), mapped through script.json bg_plan
H_STRIKES = [0.0, 10.75, 11.45, 12.10, 12.70]; H_HAIR0 = 10.5; H_POUR0 = 13.30
T_STRIKE1, T_BROWS, T_WINUP0, T_STRIKE2 = 1.15, 2.78, 3.40, 4.55
G_STRIKE = 1.45
F_STRIKE, F_SHOES = 1.20, 6.40
B_STRIKE, B_BEAR0, B_GRAB, B_BONK = 0.80, 2.2, 4.45, 5.55

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

def growl(d=0.9):
    t = t_axis(d); f = 85 * (1 + 0.15 * np.sin(2 * np.pi * 7 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    o = np.tanh(3 * (np.sin(ph) + 0.5 * np.sin(2 * ph))) + 0.4 * lowpass_fast(noise(d), 600)
    return o / (np.abs(o).max() + 1e-9) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.5
def bonk():
    t = t_axis(0.35); return (np.sin(2 * np.pi * 520 * t * (1 - 0.4 * t)) * np.exp(-t / 0.07) + 0.6 * thud(110, 0.35)) * 0.9
def splash(d=0.8):
    n = bandpass_fast(noise(d), 600, 7000); t = t_axis(d); return n * np.minimum(1, t / 0.05) * np.exp(-t / 0.3) / (np.abs(n).max() + 1e-9)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(6)
    # --- rain + wind under the storm beats (quiet room for the fern close-up; low under the panels)
    rain = bandpass_fast(noise(D), 1500, 9000); wind = lowpass_fast(noise(D), 220) * (1 + 0.6 * lowpass_fast(noise(D), 0.5))
    ta = t_axis(D); env = np.zeros_like(ta)
    for bid, lvl in (("hook", 1), ("roy", 1), ("why", 0.5), ("truck", 1), ("hair", 1), ("golf", 1), ("heart", 0.35), ("odds", 0.35), ("roymath", 0.8), ("bear", 1), ("cta", 0.9)):
        b = B[bid]; env += lvl * np.clip((ta - b["start"] + 0.2) / 0.3, 0, 1) * np.clip((b["end"] - ta + 0.2) / 0.3, 0, 1)
    env = np.clip(env, 0, 1)
    place(sfx, rain / (np.abs(rain).max() + 1e-9) * env, 0, 0.14); place(sfx, wind / (np.abs(wind).max() + 1e-9) * env, 0, 0.18)
    # --- strike one (hook): crack, the current runs down the leg, the shoe pops and sizzles; hopping thumps in roy
    place(sfx, crack(), 0.0, 1.0); place(sfx, buzz(0.25, 140), 0.0, 0.25); place(sfx, poof(0.4), 0.08, 0.7); place(sfx, sizzle(0.9), 0.1, 0.35); place(sfx, boing(240), 0.12, 0.3)
    r = B["roy"]; H0 = r["start"] - 78 / 24   # roy shows shot H from frame 78
    for k in range(9): place(sfx, thud(140, 0.15), H0 + 4.9 + k * 0.45, 0.35)   # hops
    place(sfx, sizzle(1.2), W("roy", "hole"), 0.3); place(sfx, ding(1318, 0.6), W("roy", "strike"), 0.3)
    # --- why: slow-motion leader, slowed boom, hum of the flashover, the feet popping
    w = B["why"]; place(sfx, crackle(1.1, 22, rng), w["start"] + 0.05, 0.35); place(sfx, hum(1.1, 45, 130), w["start"] + 0.05, 0.18)
    tS = w["start"] + F_STRIKE
    boom = lowpass_fast(crack(1.2, 3.5), 900); place(sfx, boom / (np.abs(boom).max() + 1e-9), tS - 0.02, 1.0); place(sfx, thud(40, 0.9), tS, 0.8)
    place(sfx, buzz(4.5, 80) * 0.6 + sizzle(4.5) * 0.4, tS + 0.2, 0.22)
    place(sfx, poof(0.4), w["start"] + F_SHOES, 0.8); place(sfx, boing(300, 0.5), w["start"] + F_SHOES + 0.05, 0.4); place(sfx, ding(1760, 0.5), W("why", "millionths"), 0.3)
    # --- truck: engine idle, strike through the window, eyebrow poof, window motor, roof strike + buzz over the shell
    tr = B["truck"]; idle = lowpass_fast(noise(tr["end"] - tr["start"]), 120) * (1 + 0.3 * np.sin(2 * np.pi * 14 * t_axis(tr["end"] - tr["start"])))
    place(sfx, idle / (np.abs(idle).max() + 1e-9), tr["start"], 0.25)
    place(sfx, crack(), tr["start"] + T_STRIKE1 - 0.01, 0.95); place(sfx, poof(0.3), tr["start"] + T_BROWS, 0.7); place(sfx, sizzle(0.5), tr["start"] + T_BROWS, 0.3)
    mot = hum(0.55, 300, 420, (1, 2)); place(sfx, mot, tr["start"] + T_WINUP0, 0.15)
    place(sfx, crack(), tr["start"] + T_STRIKE2 - 0.01, 0.9); place(sfx, buzz(1.4, 100), tr["start"] + T_STRIKE2 + 0.05, 0.3); place(sfx, ding(1568, 0.6), W("truck", "windows"), 0.3)
    # --- hair: strikes 3-6 rapid-fire, crackling hair, then the water can: splash + big steam hiss
    h = B["hair"]; HH = h["start"] - H_HAIR0
    for ts in H_STRIKES[1:]: place(sfx, crack(0.5, 1.4), HH + ts, 0.7); place(sfx, sizzle(0.6), HH + ts + 0.08, 0.35)
    place(sfx, ignite(0.5), HH + H_STRIKES[1] + 0.05, 0.45)
    place(sfx, splash(0.8), HH + H_POUR0 + 0.25, 0.7); place(sfx, sizzle(1.5), HH + H_POUR0 + 0.35, 0.6)
    # --- golf: strike into the pond, umbrella whoosh, a hopeful rumble under the 1-iron joke and nothing
    g = B["golf"]; place(sfx, crack(), g["start"] + G_STRIKE - 0.01, 0.95); place(sfx, sizzle(1.2), g["start"] + G_STRIKE + 0.05, 0.4)
    place(sfx, whoosh(0.6, 300, 3000), g["start"] + G_STRIKE + 0.1, 0.4); place(sfx, rumble(2.0, 90), W("golf", "not"), 0.5); place(sfx, ding(1318, 0.6), W("golf", "joke"), 0.3)
    # --- fern: quiet, a shimmer as it grows, a reverse swell as it fades
    fe = B["fern"]; place(sfx, shimmer(1.2), fe["start"] + 0.5, 0.25); place(sfx, ding(1046, 1.0), W("fern", "lichtenberg"), 0.3)
    place(sfx, whoosh(1.0, 200, 3000, rev=True), W("fern", "fade") - 0.2, 0.25)
    # --- heart: monitor beeps on the drawn spikes, flatline while stopped, beeps back after CPR
    he = B["heart"]; tSt, tC = W("heart", "stopped"), W("heart", "cpr"); t = he["start"] - 0.3
    while t < he["end"]:
        k = np.floor(t * 1.6); ts = (k + 0.30) / 1.6
        if he["start"] < ts < he["end"] - 0.2 and (ts < tSt or ts > tC + 0.2): place(sfx, beep(1000, 0.1), ts, 0.25)
        t += 1 / 1.6
    place(sfx, beep(1000, tC + 0.2 - tSt), tSt + 0.1, 0.18); place(sfx, ding(1568, 0.7), tC, 0.35)
    # --- odds / roymath
    place(sfx, ding(1318, 0.6), W("odds", "about"), 0.35); tSv = W("odds", "survive")
    for i in range(9): place(sfx, pluck(523.25 * 2 ** (i / 12 * 2), 0.25), tSv + i * 0.04, 0.25)
    place(sfx, ding(1568, 0.8), W("roymath", "one"), 0.4); place(sfx, ding(1046, 0.9), W("roymath", "he"), 0.35)
    # --- bear: strike seven, creek babble, a growl on 'bear', the bonk, a yelp and running paws
    be = B["bear"]; creek = bandpass_fast(noise(be["end"] - be["start"] + 3.9), 400, 3000) * (1 + 0.4 * lowpass_fast(noise(be["end"] - be["start"] + 3.9), 3))
    place(sfx, creek / (np.abs(creek).max() + 1e-9), be["start"], 0.12)
    place(sfx, crack(), be["start"] + B_STRIKE - 0.01, 1.0); place(sfx, sizzle(1.0), be["start"] + B_STRIKE + 0.1, 0.35)
    place(sfx, growl(1.0), W("bear", "bear"), 0.55); place(sfx, growl(0.6), be["start"] + B_GRAB, 0.4)
    place(sfx, bonk(), be["start"] + B_BONK, 1.0); place(sfx, boing(400, 0.4), be["start"] + B_BONK + 0.05, 0.4)
    for k in range(10): place(sfx, thud(90, 0.12), be["start"] + B_BONK + 0.3 + k * 0.17, 0.3)
    c = B["cta"]; place(sfx, rumble(1.8, 100), W("cta", "thunder"), 0.45)
    # --- cut whooshes
    for bid in ("why", "truck", "hair", "golf", "fern", "heart", "roymath", "bear"): place(sfx, whoosh(0.32), B[bid]["start"] - 0.18, 0.35)
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
