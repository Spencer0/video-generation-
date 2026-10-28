#!/usr/bin/env python3
"""Flip a fair coin until HEADS is immediately followed by HEADS (game HH),
and separately until HEADS is immediately followed by TAILS (game HT).
Play each game 1,000,000 times and report the average number of flips.

Exact answers (two-state Markov chain, E0 = expected flips from scratch,
E1 = expected flips when the last flip was H):
  HH: E0 = 1 + E1/2 + E0/2,  E1 = 1 + 0/2 + E0/2   ->  E0 = 6
  HT: E0 = 1 + E1/2 + E0/2,  E1 = 1 + E1/2 + 0/2   ->  E0 = 4
The only difference: in HH a T from "holding an H" sends you back to the
start; in HT an H keeps you holding an H, so you never lose progress.

usage: python3 sim.py      (seeded, ~2 s; writes out/sim.json for the panels)
"""
import json, os
import numpy as np

TRIALS = 1_000_000
SEED = 20261028


def play(pattern, trials, rng):
    """Vectorised: every game flips once per round until it finishes. Returns flips per game."""
    flips = np.zeros(trials, dtype=np.int64)
    holding = np.zeros(trials, dtype=bool)        # last flip was H
    active = np.arange(trials)
    n = 0
    while active.size:
        n += 1
        heads = rng.random(active.size) < 0.5      # fair coin
        h = holding[active]
        if pattern == "HH":
            done = h & heads                       # H after H
            holding[active] = heads                # T sends you back to the start
        else:                                      # "HT"
            done = h & ~heads                      # T after H
            holding[active] = h | heads            # an H keeps you holding an H
        flips[active[done]] = n
        active = active[~done]
    return flips


def exact(pattern):
    # E0, E1 from the chain above, solved as a 2x2 linear system
    if pattern == "HH": A, b = [[0.5, -0.5], [-0.5, 1.0]], [1, 1]
    else:               A, b = [[0.5, -0.5], [0.0, 0.5]], [1, 1]
    return float(np.linalg.solve(A, b)[0])


def main():
    rng = np.random.default_rng(SEED)
    res = {"trials": TRIALS, "seed": SEED}
    for pat in ("HH", "HT"):
        f = play(pat, TRIALS, rng)
        m, se = f.mean(), f.std(ddof=1) / np.sqrt(TRIALS)
        res[pat] = {"mean": float(m), "stderr": float(se), "exact": exact(pat), "median": float(np.median(f)),
                    "p_over_10": float((f > 10).mean()), "max": int(f.max())}
        print(f"{pat}: mean {m:.2f} flips over {TRIALS:,} games (+/- {1.96*se:.3f} at 95%), exact {exact(pat):.0f}, "
              f"median {np.median(f):.0f}, longest {f.max()}")
    assert abs(res["HH"]["mean"] - 6) < 5 * res["HH"]["stderr"] and abs(res["HT"]["mean"] - 4) < 5 * res["HT"]["stderr"]
    res["display"] = {"hh": f"{res['HH']['mean']:.2f}", "ht": f"{res['HT']['mean']:.2f}", "trials": f"{TRIALS:,}"}
    os.makedirs("out", exist_ok=True)
    with open(os.path.join("out", "sim.json"), "w") as fh: json.dump(res, fh, indent=1)
    print(f"HH {res['display']['hh']} vs HT {res['display']['ht']} average flips ({TRIALS:,} games each)")


if __name__ == "__main__":
    main()
