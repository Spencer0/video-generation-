"""Sound cues for video 006 (Mount St. Helens, 1980). The blast lands on frame 0 and again on 'explodes';
calm-morning birds under 'who'; a growing sub pulse under the bulge; quake rumble -> crack -> landslide roar;
soda hiss + pop; radio static under the call that cuts to near-silence; a soft pad for Harry and the toll.
The music bed is taiko-style hits + a minor pad for the tense beats and drops out for the dead-air moment."""
import numpy as np
from audiolib import *
CAPTION_TICKS = True

def norm(x): return x / (np.abs(x).max() + 1e-9)
def boom(d=3.0):
    """Explosion: sharp crack, sub thump, long low roar tail."""
    t = t_axis(d); out = np.zeros_like(t)
    place(out, norm(bandpass_fast(noise(0.25), 700, 7000)) * env_exp(0.25, 0.04), 0.0, 0.9)
    place(out, thud(48, 1.4), 0.0, 1.6); place(out, thud(90, 0.5), 0.02, 0.9)
    out += norm(lowpass_fast(noise(d), 220)) * np.exp(-t / 0.9) * 1.1 + norm(bandpass_fast(noise(d), 200, 1400)) * np.exp(-t / 0.45) * 0.5
    return norm(out)
def rumble(d, fc=110): return norm(lowpass_fast(noise(d), fc)) * (1 + 0.3 * norm(lowpass_fast(noise(d), 5)))
def roar(d): return norm(lowpass_fast(noise(d), 500) + 0.25 * bandpass_fast(noise(d), 500, 3000)) * (1 + 0.25 * norm(lowpass_fast(noise(d), 7)))
def chirp(f0, f1, d=0.09):
    t = t_axis(d); f = f0 + (f1 - f0) * (t / d); return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 2
def static(d, rng):
    n = norm(bandpass_fast(noise(d), 1200, 5200)); t = t_axis(d)
    crack = np.repeat(rng.uniform(0.35, 1.0, int(d * 40) + 1), SR // 40)[:len(t)]
    return n * crack
def pad_tone(d, f, a=0.6, rel=0.8):
    t = t_axis(d); o = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.004 * t) + 0.3 * np.sin(2 * np.pi * f * 0.5 * t) + 0.2 * np.sin(2 * np.pi * f * 1.498 * t)
    return o / 2.0 * np.minimum(1, t / a) * np.clip((d - t) / rel, 0, 1)
