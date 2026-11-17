#!/usr/bin/env python3
"""Simulate customer traffic against the LLM, with and without the semantic cache.

  python3 demo.py --sweep                 # pick a threshold (no cache or LLM needed)
  python3 demo.py --no-cache -n 60        # baseline: every question goes to the LLM
  python3 demo.py -n 300                  # with cache: exact + semantic hits
  python3 demo.py --traps                 # ask the trap questions after a run
  python3 demo.py --reset                 # delete the lab's cache keys and index
"""
import argparse
import os
import random
import statistics
import time

import numpy as np

from llm import PRICE_PER_CALL, get_llm

HERE = os.path.dirname(os.path.abspath(__file__))


def load_questions(path=None):
    path = path or os.path.join(HERE, "questions.txt")
    blocks, traps, cur = [], [], []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("#"):
            continue
        if not line:
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if line.startswith("!"):
            traps.append((len(blocks), line[1:].strip()))
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)
    return blocks, traps


def sweep(embedder, blocks, traps):
    """For each threshold: share of paraphrases served (good) and traps served (bad)."""
    # Distance to the NEAREST other wording of the same intent, because that is what a
    # KNN lookup finds once the cache is warm.
    vecs = [[embedder(q) for q in b] for b in blocks]
    para, trap = [], []
    for vs in vecs:
        for j, v in enumerate(vs):
            para.append(min(1 - float(np.dot(v, o)) for k, o in enumerate(vs) if k != j))
    for i, q in traps:
        t = embedder(q)
        trap.append(min(1 - float(np.dot(t, o)) for o in vecs[i]))
    print(f"paraphrase distance: min {min(para):.3f}  median {statistics.median(para):.3f}  max {max(para):.3f}")
    print(f"trap distance      : min {min(trap):.3f}  median {statistics.median(trap):.3f}  max {max(trap):.3f}\n")
    print("threshold  paraphrases served  traps served (wrong answers)")
    for t in (0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25):
        p = sum(d <= t for d in para) / len(para)
        w = sum(d <= t for d in trap) / len(trap)
        print(f"  {t:4.2f}         {p:6.0%}              {w:6.0%}")
    print("\nPick the highest threshold whose trap column is still 0%, then add business rules"
          " (product IDs, locations) to the scope for questions where details matter.")


def percentile(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=200, help="number of simulated requests")
    ap.add_argument("--threshold", type=float, default=float(os.environ.get("CACHE_THRESHOLD", "0.10")))
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--traps", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--tenant", default="harborpine")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    random.seed(a.seed)

    from semantic_cache import Embedder, SemanticCache
    blocks, traps = load_questions()
    embedder = Embedder()

    if a.sweep:
        return sweep(embedder, blocks, traps)

    llm = get_llm()
    cache = None
    if not a.no_cache:
        from cache_client import connect
        cache = SemanticCache(connect(), embedder, threshold=a.threshold)
        if a.reset:
            try:
                cache.r.execute_command("FT.DROPINDEX", cache.index)
            except Exception:
                pass
            n = 0
            for k in cache.r.scan_iter(match=cache.prefix + "*", count=500):
                cache.r.delete(k)
                n += 1
            print(f"deleted {n} keys and the index")
            return
        if cache.ensure_index():
            print("created vector index", cache.index)

    if a.traps:
        for _i, q in traps:
            ans, kind, dist = cache.lookup(q, tenant=a.tenant, model=llm.name)
            verdict = "WRONG: served a cached answer for a different question" if kind != "miss" else "ok: sent to LLM"
            print(f"{q!r:60} {kind:8} dist={dist if dist is None else round(dist, 3)}  {verdict}")
        return

    # A few intents are asked far more often than others (Zipf-like), like real support traffic.
    weights = [1 / (i + 1) for i in range(len(blocks))]
    lat, kinds, llm_calls = [], [], 0
    for i in range(a.n):
        q = random.choice(random.choices(blocks, weights)[0])
        t0 = time.perf_counter()
        ans, kind = None, "miss"
        if cache:
            ans, kind, _ = cache.lookup(q, tenant=a.tenant, model=llm.name)
        if ans is None:
            ans = llm(q)
            llm_calls += 1
            if cache:
                cache.store(q, ans, tenant=a.tenant, model=llm.name)
        lat.append((time.perf_counter() - t0) * 1000)
        kinds.append(kind)
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{a.n} requests, LLM calls so far {llm_calls}")

    n = len(lat)
    hits = [ms for ms, k in zip(lat, kinds, strict=True) if k != "miss"]
    print("\n================ results ================")
    print(f"requests            : {n}")
    print(f"exact hits          : {kinds.count('exact')}")
    print(f"semantic hits       : {kinds.count('semantic')}")
    print(f"misses (LLM calls)  : {llm_calls}")
    print(f"hit rate            : {(n - llm_calls) / n:.0%}")
    print(f"latency p50 / p95   : {percentile(lat, 50):.0f} ms / {percentile(lat, 95):.0f} ms")
    if hits:
        print(f"cache-hit latency   : p50 {percentile(hits, 50):.1f} ms (embedding + vector search)")
    print(f"LLM spend           : ${llm_calls * PRICE_PER_CALL:.3f} vs ${n * PRICE_PER_CALL:.3f} without cache")
    if cache:
        print(f"cache errors        : {cache.stats['errors']} (fail-open fallbacks)")


if __name__ == "__main__":
    main()
