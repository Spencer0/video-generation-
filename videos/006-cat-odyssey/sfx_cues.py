"""Sound cues for video 006 (cat Odyssey): sea bed, a square-wave adventure loop, and one gag sound per stage
(giant's rumble, the storm leaving the bag, zap + barks, a rattling treat tin, year chimes, doors + scatter, one meow)."""
import numpy as np
from audiolib import *
CAPTION_TICKS = True

def sq(f, d, duty=0.5):   # band-limited-ish square/pulse (lowpassed), the "console" voice
    t = t_axis(d); return lowpass_fast(np.where((t * f) % 1.0 < duty, 1.0, -1.0), 3200)
def note(m): return 440 * 2 ** ((m - 69) / 12)
def meow(d=0.7):
    t = t_axis(d); k = t / d; f = 520 + 380 * np.sin(np.pi * np.clip(k * 1.25, 0, 1)) ** 0.8 - 160 * k; ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + 0.55 * np.sin(2 * ph) + 0.35 * np.sin(3 * ph) + 0.15 * np.sin(5 * ph)
    return bandpass_fast(s, 500, 3200) * np.sin(np.pi * k) ** 0.6
def bark(f0=420):
    d = 0.13; t = t_axis(d); f = f0 * (1.25 - 0.6 * t / d); ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sign(np.sin(ph)) * 0.5 + np.sin(ph)) * np.exp(-t / 0.05) + 0.3 * bandpass_fast(noise(d), 600, 2500) * np.exp(-t / 0.03)
def wind(d):
    n = noise(d); t = t_axis(d); out = bandpass_fast(n, 250, 1400) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.9 * t)) + 0.5 * bandpass_fast(n, 900, 3000) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.7 * t + 1))
    return out * np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 0.5)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(6); ta = t_axis(D)
    # sea bed under the outdoor beats (swelling lowpassed noise)
    env = np.zeros_like(ta)
    for bid, g in (("hook", 1.0), ("home", 1.0), ("winds", 1.0), ("circe", 0.5), ("sirens", 0.9), ("calypso", 0.5)):
        b = B[bid]; env += g * np.clip((ta - b["start"] + 0.15) / 0.3, 0, 1) * np.clip((b["end"] - ta + 0.15) / 0.3, 0, 1)
    sea = bandpass_fast(noise(D), 150, 1600)[:len(ta)] * (0.55 + 0.45 * np.sin(2 * np.pi * 0.22 * ta)) ; place(sfx, sea * np.clip(env, 0, 1), 0, 0.10)
    for bid in ("home", "cyclops", "winds", "circe", "sirens", "calypso", "suitors", "door"): place(sfx, whoosh(0.3, 400, 4000), B[bid]["start"] - 0.12, 0.22)
    place(sfx, ding(1568, 0.7), W("hook", "cat"), 0.2); place(sfx, shimmer(0.5), 0.0, 0.2)
    place(sfx, thud(60, 0.5), W("home", "ten"), 0.5)
    # cyclops: low rumble + footfall thuds, then sheep hooves
    c = B["cyclops"]; place(sfx, lowpass_fast(noise(2.6), 90) * np.minimum(1, t_axis(2.6) / 0.4) * np.minimum(1, (2.6 - t_axis(2.6)) / 0.6), c["start"] + 0.1, 1.4)
    place(sfx, thud(48, 0.6), W("cyclops", "giant"), 0.8)
    t0 = W("cyclops", "they")
    for k in range(18): place(sfx, tick(700 + 150 * (k % 2), 0.03), t0 + 0.1 + k * 0.13, 0.12)
    # winds: paw taps on the sack, burst, gale
    w = B["winds"]; to = W("winds", "opens")
    for k in range(int((to - w["start"]) / 0.9)): place(sfx, thud(180, 0.1), w["start"] + 0.4 + k * 0.9, 0.2)
    place(sfx, whoosh(0.7, 200, 5000), to - 0.05, 0.6); place(sfx, thud(55, 0.5), to, 0.6); place(sfx, wind(w["end"] - to), to + 0.1, 0.5)
    # circe: zap, poof, barks
    tp, td = W("circe", "pigs"), W("circe", "dogs")
    place(sfx, shimmer(0.4), tp - 0.4, 0.3); place(sfx, sq(880, 0.12, 0.25) * env_exp(0.12, 0.04), tp - 0.03, 0.3); place(sfx, whoosh(0.35, 300, 3000, rev=True), tp + 0.05, 0.3)
    for k, f in enumerate((430, 520, 380, 470, 540)): place(sfx, bark(f), td + 0.25 + k * 0.22 + rng.uniform(0, 0.04), 0.35)
    # sirens: the tin rattles the whole first half; a little "song" on top
    s = B["sirens"]; t2 = W("sirens", "so"); tt = s["start"] + 0.3
    while tt < s["end"] - 0.2:
        place(sfx, bandpass_fast(noise(0.03), 3000, 9000) * env_exp(0.03, 0.008), tt, 0.30 if tt < t2 else 0.12); tt += rng.uniform(0.035, 0.08)
    for k, m in enumerate((76, 79, 81, 79, 76, 79, 84)): place(sfx, np.sin(2 * np.pi * note(m) * t_axis(0.5)) * np.sin(np.pi * t_axis(0.5) / 0.5) ** 2, s["start"] + 0.5 + k * 0.42, 0.10)
    # calypso: one chime per year
    cl = B["calypso"]; ts = W("calypso", "seven")
    for k in range(7): place(sfx, ding(988 * 2 ** (k / 12), 0.5), ts + (cl["end"] - 0.5 - ts) * k / 7, 0.2)
    # suitors: munching, doors, scatter
    su = B["suitors"]; th = W("suitors", "he", 1); tt = su["start"] + 0.2
    while tt < th: place(sfx, bandpass_fast(noise(0.04), 800, 3000) * env_exp(0.04, 0.012), tt, 0.14); tt += rng.uniform(0.06, 0.14)
    place(sfx, thud(70, 0.5), th + 0.05, 0.9); place(sfx, bandpass_fast(noise(0.25), 200, 2000) * env_exp(0.25, 0.06), th + 0.05, 0.5)
    place(sfx, whoosh(0.6, 500, 6000), th + 0.5, 0.5)
    for k in range(5): place(sfx, meow(0.3) , th + 0.5 + k * 0.07, 0.10)
    # door: scratch + the meow
    d = B["door"]; to = W("door", "out")
    for k in range(6): place(sfx, bandpass_fast(noise(0.09), 1500, 6000) * env_exp(0.09, 0.03), to + 0.05 + k * 0.19, 0.16)
    place(sfx, meow(0.75), to + 0.38, 0.55)
    # music: 112 bpm square-wave arpeggio over a soft bass, i-VI-III-VII in A minor; brighter IV-V-I for the last two beats
    bpm = 112; beat = 60 / bpm; prog = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
    tt = 0.0; k = 0
    while tt < D:
        ch = prog[(k // 8) % 4]; m = ch[k % 3] + (12 if (k % 8) in (3, 6) else 0)
        place(music, sq(note(m), beat * 0.48, 0.25) * env_exp(beat * 0.48, 0.12), tt, 0.5)
        if k % 4 == 0: place(music, np.sin(2 * np.pi * note(ch[0] - 24) * t_axis(beat * 1.9)) * env_exp(beat * 1.9, 0.5), tt, 0.9)
        if k % 2 == 1: place(music, tick(6000, 0.02), tt, 0.12)
        tt += beat / 2; k += 1