def taiko(f=62): return thud(f, 0.5) + 0.25 * norm(bandpass_fast(noise(0.5), 150, 900)) * env_exp(0.5, 0.05)
def midi(m): return 440 * 2 ** ((m - 69) / 12)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(606); ta = t_axis(D)
    def span(a, b, fi=0.15, fo=0.3): return np.clip((ta - a) / fi, 0, 1) * np.clip((b - ta) / fo, 0, 1)
    hook, who, bulge, slide, blast, radio, harry, toll, ask = (B[k] for k in ("hook", "who", "bulge", "slide", "blast", "radio", "harry", "toll", "ask"))
    # --- hook: the blast is already happening on frame 0
    place(sfx, boom(3.2), 0.0, 1.0)
    place(sfx, roar(D) * span(-1, hook["end"], 0.01, 0.25), 0, 0.30)
    tc = W("hook", "world") + 0.05
    place(sfx, whoosh(0.25, 1500, 9000), tc - 0.1, 0.5); place(sfx, ding(2640, 0.5), tc, 0.25)        # eye cut-in "shing"
    # --- who: cut to calm. birds, light air, tag dings
    place(sfx, whoosh(0.35, 300, 4000, rev=True), who["start"] - 0.3, 0.4)
    place(sfx, norm(bandpass_fast(noise(D), 300, 1500)) * span(who["start"], who["end"], 0.3, 0.3), 0, 0.035)
    tt = who["start"] + 0.3
    while tt < who["end"] - 0.3:
        f = rng.uniform(2600, 3800)
        for k in range(int(rng.integers(2, 5))): place(sfx, chirp(f, f * rng.uniform(1.15, 1.5), 0.07), tt + k * 0.11, 0.10)
        tt += rng.uniform(0.5, 1.1)
    place(sfx, ding(1320, 0.6), W("who", "david"), 0.18); place(sfx, whoosh(0.25, 400, 4000), W("who", "mount") - 0.2, 0.3)
    place(sfx, ding(1760, 0.6), W("who", "six"), 0.2)
    # --- bulge: a pulse that speeds up, like something breathing under the rock
    tt = bulge["start"] + 0.1; gap = 0.55
    while tt < bulge["end"]:
        place(sfx, thud(52, 0.4), tt, 0.5); place(sfx, thud(52, 0.3), tt + 0.14, 0.3); tt += gap; gap = max(0.3, gap * 0.9)
    place(sfx, rumble(D, 80) * span(bulge["start"], slide["start"] + 1.2, 1.5, 0.5), 0, 0.22)
    place(sfx, ding(1320, 0.6), W("bulge", "magma"), 0.15); place(sfx, ding(1760, 0.7), W("bulge", "five"), 0.2)
    # --- slide: clock tick, quake, crack, landslide roar
    for k in range(3): place(sfx, tick(1500, 0.03), W("slide", "eight") + k * 0.22, 0.35)
    tq = W("slide", "earthquake"); tlz = W("slide", "loose")
    place(sfx, rumble(D, 140) * span(tq, tlz + 1.6, 0.12, 1.2), 0, 0.75)
    place(sfx, norm(bandpass_fast(noise(0.3), 500, 6000)) * env_exp(0.3, 0.05), tlz - 0.03, 0.8); place(sfx, thud(60, 0.8), tlz, 1.0)
    place(sfx, roar(D) * span(tlz, slide["end"] + 0.3, 0.2, 1.4), 0, 0.5)
    for k in range(14): place(sfx, thud(rng.uniform(70, 130), 0.2), tlz + 0.2 + rng.uniform(0, 1.8), rng.uniform(0.15, 0.4))   # boulders
    place(sfx, thud(45, 0.7), W("slide", "biggest"), 0.7)
    # --- blast: soda hiss + pop, then the lateral blast
    ts = W("blast", "shaken") - 0.25; tx = W("blast", "explodes") - 0.06
    place(sfx, norm(bandpass_fast(noise(0.75), 3000, 11000)) * np.linspace(0.1, 1, int(0.75 * SR)) ** 2, ts, 0.3)
    place(sfx, bubble_pop(700, 0.08, 0.6), ts + 0.75, 0.9); place(sfx, norm(bandpass_fast(noise(0.6), 2500, 11000)) * env_exp(0.6, 0.18), ts + 0.75, 0.45)
    place(sfx, rumble(D, 120) * span(blast["start"], tx, 0.3, 0.05), 0, 0.35)
    place(sfx, shimmer(0.5), tx - 0.5, 0.4)
    place(sfx, boom(3.4), tx, 1.0)
    place(sfx, roar(D) * span(tx, radio["start"] + 1.4, 0.05, 0.3), 0, 0.42)
    place(sfx, thud(50, 0.6), W("blast", "three"), 0.8); place(sfx, whoosh(0.6, 200, 3000), W("blast", "three") - 0.1, 0.4)
    # --- radio: grab, the call over static, then dead air
    tv = W("radio", "vancouver") - 0.06; te = W("radio", "it") + 0.42
    place(sfx, whoosh(0.3, 500, 6000), W("radio", "grabs") - 0.1, 0.5); place(sfx, tick(900, 0.04), W("radio", "grabs") + 0.2, 0.6)
    place(sfx, roar(D) * span(radio["start"] + 1.0, te, 0.4, 0.03) * np.clip(0.4 + (ta - tv) / (te - tv) * 0.6, 0.4, 1.0), 0, 0.55)
    place(sfx, static(D, rng) * span(tv, te, 0.03, 0.02), 0, 0.16)
    place(sfx, tick(1900, 0.06), tv - 0.05, 0.5)                                # squelch open
    place(sfx, shimmer(0.4), te - 0.4, 0.5)
    place(sfx, static(D, rng) * span(te, te + 0.45, 0.005, 0.4), 0, 0.22)        # the carrier dies
    place(sfx, pad_tone(radio["end"] - te, 55, 0.3, 0.3), te, 0.18)
    # --- harry: warm room tone, birds again (the day before)
    place(sfx, whoosh(0.4, 300, 3000, rev=True), harry["start"] - 0.35, 0.3)
    tt = harry["start"] + 0.4
    while tt < harry["end"] - 0.3:
        f = rng.uniform(2400, 3200); place(sfx, chirp(f, f * 1.3, 0.08), tt, 0.07); place(sfx, chirp(f * 1.1, f * 1.4, 0.08), tt + 0.12, 0.07); tt += rng.uniform(0.7, 1.3)
    place(sfx, ding(1320, 0.6), W("harry", "harry"), 0.16); place(sfx, ding(990, 0.9), W("harry", "refused"), 0.16)
    # --- toll: one low bell, wind over ash; then the roadblock
    place(sfx, ding(330, 2.2), W("toll", "fiftyseven"), 0.5); place(sfx, ding(660, 1.6), W("toll", "fiftyseven"), 0.15)
    tb = W("toll", "but") - 0.08
    place(sfx, norm(bandpass_fast(noise(D), 200, 900)) * span(toll["start"], tb, 0.2, 0.2), 0, 0.10)
    place(sfx, whoosh(0.35, 300, 4000), tb - 0.15, 0.35); place(sfx, thud(110, 0.25), W("toll", "close"), 0.5); place(sfx, ding(1320, 0.6), W("toll", "close"), 0.15)
    place(sfx, shimmer(0.6), W("toll", "thousands") - 0.6, 0.3); place(sfx, ding(1760, 0.9), W("toll", "thousands"), 0.25)
    for k in range(18): place(sfx, bubble_pop(rng.uniform(500, 900), 0.03, 0.3), W("toll", "thousands") + k * 0.035, 0.12)   # the crowd pops in
    # --- ask: question ding, then a riser into the loop (frame 0 is the blast again)
    place(sfx, whoosh(0.35, 300, 4000), ask["start"] - 0.15, 0.3); place(sfx, ding(1760, 0.9), W("ask", "would"), 0.22)
    place(sfx, shimmer(0.9), ask["end"] - 0.9, 0.55); place(sfx, rumble(1.0, 100) * np.linspace(0, 1, SR) ** 2, ask["end"] - 1.0, 0.5)

    # --- music: D minor pad + taiko pattern at 120 bpm on the tense beats; warm pad for Harry / toll / ask
    bpm = 120; q = 60 / bpm
    tense = span(0, who["start"], 0.01, 0.2) + span(bulge["start"], W("radio", "it") + 0.42, 0.8, 0.02)
    soft = span(who["start"], bulge["start"] + 0.5, 0.3, 0.8) + span(harry["start"], D, 0.4, 0.6)
    drums = np.zeros(N); padT = np.zeros(N); padS = np.zeros(N)
    pat = [1.0, 0, 0.5, 0, 0.8, 0, 0.5, 0.6]   # eighth notes
    tt = 0.0; k = 0
    while tt < D:
        g = pat[k % 8]
        if g: place(drums, taiko(62 if k % 8 in (0, 4) else 82), tt, g)
        if k % 2 == 1: place(drums, tick(6000, 0.02), tt, 0.12)
        tt += q / 2; k += 1
    chordsT = [(38, 50, 53, 57), (36, 48, 51, 55), (34, 46, 50, 53), (33, 45, 49, 52)]     # Dm  Cm  Bb  A
    chordsS = [(41, 53, 57, 60), (36, 52, 55, 60), (38, 53, 57, 62), (34, 50, 53, 58)]     # F   C   Dm  Bb
    tt = 0.0; ci = 0
    while tt < D:
        d = q * 8
        for m in chordsT[ci % 4]: place(padT, pad_tone(d + 0.4, midi(m), 0.4, 0.6), tt, 0.12)
        for m in chordsS[ci % 4]: place(padS, pad_tone(d + 0.4, midi(m), 0.8, 0.9), tt, 0.12)
        ci += 1; tt += d
    music[:] = (drums * 0.8 + lowpass_fast(padT, 1400)) * np.clip(tense, 0, 1) + lowpass_fast(padS, 1100) * np.clip(soft, 0, 1) * 0.9
