#!/usr/bin/env python3
"""Build the c004 image assets.

1. Redact friends' chat screenshots (names, location) so only redacted
   copies ever reach the repo. The originals stay wherever you keep them:
     python3 make_assets.py chats <discord.png> <imessage.png> <linkpreview.jpg>
2. Capture the prank site itself at phone size, with Math.random seeded so
   re-captures match:
     python3 make_assets.py site
"""
import os, sys
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets")
SITE = "https://spencer0.github.io/infinitemoneyglitch/"

# boxes in the original 1290x2796 phone screenshots: (x0, y0, x1, y1)
# friends' names + location, and the poster's own name (labels and the spencer0.github.io URL)
REDACT = {
    "discord": [(296, 228, 505, 300), (200, 740, 375, 800), (200, 1200, 375, 1258), (395, 2572, 615, 2640),
                (266, 343, 428, 395), (578, 400, 1110, 452), (200, 475, 382, 532), (200, 1009, 382, 1066)],
    "imessage": [(525, 355, 742, 425), (500, 425, 790, 490), (365, 855, 1050, 985)],
    "preview": [(370, 952, 780, 1018)],
}


def redact(src, boxes, dst):
    im = Image.open(src).convert("RGB")
    for b in boxes:
        reg = im.crop(b)
        w, h = reg.size
        reg = reg.resize((max(1, w // 18), max(1, h // 18)), Image.BILINEAR).resize((w, h), Image.NEAREST)
        im.paste(reg.filter(ImageFilter.GaussianBlur(6)), b)
    im.save(dst, optimize=True)
    print("wrote", os.path.relpath(dst, HERE))


def chats(discord, imessage, preview):
    os.makedirs(OUT, exist_ok=True)
    redact(discord, REDACT["discord"], os.path.join(OUT, "chat_discord.png"))
    redact(imessage, REDACT["imessage"], os.path.join(OUT, "chat_imessage.png"))
    redact(preview, REDACT["preview"], os.path.join(OUT, "chat_preview.png"))


SEED = """(()=>{let s=12345;Math.random=function(){s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);
t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}})();"""


def site():
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        proxy = {"server": os.environ["HTTPS_PROXY"]} if os.environ.get("HTTPS_PROXY") else None
        try: br = p.chromium.launch(proxy=proxy)
        except Exception: br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", proxy=proxy)
        ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
        ctx.add_init_script(SEED)
        pg = ctx.new_page(); pg.goto(SITE, wait_until="networkidle"); pg.wait_for_timeout(800)
        pg.screenshot(path=os.path.join(OUT, "site_gate.png"))
        pg.tap("#check"); pg.wait_for_timeout(1800)
        pg.screenshot(path=os.path.join(OUT, "site_round1.png"))
        for k in range(3):                          # pick 3 tiles + verify: it never passes
            for t in pg.query_selector_all("#grid .tile")[:3]: t.tap(); pg.wait_for_timeout(150)
            pg.tap("#go"); pg.wait_for_timeout(2200)
            pg.screenshot(path=os.path.join(OUT, f"site_round{k+2}.png"))
        print(pg.inner_text("#tally"))
        br.close()
    for f in sorted(os.listdir(OUT)):
        if f.startswith("site_"):
            im = Image.open(os.path.join(OUT, f)).convert("RGB"); im.save(os.path.join(OUT, f), optimize=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["chats"]: chats(*sys.argv[2:5])
    elif sys.argv[1:2] == ["site"]: site()
    else: sys.exit(__doc__)
