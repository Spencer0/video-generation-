"""Sound cues for video 006 (how a forest is born). A timelapse has no literal sound, so the design is: a steady wind
bed, soft sprout pops while things grow, a wooden clock tick on the year counter (every year early, every 5 / 10 years
when the clock runs fast), birdsong that thickens as the forest matures, creak + thud for each pioneer that falls
(years from build/forest_events.json, written by scene_forest.py --list), dings on the stage tags, a tape-style rewind
for the ask beat, and a calm major bed at ~-20 dB."""
import json, os, numpy as np
from audiolib import *
CAPTION_TICKS = True

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def smoother(u): u = np.clip(u, 0, 1); return u * u * u * (u * (u * 6 - 15) + 10)

def year_curve(tl, years, D):
    """Video time -> timelapse year, the same curve as scene_forest.py / beats.js."""
    ta = t_axis(D); Y = np.zeros_like(ta); B = {b["id"]: b for b in tl["beats"]}
    for b in tl["beats"]:
        m = (ta >= b["start"]) & (ta < b["end"]); y0, y1 = years[b["id"]]
        if b["id"] == "ask":
            m = (ta >= b["start"]) & (ta < B["loop"]["end"]); Y[m] = y0 * (1 - smoother((ta[m] - b["start"]) / (B["loop"]["end"] - b["start"])))
        elif b["id"] == "loop": Y[m] = 0
        else: Y[m] = y0 + (y1 - y0) * np.clip((ta[m] - b["start"]) / b["duration"], 0, 1)
    return ta, Y

def wind(d, rng):
    n = lowpass_fast(noise(d), 600) * 0.7 + lowpass_fast(noise(d), 180) * 0.6
    mod = 1 + 0.45 * lowpass_fast(noise(d), 0.35) / (np.abs(lowpass_fast(noise(d), 0.35)).max() + 1e-9)
    return n * mod / (np.abs(n).max() + 1e-9)
def sprout(rng):
    f = rng.uniform(500, 1400); return bubble_pop(f, 0.03, 0.3) * 0.6
def wood_tick(d=0.05, f=900):
    t = t_axis(d); return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.008) + 0.5 * np.sin(2 * np.pi * f * 2.3 * t) * np.exp(-t / 0.004)) * 0.8
def chirp(rng):
    d = rng.uniform(0.06, 0.16); t = t_axis(d); f0 = rng.uniform(2200, 4200); f1 = f0 * rng.uniform(0.6, 1.5)
    f = f0 + (f1 - f0) * (t / d); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.sin(np.pi * t / d) ** 0.8 * 0.5
def creak(rng, d=0.7):
    t = t_axis(d); f = rng.uniform(140, 220) * (1 + 0.6 * t / d); ph = 2 * np.pi * np.cumsum(f) / SR
    raw = np.sign(np.sin(ph)) * 0.5 + 0.5 * np.sin(ph * 3.01); raw *= (1 + 0.5 * np.sin(2 * np.pi * 28 * t))
    return bandpass_fast(raw, 150, 2500) * np.sin(np.pi * t / d) ** 0.6 * 0.5
def crash(rng, d=0.9):
    s = np.zeros(int(d * SR)); place(s, thud(60, 0.5), 0.0, 1.0); place(s, bandpass_fast(noise(0.5), 200, 3000) * env_exp(0.5, 0.12), 0.0, 0.5)
    for k in range(10): place(s, bandpass_fast(noise(0.03), 1500, 6000) * env_exp(0.03, 0.006), rng.uniform(0.0, 0.5), rng.uniform(0.1, 0.4))   # snapping branches
    return s
def rewind_zip(d):
    """Tape rewind: a warbling tone sliding down + ticking, fading as the clock slows."""
    t = t_axis(d); u = t / d; f = 2600 * (1 - smoother(u)) ** 1.2 + 120; ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * (1 + 0.3 * np.sin(2 * np.pi * 9 * t)); tone = lowpass_fast(tone, 3000)
    return tone * (0.6 * (1 - smoother(u)) + 0.08) * 0.35
