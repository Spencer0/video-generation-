"""Sound cues for video 004 (Leidenfrost). Understated: a metallic tick, sizzle-skitter, fine hiss,
a tonal shift into the cutaway, a quiet electronic pulse. No booms."""
import numpy as np
from audiolib import *
CAPTION_TICKS = False   # this video: no per-caption ticks (understated mix)

def sizzle(d, rng, density=60, lo=2500, hi=9000):
    out = np.zeros(int(d * SR)); t = 0.0
    while t < d:
        t += rng.exponential(1 / density); n = bandpass_fast(noise(0.012), lo, hi) * env_exp(0.012, 0.003); place(out, n, t, rng.uniform(0.2, 0.8))
    return out
def hiss(d, lo=1800, hi=7000):
    h = bandpass_fast(noise(d), lo, hi); return h / (np.abs(h).max() + 1e-9)
def pad_tone(d, f, a=0.8):
    t = t_axis(d); o = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.003 * t) + 0.25 * np.sin(2 * np.pi * f * 0.5 * t)
    return o / 1.75 * np.minimum(1, t / a) * np.minimum(1, (d - t) / 1.0)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(44)
    ta = t_axis(D)
    # opening: a sharp but small metallic tick, then the skitter sizzle
    place(sfx, tick(5200, 0.05), 0.02, 0.5); place(sfx, tick(7800, 0.03), 0.02, 0.25)
    # sizzle / skitter under every macro beat (hook, compare bottom half, name, payoff macro part, loop)
    env = np.zeros_like(ta)
    for bid, g in (("hook", 1.0), ("compare", 0.9), ("name", 0.8), ("payoff", 0.6), ("loop", 0.9)):
        b = B[bid]; env += g * np.clip((ta - b["start"] + 0.2) / 0.4, 0, 1) * np.clip((b["end"] - ta + 0.2) / 0.4, 0, 1)
    env = np.clip(env, 0, 1)
    place(sfx, sizzle(D, rng, 55) * env, 0, 0.22); place(sfx, hiss(D) * env, 0, 0.05)
    # the cooler-surface half: a brief wet 'tss' when the drop lands and spreads (split window at compare start)
    c0 = B["compare"]["start"] + 0.25
    place(sfx, bandpass_fast(noise(0.6), 1500, 6000) * env_exp(0.6, 0.15), c0, 0.3); place(sfx, hiss(1.5) * env_exp(1.5, 0.5), c0 + 0.2, 0.12)
    # the cutaway: a restrained tonal shift (soft low pad swells in) + fine steady vapor hiss
    for bid in ("reveal", "glide"):
        b = B[bid]; place(sfx, hiss(b["duration"], 2500, 8000) * np.sin(np.pi * np.clip(t_axis(b["duration"]) / b["duration"], 0, 1)) ** 0.4, b["start"], 0.10)
    place(sfx, pad_tone(B["glide"]["end"] - B["reveal"]["start"], 110, 1.5), B["reveal"]["start"], 0.12)
    place(sfx, whoosh(0.5, 300, 3000, rev=True), B["reveal"]["start"] - 0.4, 0.22)
    # labels: soft single tones, no dings
    for bid, wd in (("reveal", "steam"), ("name", "leidenfrost"), ("payoff", "vapor")): place(sfx, pad_tone(0.8, 880, 0.05), W(bid, wd), 0.10)
    # payoff cutaway swell, then the drop exits: a short skitter and silence on the metal
    place(sfx, pad_tone(3.4, 82.4, 1.0), B["payoff"]["start"] + 3.0, 0.12)
    # gentle cuts (very quiet)
    for bid in ("compare", "reveal", "name", "payoff", "loop"): place(sfx, whoosh(0.25, 500, 4000), B[bid]["start"] - 0.12, 0.12)
    # music: minimal electronic texture, 100 bpm sub pulse + sparse soft pad, quiet
    bpm = 100; beat = 60 / bpm
    chords = [(45, 52, 59), (43, 50, 57), (41, 48, 55), (43, 50, 57)]
    tt = 0.0; ci = 0
    while tt < D:
        d = beat * 8
        for m in chords[ci % 4]: place(music, pad_tone(d, 440 * 2 ** ((m - 69) / 12), 1.2), tt, 0.07)
        ci += 1; tt += d
    music[:] = lowpass_fast(music, 900)
    tt = 0.0; k = 0
    while tt < D:
        place(music, thud(48, 0.22), tt, 0.35 if k % 2 == 0 else 0.18)
        if k % 4 == 2: place(music, tick(4000, 0.03) * 0.3, tt, 0.05)
        tt += beat; k += 1
