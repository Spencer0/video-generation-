#!/usr/bin/env python3
"""Acceptance checks for a finished video (numbers only; the eyes-on checks are listed as reminders).

usage: python3 pipeline/checks.py <video_id> [--out videos/<id>/out/checks.txt]
Measures: duration / beat lengths, first spoken word onset on the VO stem (50 ms RMS windows > -20 dBFS),
mean luma Y over the first 3 s and the whole final (ffmpeg signalstats YAVG), overlay safe-area bounding
box (alpha > 0 outside x 60..1020 / y 250..1500), and the frame-0 vs last-frame difference (loop seam).
"""
import sys, os, json, glob, subprocess, argparse, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import load_json, video_dir
from PIL import Image

def yavg(path):
    """Per-frame mean luma (ffmpeg signalstats YAVG) of a video file."""
    cmd = ["ffprobe", "-v", "error", "-f", "lavfi", "-i", f"movie={path},signalstats", "-show_entries", "frame_tags=lavfi.signalstats.YAVG", "-of", "csv=p=0"]
    return [float(x.strip(",")) for x in subprocess.run(cmd, capture_output=True, text=True).stdout.split() if x.strip(",")]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video_id"); ap.add_argument("--out", default=None); a = ap.parse_args()
    vd = video_dir(a.video_id); bd = os.path.join(vd, "build"); tl = load_json(os.path.join(bd, "timeline.json")); fps = tl["fps"]
    final = os.path.join(vd, "out", "final.mp4"); lines = []
    P = lambda s: (print(s), lines.append(s))
    # 1. duration + beats
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final], capture_output=True, text=True).stdout.strip())
    P(f"duration: {dur:.2f} s (timeline {tl['duration']:.2f} s)")
    for b in tl["beats"]: P(f"  beat {b['id']:8s} {b['duration']:5.2f} s {'OK' if b['duration'] <= 7.0 else 'TOO LONG'}")
    P(f"longest beat: {max(b['duration'] for b in tl['beats']):.2f} s")
    # 2. first spoken word onset on the VO stem
    vo, sr = sf.read(tl["vo"]); win = int(0.05 * sr); n = len(vo) // win
    rms = 20 * np.log10(np.sqrt((vo[:n * win].reshape(n, win) ** 2).mean(1)) + 1e-9); first = next((i for i, r in enumerate(rms) if r > -20), None)
    P(f"first spoken word onset (VO stem, 50 ms RMS > -20 dBFS): {first * 0.05:.2f} s" if first is not None else "no speech found")
    # 3. mean luma
    vals = yavg(final); n3 = int(3 * fps)
    P(f"mean luma Y: first 3 s = {np.mean(vals[:n3]):.1f}, whole = {np.mean(vals):.1f}, darkest frame = {min(vals):.1f} (frame {int(np.argmin(vals))})")
    # 4. loop seam: frame 0 vs last frame (footage only, from the background concat list) and the final
    def frame_at(i):
        p = subprocess.run(["ffmpeg", "-v", "error", "-i", final, "-vf", f"select=eq(n\\,{i})", "-vframes", "1", "-f", "image2pipe", "-pix_fmt", "rgb24", "-vcodec", "rawvideo", "-"], capture_output=True).stdout
        return np.frombuffer(p, np.uint8).reshape(tl["height"], tl["width"], 3).astype(float)
    nfr = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", final], capture_output=True, text=True).stdout.strip())
    f0, fl = frame_at(0), frame_at(nfr - 1)
    P(f"frames in final: {nfr} (timeline {tl['total_frames']})")
    P(f"loop seam: mean abs pixel difference frame 0 vs last frame = {np.abs(f0 - fl).mean():.1f} / 255 (lower is more seamless)")
    # 5. overlay safe area
    worst = [0, 0, 0, 0]; bad = []
    for f in sorted(glob.glob(os.path.join(bd, "overlay", "ov_*.png")))[::3]:
        al = np.asarray(Image.open(f).convert("RGBA"))[:, :, 3] > 128   # solid text/pills; ignores panel shadows
        ys, xs = np.where(al)
        if len(xs) == 0: continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        if x0 == 0 and x1 == 1079 and y0 == 0 and y1 == 1919: continue   # full-frame cut flash, by design
        if x0 < 60 or x1 > 1020 or y0 < 250 or y1 > 1500: bad.append((os.path.basename(f), int(x0), int(x1), int(y0), int(y1)))
    P(f"overlay safe area (x 60..1020, y 250..1500): {'all sampled frames inside' if not bad else str(len(bad)) + ' frames outside, e.g. ' + str(bad[:3])}")
    # 6. loudness
    ln = subprocess.run(["ffmpeg", "-v", "info", "-i", final, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=summary", "-f", "null", "-"], capture_output=True, text=True).stderr
    il = [l.strip() for l in ln.splitlines() if l.strip().startswith(("Input Integrated", "Input True Peak"))]
    P("loudness: " + "; ".join(il))
    out = a.out or os.path.join(vd, "out", "checks.txt")
    with open(out, "w") as f: f.write("\n".join(lines) + "\n")
    print("wrote", out)

if __name__ == "__main__":
    main()
