#!/usr/bin/env python3
"""Generate the voiceover with Kokoro (offline, CPU) and emit timeline.json.

usage: python3 pipeline/tts.py <video_id>

Per narration line we synthesize one wav, measure it, and lay the beats out
back-to-back: beat = pad_before + sum(lines + 0.18s gaps) + pad_after,
stretched up to min_duration. The resulting timeline.json has absolute
start/end for every beat, line and (estimated) word, plus the frame counts
every downstream renderer needs.
"""
import sys, os, json, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import load_json, video_dir, estimate_word_times

KOKORO_DIR = os.environ.get("KOKORO_DIR", "/home/user/tools/kokoro")
LINE_GAP = 0.18

def main(video_id):
    vd = video_dir(video_id)
    script = load_json(os.path.join(vd, "script.json"))
    build = os.path.join(vd, "build", "vo"); os.makedirs(build, exist_ok=True)
    from kokoro_onnx import Kokoro
    k = Kokoro(f"{KOKORO_DIR}/kokoro-v1.0.onnx", f"{KOKORO_DIR}/voices-v1.0.bin")
    v = script["voice"]; fps = script["fps"]
    sr = 24000; master = []; t = 0.0; beats_out = []
    for bi, beat in enumerate(script["beats"]):
        b_start = t; t += beat.get("pad_before", 0.2); lines_out = []
        for li, text in enumerate(beat["lines"]):
            wav, sr = k.create(text, voice=v["name"], speed=v.get("speed", 1.0), lang=v.get("lang", "en-us"))
            # trim leading/trailing silence (< -45 dBFS)
            env = np.abs(wav) > 10 ** (-45 / 20)
            idx = np.where(env)[0]
            if len(idx): wav = wav[max(idx[0] - int(0.03 * sr), 0): idx[-1] + int(0.06 * sr)]
            path = os.path.join(build, f"b{bi:02d}_l{li:02d}.wav"); sf.write(path, wav, sr)
            dur = len(wav) / sr
            lines_out.append({"text": text, "start": round(t, 3), "end": round(t + dur, 3), "wav": path,
                              "words": estimate_word_times(text, t, t + dur)})
            master.append((t, wav)); t += dur + LINE_GAP
        t = (t - LINE_GAP if beat["lines"] else t) + beat.get("pad_after", 0.3)
        t = max(t, b_start + beat.get("min_duration", 0))
        # snap beat boundaries to whole frames so shots concatenate cleanly
        t = round(round(t * fps) / fps, 4)
        beats_out.append({"id": beat["id"], "start": round(b_start, 4), "end": t, "bg_offset": beat.get("bg_offset", 0),
                          "duration": round(t - b_start, 4), "frames": int(round((t - b_start) * fps)),
                          "start_frame": int(round(b_start * fps)), "lines": lines_out})
    total = t
    mix = np.zeros(int(total * sr) + sr, dtype=np.float32)
    for st, wav in master:
        i = int(st * sr); mix[i:i + len(wav)] += wav
    mix = mix[: int(total * sr)]
    vo_path = os.path.join(vd, "build", "vo.wav"); sf.write(vo_path, mix, sr)
    tl = {"id": video_id, "fps": fps, "width": script["width"], "height": script["height"],
          "duration": round(total, 4), "total_frames": int(round(total * fps)), "vo": vo_path, "beats": beats_out}
    with open(os.path.join(vd, "build", "timeline.json"), "w") as f: json.dump(tl, f, indent=1)
    print(f"VO {total:.2f}s, {tl['total_frames']} frames @ {fps}fps")
    for b in beats_out: print(f"  {b['id']:8s} {b['start']:6.2f} -> {b['end']:6.2f}  ({b['frames']} fr)")

if __name__ == "__main__":
    main(sys.argv[1])
