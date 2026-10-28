#!/usr/bin/env python3
"""Render a photo carousel (TikTok photo post) to 1080x1920 PNGs and check it.

usage: python3 pipeline/carousel/render_panels.py <post_id> [--only N] [--contact]
                                                  [--preview-mp4] [--no-sim] [--no-checks]

carousels/<id>/panels.js is loaded into panels.html (shared helpers from
pipeline/overlays/helpers.js). If carousels/<id>/sim.py exists it runs first
(timed) and must write out/sim.json; that JSON is injected as window.SIM so
the panels draw the simulated numbers rather than hand-typed ones.

Writes out/01.png ..., out/post.txt, out/thumb.png, out/checks.txt and with
flags out/contact.png and out/preview.mp4. Exits 1 if an automated check fails.
"""
import sys, os, re, json, time, argparse, subprocess, shutil, tempfile, hashlib
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
W, H = 1080, 1920
SAFE = (60, 250, 1020, 1500)          # x0, y0, x1, y1: platform UI covers the rest
MAX_WORDS = 15                         # per panel, outside the problem statement
PAPER, INK = "#F4F0E6", "#161616"      # mirror of PAPER in helpers.js (checked below)

POSTING = """1. Upload the PNGs in order as a photo post; TikTok will offer carousel
   mode. Panel 1 is the cover.
2. Add a trending sound at low volume; pick one with no lyrics over the
   first 3 seconds so the hook is read, not heard.
3. Paste the caption and hashtags from this file. Post.
4. Pin the pinned comment from this file within a minute of posting.
5. Reply to the first 10-20 comments, short, never giving the answer.
   "Confident?" "Interesting, why?" Replies count as engagement twice.
6. Question post: post the answer about 24 h later (never later than a day).
   Answer post: reply to the question post's top comments with "answer's
   up", and screenshot both analytics pages for review."""


def post_dir(pid):
    return os.path.join(ROOT, "carousels", pid)


def run_sim(pd, out):
    sim = os.path.join(pd, "sim.py")
    if not os.path.exists(sim):
        return None, None
    t0 = time.time()
    r = subprocess.run([sys.executable, sim], cwd=pd, capture_output=True, text=True)
    dt = time.time() - t0
    if r.returncode:
        sys.exit(f"sim.py failed:\n{r.stdout}\n{r.stderr}")
    print(r.stdout.rstrip())
    with open(os.path.join(out, "sim.json")) as f:
        return json.load(f), {"seconds": dt, "stdout": r.stdout}


def render(pd, out, sim, only):
    html = os.path.join(HERE, "panels.html")
    logs, meta = {}, {}
    with sync_playwright() as p:
        try: br = p.chromium.launch()
        except Exception: br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto("file://" + html); page.wait_for_load_state("load")
        page.evaluate("s => { window.SIM = s; }", sim)
        page.add_script_tag(path=os.path.join(pd, "panels.js"))
        page.evaluate("""() => Promise.all([document.fonts.load('900 80px Inter'), document.fonts.load('800 80px Inter'),
                         document.fonts.load('700 40px Inter'), document.fonts.load('80px "Permanent Marker"')])""")
        ok = page.evaluate("() => document.fonts.check('80px \"Permanent Marker\"') && document.fonts.check('900 80px Inter')")
        if not ok: sys.exit("fonts failed to load")
        n = page.evaluate("() => window.panelCount()"); meta = page.evaluate("() => window.panelMeta()")
        for i in range(n):
            if only and i + 1 != only: continue
            r = page.evaluate("i => window.renderPanel(i)", i)
            path = os.path.join(out, f"{i+1:02d}.png")
            raw = page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H}, type="png")
            with tempfile.NamedTemporaryFile(suffix=".png") as tf:
                tf.write(raw); tf.flush()
                Image.open(tf.name).convert("RGB").save(path, optimize=True)
            logs[i] = r["text"]
            print(f"panel {i+1}/{n} -> {os.path.relpath(path, ROOT)} ({os.path.getsize(path)/1e6:.2f} MB)")
        br.close()
    return n, meta, logs


