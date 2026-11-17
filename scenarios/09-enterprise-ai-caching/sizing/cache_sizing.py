#!/usr/bin/env python3
"""Estimate memory for an AI caching layer (semantic LLM cache + sessions + online features).

The numbers are planning estimates, not guarantees. Measure the real thing with
INFO memory / FT.INFO after loading a sample, then re-run this with corrected inputs.

Examples:
  python3 sizing/cache_sizing.py                                  # the Harbor & Pine Azure design
  python3 sizing/cache_sizing.py --entries 1000000 --dim 1536     # same, full-size embeddings
  python3 sizing/cache_sizing.py --entries 500000 --dim 768 --sessions 0 \
      --feature-keys 20000000 --feature-bytes 400                 # the Google Cloud design
"""
import argparse
import math

# Usable memory per SKU / node (GB). Azure figures are the advertised cache sizes;
# Google figures are the default writable keyspace per node. Check current docs.
AZURE_BALANCED = {"B0": 0.5, "B1": 1, "B3": 3, "B5": 6, "B10": 12, "B20": 24, "B50": 60, "B100": 120}
GCP_NODES = {"shared-core-nano": 1.12, "standard-small": 5.2, "highmem-medium": 10.4,
             "standard-large": 20.8, "highmem-xlarge": 46.4, "highmem-2xlarge": 88}


def gb(n_bytes):
    return n_bytes / 1e9


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entries", type=int, default=1_000_000, help="cached LLM answers kept at once")
    p.add_argument("--dim", type=int, default=512, help="embedding dimensions (float32)")
    p.add_argument("--hnsw-m", type=int, default=16, help="HNSW M (graph links per node)")
    p.add_argument("--prompt-bytes", type=int, default=300)
    p.add_argument("--response-bytes", type=int, default=1500)
    p.add_argument("--sessions", type=int, default=200_000, help="concurrent chat sessions")
    p.add_argument("--session-bytes", type=int, default=8_000, help="chat history kept per session")
    p.add_argument("--feature-keys", type=int, default=0, help="online feature records (users, products)")
    p.add_argument("--feature-bytes", type=int, default=400)
    p.add_argument("--key-overhead", type=int, default=120, help="per-key bookkeeping bytes")
    p.add_argument("--headroom", type=float, default=0.30,
                   help="free space to keep (growth, fragmentation, replication buffers)")
    a = p.parse_args()

    vec = a.dim * 4
    # Vectors are held twice: once in the hash, once inside the search index.
    # HNSW adds roughly 2*M neighbour ids (8 bytes each) per vector on layer 0.
    per_entry = 2 * vec + 2 * a.hnsw_m * 8 + a.prompt_bytes + a.response_bytes + 64 + a.key_overhead
    exact_key = 64 + 40 + a.key_overhead   # exact-match pointer key
    llm_cache = a.entries * (per_entry + exact_key)
    sessions = a.sessions * (a.session_bytes + a.key_overhead)
    features = a.feature_keys * (a.feature_bytes + a.key_overhead)
    data = llm_cache + sessions + features
    need = data / (1 - a.headroom)

    print(f"Per cached answer      : {per_entry + exact_key:,} bytes "
          f"(vector {vec:,} B x2, text {a.prompt_bytes + a.response_bytes:,} B)")
    print(f"Semantic LLM cache     : {gb(llm_cache):6.2f} GB  ({a.entries:,} entries, dim {a.dim})")
    print(f"Chat sessions          : {gb(sessions):6.2f} GB  ({a.sessions:,} sessions)")
    print(f"Online features        : {gb(features):6.2f} GB  ({a.feature_keys:,} records)")
    print(f"Data total             : {gb(data):6.2f} GB")
    print(f"Provision (with {a.headroom:.0%} free): {gb(need):6.2f} GB")
    print()

    az = next((k for k, v in AZURE_BALANCED.items() if v >= gb(need)), None)
    print(f"Azure Managed Redis    : Balanced {az or '> B100, consider Memory Optimized or Flash'}"
          f" ({AZURE_BALANCED.get(az, '?')} GB); add HA for production")
    for node, cap in GCP_NODES.items():
        if node == "shared-core-nano":
            continue
        shards = max(1, math.ceil(gb(need) / cap))
        if shards <= 12:
            print(f"Memorystore for Valkey : {shards} shard(s) x {node} ({cap} GB writable each)"
                  f" = {shards * cap:.1f} GB; x2 nodes with 1 replica per shard")
    print("\nTip: halving --dim (for example 1536 -> 512 with a model that supports shorter vectors)"
          " cuts the vector part by two thirds. Check answer quality before you do it.")


if __name__ == "__main__":
    main()
