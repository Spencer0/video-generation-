"""Procedural audio primitives shared by every video (48 kHz mono float arrays)."""
import numpy as np
SR = 48000
rng = np.random.default_rng(3)

def t_axis(d): return np.arange(int(d * SR)) / SR
def env_exp(d, tau): t = t_axis(d); return np.exp(-t / tau)
def place(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i < 0: sig = sig[-i:]; i = 0
    n = min(len(sig), len(buf) - i)
    if n > 0: buf[i:i + n] += sig[:n] * gain
def lowpass(x, fc):  # one-pole, applied twice
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    for _ in range(2):
        for i in range(len(x)): acc = a * acc + (1 - a) * x[i]; y[i] = acc
        x = y.copy()
    return y
def lowpass_fast(x, fc):
    from numpy.fft import rfft, irfft
    X = rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / (1 + (f / fc) ** 4); return irfft(X, len(x))
def highpass_fast(x, fc):
    from numpy.fft import rfft, irfft
    X = rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= (f / fc) ** 2 / (1 + (f / fc) ** 2); return irfft(X, len(x))
def bandpass_fast(x, lo, hi): return highpass_fast(lowpass_fast(x, hi), lo)
def noise(d): return rng.standard_normal(int(d * SR))

def bubble_pop(f0=900, d=0.045, sweep=0.55):
    t = t_axis(d); f = f0 * (1 - sweep * t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / (d * 0.3)) * 0.8
def glug(f0=140, d=0.12):
    t = t_axis(d); f = f0 * (1 + 0.8 * t / d); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.04) * 0.9
def whoosh(d=0.35, lo=300, hi=4000, rev=False):
    n = bandpass_fast(noise(d), lo, hi); t = t_axis(d); e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    if rev: e = e ** 0.5 * (t / d)
    else: e = e ** 0.5 * (1 - t / d) ** 0.6
    return n * e / (np.abs(n).max() + 1e-9)
def tick(f=1800, d=0.03): t = t_axis(d); return np.sin(2 * np.pi * f * t) * np.exp(-t / 0.006)
def thud(f=70, d=0.35): t = t_axis(d); return np.sin(2 * np.pi * (f * (1 + 0.6 * np.exp(-t / 0.04))) * t) * np.exp(-t / 0.09)
def ding(f=1320, d=0.9):
    t = t_axis(d); return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t / 0.25) * 0.5
def shimmer(d=0.6):  # riser for stamps
    n = bandpass_fast(noise(d), 1500, 9000); t = t_axis(d); return n * (t / d) ** 2 / (np.abs(n).max() + 1e-9)
def clicklighter(): return (bandpass_fast(noise(0.02), 2000, 9000) * env_exp(0.02, 0.004)) * 2.0
def ignite(d=0.6):
    n = lowpass_fast(noise(d), 900); t = t_axis(d); e = np.exp(-t / 0.18) * np.minimum(1, t / 0.02); return n * e / (np.abs(n).max() + 1e-9)

def burner_roar(d, start, ramp=0.4):
    n = lowpass_fast(noise(d), 420) * 0.6 + lowpass_fast(noise(d), 2500) * 0.08
    t = t_axis(d); e = np.clip((t - start) / ramp, 0, 1)
    mod = 1 + 0.18 * lowpass_fast(noise(d), 6)
    return n * e * mod / (np.abs(n).max() + 1e-9)

