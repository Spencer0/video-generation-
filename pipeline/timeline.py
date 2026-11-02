"""Shared timeline helpers.

A video is described by videos/<id>/script.json (beats + narration lines).
`tts.py` turns that into videos/<id>/build/timeline.json, which is the single
source of truth for timing that Blender, the overlay renderer and the
assembler all consume. Nothing else should invent timings.
"""
import json, os, re

def load_json(p):
    with open(p) as f:
        return json.load(f)

def video_dir(video_id, root=None):
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "videos", video_id)

def estimate_word_times(text, start, end):
    """Kokoro gives no word timestamps; spread words across [start, end]
    weighted by character count, with extra weight on punctuation pauses.
    Good to ~100 ms, which is enough for caption highlighting."""
    words = text.split()
    weights = []
    for w in words:
        core = re.sub(r"[^\w']", "", w)
        wt = max(len(core), 1) + 1.0          # +1 = inter-word gap
        if re.search(r"[.!?]$", w): wt += 4.0  # sentence pause
        elif re.search(r"[,;:]$", w) or w.endswith("..."): wt += 2.0
        weights.append(wt)
    total = sum(weights)
    out, t = [], start
    for w, wt in zip(words, weights):
        d = (end - start) * wt / total
        out.append({"word": w, "start": round(t, 3), "end": round(t + d, 3)})
        t += d
    return out

def frame_map(tl, script):
    """(shot, shot_frame) for every output frame, following the bg_plan rules of assemble.py: per-beat shot + offset,
    wrap past the nominal shot length (from script.json "shots"), mid-beat "cuts". Split/stack windows keep the main
    shot. Used by render_overlays.py to look up 3D object tracks (build/tracks/<shot>.json) per output frame."""
    plan = script.get("bg_plan", {}); shots = script.get("shots", {}); out = []
    for b in tl["beats"]:
        p = plan.get(b["id"], ["A", 0]); s, off = p[0], p[1] + b.get("bg_offset", 0)
        opts = p[2] if len(p) > 2 and isinstance(p[2], dict) else {}
        n = shots.get(s, 0) or 1
        for k in range(b["frames"]):
            i = off + k
            if i >= n: i = off + (i - off) % max(n - off, 1)
            cur = (s, i)
            for cs, coff, ck, cn in opts.get("cuts", []):
                if ck <= k < ck + cn:
                    nc = shots.get(cs, 0) or 1; j = coff + (k - ck)
                    if j >= nc: j = coff + (j - coff) % max(nc - coff, 1)
                    cur = (cs, j)
            out.append(cur)
    return out
