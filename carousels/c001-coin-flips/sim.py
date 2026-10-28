#!/usr/bin/env python3
"""c001 claims "most people (who say SAME) are wrong". Check it with the
plainest possible code: flip a fair coin until HEADS is immediately followed
by HEADS, count the flips; separately until HEADS is immediately followed by
TAILS. Average over many games. (The full 1,000,000-game version with the
exact Markov-chain answer is carousels/c002-coin-flips-answer/sim.py.)

usage: python3 sim.py      (seeded, pure Python, ~1 s; writes out/sim.json)
"""
import json, os, random

GAMES = 200_000
rng = random.Random(2026)


def flips_until(pattern):
    seq = ""
    while not seq.endswith(pattern):
        seq += rng.choice("HT")          # fair coin
    return len(seq)


res = {}
for pat in ("HH", "HT"):
    f = [flips_until(pat) for _ in range(GAMES)]
    m = sum(f) / GAMES
    sd = (sum((x - m) ** 2 for x in f) / (GAMES - 1)) ** 0.5
    res[pat] = {"mean": m, "stderr": sd / GAMES ** 0.5}
    print(f"{pat}: {m:.2f} flips on average over {GAMES:,} games")

gap = res["HH"]["mean"] - res["HT"]["mean"]
z = gap / (res["HH"]["stderr"] ** 2 + res["HT"]["stderr"] ** 2) ** 0.5
assert z > 20, "SAME would not be wrong"
res["display"] = {"verdict": "SAME is wrong"}
os.makedirs("out", exist_ok=True)
json.dump(res, open(os.path.join("out", "sim.json"), "w"), indent=1)
print(f"SAME is wrong: HH - HT = {gap:.2f} flips ({z:.0f} standard errors)")
