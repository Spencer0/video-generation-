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

# Background plan lives in videos/<id>/script.json:
#   "bg_plan": {beat: [shot, start_frame]}  which shot / shot-frame a beat starts on (wraps past the end)
#   "blur_beats": [...]                     beats whose footage is blurred + dimmed behind panels
# (the dicts below are the fallback for video 001)
BG_PLAN = {"hook": ("A", 0), "empty": ("B", 0), "water": ("C", 0), "temps": ("D", 0), "equation": ("C", 40),
           "ceiling": ("D", 20), "punch": ("D", 0), "noodles": ("C", 60), "cta": ("D", 90)}
BLUR_BEATS = ("equation", "ceiling")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video_id"); ap.add_argument("--out", default=None); ap.add_argument("--preview", action="store_true")
    ap.add_argument("--crf", type=int, default=17); ap.add_argument("--overlay-dir", default="overlay")
    a = ap.parse_args()
    vd = video_dir(video_id := a.video_id); bd = os.path.join(vd, "build")
    tl = load_json(os.path.join(bd, "timeline.json")); fps = tl["fps"]
    script = load_json(os.path.join(vd, "script.json"))
    bg_plan = {k: tuple(v) for k, v in script.get("bg_plan", BG_PLAN).items()}
    blur_beats = tuple(script.get("blur_beats", BLUR_BEATS))
    shot_ids = sorted(script.get("shots", {"A": 0, "B": 0, "C": 0, "D": 0}).keys())
    frames_dir = os.path.join(bd, "frames")
    shots = {}
    for s in shot_ids:
        fl = sorted(glob.glob(os.path.join(frames_dir, s, f"{s}_*.png")))
        shots[s] = ([int(os.path.basename(f)[2:6]) for f in fl], fl)
    missing = 0
    def shot_frame(s, i):
        nonlocal missing
        idx, files = shots[s]
        if not files:  # shot not started yet: borrow any rendered shot so previews still cut
            s = next((k for k in shot_ids if shots[k][1]), None)
            if s is None: raise SystemExit("no 3D frames rendered yet")
            idx, files = shots[s]
        if i in idx: return files[idx.index(i)]
        missing += 1
        j = bisect.bisect_left(idx, i); j = min(max(j, 0), len(idx) - 1)
        if j > 0 and abs(idx[j - 1] - i) < abs(idx[j] - i): j -= 1
        return files[j]
    lines, top_lines, split_windows = [], [], []
    for b in tl["beats"]:
        plan = bg_plan[b["id"]]; s, off = plan[0], plan[1]
        split = plan[2]["split"] if len(plan) > 2 and isinstance(plan[2], dict) and "split" in plan[2] else None
        off += b.get("bg_offset", 0)   # script.json can shift a beat's footage (e.g. ignition on a word)
        n_avail = (max(shots[s][0]) + 1) if shots[s][0] else 1
        if split:
            split_windows.append((b["start"], b["start"] + split[2] / fps))
        for k in range(b["frames"]):
            i = off + k
            if i >= n_avail and shots[s][0]: i = idx_wrap(i, n_avail, off)
            main = os.path.abspath(shot_frame(s, i))
            lines.append(f"file '{main}'\nduration {1/fps:.6f}")
            if split and k < split[2]:
                s2, off2 = split[0], split[1]; n2 = (max(shots[s2][0]) + 1) if shots[s2][0] else 1
                j = off2 + k
                if j >= n2 and shots[s2][0]: j = idx_wrap(j, n2, off2)
                top_lines.append(f"file '{os.path.abspath(shot_frame(s2, j))}'\nduration {1/fps:.6f}")
            else:
                top_lines.append(f"file '{main}'\nduration {1/fps:.6f}")
    lines.append(lines[-1].split("\n")[0]); top_lines.append(top_lines[-1].split("\n")[0])  # concat demuxer needs the last file repeated
    concat = os.path.join(bd, "bg_concat.txt"); open(concat, "w").write("\n".join(lines) + "\n")
    concat_top = os.path.join(bd, "bg_concat_top.txt"); open(concat_top, "w").write("\n".join(top_lines) + "\n")
    if missing: print(f"warning: {missing} background frames substituted with nearest rendered frame")
    W, H = tl["width"], tl["height"]
    enable = "+".join(f"between(t,{b['start']:.3f},{b['end']:.3f})" for b in tl["beats"] if b["id"] in blur_beats)
    blur = f"gblur=sigma=14:enable='{enable}',eq=brightness=-0.12:saturation=0.85:enable='{enable}'," if enable else ""
    if split_windows:
        # split screen: top half from the 'top' sequence, bottom half from the main one, each cropped to its centre band
        sw = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in split_windows)
        vf = (f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p,{blur}split[bgA][bgB];"
              f"[3:v]scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p,crop={W}:{H//2}:0:{H//4},eq=brightness=0.07:contrast=1.08[top];"
              f"[bgB]crop={W}:{H//2}:0:{H//4}[bot];[top][bot]vstack,drawbox=y={H//2-3}:w={W}:h=6:color=black@0.9:t=fill[sp];"
              f"[bgA][sp]overlay=0:0:enable='{sw}'[bg];[1:v]format=rgba[ov];[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]")
    else:
        vf = (f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p,{blur}null[bg];"
              f"[1:v]format=rgba[ov];[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]")
    out = a.out or os.path.join(vd, "out", ("preview.mp4" if a.preview else "final.mp4"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats",
           "-f", "concat", "-safe", "0", "-r", str(fps), "-i", concat,
           "-framerate", str(fps), "-i", os.path.join(bd, a.overlay_dir, "ov_%04d.png"),
           "-i", os.path.join(bd, "mix.wav"),
           "-f", "concat", "-safe", "0", "-r", str(fps), "-i", concat_top,
           "-filter_complex", vf, "-map", "[v]", "-map", "2:a",
           "-c:v", "libx264", "-preset", ("veryfast" if a.preview else "slow"), "-crf", str(a.crf if not a.preview else 23),
           "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",   # platform-style loudness so uploads are not re-leveled
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-t", f"{tl['duration']:.3f}", out]
    print(" ".join(cmd)); subprocess.run(cmd, check=True)
    print("wrote", out)

def idx_wrap(i, n, off):
    span = max(n - off, 1); return off + (i - off) % span

if __name__ == "__main__":
    main()
