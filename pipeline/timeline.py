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
