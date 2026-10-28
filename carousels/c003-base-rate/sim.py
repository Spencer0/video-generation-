#!/usr/bin/env python3
"""c003: 1 in 10,000 people have a disease. The test is "99% accurate":
it flags 99% of people who have it (sensitivity) and clears 99% of people
who don't (specificity). A person tested at random tests positive. What are
the odds they have it?

Simulate 100,000,000 randomly tested people and look only at the positives.
Exact (Bayes): 0.0001*0.99 / (0.0001*0.99 + 0.9999*0.01) = 0.98 %.
Per 1,000,000 people: 99 sick positives vs 9,999 healthy false positives.

usage: python3 sim.py      (seeded, numpy, a few seconds; writes out/sim.json)
"""
import json, os
import numpy as np

PEOPLE, CHUNK = 100_000_000, 10_000_000
PREV, SENS, SPEC = 1 / 10_000, 0.99, 0.99
rng = np.random.default_rng(20261028)

sick_pos = healthy_pos = sick_total = 0
for _ in range(PEOPLE // CHUNK):
    sick = rng.random(CHUNK) < PREV
    flagged = rng.random(CHUNK)
    pos = np.where(sick, flagged < SENS, flagged < 1 - SPEC)
    sick_pos += int((sick & pos).sum()); healthy_pos += int((~sick & pos).sum()); sick_total += int(sick.sum())

p = sick_pos / (sick_pos + healthy_pos)
exact = PREV * SENS / (PREV * SENS + (1 - PREV) * (1 - SPEC))
se = (p * (1 - p) / (sick_pos + healthy_pos)) ** 0.5
print(f"{PEOPLE:,} people tested: {sick_total:,} sick, {sick_pos + healthy_pos:,} positive "
      f"({sick_pos:,} sick, {healthy_pos:,} healthy)")
assert abs(p - exact) < 5 * se
res = {"people": PEOPLE, "sick": sick_total, "sick_positive": sick_pos, "healthy_positive": healthy_pos,
       "p_sick_given_positive": p, "exact": exact,
       "display": {"answer": f"{100 * p:.2f}%", "exact": f"{100 * exact:.2f}%"}}
os.makedirs("out", exist_ok=True)
json.dump(res, open(os.path.join("out", "sim.json"), "w"), indent=1)
print(f"P(sick | positive) = {100 * p:.2f}% simulated, {100 * exact:.2f}% exact (most people say 99%)")