def pad_tone(d, f, a=0.8):
    t = t_axis(d); o = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.003 * t) + 0.25 * np.sin(2 * np.pi * f * 0.5 * t) + 0.15 * np.sin(2 * np.pi * f * 3.0 * t)
    return o / 1.9 * np.minimum(1, t / a) * np.minimum(1, (d - t) / 1.0)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(66); vd = os.path.dirname(os.path.abspath(__file__))
    script = json.load(open(os.path.join(vd, "script.json"))); years = script["years"]
    ev_path = os.path.join(vd, "build", "forest_events.json"); falls = json.load(open(ev_path))["falls"] if os.path.exists(ev_path) else []
    ta, Y = year_curve(tl, years, D)
    # --- wind bed, a little stronger when the clock runs fast, dipped under the explainer panel
    env = 0.5 + 0.5 * smoothstep(5, 60, Y); env[(ta >= B["why"]["start"]) & (ta < B["why"]["end"])] *= 0.55
    place(sfx, wind(D, rng) * env, 0, 0.14)
    # --- counter ticks: every year up to 12, every 5 to 60, every 10 after (forward and in the rewind)
    step = np.where(Y < 12, 1, np.where(Y < 60, 5, 10)); mark = np.floor(Y / step); edges = np.where(np.diff(mark) != 0)[0]
    for i in edges: place(sfx, wood_tick(0.05, 900 if Y[i] < 12 else 760), ta[i], 0.22)
    # --- sprout pops while cover is growing (weeds, grass, shrubs beats), Poisson
    for bid, rate in (("hook", 4), ("weeds", 9), ("grass", 7), ("shrubs", 4), ("pioneers", 2)):
        t = B[bid]["start"]
        while t < B[bid]["end"]:
            t += rng.exponential(1 / rate); place(sfx, sprout(rng), t, rng.uniform(0.08, 0.2))
    # --- birdsong: density grows with the forest (year > 12), none under the panel, back in the rewind as the years fall
    t = 0.0
    while t < D:
        yr = Y[min(int(t * SR), len(Y) - 1)]; rate = 0.2 + 2.6 * smoothstep(12, 70, yr)
        if B["why"]["start"] <= t < B["why"]["end"]: rate *= 0.4
        t += rng.exponential(1 / rate)
        for k in range(rng.integers(1, 4)): place(sfx, chirp(rng), t + k * rng.uniform(0.08, 0.16), rng.uniform(0.05, 0.14))
    # --- pioneer falls: creak then crash where the forward clock passes each fall year (thinned to one per 0.35 s)
    last = -1.0
    for fy in sorted(falls):
        idx = np.where((Y[:-1] < fy) & (Y[1:] >= fy) & (ta[1:] < B["ask"]["start"]))[0]
        if len(idx) == 0: continue
        t0 = ta[idx[0]]
        if t0 - last < 0.35: continue
        last = t0; g = 0.55 if fy < 100 else 0.35
        place(sfx, creak(rng), t0 - 0.5, 0.35 * g); place(sfx, crash(rng), t0 + 0.05, g)
    # --- stage tags and labels: dings; the stamp: thud; "born": big ding + shimmer; the panel: shimmer
    for bid, wd, f in (("weeds", "weeds", 1320), ("weeds", "wind", 1320), ("weeds", "sun", 1760), ("grass", "grasses", 1320), ("grass", "soil", 1320), ("shrubs", "birds", 1760), ("shrubs", "shrubs", 1320), ("shrubs", "shade", 1320),
                       ("pioneers", "birch", 1320), ("pioneers", "light", 1760), ("climax", "oaks", 1320), ("climax", "underneath", 1760), ("why", "succession", 1760), ("ask", "whats", 1320), ("ask", "cracks", 1320)):
        place(sfx, ding(f, 0.7), W(bid, wd), 0.15)
    place(sfx, thud(90, 0.3), W("pioneers", "cant"), 0.6); place(sfx, bandpass_fast(noise(0.12), 300, 2500) * env_exp(0.12, 0.03), W("pioneers", "cant"), 0.3)
    tb = W("climax", "born"); place(sfx, shimmer(0.5), tb - 0.45, 0.3); place(sfx, ding(1760, 1.4), tb, 0.3); place(sfx, ding(2637, 1.2), tb + 0.08, 0.15)
    place(sfx, shimmer(0.6), B["why"]["start"] + 0.1, 0.25)
    # --- the bird: wing flutter (fast noise bursts) as it crosses
    tb = W("shrubs", "birds")
    for k in range(9): place(sfx, bandpass_fast(noise(0.05), 800, 4000) * env_exp(0.05, 0.015), tb + 0.1 + k * 0.11, 0.12)
    # --- rewind: zip + a few reverse whooshes, ends silent so the loop is clean
    place(sfx, rewind_zip(B["loop"]["end"] - B["ask"]["start"] - 0.4), B["ask"]["start"], 0.5)
    for k in range(3): place(sfx, whoosh(0.5, 300, 3000, rev=True), B["ask"]["start"] + 0.2 + k * 1.1, 0.18 * (1 - k * 0.25))
    # --- cuts
    for bid in ("weeds", "grass", "shrubs", "pioneers", "climax", "why", "ask"): place(sfx, whoosh(0.3, 400, 4000), B[bid]["start"] - 0.12, 0.22)
    fps = tl["fps"]; place(sfx, whoosh(0.3, 400, 4000), B["pioneers"]["start"] + 90 / fps - 0.12, 0.2); place(sfx, whoosh(0.3, 400, 4000), B["climax"]["start"] + 84 / fps - 0.12, 0.2)
    # --- music: slow major bed, 84 bpm, I - V - vi - IV, a soft pulse; warmer (one more voice) once the trees arrive
    bpm = 84; beat = 60 / bpm; chords = [(48, 55, 64, 71), (43, 50, 59, 67), (45, 52, 60, 67), (41, 48, 57, 64)]
    tt = 0.0; ci = 0
    while tt < D:
        d = beat * 4; voices = chords[ci % 4] if tt > B["pioneers"]["start"] else chords[ci % 4][:3]
        for m in voices: place(music, pad_tone(d, 440 * 2 ** ((m - 69) / 12), 0.7), tt, 0.07)
        ci += 1; tt += d
    music[:] = lowpass_fast(music, 1100)
    tt = 0.0; k = 0
    while tt < D:
        place(music, thud(50, 0.25), tt, 0.25 if k % 4 == 0 else 0.12)
        if k % 2 == 1: place(music, tick(4200, 0.02) * 0.3, tt + beat / 2, 0.06)
        tt += beat; k += 1
