"""Sound cues for video 005 (Kaye effect). Wet splat on impact, a soft rising whoosh on each leap (no cartoon
boings), a faint continuous pour, dings on labels, whooshes on cuts, a quiet bed at ~-20 dB."""
import numpy as np
from audiolib import *
CAPTION_TICKS = True

def pour(d, rng, density=140):
    """Continuous thin-stream pour: dense tiny wet ticks + a low filtered hiss."""
    out = np.zeros(int(d * SR)); t = 0.0
    while t < d:
        t += rng.exponential(1 / density); n = bandpass_fast(noise(0.01), 900, 5000) * env_exp(0.01, 0.003); place(out, n, t, rng.uniform(0.15, 0.6))
    out += 0.35 * bandpass_fast(noise(d), 300, 1800) / 3.0
    return out
def splat(rng):
    """Wet slap: short low thump + a burst of bandpassed noise with a few bubbles."""
    s = np.zeros(int(0.45 * SR)); place(s, thud(140, 0.18), 0.0, 0.9); place(s, bandpass_fast(noise(0.22), 500, 4500) * env_exp(0.22, 0.04), 0.0, 0.7)
    for k in range(6): place(s, bubble_pop(rng.uniform(500, 1300), 0.04, 0.5), rng.uniform(0.02, 0.2), rng.uniform(0.2, 0.5))
    return s
def leap(d=0.9):
    """Rising airy whoosh for the jet: filtered noise with an upward bandpass sweep, no tone."""
    n = noise(d); t = t_axis(d); out = np.zeros_like(n)
    seg = int(0.05 * SR)
    for i in range(0, len(n), seg):
        f = 500 + 3500 * (i / len(n)); out[i:i + seg] = bandpass_fast(n[i:i + seg], f, f * 2.2)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7 * (1 - 0.5 * t / d)
    return out * env / (np.abs(out).max() + 1e-9)
def pad_tone(d, f, a=0.8):
    t = t_axis(d); o = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.003 * t) + 0.25 * np.sin(2 * np.pi * f * 0.5 * t)
    return o / 1.75 * np.minimum(1, t / a) * np.minimum(1, (d - t) / 1.0)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(55); ta = t_axis(D)
    fps = tl["fps"]
    # continuous pour under every footage beat (quiet during the blurred explainer)
    env = np.zeros_like(ta)
    for bid, g in (("hook", 1.0), ("compare", 0.8), ("why1", 0.35), ("why2", 1.0), ("tryit", 0.9), ("ask", 0.9), ("loop", 1.0)):
        b = B[bid]; env += g * np.clip((ta - b["start"] + 0.2) / 0.4, 0, 1) * np.clip((b["end"] - ta + 0.2) / 0.4, 0, 1)
    place(sfx, pour(D, rng) * np.clip(env, 0, 1), 0, 0.16)
    # leaps: scene time of each jet event (scene_kaye.py EVENTS, 4x slow motion) -> video time via bg_plan offsets
    #   hook: A from 0, event at A t=6.6 wraps -> airborne at video 0.0; full arc 0.0-0.6 s; tail flies out to ~2.4 s
    leaps = [(0.0, 0.9), (B["hook"]["start"] + 2.5 + 3.3 - 75 / fps, 0.8),            # second A leap lands inside 'compare' (A offset 75, event 3.3)
             (B["compare"]["start"] + 2.4, 0.7), (B["compare"]["start"] + 4.3, 0.7),  # shampoo panel events (S: 2.4, 4.3)
             (B["why2"]["start"] + 4.6, 0.9),                                          # X event 4.6
             (B["tryit"]["start"] + 0.5, 0.8), (B["tryit"]["start"] + 3.0, 0.8),       # B events
             (B["ask"]["start"] + (3.3 - 114 / fps) if False else B["ask"]["start"] + 3.3 - 114 / fps, 0.7),   # A event 3.3 seen from offset 114 (negative -> already running)
             (B["loop"]["start"] + 6.6 - 204 / fps, 0.9)]                                 # A event 6.6 seen from offset 204 (the loop leap)
    for t0, g in leaps:
        if t0 < -0.5 or t0 > D: continue
        place(sfx, leap(0.9), max(t0, 0.0), 0.5 * g)
        place(sfx, splat(rng), t0 + 0.95, 0.35 * g)   # the tip lands ~0.95 s (slow) after it leaves
    # the opening: a splat right away (the jet in the air at frame 0 is mid-leap), small
    place(sfx, splat(rng), 0.55, 0.3)
    # honey: a slow wet glug-ish coil tick; water: splashy droplets during the compare stack
    c0 = B["compare"]["start"]
    for k in range(9): place(sfx, glug(120 + 10 * (k % 3), 0.10), c0 + 0.3 + k * 0.5, 0.18)
    for k in range(40): place(sfx, bubble_pop(rng.uniform(900, 2200), 0.03, 0.6), c0 + rng.uniform(0.2, 4.9), rng.uniform(0.08, 0.22))
    # labels: dings on the comparison verbs, bars, cutaway labels, checklist items, the question
    for bid, wd in (("compare", "coils"), ("compare", "splashes"), ("compare", "leaps"), ("why1", "slowly"), ("why1", "fast"), ("why1", "ten"),
                    ("why2", "dimple"), ("why2", "layer"), ("why2", "slippery"), ("why2", "jet"), ("tryit", "plate"), ("tryit", "stream"), ("tryit", "handspan"), ("tryit", "tries"), ("ask", "does")):
        place(sfx, ding(1320 if wd not in ("leaps", "jet", "does") else 1760, 0.6), W(bid, wd), 0.16)
    # explainer panel in: soft shimmer; cutaway pad under why2
    place(sfx, shimmer(0.6), B["why1"]["start"] + 0.1, 0.25)
    place(sfx, pad_tone(B["why2"]["duration"], 98, 1.2), B["why2"]["start"], 0.10)
    # cuts
    for bid in ("compare", "why1", "why2", "tryit", "ask"): place(sfx, whoosh(0.3, 400, 4000), B[bid]["start"] - 0.12, 0.22)
    # music: light, upbeat-ish bed at 104 bpm, major-ish pad + soft pulse, kept quiet (~-20 dB after the mixer's 0.12 gain)
    bpm = 104; beat = 60 / bpm
    chords = [(48, 55, 64), (45, 52, 60), (41, 48, 57), (43, 50, 59)]
    tt = 0.0; ci = 0
    while tt < D:
        d = beat * 4
        for m in chords[ci % 4]: place(music, pad_tone(d, 440 * 2 ** ((m - 69) / 12), 0.6), tt, 0.07)
        ci += 1; tt += d
    music[:] = lowpass_fast(music, 1200)
    tt = 0.0; k = 0
    while tt < D:
        place(music, thud(55, 0.2), tt, 0.3 if k % 2 == 0 else 0.15)
        if k % 2 == 1: place(music, tick(5000, 0.02) * 0.3, tt + beat / 2, 0.08)
        tt += beat; k += 1
