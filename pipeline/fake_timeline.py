#!/usr/bin/env python3
"""Write an ESTIMATED build/timeline.json from script.json without Kokoro,
for overlay previews and safe-area audits only (3 words/s, same beat padding
rules as tts.py). It is marked "estimated": true; checks.py warns on it and it
must never be used to assemble a deliverable. Re-run tts.py for the real one.

usage: python3 pipeline/fake_timeline.py <video_id> [--wps 3.0]
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import load_json, video_dir, estimate_word_times
LINE_GAP = 0.18

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video_id"); ap.add_argument("--wps", type=float, default=3.0); a = ap.parse_args()
    vd = video_dir(a.video_id); script = load_json(os.path.join(vd, "script.json")); fps = script["fps"]
    os.makedirs(os.path.join(vd, "build"), exist_ok=True)
    t = 0.0; beats_out = []
    for bi, beat in enumerate(script["beats"]):
        b_start = t; t += beat.get("pad_before", 0.2); lines_out = []
        for text in beat["lines"]:
            dur = max(0.4, len(text.split()) / a.wps)
            lines_out.append({"text": text, "start": round(t, 3), "end": round(t + dur, 3), "wav": None, "words": estimate_word_times(text, t, t + dur)})
            t += dur + LINE_GAP
        t = (t - LINE_GAP if beat["lines"] else t) + beat.get("pad_after", 0.3)
        t = max(t, b_start + beat.get("min_duration", 0)); t = round(round(t * fps) / fps, 4)
        beats_out.append({"id": beat["id"], "start": round(b_start, 4), "end": t, "bg_offset": beat.get("bg_offset", 0), "duration": round(t - b_start, 4),
                          "frames": int(round((t - b_start) * fps)), "start_frame": int(round(b_start * fps)), "lines": lines_out})
    tl = {"id": a.video_id, "fps": fps, "width": script["width"], "height": script["height"], "duration": round(t, 4), "total_frames": int(round(t * fps)),
          "vo": None, "estimated": True, "beats": beats_out}
    with open(os.path.join(vd, "build", "timeline.json"), "w") as f: json.dump(tl, f, indent=1)
    print(f"ESTIMATED timeline {t:.2f}s, {tl['total_frames']} frames @ {fps}fps (not for assembly; run tts.py for the real one)")

if __name__ == "__main__":
    main()
