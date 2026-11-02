"""Sound cues for video 006 (tornado). Fun first: wind bed with gusts, debris whooshes, a formant-synth cow moo,
a spring boing for the trampoline gag, skate swishes for the skater, a rising whirr under the gauge, office-chair
creaks, dings on labels, whooshes on cuts, and an upbeat plucky bed at ~-20 dB."""
import numpy as np
from audiolib import *
CAPTION_TICKS = True

def formant(sig, peaks):
    """Shape a signal's spectrum with Gaussian resonances: peaks = [(f_centre, bandwidth, gain), ...]."""
    from numpy.fft import rfft, irfft
    X = rfft(sig); f = np.fft.rfftfreq(len(sig), 1 / SR); g = np.full_like(f, 0.03)
    for fc, bw, gain in peaks: g += gain * np.exp(-0.5 * ((f - fc) / bw) ** 2)
    return irfft(X * g, len(sig))
def moo(d=1.0, f0=118.0):
    """Cartoon cow: harmonic-rich glottal source with a droop, 'm' (nasal, dull) opening into 'oo' (rounder)."""
    t = t_axis(d); f = f0 * (1 - 0.18 * t / d) * (1 + 0.025 * np.sin(2 * np.pi * 5.5 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR; src = sum(np.sin(ph * n) / n for n in range(1, 14))
    env = np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.25) * (0.55 + 0.45 * np.minimum(1, t / 0.3))
    m = formant(src, [(260, 90, 1.0), (900, 180, 0.35), (2400, 300, 0.1)]) * (1 - np.minimum(1, t / 0.3))
    oo = formant(src, [(330, 110, 1.0), (750, 160, 0.6), (2300, 350, 0.12)]) * np.minimum(1, t / 0.3)
    out = (m + oo) * env; return out / (np.abs(out).max() + 1e-9)
def boing(d=0.7):
    """Spring: a pitch that drops while wobbling, with a bright click at the start."""
    t = t_axis(d); f = 420 * np.exp(-t / 0.25) * (1 + 0.35 * np.exp(-t / 0.2) * np.sin(2 * np.pi * 28 * t)) + 90
    ph = 2 * np.pi * np.cumsum(f) / SR; o = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)) * np.exp(-t / 0.22)
    o[: int(0.01 * SR)] += bandpass_fast(noise(0.01), 2000, 8000) * 1.5; return o / (np.abs(o).max() + 1e-9)
def wind(d, seed=1):
    """Tornado roar: low rumble + mid hiss, gusting slowly, with a faint whistle."""
    r = np.random.default_rng(seed); t = t_axis(d)
    low = lowpass_fast(r.standard_normal(int(d * SR)), 260); mid = bandpass_fast(r.standard_normal(int(d * SR)), 500, 2600)
    gust = 0.6 + 0.4 * lowpass_fast(r.standard_normal(int(d * SR)), 0.6) / 0.25; gust = np.clip(gust, 0.3, 1.4)
    out = low / (np.abs(low).max() + 1e-9) * 0.8 + mid / (np.abs(mid).max() + 1e-9) * 0.25
    return out * gust
def swish(d=0.25):
    n = bandpass_fast(noise(d), 1500, 7000); t = t_axis(d); e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5; return n * e / (np.abs(n).max() + 1e-9)
def creak(d=0.18, f0=900):
    t = t_axis(d); f = f0 * (1 + 0.25 * np.sin(2 * np.pi * 9 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    o = (2 * ((ph / (2 * np.pi)) % 1) - 1) * np.sin(np.pi * t / d) ** 0.6; return lowpass_fast(o, 3000) / (np.abs(o).max() + 1e-9)
def whirr(d, speed_fn):
    """Spinning hum whose pitch follows speed_fn(t) in 0..1: for the gauge climb."""
    t = t_axis(d); sp = np.array([speed_fn(x) for x in t]); f = 55 + 260 * sp
    ph = 2 * np.pi * np.cumsum(f) / SR; o = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph) + 0.12 * np.sin(4 * ph)
    o *= 1 + 0.25 * np.sin(2 * np.pi * f * 0.5 * t / 10); return o / (np.abs(o).max() + 1e-9) * (0.4 + 0.6 * sp)
def flutter(d, rate=8.0, rise=(500, 1100)):
    """Full-speed footage: whooshes passing at `rate` Hz (the cow's orbit rate at 20x) under a rising whine."""
    t = t_axis(d); n = bandpass_fast(noise(d), 400, 5000); am = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * rate * t)) ** 3
    f = rise[0] + (rise[1] - rise[0]) * t / d; ph = 2 * np.pi * np.cumsum(f) / SR; wh = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * 0.25
    out = n / (np.abs(n).max() + 1e-9) * am + wh; return out / (np.abs(out).max() + 1e-9)
def sweep(d, f0, f1):
    """Tape-speed glide: a buzzy tone sliding from f0 to f1 (down = snapping into slow motion, up = back to full speed)."""
    t = t_axis(d); f = f0 * (f1 / f0) ** (t / d); ph = 2 * np.pi * np.cumsum(f) / SR
    o = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * np.sin(np.pi * t / d) ** 0.5; return o / (np.abs(o).max() + 1e-9)
