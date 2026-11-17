#!/usr/bin/env python3
"""Measure how long a write in one region takes to appear in the other.

Run it on a VM that can reach both endpoints (for example over VNet peering or a
second private endpoint). Point CACHE_HOST at the region you write to and
READ_HOST at the other region; every other CACHE_* variable is shared.

  READ_HOST=<other-region-host> python3 replication_check.py

Azure Managed Redis active geo-replication: both regions accept writes.
Memorystore cross-region replication: the secondary is read-only until you promote it.
"""
import os
import time
import uuid

from cache_client import connect

writer = connect(decode_responses=True)
os.environ["CACHE_HOST"] = os.environ["READ_HOST"]
reader = connect(decode_responses=True)

samples = []
for _ in range(10):
    key, value = f"geo-check:{uuid.uuid4()}", str(time.time())
    writer.set(key, value, ex=300)
    t = time.perf_counter()
    while reader.get(key) != value:
        if time.perf_counter() - t > 30:
            raise SystemExit("not replicated after 30 s; check the replication link")
        time.sleep(0.005)
    samples.append((time.perf_counter() - t) * 1000)
samples.sort()
print(f"replication lag over 10 writes: min {samples[0]:.0f} ms, median {samples[5]:.0f} ms, max {samples[-1]:.0f} ms")
