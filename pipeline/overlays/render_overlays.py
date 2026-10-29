#!/usr/bin/env python3
"""Render the 2D overlay layer (captions + graphics) to a PNG-with-alpha
sequence using headless Chromium + the canvas engine in overlay.html.

usage: python3 pipeline/overlays/render_overlays.py <video_id> [--start N] [--end N] [--every K]
"""
import sys, os, json, time, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from timeline import load_json, video_dir
from playwright.sync_api import sync_playwright

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video_id"); ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None); ap.add_argument("--every", type=int, default=1); ap.add_argument("--out", default=None); ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--show-safe-area", action="store_true", help="paint the TikTok UI zones (pipeline/safe_area.json) on every frame; previews only")
    a = ap.parse_args()
    vd = video_dir(a.video_id); tl = load_json(os.path.join(vd, "build", "timeline.json"))
    out = a.out or os.path.join(vd, "build", "overlay"); os.makedirs(out, exist_ok=True)
    end = a.end if a.end is not None else tl["total_frames"]
    html = os.path.abspath(os.path.join(os.path.dirname(__file__), "overlay.html"))
    with sync_playwright() as p:
        try: br = p.chromium.launch()
        except Exception: br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = br.new_page(viewport={"width": tl["width"], "height": tl["height"]}, device_scale_factor=1)
        page.goto("file://" + html); page.wait_for_load_state("load")
        page.add_script_tag(path=os.path.join(vd, "beats.js"))   # per-video beat graphics
        page.evaluate("document.fonts.load('900 80px Inter'); document.fonts.load('700 40px Inter')")
        page.wait_for_timeout(300)
        page.evaluate("tl => window.setTimeline(tl)", tl)
        if a.no_captions: page.evaluate("window.NO_CAPTIONS = true")
        if a.show_safe_area:
            sa = load_json(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "safe_area.json"))
            page.evaluate("sa => { window.SAFE_ZONES = sa; window.SHOW_SAFE_ZONES = true; }", sa)
        t0 = time.time(); n = 0
        for f in range(a.start, end, a.every):
            path = os.path.join(out, f"ov_{f:04d}.png")
            page.evaluate("f => window.renderFrame(f)", f)
            page.screenshot(path=path, omit_background=True, clip={"x": 0, "y": 0, "width": tl["width"], "height": tl["height"]})
            n += 1
            if n % 100 == 0: print(f"overlay {f}/{end} {(time.time()-t0)/n:.3f}s/frame", flush=True)
        br.close()
    print(f"rendered {n} overlay frames to {out} in {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
