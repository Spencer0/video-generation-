"""Sound cues for video 006 (Lake Peigneur, low-poly anime). Water roar that swells with the whirlpool, a drill
grind that stops on 'punched' with a crack + boom + gush, a waterfall roar, anime pops on every label, whooshes on
cuts, and a light pentatonic pluck bed (anime-lofi feel) kept at ~-20 dB."""
import numpy as np
from audiolib import *
CAPTION_TICKS = True

def roar(d, lo=60, hi=900):
    n = bandpass_fast(noise(d), lo, hi); mod = 1 + 0.25 * lowpass_fast(noise(d), 3); return n * mod / (np.abs(n).max() + 1e-9)
def drill(d, f=38):
    t = t_axis(d); saw = 2 * ((f * t + 0.3 * np.sin(2 * np.pi * 1.7 * t)) % 1) - 1
    grit = bandpass_fast(noise(d), 800, 3000) * (0.5 + 0.5 * np.sin(2 * np.pi * f * t) ** 2)
    out = lowpass_fast(saw, 600) * 0.7 + grit * 0.3; return out / (np.abs(out).max() + 1e-9)
def crack():
    s = np.zeros(int(0.6 * SR)); place(s, bandpass_fast(noise(0.08), 1500, 9000) * env_exp(0.08, 0.01), 0, 1.0); place(s, thud(48, 0.6), 0.01, 1.2); return s
def pop(f=880):
    t = t_axis(0.12); fr = f * (1 + 1.2 * np.exp(-t / 0.02)); return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.04)
def pluck(f, d=0.5):
    t = t_axis(d); return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.18) * np.minimum(1, t / 0.004)
def gush(d): n = bandpass_fast(noise(d), 200, 2500); t = t_axis(d); return n * np.minimum(1, t / 0.3) / (np.abs(n).max() + 1e-9)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(6); ta = t_axis(D)
    # water roar under the lake shots; big during the whirlpool, light on the calm establishing shot
    env = np.zeros_like(ta)
    for bid, g in (("hook", 0.9), ("setup", 0.15), ("whirlpool", 1.0), ("why", 0.7), ("spin", 0.5), ("salt", 0.25), ("payoff", 0.5), ("cta", 0.5)):
        b = B[bid]; env += g * np.clip((ta - b["start"] + 0.2) / 0.4, 0, 1) * np.clip((b["end"] - ta + 0.2) / 0.4, 0, 1)
    place(sfx, roar(D) * np.clip(env, 0, 1), 0, 0.5)
    # drill grind through the mine beat until 'punched'; crack + boom + gush after
    tP = W("mine", "punched"); m0 = B["mine"]["start"]
    dr = drill(tP - m0 + 0.1); dr *= np.minimum(1, t_axis(len(dr) / SR) / 0.3); place(sfx, dr, m0, 0.28)
    place(sfx, crack(), tP + 0.05, 0.9)
    g = gush(B["mine"]["end"] - tP + 0.3); g *= np.minimum(1, (len(g) / SR - t_axis(len(g) / SR)) / 0.4); place(sfx, g, tP + 0.1, 0.45)
    # the rig and barges going under: low glugs
    for k in range(8): place(sfx, glug(90 + 15 * (k % 3), 0.14), B["whirlpool"]["start"] + 2.4 + k * 0.33, 0.35)
    # waterfall roar
    b = B["waterfall"]; d = b["duration"] + 0.3; place(sfx, roar(d, 200, 4000) * np.minimum(1, t_axis(d) / 0.3) * np.minimum(1, (d - t_axis(d)) / 0.4), b["start"], 0.55)
    # anime pops on labels and headlines
    for bid, wd in (("hook", "plug"), ("hook", "1980"), ("setup", "ten"), ("setup", "rig"), ("mine", "salt"), ("mine", "fiftyfive"), ("mine", "twelve"),
                    ("whirlpool", "spin"), ("whirlpool", "rig"), ("whirlpool", "barges"), ("whirlpool", "tugboat"), ("waterfall", "backwards"), ("waterfall", "sixtyfour"),
                    ("why", "whirlpool"), ("spin", "speed"), ("spin", "radius"), ("spin", "half"), ("spin", "double"), ("salt", "eats"), ("salt", "three"), ("salt", "growing"),
                    ("payoff", "bathtub")):
        place(sfx, pop(rng.choice([784, 880, 988])), W(bid, wd), 0.22)
    # sparkle chimes on the good news and the payoff
    for t0 in (W("waterfall", "every"), B["payoff"]["start"]):
        for k, f in enumerate((1568, 1976, 2349)): place(sfx, ding(f, 0.6), t0 + 0.08 * k, 0.09)
    # shock sting on the hook
    place(sfx, whoosh(0.4, 300, 6000, rev=True), 0.0, 0.3); place(sfx, thud(55, 0.5), 0.05, 0.6)
    # cuts
    for bid in ("setup", "mine", "whirlpool", "waterfall", "why", "spin", "salt", "payoff", "cta"): place(sfx, whoosh(0.3, 400, 5000), B[bid]["start"] - 0.12, 0.22)
    # music: pentatonic plucks over soft chords, 112 bpm
    bpm = 112; beat = 60 / bpm; chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
    scale = [69, 72, 74, 76, 79, 81]; tt = 0.0; ci = 0; arng = np.random.default_rng(12)
    while tt < D:
        for m in chords[ci % 4]:
            f = 440 * 2 ** ((m - 69) / 12); dd = beat * 4; tq = t_axis(dd)
            place(music, np.sin(2 * np.pi * f * tq) * np.minimum(1, tq / 0.3) * np.minimum(1, (dd - tq) / 0.5), tt, 0.05)
        for k in range(8):
            if arng.random() < 0.75: place(music, pluck(440 * 2 ** ((scale[arng.integers(0, len(scale))] - 69) / 12)), tt + k * beat / 2, 0.08)
        ci += 1; tt += beat * 4
    tt = 0.0; k = 0
    while tt < D:
        place(music, thud(60, 0.18), tt, 0.25 if k % 2 == 0 else 0.0); place(music, tick(6000, 0.02) * 0.4, tt + beat / 2, 0.05); tt += beat; k += 1