def pluck(f, d=0.35):
    t = t_axis(d); return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)) * np.exp(-t / 0.09) * np.minimum(1, t / 0.003)
def kick(d=0.25): t = t_axis(d); return np.sin(2 * np.pi * (48 + 90 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.08)

def cues(tl, B, W, sfx, music, D, N):
    rng = np.random.default_rng(66); ta = t_axis(D); fps = tl["fps"]
    # wind bed under every beat; quieter under the blurred explainer panels, loudest on the hero and close-up footage
    env = np.zeros_like(ta)
    for bid, g in (("hook", 1.0), ("fact", 0.5), ("cheque", 0.3), ("ask", 1.1), ("turn", 1.0), ("skater", 0.35), ("roll", 0.6), ("tilt", 0.8), ("squeeze", 1.0), ("speed", 1.0), ("tryit", 0.35), ("loop", 1.0)):
        b = B[bid]; env += g * np.clip((ta - b["start"] + 0.25) / 0.5, 0, 1) * np.clip((b["end"] - ta + 0.25) / 0.5, 0, 1)
    FAST_T = 0.5; LOOP_FAST_AT = 12 / fps; tl_fast = B["loop"]["start"] + LOOP_FAST_AT
    env *= 1 - 0.7 * ((ta < FAST_T) | (ta > tl_fast))   # wind ducks under the full-speed flutter
    place(sfx, wind(D) * np.clip(env, 0, 1.2), 0, 0.22)
    # full speed -> snap into slow motion (hook), and back up to full speed at the very end (loop)
    place(sfx, flutter(FAST_T), 0.0, 0.5); place(sfx, sweep(0.35, 1400, 120), FAST_T - 0.05, 0.4); place(sfx, thud(70, 0.4), FAST_T, 0.6)
    place(sfx, sweep(0.4, 120, 1400), tl_fast - 0.1, 0.35); place(sfx, flutter(D - tl_fast + 0.1, rise=(900, 1100)), tl_fast, 0.45)
    # debris whooshes on the live footage (hero, squeeze, record, close-up): Poisson-ish passes, pitched by size
    for bid, rate in (("hook", 1.6), ("turn", 1.6), ("squeeze", 2.2), ("speed", 1.6), ("ask", 2.0), ("loop", 1.6)):
        b = B[bid]; t = b["start"] + rng.uniform(0, 0.4) + (FAST_T if bid == "hook" else 0)
        while t < (b["end"] if bid != "loop" else tl_fast):
            lo = rng.uniform(250, 700); place(sfx, whoosh(rng.uniform(0.25, 0.5), lo, lo * 6), t, rng.uniform(0.12, 0.3)); t += rng.exponential(1 / rate) + 0.15
    # the cow: moo on the hook, on 'cow' in the ask, and once in the loop (so the wrap lands on a moo)
    place(sfx, moo(1.0), 0.62, 0.55); place(sfx, moo(0.9, 105), W("ask", "her") + 0.05, 0.5); place(sfx, moo(0.8, 125), B["loop"]["start"] + 0.05, 0.3)
    place(sfx, boing(), B["hook"]["start"] + 1.2, 0.35)                                      # trampoline tag
    place(sfx, ding(1760, 0.5), B["hook"]["start"] + 1.8, 0.12)                                # gnome tag
    # skater: skate swishes at the spin rate (slow with arms out, fast after 'skater')
    b = B["skater"]; tS = W("skater", "skater"); t = b["start"] + 0.2; k = 0
    while t < b["end"] - 0.2:
        fast = t > tS; place(sfx, swish(0.22 if fast else 0.3), t, 0.2 if fast else 0.14); t += (0.14 if fast else 0.45); k += 1
    place(sfx, shimmer(0.6), b["start"] + 0.05, 0.25)
    # fact: falling whistle, a big thud on the landing (shot L lands at 1.4 s), an indignant moo, ding on 'survived'
    b = B["fact"]; T_LAND = 1.4
    place(sfx, sweep(1.3, 1600, 500) * 0.6, b["start"] + 0.05, 0.3); place(sfx, thud(60, 0.5), b["start"] + T_LAND, 0.9); place(sfx, lowpass_fast(noise(0.3), 300) * env_exp(0.3, 0.06), b["start"] + T_LAND, 0.5)
    place(sfx, moo(0.9, 98), b["start"] + T_LAND + 0.45, 0.5); place(sfx, ding(1320, 0.6), W("fact", "quarter"), 0.14); place(sfx, ding(1760, 0.8), W("fact", "survived"), 0.18)
    # cheque: panel shimmer, paper flutter while it flies, ding on the number
    b = B["cheque"]; place(sfx, shimmer(0.6), b["start"] + 0.05, 0.25); tF = W("cheque", "flew")
    fl = bandpass_fast(noise(1.4), 1200, 6000); fl = fl / (np.abs(fl).max() + 1e-9) * (0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * 13 * t_axis(1.4))) ** 2) * np.sin(np.pi * t_axis(1.4) / 1.4) ** 0.5
    place(sfx, fl, tF, 0.25); place(sfx, ding(1760, 0.8), W("cheque", "twentythree"), 0.18)
    # turn: record-scratch style brake on 'how' (fast down-sweep + noise), then the question ding
    tH = W("turn", "how"); place(sfx, sweep(0.22, 900, 140) * 0.8, tH - 0.15, 0.35); place(sfx, bandpass_fast(noise(0.2), 800, 4000) * env_exp(0.2, 0.05) * 0.6, tH - 0.15, 0.3); place(sfx, ding(1320, 0.6), W("turn", "throw"), 0.14)
    # roll: a low rolling rumble under the tube, ding on 'tube', pop on 'rolling'
    b = B["roll"]; rum = lowpass_fast(noise(b["duration"]), 120); place(sfx, rum / (np.abs(rum).max() + 1e-9) * (1 + 0.5 * np.sin(2 * np.pi * 1.1 * t_axis(b["duration"]))), b["start"], 0.35)
    place(sfx, ding(1320, 0.6), W("roll", "rolls"), 0.14); place(sfx, ding(1760, 0.6), W("roll", "tube"), 0.14)
    # tilt: rising whoosh for the updraft, a 'thunk' when it stands
    place(sfx, whoosh(1.4, 200, 3000, rev=True), W("tilt", "updraft"), 0.4); place(sfx, thud(80, 0.4), W("tilt", "stands") + 0.3, 0.5)
    # squeeze: whirr that climbs with the gauge (same curve as beats.js squeezeSpeed), gauge ticks, ding on 'faster', swishes on 'arms'
    b = B["squeeze"]; sq = lambda x: 0.2 + 0.8 * min(1, max(0, (x - 0.6) / 3.8)) ** 1.5
    place(sfx, whirr(b["duration"], lambda x: sq(x) * (1 - max(0, (x - b["duration"] + 0.4) / 0.4))), b["start"], 0.22)
    t = b["start"] + 0.6
    while t < b["end"] - 0.3:
        place(sfx, tick(2200, 0.02), t, 0.15); t += 0.5 - 0.42 * sq(t - b["start"])
    place(sfx, ding(1760, 0.7), W("squeeze", "faster"), 0.18)
    tA = W("squeeze", "arms")
    for k in range(6): place(sfx, swish(0.18), tA + 0.15 + k * 0.13, 0.18)
    # speed: needle slam on 'three' (clack + shimmer + big ding), whirr held high
    b = B["speed"]; place(sfx, whirr(b["duration"], lambda x: 0.95), b["start"], 0.18)
    t3 = W("speed", "three"); place(sfx, shimmer(0.5), t3 - 0.4, 0.3); place(sfx, thud(140, 0.2), t3 + 0.45, 0.5); place(sfx, ding(2093, 1.0), t3 + 0.45, 0.25)
    # tryit: panel shimmer, chair creaks while it spins, swishes when the arms come in
    b = B["tryit"]; place(sfx, shimmer(0.6), b["start"] + 0.05, 0.25); tSp = W("tryit", "spin"); tAr = W("tryit", "arms")
    t = tSp
    while t < b["end"] - 0.3:
        place(sfx, creak(0.16, rng.uniform(700, 1100)), t, 0.2); t += 0.42 if t < tAr else 0.16
    place(sfx, ding(1320, 0.6), W("tryit", "try"), 0.14)
    # ask: ding on 'name', question pop
    place(sfx, ding(1760, 0.7), W("ask", "name"), 0.16); place(sfx, bubble_pop(600, 0.08, 0.4), W("ask", "cow") + 0.3, 0.3)
    # cuts
    for bid in ("fact", "ask", "turn", "roll", "squeeze", "speed"): place(sfx, whoosh(0.3, 400, 4000), B[bid]["start"] - 0.12, 0.25)
    # music: 122 bpm, bright major-key pluck arpeggio over a kick/hat pulse, kept quiet (the mixer's 0.12 gain -> ~-20 dB)
    bpm = 122; beat = 60 / bpm; chords = [(57, 60, 64, 69), (53, 57, 60, 65), (55, 59, 62, 67), (52, 55, 59, 64)]
    tt = 0.0; k = 0
    while tt < D:
        ch = chords[(k // 8) % 4]; n = ch[k % 4] + (12 if k % 8 >= 4 else 0)
        place(music, pluck(440 * 2 ** ((n - 69) / 12)), tt, 0.5); tt += beat / 2; k += 1
    tt = 0.0; k = 0
    while tt < D:
        place(music, kick(), tt, 0.9 if k % 2 == 0 else 0.5)
        place(music, tick(6000, 0.02) * 0.35, tt + beat / 2, 0.25)
        if k % 4 == 1: place(music, thud(60, 0.3), tt + beat / 2, 0.3)
        tt += beat; k += 1
    music[:] = lowpass_fast(music, 2500)
