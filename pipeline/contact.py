#!/usr/bin/env python3
"""Contact sheet + phone-size thumbnail of a cut, for the eyes-on checks (every frame should have motion or a
label appearing; frame 0 must sell the claim at feed size).

usage: python3 pipeline/contact.py <video_id> [--src out/final.mp4] [--fps 1] [--cols 10] [--out out/contact.png]
Writes out/contact.png (one tile per 1/fps s) and out/thumb.png (frame 0 at 135x240, the size of a feed thumbnail).
"""
import sys, os, argparse, subprocess, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import load_json, video_dir

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video_id"); ap.add_argument("--src", default=None); ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--cols", type=int, default=10); ap.add_argument("--out", default=None); ap.add_argument("--tile-w", type=int, default=216); a = ap.parse_args()
    vd = video_dir(a.video_id); src = a.src or os.path.join(vd, "out", "final.mp4"); out = a.out or os.path.join(vd, "out", "contact.png")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip())
    n = int(math.ceil(dur * a.fps)); rows = int(math.ceil(n / a.cols))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", f"fps={a.fps},scale={a.tile_w}:-1,tile={a.cols}x{rows}:padding=4:color=gray", "-frames:v", "1", out], check=True)
    thumb = os.path.join(os.path.dirname(out), "thumb.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", "select=eq(n\\,0),scale=135:240", "-frames:v", "1", thumb], check=True)
    print(f"wrote {out} ({n} tiles, {a.cols}x{rows}) and {thumb}")

if __name__ == "__main__":
    main()
