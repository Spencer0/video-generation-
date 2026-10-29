#!/usr/bin/env python3
"""Acceptance checks for a finished video (numbers only; the eyes-on checks are listed as reminders).

usage: python3 pipeline/checks.py <video_id> [--out videos/<id>/out/checks.txt]
Measures: duration / beat lengths, first spoken word onset on the VO stem (50 ms RMS windows > -20 dBFS),
mean luma Y over the first 3 s and the whole final (ffmpeg signalstats YAVG), overlay pixels (alpha > 128)
inside the TikTok UI zones of pipeline/safe_area.json, and the frame-0 vs last-frame difference (loop seam).
--only-safe-area runs just the zone check (works on an estimated timeline + an --every N overlay render).
"""
import sys, os, json, glob, subprocess, argparse, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import load_json, video_dir
from PIL import Image

def yavg(path):
    """Per-frame mean luma (ffmpeg signalstats YAVG) of a video file."""
    cmd = ["ffprobe", "-v", "error", "-f", "lavfi", "-i", f"movie={path},signalstats", "-show_entries", "frame_tags=lavfi.signalstats.YAVG", "-of", "csv=p=0"]
    return [float(x.strip(",")) for x in subprocess.run(cmd, capture_output=True, text=True).stdout.split() if x.strip(",")]

def safe_area_check(overlay_dir, P, step=3):
    """Overlay pixels with alpha > 128 inside any UI zone of pipeline/safe_area.json. Full-frame cut flashes are skipped.
    Reports per zone: frames hit, worst frame and the bounding box of the offending pixels (in video coordinates)."""
    sa = load_json(os.path.join(os.path.dirname(os.path.abspath(__file__)), "safe_area.json")); hits = {z["id"]: [] for z in sa["zones"]}
    files = sorted(glob.glob(os.path.join(overlay_dir, "ov_*.png")))[::step]
    for f in files:
        al = np.asarray(Image.open(f).convert("RGBA"))[:, :, 3] > 128
        ys, xs = np.where(al)
        if len(xs) == 0 or (xs.min() == 0 and xs.max() == al.shape[1] - 1 and ys.min() == 0 and ys.max() == al.shape[0] - 1): continue
        for z in sa["zones"]:
            sub = al[z["y0"]:z["y1"], z["x0"]:z["x1"]]; n = int(sub.sum())
            if n > 30:   # a few anti-aliased edge pixels are fine
                zy, zx = np.where(sub); hits[z["id"]].append((n, os.path.basename(f), int(zx.min() + z["x0"]), int(zx.max() + z["x0"]), int(zy.min() + z["y0"]), int(zy.max() + z["y0"])))
    bad = {k: v for k, v in hits.items() if v}
    P(f"safe area ({len(files)} overlay frames sampled against {len(sa['zones'])} UI zones): {'PASS, nothing readable under the TikTok UI' if not bad else 'FAIL'}")
    for k, v in bad.items():
        w = max(v); P(f"  {k}: {len(v)} frames, worst {w[1]} with {w[0]} px in x {w[2]}..{w[3]}, y {w[4]}..{w[5]}  ({next(z['why'] for z in sa['zones'] if z['id'] == k)})")
    return not bad

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video_id"); ap.add_argument("--out", default=None); ap.add_argument("--only-safe-area", action="store_true")
    ap.add_argument("--overlay-dir", default=None, help="overlay PNG dir (default build/overlay)"); a = ap.parse_args()
    vd = video_dir(a.video_id); bd = os.path.join(vd, "build"); tl = load_json(os.path.join(bd, "timeline.json")); fps = tl["fps"]
    final = os.path.join(vd, "out", "final.mp4"); lines = []
    P = lambda s: (print(s), lines.append(s))
    if tl.get("estimated"): P("WARNING: timeline.json is ESTIMATED (fake_timeline.py); timing numbers below are not real, re-run tts.py before assembling")
    if a.only_safe_area:
        ok = safe_area_check(a.overlay_dir or os.path.join(bd, "overlay"), P, step=1); sys.exit(0 if ok else 1)
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
    # 5. overlay safe area (TikTok UI zones)
    safe_area_check(a.overlay_dir or os.path.join(bd, "overlay"), P)
    # 6. loudness
    ln = subprocess.run(["ffmpeg", "-v", "info", "-i", final, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=summary", "-f", "null", "-"], capture_output=True, text=True).stderr
    il = [l.strip() for l in ln.splitlines() if l.strip().startswith(("Input Integrated", "Input True Peak"))]
    P("loudness: " + "; ".join(il))
    out = a.out or os.path.join(vd, "out", "checks.txt")
    with open(out, "w") as f: f.write("\n".join(lines) + "\n")
    print("wrote", out)

if __name__ == "__main__":
    main()