def contact(out, n):
    s, gap = 0.4, 28
    w, h = int(W * s), int(H * s)
    sheet = Image.new("RGB", (n * w + (n + 1) * gap, h + 2 * gap), (38, 38, 38))
    for i in range(n):
        im = Image.open(os.path.join(out, f"{i+1:02d}.png")).resize((w, h), Image.LANCZOS)
        sheet.paste(im, (gap + i * (w + gap), gap))
    sheet.save(os.path.join(out, "contact.png"), optimize=True)


def preview_mp4(out, n, per=2.5, td=0.4):
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for i in range(n):
        args += ["-loop", "1", "-t", f"{per + (td if i < n - 1 else 0):.2f}", "-i", os.path.join(out, f"{i+1:02d}.png")]
    f, prev = [], "[0:v]"
    for i in range(n): f.append(f"[{i}:v]scale=540:960,fps=30,format=yuv420p[v{i}]")
    prev = "[v0]"
    for i in range(1, n):
        f.append(f"{prev}[v{i}]xfade=transition=slideleft:duration={td}:offset={i*per:.2f}[x{i}]"); prev = f"[x{i}]"
    args += ["-filter_complex", ";".join(f), "-map", prev, "-an", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
             os.path.join(out, "preview.mp4")]
    subprocess.run(args, check=True)


def write_post(out, n, meta, pid):
    lines = [f"# {pid}", "", "ORDER: " + ", ".join(f"{i+1:02d}.png" for i in range(n)) + " (01 is the cover)", "",
             "CAPTION:", meta.get("caption", ""), "", "HASHTAGS:", " ".join(meta.get("hashtags", [])), "",
             "CAPTION + HASHTAGS (paste as one):", meta.get("caption", "") + " " + " ".join(meta.get("hashtags", [])), "",
             "PINNED COMMENT (post and pin within a minute):", meta.get("pinned", ""), "",
             "SOUND:", meta.get("sound_note", ""), ""]
    for title, body in meta.get("extra", []):
        lines += [title.upper() + ":", body, ""]
    lines += ["POSTING INSTRUCTIONS:", POSTING, ""]
    with open(os.path.join(out, "post.txt"), "w") as f: f.write("\n".join(lines))


# ------------------------------------------------------------------ checks
def lum(hexcol):
    c = [int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

def lum_px(rgb):
    c = rgb.astype(np.float64) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]

def ratio(a, b):
    a, b = max(a, b), min(a, b)
    return (a + 0.05) / (b + 0.05)

def words(s):
    return [w for w in s.split() if re.search(r"[A-Za-z0-9]", w)]

TYPO_PATTERNS = [r"\btheir (the|is|are|was|were|a|an|not)\b", r"\bthere (own|car|house|answer)\b",
                 r"\byour (the|a|wrong|right|welcome|going|not)\b", r"\bits (a|an|the|not|been|going|\d)", r"\bit's own\b",
                 r"\b(more|less|better|rather|other|worse) then\b", r"\bwho's (turn|coin)\b", r"\bloose (the|your)\b"]

