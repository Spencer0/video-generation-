#!/usr/bin/env python3
"""Composite 3D frames + overlay PNGs + audio mix into the final vertical MP4.

usage: python3 pipeline/assemble.py <video_id> [--out path] [--preview]

The 3D shots are rendered at a lower resolution for speed; here they are
mapped onto the timeline (which shot/frame each output frame shows), upscaled
to the delivery size with lanczos, blurred/dimmed during the explainer beats,
and the overlay layer is alpha-composited on top. Missing 3D frames (render
still running) fall back to the nearest rendered frame so previews can be cut
at any time.
"""
import sys, os, glob, argparse, subprocess, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import load_json, video_dir

# background plan: for each beat, which shot and which shot-frame the beat starts on.
# "loop" lets a beat run past the end of a shot by wrapping.
BG_PLAN = {
    "hook":    ("A", 0),
    "empty":   ("B", 0),
    "water":   ("C", 0),
    "temps":   ("C", 24),     # behind the HOW HOT panel: replay the boil ramp
    "sponge":  ("D", 0),      # behind the explainer panels; blurred + dimmed
    "ceiling": ("D", 60),
    "punch":   ("D", 0),
    "cta":     ("C", 100),
}
BLUR_BEATS = ("sponge", "ceiling")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video_id"); ap.add_argument("--out", default=None); ap.add_argument("--preview", action="store_true")
    ap.add_argument("--crf", type=int, default=17)
    a = ap.parse_args()
    vd = video_dir(video_id := a.video_id); bd = os.path.join(vd, "build")
    tl = load_json(os.path.join(bd, "timeline.json")); fps = tl["fps"]
    frames_dir = os.path.join(bd, "frames")
    shots = {}
    for s in "ABCD":
        fl = sorted(glob.glob(os.path.join(frames_dir, s, f"{s}_*.png")))
        shots[s] = ([int(os.path.basename(f)[2:6]) for f in fl], fl)
    missing = 0
    def shot_frame(s, i):
        nonlocal missing
        idx, files = shots[s]
        if not files: raise SystemExit(f"no frames rendered for shot {s}")
        if i in idx: return files[idx.index(i)]
        missing += 1
        j = bisect.bisect_left(idx, i); j = min(max(j, 0), len(idx) - 1)
        if j > 0 and abs(idx[j - 1] - i) < abs(idx[j] - i): j -= 1
        return files[j]
    lines = []
    for b in tl["beats"]:
        s, off = BG_PLAN[b["id"]]
        n_avail = (max(shots[s][0]) + 1) if shots[s][0] else 1
        for k in range(b["frames"]):
            i = off + k
            if i >= n_avail and shots[s][0]: i = idx_wrap(i, n_avail, off)
            lines.append(f"file '{os.path.abspath(shot_frame(s, i))}'\nduration {1/fps:.6f}")
    lines.append(lines[-1].split("\n")[0])  # concat demuxer needs the last file repeated
    concat = os.path.join(bd, "bg_concat.txt"); open(concat, "w").write("\n".join(lines) + "\n")
    if missing: print(f"warning: {missing} background frames substituted with nearest rendered frame")
    W, H = tl["width"], tl["height"]
    enable = "+".join(f"between(t,{b['start']:.3f},{b['end']:.3f})" for b in tl["beats"] if b["id"] in BLUR_BEATS)
    vf = (f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p,"
          f"gblur=sigma=14:enable='{enable}',eq=brightness=-0.12:saturation=0.85:enable='{enable}'[bg];"
          f"[1:v]format=rgba[ov];[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]")
    out = a.out or os.path.join(vd, "out", ("preview.mp4" if a.preview else "final.mp4"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats",
           "-f", "concat", "-safe", "0", "-r", str(fps), "-i", concat,
           "-framerate", str(fps), "-i", os.path.join(bd, "overlay", "ov_%04d.png"),
           "-i", os.path.join(bd, "mix.wav"),
           "-filter_complex", vf, "-map", "[v]", "-map", "2:a",
           "-c:v", "libx264", "-preset", ("veryfast" if a.preview else "slow"), "-crf", str(a.crf if not a.preview else 23),
           "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-t", f"{tl['duration']:.3f}", out]
    print(" ".join(cmd)); subprocess.run(cmd, check=True)
    print("wrote", out)

def idx_wrap(i, n, off):
    span = max(n - off, 1); return off + (i - off) % span

if __name__ == "__main__":
    main()