def checks(pd, out, n, meta, logs, simres, simrun):
    rep, fails = [], []
    def res(name, ok, detail):
        rep.append(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok: fails.append(name)
    def note(name, detail): rep.append(f"[NOTE] {name}: {detail}")
    review = meta.get("review", {})
    helpers = open(os.path.join(ROOT, "pipeline", "overlays", "helpers.js")).read()
    assert f"bg:'{PAPER}'" in helpers and f"ink:'{INK}'" in helpers, "PAPER palette drifted from render_panels.py"

    # 1. thumbnail: the cover at 1/8 scale (135x240), the largest line's cap height there
    th = os.path.join(out, "thumb.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(out, "01.png"), "-vf", "scale=135:240:flags=area", th], check=True)
    big = max((t for t in logs[0] if t["kind"] == "body" and t["mode"] == "fill"), key=lambda t: (t["bounds"][2] - t["bounds"][0]) * (t["bounds"][3] - t["bounds"][1]))
    cap = (big["bounds"][3] - big["bounds"][1]) / 8
    res("1 thumbnail", cap >= 9, f"largest cover line {big['str']!r} is {cap:.1f}px tall at 135x240 (want >= 9); out/thumb.png. "
        f"By eye: {review.get('thumbnail', 'NOT REVIEWED')}")

    # 2. safe area, measured from every glyph run that reached the canvas
    bad = [(i + 1, t["str"], t["bounds"]) for i in logs for t in logs[i]
           if t["bounds"][0] < SAFE[0] or t["bounds"][1] < SAFE[1] or t["bounds"][2] > SAFE[2] or t["bounds"][3] > SAFE[3]]
    ext = [min(t["bounds"][k] for i in logs for t in logs[i]) for k in (0, 1)] + [max(t["bounds"][k] for i in logs for t in logs[i]) for k in (2, 3)]
    res("2 safe area", not bad, (f"{sum(len(v) for v in logs.values())} text runs, union bounds x {ext[0]:.0f}..{ext[2]:.0f}, "
        f"y {ext[1]:.0f}..{ext[3]:.0f} inside x 60..1020, y 250..1500") if not bad else f"outside: {bad[:6]}")

    # 3. contrast: palette ratio, plus measured ink-vs-paper on the rendered pixels
    pr = ratio(lum(INK), lum(PAPER))
    measured = []
    blue_px = 0
    for i in logs:
        im = np.asarray(Image.open(os.path.join(out, f"{i+1:02d}.png")).convert("RGB"))
        paper = lum_px(np.median(im[SAFE[1]:SAFE[3], SAFE[0]:SAFE[2]].reshape(-1, 3), axis=0))
        for t in logs[i]:
            if t["kind"] in ("body", "problem") and t["mode"] == "fill" and t["color"].lower() == INK.lower():
                x0, y0, x1, y1 = [int(round(v)) for v in t["bounds"]]
                L = lum_px(im[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3))
                if L.size > 50: measured.append(ratio(paper, float(np.percentile(L, 2))))
        r, g, b = [im[..., k].astype(int) for k in range(3)]
        blue_px += int(((b - r > 70) & (b - g > 40)).sum())
    allow_blue = meta.get("allow_blue", False)
    red_txt = sorted({t["str"] for i in logs for t in logs[i] if "e5261e" in t["color"].lower() or "229, 38, 30" in t["color"]})
    res("3 contrast", pr >= 10 and (not measured or min(measured) >= 10) and (allow_blue or blue_px == 0),
        f"palette ink/paper {pr:.1f}:1; measured on rendered ink text min {min(measured) if measured else 0:.1f}:1 over {len(measured)} runs; "
        f"red/paper {ratio(lum('#E5261E'), lum(PAPER)):.1f}:1 (accent only); blue pixels {blue_px} ({'allowed: answer post' if allow_blue else 'must be 0'}); "
        f"red text runs: {red_txt}. By eye: {review.get('accent', 'NOT REVIEWED')}")

    # 4. words per panel outside the problem statement (coin letters and corner tags excluded)
    counts = {}
    for i in logs:
        counts[i + 1] = sum(len(words(t["str"])) for t in logs[i] if t["kind"] == "body" and t["mode"] == "fill")
    res("4 word count", max(counts.values()) <= MAX_WORDS, ", ".join(f"p{k}: {v}" for k, v in counts.items()) + f" (max {MAX_WORDS})")

    # 5. typos: exactly the intended ones (spelling via pyspellchecker if installed, plus known grammar slips)
    txt = {i + 1: " ".join(t["str"] for t in logs[i] if t["kind"] in ("body", "problem") and t["mode"] == "fill") for i in logs}
    found = []
    for k, s in txt.items():
        for pat in TYPO_PATTERNS:
            for m in re.finditer(pat, s, re.I): found.append((k, m.group(0)))
    try:
        from spellchecker import SpellChecker
        sc = SpellChecker(); ok = {w.lower() for w in meta.get("spell_ok", [])}
        for k, s in txt.items():
            toks = [re.sub(r"[^A-Za-z']", "", w).strip("'") for w in s.split()]
            for w in sc.unknown([w for w in toks if w and not w.isupper() and w.lower() not in ok]):
                found.append((k, w))
        speller = "pyspellchecker"
    except ImportError:
        speller = "no spellchecker installed (grammar patterns only)"
    want = [(t["panel"], t["text"]) for t in meta.get("typos", [])]
    norm = lambda L: sorted((p, s.lower()) for p, s in L)
    res("5 typos", norm(found) == norm(want), f"found {found}, intended {want} ({speller})")

    # 6. problem statement contains the phrases that make it unambiguous
    alltxt = re.sub(r"\s+", " ", " ".join(txt.values())).lower()
    need = meta.get("required_phrases", [])
    miss = [p for p in need if p.lower() not in alltxt]
    res("6 problem statement", not miss, f"required phrases {need} " + ("all present" if not miss else f"MISSING {miss}") +
        f". By eye: {review.get('statement', 'NOT REVIEWED')}")

    # 7. simulation: runs < 60 s, and the numbers it printed are the numbers on the panels
    if simres is not None:
        disp = simres.get("display", {})
        shown = {k: v for k, v in disp.items() if v in alltxt or v.lower() in alltxt}
        must = meta.get("sim_on_panels", [])
        missing = [k for k in must if k not in shown]
        res("7 simulation", simrun["seconds"] < 60 and not missing,
            f"sim.py {simrun['seconds']:.1f}s; printed: {simrun['stdout'].strip().splitlines()[-1] if simrun['stdout'].strip() else ''}; "
            f"on panels: {shown}" + (f"; MISSING {missing}" if missing else ""))
    else:
        note("7 simulation", "no sim.py for this post")

    # 8 + 9: renderer-wide and by-eye items
    note("8 overlay regression", review.get("overlays", "NOT REVIEWED"))
    note("9 flow (contact sheet)", review.get("flow", "NOT REVIEWED"))
    hashes = " ".join(f"{i+1:02d}:{hashlib.sha1(open(os.path.join(out, f'{i+1:02d}.png'), 'rb').read()).hexdigest()[:10]}" for i in logs)
    note("determinism", f"sha1 {hashes}")
    note("text", " | ".join(f"p{k}: {s}" for k, s in txt.items()))

    with open(os.path.join(out, "checks.txt"), "w") as f:
        f.write(f"# acceptance checks, {os.path.basename(pd)}, {time.strftime('%Y-%m-%d %H:%M')}\n" + "\n".join(rep) + "\n")
    print("\n".join(rep))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post_id"); ap.add_argument("--only", type=int, default=None, help="render only panel N (1-based)")
    ap.add_argument("--contact", action="store_true"); ap.add_argument("--preview-mp4", action="store_true")
    ap.add_argument("--no-sim", action="store_true", help="reuse out/sim.json instead of re-running sim.py")
    ap.add_argument("--no-checks", action="store_true")
    a = ap.parse_args()
    pd = post_dir(a.post_id); out = os.path.join(pd, "out"); os.makedirs(out, exist_ok=True)
    simres = simrun = None
    if a.no_sim and os.path.exists(os.path.join(out, "sim.json")):
        simres = json.load(open(os.path.join(out, "sim.json")))
    else:
        simres, simrun = run_sim(pd, out)
    n, meta, logs = render(pd, out, simres, a.only)
    if a.only: return
    write_post(out, n, meta, a.post_id)
    if a.contact: contact(out, n)
    if a.preview_mp4: preview_mp4(out, n)
    if not a.no_checks:
        if simres is not None and simrun is None:
            simres, simrun = run_sim(pd, out)
        fails = checks(pd, out, n, meta, logs, simres, simrun)
        if fails: sys.exit(f"FAILED: {fails}")


if __name__ == "__main__":
    main()
